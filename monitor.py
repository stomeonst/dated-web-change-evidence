#!/usr/bin/env python3
"""Create dated, hash based evidence for visible HTML text changes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

MAX_BYTES = 2_000_000
SKIP_TAGS = {"script", "style", "template", "svg", "noscript"}


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._parts: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        if name in SKIP_TAGS:
            self._skip_depth += 1
        if name == "title" and self._skip_depth == 0:
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        name = tag.lower()
        if name == "title":
            self._in_title = False
        if name in SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self._parts.append(data)
        if self._in_title:
            self.title += data

    @property
    def text(self) -> str:
        return " ".join(self._parts)


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", normalized).strip()


def extract_visible_text(html: str) -> tuple[str, str]:
    parser = VisibleTextParser()
    parser.feed(html)
    parser.close()
    return normalize_text(parser.text), normalize_text(parser.title)


def _bounded_read(response: Any) -> bytes:
    payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError(f"source exceeds {MAX_BYTES} bytes")
    return payload


def load_source(source: str, timeout: float = 20.0) -> tuple[str, str]:
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        request = urllib.request.Request(
            source,
            headers={"User-Agent": "dated-change-evidence-sample/1.0"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "application/xhtml+xml"}:
                raise ValueError(f"expected HTML, received {content_type}")
            charset = response.headers.get_content_charset() or "utf-8"
            return _bounded_read(response).decode(charset, errors="replace"), response.geturl()
    if parsed.scheme:
        raise ValueError("source must be a local file or an HTTP or HTTPS URL")

    path = Path(source).expanduser().resolve()
    if path.stat().st_size > MAX_BYTES:
        raise ValueError(f"source exceeds {MAX_BYTES} bytes")
    return path.read_text(encoding="utf-8"), str(path)


def read_previous_hash(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    value = data.get("text_sha256")
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError("baseline does not contain a valid text_sha256 value")
    return value


def build_record(html: str, resolved_source: str, previous_hash: str | None) -> dict[str, Any]:
    text, title = extract_visible_text(html)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": resolved_source,
        "title": title,
        "text_sha256": digest,
        "text_chars": len(text),
        "previous_hash": previous_hash,
        "changed": previous_hash is not None and previous_hash != digest,
        "excerpt": text[:240],
    }


def atomic_write_json(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create dated SHA256 evidence for visible HTML text changes."
    )
    parser.add_argument("source", help="local HTML file or HTTP or HTTPS URL")
    parser.add_argument("--baseline", type=Path, help="existing JSON baseline to compare")
    parser.add_argument("--write-baseline", type=Path, help="write the new JSON baseline")
    parser.add_argument("--timeout", type=float, default=20.0, help="URL timeout in seconds")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        previous_hash = read_previous_hash(args.baseline)
        html, resolved_source = load_source(args.source, timeout=args.timeout)
        record = build_record(html, resolved_source, previous_hash)
        if args.write_baseline:
            atomic_write_json(args.write_baseline, record)
        print(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

