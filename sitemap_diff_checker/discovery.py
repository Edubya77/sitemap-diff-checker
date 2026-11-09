"""Fetch a site's robots.txt and discover declared sitemap URLs."""

from urllib.parse import urlsplit, urlunsplit

from sitemap_diff_checker.fetch import DEFAULT_TIMEOUT, fetch_bytes, validate_url
from sitemap_diff_checker.parse import parse_robots


ROBOTS_MAX_BYTES = 512 * 1024


def discover_sitemaps(
    site_url: str, *, timeout: float = DEFAULT_TIMEOUT, max_bytes: int = ROBOTS_MAX_BYTES,
) -> list[str]:
    """Return unique declarations in source order; do not guess fallback paths.

    Always request /robots.txt at the supplied origin, regardless of the input
    path. Decode robots as UTF-8, tolerate invalid bytes, and strip a UTF-8 BOM.
    Declarations are validated as absolute HTTP(S) URLs before being returned;
    they may point at another origin. Missing robots files remain HTTP errors.
    """
    parts = urlsplit(validate_url(site_url))
    robots_url = urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
    content = fetch_bytes(robots_url, timeout=timeout, max_bytes=max_bytes)
    urls = parse_robots(content.decode("utf-8-sig", errors="replace"))
    for url in urls:
        validate_url(url)
    return urls
