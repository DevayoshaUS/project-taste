#!/usr/bin/env python3
"""Small CI checks for the Project Taste static site."""

from __future__ import annotations

import json
import sys
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class BasicHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_seen = False
        self._inside_title = False
        self._title_text = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._inside_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._inside_title = False
            if "".join(self._title_text).strip():
                self.title_seen = True

    def handle_data(self, data: str) -> None:
        if self._inside_title:
            self._title_text.append(data)


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_tools_registry() -> dict:
    registry_path = ROOT / "data" / "tools.json"
    if not registry_path.exists():
        fail("data/tools.json is missing")

    try:
        return json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"data/tools.json is invalid JSON: {exc}")


def validate_tools_registry(registry: dict) -> None:
    categories = registry.get("categories")
    tools = registry.get("tools")

    if not isinstance(categories, list) or not categories:
        fail("data/tools.json must contain a non-empty categories array")
    if not isinstance(tools, list) or not tools:
        fail("data/tools.json must contain a non-empty tools array")

    category_ids = {category.get("id") for category in categories if isinstance(category, dict)}
    if len(category_ids) != len(categories):
        fail("categories must have unique ids")

    tool_ids: set[str] = set()
    for tool in tools:
        if not isinstance(tool, dict):
            fail("each tool entry must be an object")

        tool_id = tool.get("id")
        category = tool.get("category")
        status = tool.get("status")

        if not isinstance(tool_id, str) or not tool_id:
            fail("each tool must have a non-empty id")
        if tool_id in tool_ids:
            fail(f"duplicate tool id: {tool_id}")
        tool_ids.add(tool_id)

        if category not in category_ids:
            fail(f"tool '{tool_id}' references unknown category '{category}'")
        if status not in {"ready", "soon"}:
            fail(f"tool '{tool_id}' has unsupported status '{status}'")

        tool_file = ROOT / "tools" / f"{tool_id}.html"
        if status == "ready" and not tool_file.exists():
            fail(f"ready tool '{tool_id}' is missing {tool_file.relative_to(ROOT)}")

    meta_count = registry.get("meta", {}).get("toolCount")
    if meta_count is not None and meta_count != len(tools):
        fail(f"meta.toolCount is {meta_count}, but {len(tools)} tools are registered")

    print(f"Validated {len(categories)} categories and {len(tools)} registered tools.")


def validate_html_files() -> None:
    html_files = sorted(ROOT.glob("*.html"))
    if not html_files:
        fail("no HTML files found")

    for html_file in html_files:
        text = html_file.read_text(encoding="utf-8")
        if "<!doctype html>" not in text[:200].lower():
            fail(f"{html_file.relative_to(ROOT)} is missing a <!DOCTYPE html> declaration")

        parser = BasicHtmlParser()
        parser.feed(text)
        if not parser.title_seen:
            fail(f"{html_file.relative_to(ROOT)} is missing a non-empty <title>")

    print(f"Validated {len(html_files)} HTML files.")


def main() -> None:
    validate_tools_registry(load_tools_registry())
    validate_html_files()


if __name__ == "__main__":
    main()
