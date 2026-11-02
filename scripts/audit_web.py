"""Static-site payload and accessibility smoke audit for the Bogotá viewer."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


class AccessibilityParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.label_for: set[str] = set()
        self.inputs: list[tuple[dict[str, str], bool]] = []
        self.buttons: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.landmarks: set[str] = set()
        self.lang = ""
        self.title = False
        self.skip_target = False
        self.main_id = ""
        self.fragment_links: set[str] = set()
        self._label_depth = 0
        self._button_stack: list[tuple[dict[str, str], list[str]]] = []
        self._title_depth = 0
        self._title_text: list[str] = []

    def handle_starttag(self, tag: str, raw_attrs: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in raw_attrs}
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "html":
            self.lang = attrs.get("lang", "")
        elif tag == "main":
            self.landmarks.add("main")
            self.main_id = attrs.get("id", "")
        elif tag == "nav":
            self.landmarks.add("nav")
        elif tag == "header":
            self.landmarks.add("header")
        elif tag == "footer":
            self.landmarks.add("footer")
        elif tag == "label":
            self._label_depth += 1
            if attrs.get("for"):
                self.label_for.add(attrs["for"])
        elif tag in {"input", "select", "textarea"}:
            self.inputs.append((attrs, self._label_depth > 0))
        elif tag == "button":
            self._button_stack.append((attrs, []))
        elif tag == "img":
            self.images.append(attrs)
        elif tag == "title":
            self._title_depth += 1
        elif tag == "a" and attrs.get("href", "").startswith("#"):
            self.fragment_links.add(attrs["href"][1:])

    def handle_endtag(self, tag: str) -> None:
        if tag == "label" and self._label_depth:
            self._label_depth -= 1
        elif tag == "button" and self._button_stack:
            attrs, text = self._button_stack.pop()
            attrs["_text"] = " ".join("".join(text).split())
            self.buttons.append(attrs)
        elif tag == "title" and self._title_depth:
            self._title_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._button_stack:
            self._button_stack[-1][1].append(data)
        if self._title_depth:
            self._title_text.append(data)


def contrast_ratio(foreground: str, background: str) -> float:
    def luminance(color: str) -> float:
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    first, second = luminance(foreground), luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def audit_document(path: Path) -> list[str]:
    parser = AccessibilityParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.skip_target = bool(parser.fragment_links.intersection(parser.ids))
    errors: list[str] = []
    relative = path.relative_to(ROOT).as_posix()
    if not parser.lang:
        errors.append(f"{relative}: missing html lang attribute")
    if not "".join(parser._title_text).strip():
        errors.append(f"{relative}: missing document title")
    if "main" not in parser.landmarks:
        errors.append(f"{relative}: missing main landmark")
    if not parser.skip_target:
        errors.append(f"{relative}: missing working skip link to main content")
    for attrs, wrapped in parser.inputs:
        name = attrs.get("aria-label") or attrs.get("aria-labelledby")
        labelled = wrapped or (attrs.get("id") and attrs["id"] in parser.label_for)
        if not name and not labelled:
            errors.append(f"{relative}: form control without an accessible label ({attrs})")
    for attrs in parser.buttons:
        if not (attrs.get("aria-label") or attrs.get("aria-labelledby") or attrs.get("_text")):
            errors.append(f"{relative}: button without an accessible name ({attrs})")
    for attrs in parser.images:
        if "alt" not in attrs:
            errors.append(f"{relative}: image missing alt text")
    return errors


def audit_site() -> dict[str, object]:
    manifest = json.loads((WEB / "manifest.json").read_text(encoding="utf-8"))
    references = [*manifest.get("pmtiles", []), *manifest.get("geojson", []), *manifest.get("media", [])]
    errors: list[str] = []
    for item in references:
        target = (WEB / item).resolve()
        if WEB.resolve() not in target.parents or not target.is_file():
            errors.append(f"Manifest reference missing or outside web/: {item}")

    files = [path for path in WEB.rglob("*") if path.is_file()]
    oversized = [path.relative_to(WEB).as_posix() for path in files if path.stat().st_size >= 95 * 1024 * 1024]
    errors.extend(f"web/{name} exceeds the 95 MB publication ceiling" for name in oversized)
    temporary_suffixes = (".part", ".copying", ".tmp", ".temp.db", ".mbtiles")
    temporary_files = [
        path.relative_to(WEB).as_posix()
        for path in files
        if path.name.endswith(temporary_suffixes) or "-journal" in path.name or path.name.endswith(("-wal", "-shm"))
    ]
    errors.extend(f"Temporary processing artifact must not be published: {name}" for name in temporary_files)
    docs = [WEB / "index.html", WEB / "metodologia.html"]
    for path in docs:
        errors.extend(audit_document(path))

    styles = "\n".join(path.read_text(encoding="utf-8") for path in (WEB / "assets").glob("*.css"))
    variables = dict(re.findall(r"(--(?:text|muted|quiet|bg|panel))\s*:\s*(#[0-9a-fA-F]{6})", styles))
    backgrounds = [value for key, value in variables.items() if key in {"--bg", "--panel"}]
    contrast: dict[str, float] = {}
    for name, color in variables.items():
        if name in {"--bg", "--panel"}:
            continue
        ratios = [contrast_ratio(color, background) for background in backgrounds]
        contrast[name] = round(min(ratios), 2)
        if min(ratios) < 4.5:
            errors.append(f"{name} contrast is below WCAG AA for normal text: {contrast[name]}:1")

    return {
        "files": len(files),
        "bytes": sum(path.stat().st_size for path in files),
        "largest_files": sorted(
            ({"path": path.relative_to(WEB).as_posix(), "bytes": path.stat().st_size} for path in files),
            key=lambda item: item["bytes"], reverse=True,
        )[:10],
        "pmtiles": [item for item in manifest.get("pmtiles", [])],
        "manifest_assets": len(references),
        "contrast_ratios": contrast,
        "errors": errors,
    }


def measure_local_http(base_url: str) -> dict[str, object]:
    paths = [
        "", "assets/app.css", "assets/app.js", "assets/model-viewer.js",
        "manifest.json", "metodologia.html", "assets/methodology.css",
    ]
    total_bytes = 0
    total_seconds = 0.0
    results = []
    for path in paths:
        started = time.perf_counter()
        with urlopen(base_url.rstrip("/") + "/" + path, timeout=15) as response:
            body = response.read()
            elapsed = time.perf_counter() - started
            total_bytes += len(body)
            total_seconds += elapsed
            results.append({"path": path or "/", "status": response.status, "bytes": len(body), "seconds": round(elapsed, 4)})
    return {"requests": results, "sequential_bytes": total_bytes, "sequential_seconds": round(total_seconds, 4)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="optional local HTTP URL for a sequential static-resource timing sample")
    parser.add_argument("--output", type=Path, help="write the JSON report to this path")
    args = parser.parse_args()
    report = audit_site()
    if args.base_url:
        try:
            report["local_http_sample"] = measure_local_http(args.base_url)
        except Exception as exc:
            report["errors"].append(f"Local HTTP measurement failed: {exc}")
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
