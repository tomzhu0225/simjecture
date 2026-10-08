"""Check local destinations in generated documentation, including raw HTML cards."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.anchors.add(values["id"])
        for key in ("href", "src"):
            if values.get(key):
                self.links.append(values[key])


def check(root: Path) -> list[str]:
    root = root.resolve()
    pages = {}
    for path in root.rglob("*.html"):
        parser = Links()
        parser.feed(path.read_text())
        pages[path.resolve()] = parser
    failures = []
    for path, page in pages.items():
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (root / unquote(url.path).lstrip("/")) if url.path.startswith("/") else (
                path.parent / unquote(url.path) if url.path else path
            )
            if target.is_dir():
                target /= "index.html"
            target = target.resolve()
            if not target.exists():
                failures.append(f"{path.relative_to(root)}: missing {link}")
            elif url.fragment and target in pages and unquote(url.fragment) not in (
                pages[target].anchors
            ):
                failures.append(f"{path.relative_to(root)}: missing anchor {link}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    root = args.directory.resolve()
    if not (root / "index.html").is_file():
        parser.error("Expected a built documentation directory containing index.html")
    failures = check(root)
    for failure in failures:
        print(failure)
    print(f"Local documentation link check: {len(failures)} failures")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
