"""Bounded HTTP transport, independent of robots and sitemap parsing."""

from __future__ import annotations

import gzip
from http.client import HTTPException
from io import BytesIO
import math
import zlib
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


DEFAULT_TIMEOUT = 10.0
DEFAULT_MAX_BYTES = 10 * 1024 * 1024


class FetchError(ValueError):
    """A URL could not be fetched within the supported transport policy."""


def validate_url(url: str) -> str:
    """Require an absolute HTTP(S) URL without credentials or whitespace."""
    try:
        if not url or any(character.isspace() or ord(character) < 32 or ord(character) == 127
                          for character in url):
            raise FetchError("Malformed URL: empty URL, whitespace, or control character")
        if not url.isascii():
            raise FetchError("Malformed URL: use an IDNA host and percent-encoded non-ASCII characters")
        parts = urlsplit(url)
        if not parts.scheme:
            raise FetchError("Malformed URL: an absolute HTTP(S) URL is required")
        if parts.scheme.lower() not in ("http", "https"):
            raise FetchError(f"Unsupported URL scheme: {parts.scheme}")
        if not parts.hostname or parts.username is not None or parts.password is not None:
            raise FetchError("Malformed URL: host required and credentials are unsupported")
        parts.port  # Validate the port before attempting a connection.
    except ValueError as error:
        if isinstance(error, FetchError):
            raise
        raise FetchError("Malformed URL: invalid host or port") from error
    return url


class _HTTPOnlyRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        validate_url(new_url)
        return super().redirect_request(request, response, code, message, headers, new_url)


def _read_limited(stream, max_bytes: int) -> bytes:
    content = stream.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise FetchError(f"Response exceeds size limit of {max_bytes} bytes")
    return content


def fetch_bytes(
    url: str, *, timeout: float = DEFAULT_TIMEOUT, max_bytes: int = DEFAULT_MAX_BYTES,
) -> bytes:
    """Fetch bytes, decoding one gzip layer identified by header or magic bytes.

    The limit applies independently to downloaded and decompressed bytes. The
    timeout applies to blocking socket operations, not total elapsed time.
    Redirects use urllib's bounded redirect policy and remain HTTP(S)-only.
    """
    validate_url(url)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be positive and finite")
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    request = Request(url, headers={
        "User-Agent": "sitemap-diff-checker",
        "Accept-Encoding": "gzip",
    })
    try:
        with build_opener(_HTTPOnlyRedirects()).open(request, timeout=timeout) as response:
            if not 200 <= response.status < 300:
                raise FetchError(f"HTTP response was not successful: {response.status}")
            encoding = response.headers.get("Content-Encoding", "identity").strip().lower()
            if encoding not in ("identity", "gzip"):
                raise FetchError(f"Unsupported Content-Encoding: {encoding}")
            content = _read_limited(response, max_bytes)
        if encoding == "gzip" or content.startswith(b"\x1f\x8b"):
            try:
                with gzip.GzipFile(fileobj=BytesIO(content)) as decompressed:
                    return _read_limited(decompressed, max_bytes)
            except (OSError, EOFError, zlib.error) as error:
                raise FetchError("Invalid gzip response") from error
        return content
    except HTTPError as error:
        error.close()
        raise FetchError(f"HTTP response was not successful: {error.code}") from error
    except (TimeoutError, URLError, OSError, HTTPException) as error:
        raise FetchError(f"Network failure or timeout: {error}") from error
