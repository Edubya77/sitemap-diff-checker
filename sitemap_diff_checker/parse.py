"""Pure parsers for robots.txt and XML sitemaps.

URLs are stripped of surrounding whitespace and deduplicated in document order.
No URL normalization, resolution, or fetching is performed.
"""

from __future__ import annotations

from xml.etree import ElementTree


SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


def parse_robots(text: str) -> list[str]:
    """Return nonempty Sitemap declarations, ignoring case and comments."""
    urls = []
    for line in text.splitlines():
        declaration = line.split("#", 1)[0]
        name, separator, value = declaration.partition(":")
        if separator and name.strip().lower() == "sitemap":
            url = value.strip()
            if url:
                urls.append(url)
    return list(dict.fromkeys(urls))


def parse_urlset(xml: str | bytes) -> list[str]:
    """Return page locations from a URL set; raise ValueError for invalid XML/root."""
    return _parse_locations(xml, "urlset", "url")


def parse_sitemap_index(xml: str | bytes) -> list[str]:
    """Return sitemap locations from an index; raise ValueError for invalid XML/root."""
    return _parse_locations(xml, "sitemapindex", "sitemap")


def _parse_locations(xml: str | bytes, root_name: str, entry_name: str) -> list[str]:
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as error:
        raise ValueError(f"Malformed sitemap XML: {error}") from error

    if root.tag == root_name:
        prefix = ""
    elif root.tag == f"{{{SITEMAP_NAMESPACE}}}{root_name}":
        prefix = f"{{{SITEMAP_NAMESPACE}}}"
    else:
        raise ValueError(f"Expected sitemap root {root_name!r}, got {root.tag!r}")

    urls = []
    for location in root.findall(f"{prefix}{entry_name}/{prefix}loc"):
        url = (location.text or "").strip()
        if url:
            urls.append(url)
    return list(dict.fromkeys(urls))
