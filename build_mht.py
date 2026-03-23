#!/usr/bin/env python3
"""Generate .mht files from the static wedding site pages."""

import base64
import os
import re
from email.mime.base import MIMEBase
from pathlib import Path

SITE_DIR = Path("/home/user/Wedding-site")
OUTPUT_DIR = SITE_DIR / "mht_output"
BOUNDARY = "----=_NextPart_Wedding_Site"

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


def get_mime_type(filepath):
    ext = Path(filepath).suffix.lower()
    return MIME_TYPES.get(ext, "application/octet-stream")


def encode_file(filepath):
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def find_referenced_assets(html_content):
    """Extract all local file references from HTML."""
    assets = set()
    # Match src="..." and href="..." for local files
    for attr in ["src", "href"]:
        pattern = rf'{attr}="([^"]*?)"'
        for match in re.finditer(pattern, html_content):
            ref = match.group(1)
            if not ref.startswith(("http://", "https://", "#", "mailto:")):
                assets.add(ref)
    return assets


def build_mht(html_file, title):
    html_path = SITE_DIR / html_file
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Rewrite local refs to use content-location style paths
    assets = find_referenced_assets(html_content)

    parts = []

    # --- HTML part ---
    location = f"file:///{html_file}"
    parts.append(
        f"Content-Type: text/html; charset=\"utf-8\"\n"
        f"Content-Transfer-Encoding: quoted-printable\n"
        f"Content-Location: {location}\n"
        f"\n"
        f"{html_content}"
    )

    # --- Asset parts ---
    for asset_ref in sorted(assets):
        asset_path = SITE_DIR / asset_ref
        if not asset_path.exists():
            print(f"  Warning: {asset_ref} not found, skipping")
            continue

        mime = get_mime_type(asset_ref)
        encoded = encode_file(asset_path)

        # Wrap base64 at 76 chars
        wrapped = "\n".join(
            encoded[i : i + 76] for i in range(0, len(encoded), 76)
        )

        parts.append(
            f"Content-Type: {mime}\n"
            f"Content-Transfer-Encoding: base64\n"
            f"Content-Location: {asset_ref}\n"
            f"\n"
            f"{wrapped}"
        )

    # --- Assemble MHT ---
    mht = (
        f"From: <Saved by Claude>\n"
        f"Subject: {title}\n"
        f"MIME-Version: 1.0\n"
        f"Content-Type: multipart/related;\n"
        f"\tboundary=\"{BOUNDARY}\";\n"
        f"\ttype=\"text/html\"\n"
        f"\n"
        f"This is a multi-part message in MIME format.\n"
        f"\n"
    )

    for part in parts:
        mht += f"--{BOUNDARY}\n{part}\n\n"

    mht += f"--{BOUNDARY}--\n"
    return mht


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    for html_file, title in PAGES:
        print(f"Building: {title} ({html_file})")
        mht_content = build_mht(html_file, title)

        # Output filename
        stem = Path(html_file).stem
        out_name = f"{title.replace(' - ', ' _ ')}.mht"
        out_path = OUTPUT_DIR / out_name

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(mht_content)

        size_kb = os.path.getsize(out_path) / 1024
        print(f"  -> {out_path.name} ({size_kb:.0f} KB)")

    print(f"\nDone! {len(PAGES)} MHT files in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
