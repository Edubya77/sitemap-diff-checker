# Sitemap Diff Checker

CLI tool that:
1. Fetches robots.txt for a target site.
2. Discovers sitemap URLs.
3. Fetches and parses sitemap(s).
4. Compares discovered sitemap URLs against prior or reference state.
5. Reports additions, removals, inconsistencies, and useful diagnostics.

Initial goal:
- Small, reliable CLI
- Clear human-readable output
- Machine-readable output later
- Good tests
- Minimal dependencies

## Implemented library slice

Pure parsers in `sitemap_diff_checker.parse` handle robots.txt declarations,
XML URL sets, and sitemap indexes. `discovery.discover_sitemaps(site_url)` fetches
the origin's `/robots.txt` and returns unique absolute HTTP/HTTPS sitemap
declarations in document order. Directive names are case-insensitive, comments
are ignored, and multiple declarations (including cross-origin URLs) are supported.
Robots text uses UTF-8 with BOM support and replacement of invalid bytes.

No declarations means an empty list. The MVP has no documented fallback policy,
so this increment does not guess `/sitemap.xml` or other paths. A missing or
unavailable robots.txt raises a fetch error; it is not treated as an empty file.
Invalid or unsupported declared URLs also raise an error.

`fetch.fetch_bytes(url)` downloads an individual HTTP/HTTPS resource for a parser
to consume. It supports gzip HTTP responses and gzip files identified by their
magic bytes, with or without a `.gz` suffix. It uses only the Python standard
library, follows urllib's bounded HTTP/HTTPS redirects, and rejects credentials
in URLs. HTTPS uses the standard library's default certificate verification.
Non-ASCII URLs must use IDNA hostnames and percent-encoded paths/queries.
Only successful 2xx responses are accepted. URL, HTTP, connection/timeout,
unsupported content encoding, invalid gzip, and size failures raise `FetchError`.

The default socket timeout is 10 seconds per blocking operation (not an overall
deadline). Downloads and decompressed content are each limited to 10 MiB;
discovery uses a 512 KiB robots limit. Callers may override `timeout` and
`max_bytes`. Limits are enforced while reading, independently of Content-Length.
HTTP access may use the standard library's environment proxy configuration.

```python
from sitemap_diff_checker.discovery import discover_sitemaps
from sitemap_diff_checker.fetch import fetch_bytes
from sitemap_diff_checker.parse import parse_urlset

sitemap_urls = discover_sitemaps("https://example.com")
# For a known URL-set sitemap (use parse_sitemap_index for a known index):
# page_urls = parse_urlset(fetch_bytes(sitemap_urls[0]))
```

Recursive traversal, snapshots, comparison, and the final CLI are not implemented.

Run the tests without public internet access:

```sh
python3 -m unittest discover -v
```
