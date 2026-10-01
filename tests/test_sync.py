"""Unit tests for sync orchestration (diff, apply, resolve).

These tests are pure (no network) and never touch Steam or HeyBox.
"""

import unittest

from hey2steam import sync


class TestComputeDiff(unittest.TestCase):
    def setUp(self):
        self.hb = [
            {"appid": 1, "name": "A"},
            {"appid": 2, "name": "B"},
            {"appid": 3, "name": "C"},
        ]
        self.steam = [1, 4, 5]

    def test_bidirectional(self):
        d = sync.compute_diff(self.hb, self.steam, name_map={4: "D", 5: "E"})
        self.assertEqual([x["appid"] for x in d["heybox_only"]], [2, 3])
        self.assertEqual([x["appid"] for x in d["steam_only"]], [4, 5])
        self.assertEqual(d["both_count"], 1)
        self.assertEqual(d["heybox_total"], 3)
        self.assertEqual(d["steam_total"], 3)

    def test_name_map_fills_steam_only_names(self):
        d = sync.compute_diff(self.hb, self.steam, name_map={4: "D", 5: "E"})
        self.assertEqual(d["steam_only"][0]["name"], "D")
        self.assertEqual(d["steam_only"][1]["name"], "E")

    def test_no_diff(self):
        d = sync.compute_diff([{"appid": 1, "name": "A"}], [1])
        self.assertEqual(d["heybox_only"], [])
        self.assertEqual(d["steam_only"], [])
        self.assertEqual(d["both_count"], 1)

    def test_empty_both(self):
        d = sync.compute_diff([], [])
        self.assertEqual(d["heybox_only"], [])
        self.assertEqual(d["steam_only"], [])
        self.assertEqual(d["both_count"], 0)


class TestApplyChanges(unittest.TestCase):
    def test_dry_run_does_not_touch_steam(self):
        r = sync.apply_changes(
            [{"appid": 2, "name": "B"}],
            [{"appid": 4, "name": "D"}],
            None,
            dry_run=True,
        )
        self.assertEqual(len(r["added"]), 1)
        self.assertEqual(len(r["removed"]), 1)
        self.assertEqual(r["failed_add"], [])
        self.assertEqual(r["failed_remove"], [])

    def test_missing_token_fails_per_item_without_writing(self):
        # Without an access token, add_to_wishlist raises before any request
        # is sent, so this is safe and never modifies Steam.
        r = sync.apply_changes([{"appid": 2, "name": "B"}], [], None, dry_run=False)
        self.assertEqual(len(r["added"]), 0)
        self.assertEqual(len(r["failed_add"]), 1)

    def test_missing_token_fails_remove_without_writing(self):
        r = sync.apply_changes([], [{"appid": 4, "name": "D"}], None, dry_run=False)
        self.assertEqual(len(r["removed"]), 0)
        self.assertEqual(len(r["failed_remove"]), 1)


class TestResolveAppids(unittest.TestCase):
    def test_explicit_mixed_list(self):
        ids = sync.resolve_appids([1, "2", {"appid": 3}, {"appid": "4"}], None)
        self.assertEqual(ids, [1, 2, 3, 4])

    def test_invalid_entries_skipped(self):
        ids = sync.resolve_appids([1, "x", None, {"appid": 5}], None)
        self.assertEqual(ids, [1, 5])

    def test_none_returns_empty(self):
        self.assertEqual(sync.resolve_appids(None, None), [])


class TestBuildNameMap(unittest.TestCase):
    def test_from_dicts(self):
        m = sync.build_name_map([{"appid": 1, "name": "A"}, {"appid": 2, "name": "B"}])
        self.assertEqual(m, {1: "A", 2: "B"})

    def test_empty(self):
        self.assertEqual(sync.build_name_map(None), {})


if __name__ == "__main__":
    unittest.main()
