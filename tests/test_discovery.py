import unittest
from unittest.mock import patch

from sitemap_diff_checker.discovery import ROBOTS_MAX_BYTES, discover_sitemaps
from sitemap_diff_checker.fetch import FetchError


class DiscoveryTests(unittest.TestCase):
    @patch("sitemap_diff_checker.discovery.fetch_bytes")
    def test_robots_declarations(self, fetch):
        cases = (
            (b"User-agent: *\nSitemap: https://example.com/map.xml", ["https://example.com/map.xml"]),
            (b"Sitemap: https://example.com/a.xml\nSitemap: https://other.example/b.xml\n"
             b"Sitemap: https://example.com/a.xml", ["https://example.com/a.xml", "https://other.example/b.xml"]),
            (b"\xef\xbb\xbfsItEmAp: https://example.com/map.xml # comment", ["https://example.com/map.xml"]),
            (b"User-agent: *\nDisallow: /", []),
            (b"", []),
        )
        for content, expected in cases:
            with self.subTest(content=content):
                fetch.return_value = content
                self.assertEqual(discover_sitemaps("https://example.com/path?query#fragment"), expected)
                fetch.assert_called_with("https://example.com/robots.txt", timeout=10.0, max_bytes=ROBOTS_MAX_BYTES)

    @patch("sitemap_diff_checker.discovery.fetch_bytes")
    def test_origin_port_and_custom_limits(self, fetch):
        fetch.return_value = b""
        discover_sitemaps("http://example.com:8080/path", timeout=3, max_bytes=100)
        fetch.assert_called_once_with("http://example.com:8080/robots.txt", timeout=3, max_bytes=100)

    @patch("sitemap_diff_checker.discovery.fetch_bytes")
    def test_invalid_declaration(self, fetch):
        for declaration in (b"/relative.xml", b"file:///tmp/map.xml"):
            with self.subTest(declaration=declaration):
                fetch.return_value = b"Sitemap: " + declaration
                with self.assertRaises(FetchError):
                    discover_sitemaps("https://example.com")

    @patch("sitemap_diff_checker.discovery.fetch_bytes")
    def test_fetch_failure_propagates_without_fallback(self, fetch):
        fetch.side_effect = FetchError("HTTP response was not successful: 404")
        with self.assertRaisesRegex(FetchError, "404"):
            discover_sitemaps("https://example.com")
        fetch.assert_called_once()
