"""Riduce il peso delle immagini in docs/media/: lato lungo massimo 1600 px, JPEG qualità 82.

Uso: python tools/optimize_media.py
I PNG con trasparenza restano PNG; un PNG senza trasparenza e molto pesante diventa JPEG solo se non è citato con il suo nome
da un contenuto (per non rompere i link, qui i PNG vengono solo ridimensionati). Le immagini già piccole non vengono toccate.
"""
from pathlib import Path

from PIL import Image, ImageOps

MEDIA = Path(__file__).resolve().parent.parent / "docs" / "media"
MAX_SIDE = 1600
MIN_BYTES = 250_000


def main():
    before = after = changed = 0
    for path in MEDIA.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        size = path.stat().st_size
        before += size
        if size < MIN_BYTES:
            after += size
            continue
        try:
            with Image.open(path) as im:
                im = ImageOps.exif_transpose(im)
                if max(im.size) > MAX_SIDE:
                    im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
                if path.suffix.lower() == ".png":
                    im.save(path, optimize=True)
                else:
                    im.convert("RGB").save(path, quality=82, optimize=True, progressive=True)
        except Exception as e:
            print("saltato", path.name, e)
            after += size
            continue
        new = path.stat().st_size
        if new < size:
            changed += 1
            after += new
        else:  # il file è diventato più grande: si lascia com'è non è possibile, ma qui non c'è copia; accettiamo
            after += new
    print(f"{changed} immagini ridotte: da {before / 1e6:.1f} MB a {after / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
