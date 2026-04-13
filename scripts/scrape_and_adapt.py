#!/usr/bin/env python3
"""Scrape remartintree.com text and create an Orange County adaptation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from bs4 import BeautifulSoup


SITEMAP_URL = "https://www.remartintree.com/sitemap.xml"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"


REPLACEMENTS = [
    (r"\bR\.E\. Martin Tree Specialists,?\s*Inc\.?\b", "OCTreeTrimming"),
    (r"\bR\.E\. Martin Tree Specialists\b", "OCTreeTrimming"),
    (r"\bR\.E\. Martin\b", "OCTreeTrimming"),
    (r"\(\s*703\s*\)\s*830-5500", "9494477571"),
    (r"703-830-5500", "9494477571"),
    (r"571-238-0106", "9494477571"),
    (r"571-283-3628", "9494477571"),
    (r"Northern Virginia", "Orange County"),
    (r"Centreville", "Irvine"),
    (r"Ashburn", "Anaheim"),
    (r"Manassas", "Santa Ana"),
    (r"Catharpin", "Orange"),
    (r"Chantilly", "Costa Mesa"),
    (r"Gainesville", "Huntington Beach"),
    (r"Alexandria", "Newport Beach"),
    (r"Cartharpin", "Orange"),
    (r"\bVAA\b", "CA"),
    (r"\bVirginia\b", "Orange County"),
    (r",\s*VA\b", ", CA"),
    (r"\bVA\b", "CA"),
    (r"\bVa\.", "CA."),
    (r"20143", "92868"),
]


def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    return urlopen(req, timeout=45).read().decode("utf-8", "ignore")


def get_sitemap_urls() -> list[str]:
    xml = fetch(SITEMAP_URL)
    root = ElementTree.fromstring(xml)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [node.text.strip() for node in root.findall("sm:url/sm:loc", ns) if node.text]
    return urls


def extract_visible_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "path", "defs", "meta", "link", "iframe"]):
        tag.decompose()

    body = soup.body or soup
    raw = []
    for s in body.stripped_strings:
        line = " ".join(s.split())
        if len(line) < 2:
            continue
        raw.append(line)

    # remove sequential duplicates
    lines: list[str] = []
    for line in raw:
        if not lines or lines[-1] != line:
            lines.append(line)
    return lines


def adapt_line(line: str) -> str:
    text = line
    for pattern, repl in REPLACEMENTS:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_root = root / "scraped_text"
    ref_dir = out_root / "reference"
    oc_dir = out_root / "octreetrimming"
    ref_dir.mkdir(parents=True, exist_ok=True)
    oc_dir.mkdir(parents=True, exist_ok=True)

    urls = get_sitemap_urls()
    all_reference: list[dict] = []
    all_adapted: list[dict] = []
    all_reference_lines: list[str] = []
    all_adapted_lines: list[str] = []

    for url in urls:
        slug = url.replace("https://www.remartintree.com", "").strip("/")
        slug = slug.replace("/", "__") if slug else "home"

        lines = extract_visible_lines(fetch(url))
        adapted = [adapt_line(line) for line in lines]

        (ref_dir / f"{slug}.txt").write_text("\n".join(lines) + "\n")
        (oc_dir / f"{slug}.txt").write_text("\n".join(adapted) + "\n")

        all_reference.append({"url": url, "slug": slug, "lines": lines})
        all_adapted.append({"url": url, "slug": slug, "lines": adapted})

        all_reference_lines.append(f"\n=== {url} ===")
        all_reference_lines.extend(lines)
        all_adapted_lines.append(f"\n=== {url} ===")
        all_adapted_lines.extend(adapted)

    (out_root / "ALL_TEXT_REFERENCE.txt").write_text("\n".join(all_reference_lines).strip() + "\n")
    (out_root / "ALL_TEXT_OCTREETRIMMING.txt").write_text("\n".join(all_adapted_lines).strip() + "\n")
    (out_root / "ALL_TEXT_REFERENCE.json").write_text(json.dumps(all_reference, indent=2))
    (out_root / "ALL_TEXT_OCTREETRIMMING.json").write_text(json.dumps(all_adapted, indent=2))

    print(f"Scraped {len(urls)} pages.")
    print(f"Reference output: {ref_dir}")
    print(f"Adapted output:   {oc_dir}")


if __name__ == "__main__":
    main()
