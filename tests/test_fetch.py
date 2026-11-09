"""Transport tests use in-memory responses and never access the network."""

import gzip
from io import BytesIO
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

from sitemap_diff_checker.fetch import FetchError, _HTTPOnlyRedirects, fetch_bytes
from sitemap_diff_checker.parse import parse_urlset


URL = "https://example.com/sitemap.xml"


class FetchTests(unittest.TestCase):
    def setUp(self):
        patcher = patch("sitemap_diff_checker.fetch.build_opener")
        self.opener = patcher.start().return_value
        self.addCleanup(patcher.stop)

    def response(self, body, *, headers=None, status=200):
        response = BytesIO(body)
        response.status = status
        response.headers = headers or {}
        self.opener.open.return_value = response
        return response

    def test_success_and_transport_options(self):
        response = self.response(b"<urlset/>")
        self.assertEqual(fetch_bytes(URL, timeout=2), b"<urlset/>")
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, URL)
        self.assertEqual(request.get_header("Accept-encoding"), "gzip")
        self.assertEqual(self.opener.open.call_args.kwargs, {"timeout": 2})
        self.assertTrue(response.closed)

    def test_http_failure(self):
        for code in (404, 500):
            with self.subTest(code=code):
                body = BytesIO(b"failure")
                self.opener.open.side_effect = HTTPError(URL, code, "failure", {}, body)
                with self.assertRaisesRegex(FetchError, str(code)):
                    fetch_bytes(URL)
                self.assertTrue(body.closed)

    def test_non_success_response(self):
        self.response(b"redirect", status=304)
        with self.assertRaisesRegex(FetchError, "304"):
            fetch_bytes(URL)

    def test_timeout_and_network_failure(self):
        for error in (TimeoutError("timed out"), URLError("DNS failure"),
                      ConnectionResetError("reset")):
            with self.subTest(error=error):
                self.opener.open.side_effect = error
                with self.assertRaisesRegex(FetchError, "Network failure or timeout") as caught:
                    fetch_bytes(URL)
                self.assertIs(caught.exception.__cause__, error)

    def test_read_timeout(self):
        response = Mock()
        response.status = 200
        response.headers = {}
        response.read.side_effect = TimeoutError("read timed out")
        self.opener.open.return_value.__enter__.return_value = response
        with self.assertRaisesRegex(FetchError, "timeout"):
            fetch_bytes(URL)

    def test_invalid_urls_fail_before_network_access(self):
        for url, message in (("", "Malformed"), ("example.com/map.xml", "Malformed"),
                             ("https:///map.xml", "Malformed"),
                             ("https://example.com:bad/", "Malformed"),
                             ("https://[invalid/", "Malformed"),
                             ("https://example.com/a b", "Malformed"),
                             ("https://example.com/café", "Malformed"),
                             ("https://example.com/\x7f", "Malformed"),
                             ("https://user:password@example.com/", "Malformed"),
                             ("file:///tmp/map.xml", "Unsupported"),
                             ("ftp://example.com/map.xml", "Unsupported")):
            with self.subTest(url=url), self.assertRaisesRegex(FetchError, message):
                fetch_bytes(url)
        self.opener.open.assert_not_called()

    def test_redirect_scheme_is_validated(self):
        handler = _HTTPOnlyRedirects()
        for target in ("file:///tmp/map.xml", "ftp://example.com/map.xml"):
            with self.subTest(target=target), self.assertRaisesRegex(FetchError, "Unsupported"):
                handler.redirect_request(Request(URL), None, 302, "Found", {}, target)
        redirected = handler.redirect_request(
            Request(URL), None, 302, "Found", {}, "https://other.example/map.xml",
        )
        self.assertEqual(redirected.full_url, "https://other.example/map.xml")

    def test_gzip_header_or_file_magic_and_parser_integration(self):
        xml = b"<urlset><url><loc>https://example.com/</loc></url></urlset>"
        for headers, url in (({"Content-Encoding": "GZip"}, URL),
                             ({}, URL + ".gz"), ({}, URL)):
            with self.subTest(headers=headers, url=url):
                self.response(gzip.compress(xml), headers=headers)
                self.assertEqual(parse_urlset(fetch_bytes(url)), ["https://example.com/"])

    def test_invalid_gzip(self):
        for content in (b"not gzip", gzip.compress(b"payload")[:-4]):
            with self.subTest(content=content):
                self.response(content, headers={"Content-Encoding": "gzip"})
                with self.assertRaisesRegex(FetchError, "Invalid gzip"):
                    fetch_bytes(URL)

    def test_unsupported_content_encoding(self):
        self.response(b"content", headers={"Content-Encoding": "br"})
        with self.assertRaisesRegex(FetchError, "Unsupported Content-Encoding"):
            fetch_bytes(URL)

    def test_download_limit_without_content_length(self):
        for size in (9, 10, 11):
            with self.subTest(size=size):
                self.response(b"x" * size)
                if size <= 10:
                    self.assertEqual(fetch_bytes(URL, max_bytes=10), b"x" * size)
                else:
                    with self.assertRaisesRegex(FetchError, "size limit"):
                        fetch_bytes(URL, max_bytes=10)

    def test_gzip_expansion_limit(self):
        self.response(gzip.compress(b"x" * 1000))
        with self.assertRaisesRegex(FetchError, "size limit"):
            fetch_bytes(URL, max_bytes=100)

    def test_invalid_limits(self):
        for kwargs in ({"timeout": 0}, {"timeout": float("inf")},
                       {"max_bytes": 0}, {"max_bytes": 1.5}, {"max_bytes": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                fetch_bytes(URL, **kwargs)
        self.opener.open.assert_not_called()
