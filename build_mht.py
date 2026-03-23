#!/usr/bin/env python3
"""Generate self-contained single-file HTML from the wedding site pages.

Inlines CSS, JS, and embeds all images as base64 data URIs so each
file can be opened directly in any browser with zero dependencies.
"""

import base64
import os
import re
from pathlib import Path

SITE_DIR = Path("/home/user/Wedding-site")
OUTPUT_DIR = SITE_DIR / "mht_output"

PAGES = [
    ("index.html", "Justin & Jen _ Home"),
    ("schedule.html", "Justin & Jen _ Schedule"),
    ("story.html", "Justin & Jen _ Story"),
    ("travel.html", "Justin & Jen _ Travel"),
    ("accommodations.html", "Justin & Jen _ Accommodations"),
    ("things-to-do.html", "Justin & Jen _ Things to Do"),
    ("faq.html", "Justin & Jen _ Q&A"),
    ("registry.html", "Justin & Jen _ Registry"),
    ("beach-day.html", "Justin & Jen _ Beach Day"),
]

MIME_TYPES = {
    ".webp": "image/webp",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def img_to_data_uri(filepath):
    ext = Path(filepath).suffix.lower()
    mime = MIME_TYPES.get(ext, "application/octet-stream")
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def build_single_html(html_file):
    html_path = SITE_DIR / html_file
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Inline CSS
    css_path = SITE_DIR / "css" / "style.css"
    if css_path.exists():
        with open(css_path, "r") as f:
            css = f.read()
        html = re.sub(
            r'<link\s+rel="stylesheet"\s+href="css/style\.css"\s*/?>',
            f"<style>\n{css}\n</style>",
            html,
        )

    # Inline JS
    js_path = SITE_DIR / "js" / "main.js"
    if js_path.exists():
        with open(js_path, "r") as f:
            js = f.read()
        html = re.sub(
            r'<script\s+src="js/main\.js"\s*>\s*</script>',
            f"<script>\n{js}\n</script>",
            html,
        )

    # Replace all local image src="..." with data URIs
    def replace_img(match):
        attr = match.group(1)  # src or href
        ref = match.group(2)
        # Skip external URLs, anchors, mailto, other html pages
        if ref.startswith(("http://", "https://", "#", "mailto:", "javascript:")):
            return match.group(0)
        if ref.endswith(".html"):
            return match.group(0)

        img_path = SITE_DIR / ref
        if img_path.exists():
            data_uri = img_to_data_uri(img_path)
            return f'{attr}="{data_uri}"'
        else:
            print(f"  Warning: {ref} not found")
            return match.group(0)

    html = re.sub(r'(src|href)="([^"]*?)"', replace_img, html)

    return html


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    for html_file, out_name in PAGES:
        print(f"Building: {out_name} ({html_file})")
        content = build_single_html(html_file)

        out_path = OUTPUT_DIR / f"{out_name}.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)

        size_kb = os.path.getsize(out_path) / 1024
        print(f"  -> {out_path.name} ({size_kb:.0f} KB)")

    print(f"\nDone! {len(PAGES)} files in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
