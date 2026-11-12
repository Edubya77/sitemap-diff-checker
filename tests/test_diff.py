"""Run with: python3 -m unittest discover -v."""

import unittest

from sitemap_diff_checker.diff import diff_urls


class DiffUrlsTests(unittest.TestCase):
    def test_added_and_removed(self):
        previous = ["https://a/", "https://b/", "https://c/"]
        current = ["https://b/", "https://c/", "https://d/"]
        self.assertEqual(
            diff_urls(previous, current),
            {"added": ["https://d/"], "removed": ["https://a/"]},
        )

    def test_result_has_exactly_added_and_removed_keys(self):
        result = diff_urls([], [])
        self.assertEqual(set(result), {"added", "removed"})
        self.assertEqual(result["added"], [])
        self.assertEqual(result["removed"], [])

    def test_empty_inputs(self):
        self.assertEqual(diff_urls([], []), {"added": [], "removed": []})
        self.assertEqual(diff_urls(["x"], []), {"added": [], "removed": ["x"]})
        self.assertEqual(diff_urls([], ["x"]), {"added": ["x"], "removed": []})

    def test_duplicates_do_not_change_results(self):
        previous = ["https://a/", "https://a/", "https://b/"]
        current = ["https://a/", "https://a/", "https://b/"]
        self.assertEqual(diff_urls(previous, current), {"added": [], "removed": []})

    def test_results_are_distinct_and_lexicographically_sorted(self):
        previous = ["https://b/", "https://a/", "https://a/", "https://z/"]
        current = []
        self.assertEqual(
            diff_urls(previous, current),
            {"added": [], "removed": ["https://a/", "https://b/", "https://z/"]},
        )

    def test_one_shot_iterables_and_generators(self):
        previous = (x for x in ["https://a/", "https://b/"])
        current = iter(["https://b/", "https://c/"])
        self.assertEqual(
            diff_urls(previous, current),
            {"added": ["https://c/"], "removed": ["https://a/"]},
        )

    def test_caller_lists_are_not_mutated(self):
        previous = ["https://b/", "https://a/"]
        current = ["https://a/", "https://c/"]
        previous_snapshot = list(previous)
        current_snapshot = list(current)
        diff_urls(previous, current)
        self.assertEqual(previous, previous_snapshot)
        self.assertEqual(current, current_snapshot)

    def test_strings_compared_literally_without_normalization(self):
        # Whitespace, case, and scheme differences are treated as distinct.
        self.assertEqual(
            diff_urls([" https://a/"], ["https://a/"]),
            {"added": ["https://a/"], "removed": [" https://a/"]},
        )
        self.assertEqual(
            diff_urls(["HTTPS://A/"], ["https://a/"]),
            {"added": ["https://a/"], "removed": ["HTTPS://A/"]},
        )

    def test_identical_inputs_produce_no_changes(self):
        urls = ["https://a/", "https://b/"]
        self.assertEqual(
            diff_urls(urls, urls),
            {"added": [], "removed": []},
        )


if __name__ == "__main__":
    unittest.main()
