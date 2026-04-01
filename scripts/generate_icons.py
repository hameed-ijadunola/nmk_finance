"""Generate favicon + app icons from the NMK logo.

Usage:
    c:/.../.venv/Scripts/python.exe scripts/generate_icons.py

This reads `nmk_logo_sqr.png` at the repo root and writes icons into `static/icons/`.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "nmk_logo.png"
OUT_DIR = REPO_ROOT / "static" / "icons"

PNG_SIZES: dict[str, int] = {
    "favicon-16x16.png": 16,
    "favicon-32x32.png": 32,
    "apple-touch-icon.png": 180,
    "android-chrome-192x192.png": 192,
    "android-chrome-512x512.png": 512,
}


def _load_source() -> Image.Image:
    if not SOURCE.exists():
        raise SystemExit(f"Source logo not found: {SOURCE}")

    img = Image.open(SOURCE)
    img.load()

    # Ensure a predictable mode for resizing/saving.
    if img.mode not in {"RGB", "RGBA"}:
        img = img.convert("RGBA")

    # Best-effort: crop to square if needed.
    w, h = img.size
    if w != h:
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))

    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img = _load_source()

    # PNGs
    for filename, size in PNG_SIZES.items():
        out_path = OUT_DIR / filename
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        # Use optimize; keep alpha if present.
        resized.save(out_path, format="PNG", optimize=True)

    # ICO (multi-size)
    ico_path = OUT_DIR / "favicon.ico"
    img_for_ico = img
    if img_for_ico.mode != "RGBA":
        img_for_ico = img_for_ico.convert("RGBA")
    img_for_ico.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
    )

    # Minimal manifest (optional but harmless)
    manifest_path = OUT_DIR / "site.webmanifest"
    manifest_path.write_text(
        """{
  \"name\": \"NMK Finance\",
  \"short_name\": \"NMK Finance\",
  \"icons\": [
    {\"src\": \"android-chrome-192x192.png\", \"sizes\": \"192x192\", \"type\": \"image/png\"},
    {\"src\": \"android-chrome-512x512.png\", \"sizes\": \"512x512\", \"type\": \"image/png\"}
  ],
  \"theme_color\": \"#047857\",
  \"background_color\": \"#ffffff\",
  \"display\": \"standalone\"
}
""",
        encoding="utf-8",
    )

    generated = ["favicon.ico", "site.webmanifest", *PNG_SIZES.keys()]
    print("Generated icons:")
    for name in generated:
        print(f"- {OUT_DIR / name}")


if __name__ == "__main__":
    main()
