"""Run with: python3 -m unittest discover -v."""

from pathlib import Path
import unittest

from sitemap_diff_checker.parse import (
    parse_robots,
    parse_sitemap_index,
    parse_urlset,
)


FIXTURES = Path(__file__).parent / "fixtures"
NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


class RobotsTests(unittest.TestCase):
    def test_declarations_comments_case_whitespace_and_duplicates(self):
        text = (FIXTURES / "robots.txt").read_text(encoding="utf-8")
        self.assertEqual(parse_robots(text), [
            "https://example.com/sitemap.xml", "https://example.com/news.xml",
        ])

    def test_empty_or_unrelated_content(self):
        for text in ("", "User-agent: *\nDisallow: /", "Sitemap: # empty"):
            with self.subTest(text=text):
                self.assertEqual(parse_robots(text), [])

    def test_crlf_and_colons_in_urls(self):
        self.assertEqual(
            parse_robots("Sitemap: https://example.com:8443/map.xml\r\n"),
            ["https://example.com:8443/map.xml"],
        )

    def test_leading_bom_prefixes_first_declaration(self):
        text = "\ufeffSitemap: https://example.com/sitemap.xml"
        self.assertEqual(parse_robots(text), ["https://example.com/sitemap.xml"])

    def test_bom_only_input_is_empty(self):
        self.assertEqual(parse_robots("\ufeff"), [])

    def test_leading_bom_with_later_declaration(self):
        text = "\ufeffUser-agent: *\nSitemap: https://example.com/sitemap.xml"
        self.assertEqual(parse_robots(text), ["https://example.com/sitemap.xml"])

    def test_interior_bom_in_url_is_preserved(self):
        text = "\ufeffSitemap: https://exa\ufeffmple.com/sitemap.xml"
        self.assertEqual(parse_robots(text), ["https://exa\ufeffmple.com/sitemap.xml"])

    def test_leading_bom_duplicate_declarations_collapse_in_source_order(self):
        text = "\ufeffSitemap: https://a\nSitemap: https://b\nSitemap: https://a"
        self.assertEqual(parse_robots(text), ["https://a", "https://b"])

    def test_only_one_leading_bom_is_stripped(self):
        text = "\ufeff\ufeffSitemap: https://example.com/sitemap.xml"
        self.assertEqual(parse_robots(text), [])


class SitemapTests(unittest.TestCase):
    def test_namespaced_urlset_fixture(self):
        self.assertEqual(parse_urlset((FIXTURES / "urlset.xml").read_bytes()), [
            "https://example.com/",
            "https://example.com/search?a=1&b=2",
            "https://example.com/café",
        ])

    def test_prefixed_index_fixture(self):
        self.assertEqual(
            parse_sitemap_index((FIXTURES / "sitemap_index.xml").read_bytes()),
            ["https://example.com/pages.xml", "https://example.com/news.xml"],
        )

    def test_both_document_types_with_all_supported_namespace_forms(self):
        for parser, root, entry in (
            (parse_urlset, "urlset", "url"),
            (parse_sitemap_index, "sitemapindex", "sitemap"),
        ):
            for prefix, declaration in (
                ("", ""),
                ("", f' xmlns="{NAMESPACE}"'),
                ("s:", f' xmlns:s="{NAMESPACE}"'),
            ):
                with self.subTest(root=root, prefix=prefix, declaration=declaration):
                    xml = (
                        f"<{prefix}{root}{declaration}>"
                        f"<{prefix}{entry}><{prefix}loc> https://example.com/ </{prefix}loc>"
                        f"</{prefix}{entry}></{prefix}{root}>"
                    )
                    self.assertEqual(parser(xml), ["https://example.com/"])

    def test_empty_documents(self):
        self.assertEqual(parse_urlset("<urlset/>"), [])
        self.assertEqual(parse_sitemap_index("<sitemapindex/>"), [])

    def test_duplicates_preserve_order_without_normalizing(self):
        for parser, root, entry in (
            (parse_urlset, "urlset", "url"),
            (parse_sitemap_index, "sitemapindex", "sitemap"),
        ):
            with self.subTest(root=root):
                urls = ["https://example.com/b", "https://example.com/a",
                        "https://example.com/b", "https://example.com/a/"]
                xml = f"<{root}>" + "".join(
                    f"<{entry}><loc>{url}</loc></{entry}>" for url in urls
                ) + f"</{root}>"
                self.assertEqual(parser(xml), [urls[0], urls[1], urls[3]])

    def test_malformed_xml_has_clear_error_and_original_cause(self):
        for parser in (parse_urlset, parse_sitemap_index):
            for xml in ((FIXTURES / "malformed.xml").read_bytes(), "", "<"):
                with self.subTest(parser=parser.__name__, xml=xml):
                    with self.assertRaisesRegex(ValueError, "Malformed sitemap XML") as caught:
                        parser(xml)
                    self.assertIsNotNone(caught.exception.__cause__)

    def test_wrong_root_or_namespace_is_rejected(self):
        for parser, wrong_root in (
            (parse_urlset, "sitemapindex"),
            (parse_sitemap_index, "urlset"),
        ):
            for xml in (f"<{wrong_root}/>", '<html/>',
                        '<urlset xmlns="urn:unrelated"/>'):
                with self.subTest(parser=parser.__name__, xml=xml):
                    with self.assertRaisesRegex(ValueError, "Expected sitemap root"):
                        parser(xml)

    def test_only_direct_sitemap_locations_are_used(self):
        xml = f'''<urlset xmlns="{NAMESPACE}" xmlns:other="urn:other">
          <loc>https://example.com/root</loc>
          <url><other:loc>https://example.com/foreign</other:loc></url>
          <wrapper><url><loc>https://example.com/nested</loc></url></wrapper>
          <url><loc>https://example.com/page</loc></url>
        </urlset>'''
        self.assertEqual(parse_urlset(xml), ["https://example.com/page"])


if __name__ == "__main__":
    unittest.main()
