"""
검색 결과 내보내기

CSV, JSON 형식 지원
"""

import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from models.search_result import SearchResult
from models.booth_item import BoothItem
from utils.logging import get_logger

logger = get_logger(__name__)


class ResultExporter:
    """
    검색 결과 내보내기

    사용법:
        exporter = ResultExporter()

        # CSV 내보내기
        exporter.export_csv(result, path)

        # JSON 내보내기
        exporter.export_json(result, path)
    """

    @staticmethod
    def export_csv(result: SearchResult, path: Path, include_header: bool = True) -> bool:
        """
        검색 결과를 CSV로 내보내기

        Args:
            result: 검색 결과
            path: 저장 경로
            include_header: 헤더 포함 여부

        Returns:
            성공 여부
        """
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)

                if include_header:
                    writer.writerow([
                        "ID",
                        "이름",
                        "가격",
                        "가격(숫자)",
                        "URL",
                        "썸네일",
                        "판매자",
                        "좋아요",
                    ])

                for item in result.items:
                    writer.writerow([
                        item.id,
                        item.name,
                        item.price_text,
                        item.price_value or "",
                        item.url,
                        item.thumbnail_url,
                        item.shop_name,
                        item.likes,
                    ])

            logger.info(f"CSV 내보내기 완료: {path} ({len(result.items)}개)")
            return True

        except Exception as e:
            logger.error(f"CSV 내보내기 실패: {e}")
            return False

    @staticmethod
    def export_json(result: SearchResult, path: Path, pretty: bool = True) -> bool:
        """
        검색 결과를 JSON으로 내보내기

        Args:
            result: 검색 결과
            path: 저장 경로
            pretty: 들여쓰기 여부

        Returns:
            성공 여부
        """
        try:
            data = {
                "exported_at": datetime.now().isoformat(),
                "query": result.query,
                "total_count": result.total_count,
                "current_page": result.current_page,
                "total_pages": result.total_pages,
                "items_count": len(result.items),
                "items": [item.to_dict() for item in result.items],
            }

            with open(path, "w", encoding="utf-8") as f:
                if pretty:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                else:
                    json.dump(data, f, ensure_ascii=False)

            logger.info(f"JSON 내보내기 완료: {path} ({len(result.items)}개)")
            return True

        except Exception as e:
            logger.error(f"JSON 내보내기 실패: {e}")
            return False

    @staticmethod
    def export_items_csv(items: List[BoothItem], path: Path) -> bool:
        """아이템 목록을 CSV로 내보내기"""
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "ID", "이름", "가격", "가격(숫자)", "URL", "썸네일", "판매자", "좋아요"
                ])
                for item in items:
                    writer.writerow([
                        item.id,
                        item.name,
                        item.price_text,
                        item.price_value or "",
                        item.url,
                        item.thumbnail_url,
                        item.shop_name,
                        item.likes,
                    ])
            logger.info(f"아이템 CSV 내보내기: {path} ({len(items)}개)")
            return True
        except Exception as e:
            logger.error(f"아이템 CSV 내보내기 실패: {e}")
            return False

    @staticmethod
    def export_items_json(items: List[BoothItem], path: Path) -> bool:
        """아이템 목록을 JSON으로 내보내기"""
        try:
            data = {
                "exported_at": datetime.now().isoformat(),
                "count": len(items),
                "items": [item.to_dict() for item in items],
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"아이템 JSON 내보내기: {path} ({len(items)}개)")
            return True
        except Exception as e:
            logger.error(f"아이템 JSON 내보내기 실패: {e}")
            return False


def get_default_export_filename(query: str, format: str) -> str:
    """기본 내보내기 파일명 생성"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = "".join(c if c.isalnum() or c in "._-" else "_" for c in query)
    return f"booth_{safe_query}_{timestamp}.{format}"
