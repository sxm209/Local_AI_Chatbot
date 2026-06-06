from __future__ import annotations

from pathlib import Path

from local_chatbot.ingestion import discover_files, extract_document


def test_extract_plain_text(tmp_path: Path) -> None:
    path = tmp_path / "example.txt"
    path.write_text("Alpha beta gamma\nDelta epsilon", encoding="utf-8")

    document = extract_document(path)

    assert document.title == "example.txt"
    assert document.file_type == "txt"
    assert document.warning is None
    assert "Alpha beta" in document.sections[0].text


def test_extract_csv(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("name,value\nAlice,42", encoding="utf-8")

    document = extract_document(path)

    assert "Row 1: name | value" in document.sections[0].text
    assert "Row 2: Alice | 42" in document.sections[0].text


def test_discover_files_recursively_skips_unsupported(tmp_path: Path) -> None:
    nested = tmp_path / "folder" / "child"
    nested.mkdir(parents=True)
    supported = nested / "notes.md"
    unsupported = nested / "image.bin"
    supported.write_text("# Notes", encoding="utf-8")
    unsupported.write_bytes(b"binary")

    files, warnings = discover_files([str(tmp_path / "folder")], recursive=True)

    assert supported in files
    assert any("Unsupported" in warning["message"] for warning in warnings)
