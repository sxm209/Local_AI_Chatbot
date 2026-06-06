from __future__ import annotations

from local_chatbot.web_search import parse_duckduckgo_html


def test_parse_duckduckgo_html_results() -> None:
    html = """
    <div class="result">
      <h2>
        <a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.com%2Fnote">Example Note</a>
      </h2>
      <a class="result__snippet">A useful web result snippet.</a>
    </div>
    """

    results = parse_duckduckgo_html(html)

    assert len(results) == 1
    assert results[0].title == "Example Note"
    assert results[0].url == "https://example.com/note"
    assert results[0].snippet == "A useful web result snippet."
