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
