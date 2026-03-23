#!/usr/bin/env python3
"""Generate .mht files from the static wedding site pages.

Uses Content-ID (cid:) references so browsers can resolve assets
within the MIME archive. Matches the format Chrome/Edge produce
when saving as "Webpage, Single File (.mht)".
"""

import base64
import os
import re
import uuid
from pathlib import Path

SITE_DIR = Path("/home/user/Wedding-site")
OUTPUT_DIR = SITE_DIR / "mht_output"
BOUNDARY = "----MultipartBoundary--WeddingSite" + uuid.uuid4().hex[:12]

PAGES = [
    ("index.html", "Justin & Jen - Home"),
    ("schedule.html", "Justin & Jen - Schedule"),
    ("story.html", "Justin & Jen - Story"),
    ("travel.html", "Justin & Jen - Travel"),
    ("accommodations.html", "Justin & Jen - Accommodations"),
    ("things-to-do.html", "Justin & Jen - Things to Do"),
    ("faq.html", "Justin & Jen - Q&A"),
    ("registry.html", "Justin & Jen - Registry"),
    ("beach-day.html", "Justin & Jen - Beach Day"),
]

MIME_TYPES = {
    ".css": "text/css",
    ".js": "application/javascript",
    ".webp": "image/webp",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

# Base URL used for Content-Location headers
BASE_URL = "https://wedding.local"


def get_mime_type(filepath):
    ext = Path(filepath).suffix.lower()
    return MIME_TYPES.get(ext, "application/octet-stream")


def make_cid(asset_ref):
    """Create a deterministic Content-ID from an asset path."""
    safe = asset_ref.replace("/", "-").replace(".", "-")
    return f"{safe}@mhtml.blink"


def encode_file_b64(filepath):
    with open(filepath, "rb") as f:
        raw = base64.b64encode(f.read()).decode("ascii")
    # Wrap at 76 chars per RFC 2045
    return "\n".join(raw[i:i+76] for i in range(0, len(raw), 76))


def find_local_refs(html_content):
    """Find all local src/href references."""
    refs = set()
    for attr in ("src", "href"):
        for m in re.finditer(rf'{attr}="([^"]*?)"', html_content):
            ref = m.group(1)
            if ref and not ref.startswith(("http://", "https://", "#", "mailto:", "javascript:")):
                refs.add(ref)
    return refs


def rewrite_html(html_content, asset_refs):
    """Replace local asset paths with cid: URIs."""
    rewritten = html_content
    for ref in asset_refs:
        cid = make_cid(ref)
        rewritten = rewritten.replace(f'"{ref}"', f'"cid:{cid}"')
    return rewritten


def build_mht(html_file, title):
    html_path = SITE_DIR / html_file
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Collect referenced assets
    asset_refs = find_local_refs(html_content)

    # Inline the CSS directly into the HTML to avoid cross-file issues
    css_path = SITE_DIR / "css" / "style.css"
    js_path = SITE_DIR / "js" / "main.js"

    # Read CSS and JS
    css_content = ""
    if css_path.exists():
        with open(css_path, "r") as f:
            css_content = f.read()

    js_content = ""
    if js_path.exists():
        with open(js_path, "r") as f:
            js_content = f.read()

    # Replace CSS link with inline style
    html_content = re.sub(
        r'<link\s+rel="stylesheet"\s+href="css/style\.css"\s*/?>',
        f"<style>\n{css_content}\n</style>",
        html_content
    )

    # Replace JS script src with inline script
    html_content = re.sub(
        r'<script\s+src="js/main\.js"\s*></script>',
        f"<script>\n{js_content}\n</script>",
        html_content
    )

    # Remove css/js from asset refs since they're now inlined
    asset_refs.discard("css/style.css")
    asset_refs.discard("js/main.js")

    # Also discard references to other HTML pages (nav links)
    asset_refs = {r for r in asset_refs if not r.endswith(".html")}

    # Rewrite remaining refs (images) to cid:
    html_content = rewrite_html(html_content, asset_refs)

    # -- Build MIME parts --
    page_url = f"{BASE_URL}/{html_file}"

    parts = []

    # HTML part
    parts.append(
        f"Content-Type: text/html; charset=\"utf-8\"\r\n"
        f"Content-Transfer-Encoding: quoted-printable\r\n"
        f"Content-Location: {page_url}\r\n"
        f"\r\n"
        f"{html_content}"
    )

    # Image parts
    for ref in sorted(asset_refs):
        asset_path = SITE_DIR / ref
        if not asset_path.exists():
            print(f"  Warning: {ref} not found, skipping")
            continue

        mime = get_mime_type(ref)
        cid = make_cid(ref)
        b64 = encode_file_b64(asset_path)

        parts.append(
            f"Content-Type: {mime}\r\n"
            f"Content-Transfer-Encoding: base64\r\n"
            f"Content-ID: <{cid}>\r\n"
            f"Content-Location: {BASE_URL}/{ref}\r\n"
            f"\r\n"
            f"{b64}"
        )

    # Assemble
    mht = (
        f"From: <Saved by Claude>\r\n"
        f"Snapshot-Content-Location: {page_url}\r\n"
        f"Subject: {title}\r\n"
        f"MIME-Version: 1.0\r\n"
        f"Content-Type: multipart/related;\r\n"
        f"\ttype=\"text/html\";\r\n"
        f"\tboundary=\"{BOUNDARY}\"\r\n"
        f"\r\n"
        f"\r\n"
    )

    for part in parts:
        mht += f"--{BOUNDARY}\r\n{part}\r\n\r\n"

    mht += f"--{BOUNDARY}--\r\n"
    return mht


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    for html_file, title in PAGES:
        print(f"Building: {title} ({html_file})")
        mht_content = build_mht(html_file, title)

        out_name = f"{title.replace(' - ', ' _ ')}.mht"
        out_path = OUTPUT_DIR / out_name

        with open(out_path, "w", encoding="utf-8", newline="") as f:
            f.write(mht_content)

        size_kb = os.path.getsize(out_path) / 1024
        print(f"  -> {out_path.name} ({size_kb:.0f} KB)")

    print(f"\nDone! {len(PAGES)} MHT files in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
