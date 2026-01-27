import unittest

from core.search_service import SearchService
from models.search_params import SearchParams
from models.search_result import SearchResult
from models.booth_item import BoothItem
from utils.query_normalize import normalize_query


class SearchServiceStub(SearchService):
    def __init__(self, responses, alias_map=None):
        self._responses = responses
        self._alias_map = alias_map or {}
        self._calls = []
        self._detail_verify_cache = {}
        self._detail_cache_ttl = 0

    def search(self, params: SearchParams, use_cache: bool = True) -> SearchResult:
        self._calls.append(params.avatar_name)
        count = self._responses.get(params.avatar_name, 0)
        items = [
            BoothItem(
                id=str(i),
                name=f"item{i}",
                price_text="¥0",
                url="",
                thumbnail_url="",
            )
            for i in range(count)
        ]
        return SearchResult(
            items=items,
            total_count=count,
            current_page=1,
            total_pages=1,
            has_next=False,
            query=params.avatar_name,
        )


class TestSearchFallback(unittest.TestCase):
    def test_fallback_stops_on_normalized(self):
        responses = {"A   B": 0, "A B": 6}
        service = SearchServiceStub(responses)
        params = SearchParams(
            avatar_name="A   B",
            raw_query="A   B",
            normalize_enabled=True,
            alias_enabled=False,
            fallback_enabled=True,
            fallback_min_results=5,
        )

        result = service.search_with_fallback(params)

        self.assertEqual(service._calls, ["A   B", "A B"])
        self.assertEqual(result.used_strategy, "normalized")
        self.assertEqual(result.attempts_count, 2)

    def test_fallback_cap_applies(self):
        alias_map = {normalize_query("A  B"): "AliasName"}
        responses = {"A  B": 0, "A B": 0, "AliasName": 0, "AB": 10}
        service = SearchServiceStub(responses, alias_map=alias_map)
        params = SearchParams(
            avatar_name="A  B",
            raw_query="A  B",
            normalize_enabled=True,
            alias_enabled=True,
            fallback_enabled=True,
            fallback_min_results=5,
        )

        result = service.search_with_fallback(params, max_attempts=3)

        self.assertEqual(service._calls, ["A  B", "A B", "AliasName"])
        self.assertNotIn("AB", service._calls)
        self.assertEqual(result.attempts_count, 3)

    def test_cancel_short_circuits(self):
        responses = {"A  B": 0, "A B": 0}
        service = SearchServiceStub(responses)
        params = SearchParams(
            avatar_name="A  B",
            raw_query="A  B",
            normalize_enabled=True,
            alias_enabled=True,
            fallback_enabled=True,
            fallback_min_results=5,
        )

        calls = {"count": 0}

        def cancel_check():
            calls["count"] += 1
            return calls["count"] >= 2

        result = service.search_with_fallback(params, cancel_check=cancel_check)

        self.assertEqual(service._calls, ["A  B"])
        self.assertEqual(result.attempts_count, 1)


if __name__ == "__main__":
    unittest.main()
