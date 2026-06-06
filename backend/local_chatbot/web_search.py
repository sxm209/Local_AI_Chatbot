from __future__ import annotations

import html
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class WebResult:
    title: str
    url: str
    snippet: str


DUCKDUCKGO_HTML_URL = "https://lite.duckduckgo.com/lite/"


def search_web(query: str, enabled: bool, limit: int = 5) -> list[WebResult]:
    if not enabled:
        return []
    query = query.strip()
    if not query:
        return []
    params = urllib.parse.urlencode({"q": query})
    request = urllib.request.Request(
        f"{DUCKDUCKGO_HTML_URL}?{params}",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        },
    )
    body = _read_search_response(request)
    return parse_duckduckgo_html(body, limit=limit)


def _read_search_response(request: urllib.request.Request) -> str:
    contexts: list[ssl.SSLContext | None] = [None]
    try:
        import certifi

        contexts.append(ssl.create_default_context(cafile=certifi.where()))
    except Exception:
        pass
    contexts.append(ssl._create_unverified_context())

    last_error: Exception | None = None
    for context in contexts:
        try:
            with urllib.request.urlopen(request, timeout=12, context=context) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            last_error = exc
            reason = getattr(exc, "reason", None)
            if not isinstance(reason, ssl.SSLError):
                break
    if last_error:
        raise last_error
    raise RuntimeError("Web search failed.")


def parse_duckduckgo_html(body: str, limit: int = 5) -> list[WebResult]:
    soup = BeautifulSoup(body, "html.parser")
    results: list[WebResult] = []
    for title_link in soup.select(".result-link"):
        if title_link.get_text(" ", strip=True).lower() == "more info":
            continue
        snippet_node = None
        row = title_link.find_parent("tr")
        if row and "sponsored" in row.get_text(" ", strip=True).lower():
            continue
        if row:
            next_row = row.find_next_sibling("tr")
            while next_row and snippet_node is None:
                if "result-sponsored" in (next_row.get("class") or []):
                    break
                snippet_node = next_row.select_one(".result-snippet")
                if snippet_node:
                    break
                next_row = next_row.find_next_sibling("tr")
        href = str(title_link.get("href", ""))
        url = _clean_duckduckgo_url(href)
        title = title_link.get_text(" ", strip=True)
        snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
        if title and url and not _is_ad_url(url):
            results.append(WebResult(title=title, url=url, snippet=snippet))
        if len(results) >= limit:
            return results

    for block in soup.select(".result"):
        title_link = block.select_one(".result__a")
        if not title_link:
            continue
        snippet_node = block.select_one(".result__snippet")
        href = str(title_link.get("href", ""))
        url = _clean_duckduckgo_url(href)
        title = title_link.get_text(" ", strip=True)
        snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
        if title and url and not _is_ad_url(url):
            results.append(WebResult(title=title, url=url, snippet=snippet))
        if len(results) >= limit:
            break
    return results


def _clean_duckduckgo_url(raw_url: str) -> str:
    url = html.unescape(raw_url)
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return query["uddg"][0]
    return url


def _is_ad_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.netloc.endswith("duckduckgo.com") and parsed.path.endswith("/y.js")
