import unittest

from utils.relevance_scoring import compute_relevance_score, score_to_label


class TestRelevanceScoring(unittest.TestCase):
    def setUp(self):
        self.weights = {
            "exact_title_match": 50,
            "token_match": 10,
            "positive_keyword": 5,
            "negative_keyword": -15,
            "unrelated_keyword": -8,
            "recent_click_title": 6,
            "recent_click_shop": 4,
        }
        self.buckets = {"strong": 60, "medium": 30}

    def test_exact_title_match_boost(self):
        score, tokens = compute_relevance_score(
            title="桔梗 対応衣装",
            shop_name="shop",
            avatar_name="桔梗",
            positive_keywords=["対応"],
            negative_keywords=[],
            unrelated_keywords=[],
            score_weights=self.weights,
        )
        self.assertGreaterEqual(score, 50)
        self.assertTrue(tokens)

    def test_negative_keyword_penalty(self):
        score, _ = compute_relevance_score(
            title="桔梗 汎用 衣装",
            shop_name="shop",
            avatar_name="桔梗",
            positive_keywords=[],
            negative_keywords=["汎用"],
            unrelated_keywords=[],
            score_weights=self.weights,
        )
        self.assertLess(score, 50)

    def test_positive_keyword_boost(self):
        score, _ = compute_relevance_score(
            title="桔梗 対応",
            shop_name="shop",
            avatar_name="桔梗",
            positive_keywords=["対応"],
            negative_keywords=[],
            unrelated_keywords=[],
            score_weights=self.weights,
        )
        self.assertGreater(score, 50)

    def test_recent_click_title_boost(self):
        score, _ = compute_relevance_score(
            title="マヌカ 冬服",
            shop_name="shop",
            avatar_name="マヌカ",
            positive_keywords=[],
            negative_keywords=[],
            unrelated_keywords=[],
            score_weights=self.weights,
            recent_clicked_titles=["겨울", "겨울服", "冬服"],
        )
        self.assertGreaterEqual(score, self.weights["recent_click_title"])

    def test_score_to_label(self):
        self.assertEqual(score_to_label(70, self.buckets), "매칭 강함")
        self.assertEqual(score_to_label(40, self.buckets), "매칭 보통")
        self.assertEqual(score_to_label(10, self.buckets), "매칭 약함")


if __name__ == "__main__":
    unittest.main()
