import unittest

from utils.query_normalize import normalize_query, parse_multi_query


class TestQueryNormalization(unittest.TestCase):
    def test_trim_and_collapse_whitespace(self):
        self.assertEqual(
            normalize_query("  セレスティア   マヌカ  "),
            "セレスティア マヌカ",
        )

    def test_full_width_to_half_width(self):
        self.assertEqual(normalize_query("ＡＢＣ１２３"), "ABC123")

    def test_middle_dot_to_space(self):
        self.assertEqual(normalize_query("セレスティア・マヌカ"), "セレスティア マヌカ")

    def test_full_width_space(self):
        self.assertEqual(normalize_query("セレスティア　マヌカ"), "セレスティア マヌカ")

    def test_japanese_quotes(self):
        self.assertEqual(normalize_query("「桔梗」"), '"桔梗"')

    def test_parse_multi_query(self):
        result = parse_multi_query("  桔梗 , セレスティア\nマヌカ/桔梗 ")
        self.assertEqual(result, ["桔梗", "セレスティア", "マヌカ"])


if __name__ == "__main__":
    unittest.main()
