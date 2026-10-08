"""Catch broken raw-HTML entry cards that Sphinx itself does not validate."""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "check_docs_links", Path(__file__).parents[1] / "scripts/check_docs_links.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_raw_cards_and_image_destinations_are_checked(tmp_path):
    (tmp_path / "index.html").write_text(
        '<a class="sj-card" href="missing.html">Study</a><img src="lost.png">'
    )
    assert MODULE.check(tmp_path) == [
        "index.html: missing missing.html",
        "index.html: missing lost.png",
    ]


def test_encoded_paths_queries_and_fragments(tmp_path):
    sub = tmp_path / "guides"
    sub.mkdir()
    (sub / "first study.html").write_text('<h1 id="start">Study</h1>')
    (tmp_path / "index.html").write_text(
        '<a href="guides/first%20study.html?q=test#start">Good</a>'
        '<a href="/guides/first%20study.html#absent">Bad</a>'
        '<a href="https://example.invalid/unavailable">External</a>'
    )
    assert MODULE.check(tmp_path) == [
        "index.html: missing anchor /guides/first%20study.html#absent"
    ]


def test_relative_root_and_directory_index(tmp_path, monkeypatch):
    root = tmp_path / "site"
    root.mkdir()
    (root / "index.html").write_text('<a href="guide/">Guide</a>')
    (root / "guide").mkdir()
    (root / "guide/index.html").write_text('<a href="../index.html">Home</a>')
    monkeypatch.chdir(tmp_path)
    assert MODULE.check(Path("site")) == []
