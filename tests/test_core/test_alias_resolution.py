import unittest
from unittest.mock import patch

from data.avatar_aliases import build_alias_map
from utils.query_normalize import normalize_query


class TestAliasResolution(unittest.TestCase):
    def test_alias_map_resolves(self):
        aliases = {"桔梗": ["ききょう", "キキョウ"]}
        with patch("data.avatar_aliases.load_avatar_aliases", return_value=aliases):
            alias_map = build_alias_map(normalize_query)

        self.assertEqual(alias_map.get(normalize_query("ききょう")), "桔梗")
        self.assertEqual(alias_map.get(normalize_query("キキョウ")), "桔梗")


if __name__ == "__main__":
    unittest.main()
