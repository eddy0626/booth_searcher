"""
즐겨찾기 데이터 모델 및 저장소
"""

import sqlite3
import json
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

from models.booth_item import BoothItem
from utils.paths import get_data_dir
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FavoriteItem:
    """즐겨찾기 아이템"""
    item_id: str
    name: str
    price_text: str
    url: str
    thumbnail_url: str
    shop_name: str
    memo: str = ""
    tags: List[str] = field(default_factory=list)
    added_at: datetime = field(default_factory=datetime.now)
    price_value: Optional[int] = None

    @classmethod
    def from_booth_item(cls, item: BoothItem, memo: str = "") -> "FavoriteItem":
        """BoothItem에서 생성"""
        return cls(
            item_id=item.id,
            name=item.name,
            price_text=item.price_text,
            price_value=item.price_value,
            url=item.url,
            thumbnail_url=item.thumbnail_url,
            shop_name=item.shop_name,
            memo=memo,
        )

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "item_id": self.item_id,
            "name": self.name,
            "price_text": self.price_text,
            "price_value": self.price_value,
            "url": self.url,
            "thumbnail_url": self.thumbnail_url,
            "shop_name": self.shop_name,
            "memo": self.memo,
            "tags": self.tags,
            "added_at": self.added_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FavoriteItem":
        """딕셔너리에서 생성"""
        added_at = datetime.now()
        if data.get("added_at"):
            try:
                added_at = datetime.fromisoformat(data["added_at"])
            except ValueError:
                pass

        return cls(
            item_id=data.get("item_id", ""),
            name=data.get("name", ""),
            price_text=data.get("price_text", ""),
            price_value=data.get("price_value"),
            url=data.get("url", ""),
            thumbnail_url=data.get("thumbnail_url", ""),
            shop_name=data.get("shop_name", ""),
            memo=data.get("memo", ""),
            tags=data.get("tags", []),
            added_at=added_at,
        )


class FavoritesStorage:
    """
    즐겨찾기 저장소 (SQLite)

    사용법:
        storage = FavoritesStorage()

        # 즐겨찾기 추가
        storage.add(booth_item)

        # 즐겨찾기 확인
        if storage.is_favorite(item_id):
            ...

        # 즐겨찾기 목록
        favorites = storage.get_all()

        # 내보내기
        storage.export_json(path)
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = get_data_dir() / "favorites.db"

        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        self._init_db()
        logger.info(f"FavoritesStorage 초기화: {db_path}")

    def _init_db(self) -> None:
        """데이터베이스 초기화"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    item_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    price_text TEXT,
                    price_value INTEGER,
                    url TEXT,
                    thumbnail_url TEXT,
                    shop_name TEXT,
                    memo TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    added_at TEXT NOT NULL
                )
            """)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """스레드 안전한 연결"""
        conn = sqlite3.connect(str(self._db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def add(self, item: BoothItem, memo: str = "") -> bool:
        """즐겨찾기 추가"""
        favorite = FavoriteItem.from_booth_item(item, memo)

        with self._lock:
            with self._get_connection() as conn:
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO favorites
                        (item_id, name, price_text, price_value, url, thumbnail_url, shop_name, memo, tags, added_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        favorite.item_id,
                        favorite.name,
                        favorite.price_text,
                        favorite.price_value,
                        favorite.url,
                        favorite.thumbnail_url,
                        favorite.shop_name,
                        favorite.memo,
                        json.dumps(favorite.tags),
                        favorite.added_at.isoformat(),
                    ))
                    conn.commit()
                    logger.debug(f"즐겨찾기 추가: {favorite.name}")
                    return True
                except sqlite3.Error as e:
                    logger.error(f"즐겨찾기 추가 실패: {e}")
                    return False

    def remove(self, item_id: str) -> bool:
        """즐겨찾기 제거"""
        with self._lock:
            with self._get_connection() as conn:
                try:
                    cursor = conn.execute(
                        "DELETE FROM favorites WHERE item_id = ?",
                        (item_id,)
                    )
                    conn.commit()
                    removed = cursor.rowcount > 0
                    if removed:
                        logger.debug(f"즐겨찾기 제거: {item_id}")
                    return removed
                except sqlite3.Error as e:
                    logger.error(f"즐겨찾기 제거 실패: {e}")
                    return False

    def is_favorite(self, item_id: str) -> bool:
        """즐겨찾기 여부 확인"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM favorites WHERE item_id = ?",
                (item_id,)
            )
            return cursor.fetchone() is not None

    def get(self, item_id: str) -> Optional[FavoriteItem]:
        """즐겨찾기 아이템 조회"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM favorites WHERE item_id = ?",
                (item_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_favorite(row)
            return None

    def get_all(self, order_by: str = "added_at DESC") -> List[FavoriteItem]:
        """모든 즐겨찾기 조회"""
        allowed_orders = ["added_at DESC", "added_at ASC", "name ASC", "name DESC", "price_value ASC", "price_value DESC"]
        if order_by not in allowed_orders:
            order_by = "added_at DESC"

        with self._get_connection() as conn:
            cursor = conn.execute(f"SELECT * FROM favorites ORDER BY {order_by}")
            return [self._row_to_favorite(row) for row in cursor.fetchall()]

    def get_count(self) -> int:
        """즐겨찾기 개수"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM favorites")
            return cursor.fetchone()[0]

    def update_memo(self, item_id: str, memo: str) -> bool:
        """메모 업데이트"""
        with self._lock:
            with self._get_connection() as conn:
                try:
                    cursor = conn.execute(
                        "UPDATE favorites SET memo = ? WHERE item_id = ?",
                        (memo, item_id)
                    )
                    conn.commit()
                    return cursor.rowcount > 0
                except sqlite3.Error as e:
                    logger.error(f"메모 업데이트 실패: {e}")
                    return False

    def clear(self) -> int:
        """모든 즐겨찾기 삭제"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM favorites")
                conn.commit()
                count = cursor.rowcount
                logger.info(f"즐겨찾기 {count}개 삭제")
                return count

    def _row_to_favorite(self, row: sqlite3.Row) -> FavoriteItem:
        """DB 행을 FavoriteItem으로 변환"""
        tags = []
        try:
            tags = json.loads(row["tags"])
        except (json.JSONDecodeError, TypeError):
            pass

        added_at = datetime.now()
        try:
            added_at = datetime.fromisoformat(row["added_at"])
        except (ValueError, TypeError):
            pass

        return FavoriteItem(
            item_id=row["item_id"],
            name=row["name"],
            price_text=row["price_text"] or "",
            price_value=row["price_value"],
            url=row["url"] or "",
            thumbnail_url=row["thumbnail_url"] or "",
            shop_name=row["shop_name"] or "",
            memo=row["memo"] or "",
            tags=tags,
            added_at=added_at,
        )

    def export_json(self, path: Path) -> bool:
        """JSON으로 내보내기"""
        try:
            favorites = self.get_all()
            data = {
                "exported_at": datetime.now().isoformat(),
                "count": len(favorites),
                "favorites": [f.to_dict() for f in favorites],
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"즐겨찾기 JSON 내보내기: {path}")
            return True
        except Exception as e:
            logger.error(f"JSON 내보내기 실패: {e}")
            return False

    def export_csv(self, path: Path) -> bool:
        """CSV로 내보내기"""
        import csv
        try:
            favorites = self.get_all()
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "이름", "가격", "URL", "판매자", "메모", "추가일"])
                for fav in favorites:
                    writer.writerow([
                        fav.item_id,
                        fav.name,
                        fav.price_text,
                        fav.url,
                        fav.shop_name,
                        fav.memo,
                        fav.added_at.strftime("%Y-%m-%d %H:%M"),
                    ])
            logger.info(f"즐겨찾기 CSV 내보내기: {path}")
            return True
        except Exception as e:
            logger.error(f"CSV 내보내기 실패: {e}")
            return False


# 전역 인스턴스
_favorites_storage: Optional[FavoritesStorage] = None
_storage_lock = threading.Lock()


def get_favorites_storage() -> FavoritesStorage:
    """전역 즐겨찾기 저장소 반환"""
    global _favorites_storage
    if _favorites_storage is None:
        with _storage_lock:
            if _favorites_storage is None:
                _favorites_storage = FavoritesStorage()
    return _favorites_storage
