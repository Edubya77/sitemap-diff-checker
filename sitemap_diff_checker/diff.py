"""Pure diff logic for comparing sitemap URL sets.

Input URLs are compared literally: no normalization, whitespace stripping,
fetching, or validation is performed. Results are distinct and sorted.
"""

from __future__ import annotations

from collections.abc import Iterable


def diff_urls(previous: Iterable[str], current: Iterable[str]) -> dict[str, list[str]]:
    """Return added and removed URLs between two URL sets.

    Each key maps to a lexicographically sorted list of distinct strings.
    Inputs are compared literally and may be one-shot iterables; caller
    collections are not mutated.
    """
    previous_set = set(previous)
    current_set = set(current)
    return {
        "added": sorted(current_set - previous_set),
        "removed": sorted(previous_set - current_set),
    }
