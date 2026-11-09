"""Estrae da uno zip di public_html i soli file citati dai contenuti e non ancora presenti in docs/media/.

Uso: python tools/extract_media.py "<percorso>\\public_html.zip"
Legge tools/media_missing.txt (prodotto da build.py). Estrae solo immagini e PDF (e i video citati, se non troppo grandi),
non apre né estrae nient'altro dallo zip (niente wp-config.php o altri file del sito).
"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEDIA = ROOT / "docs" / "media"
ALLOWED = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".mp4"}
MAX_VIDEO = 40_000_000


def main(zip_path):
    wanted = [line.strip() for line in (ROOT / "tools" / "media_missing.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    z = zipfile.ZipFile(zip_path)
    index = {}
    for info in z.infolist():
        if "wp-content/uploads/" in info.filename and not info.is_dir():
            index[info.filename.split("wp-content/uploads/", 1)[1]] = info
    # Le immagini vecchie (WordPress.com) stanno nello zip in un'altra cartella (di solito 2021/04): si cerca per nome del file.
    by_name = {}
    for key, info in index.items():
        by_name.setdefault(Path(key).name.lower(), []).append(info)
    done = notfound = skipped = by_basename = 0
    missing = []
    for src in wanted:
        rel = src[len("/media/"):]
        info = index.get(rel)
        if info is None:
            candidates = by_name.get(Path(rel).name.lower(), [])
            if candidates:
                info = max(candidates, key=lambda i: i.file_size)  # in caso di omonimi, la versione più grande
                by_basename += 1
        if info is None:
            notfound += 1
            missing.append(rel)
            continue
        suffix = Path(rel).suffix.lower()
        if suffix not in ALLOWED or ".." in Path(rel).parts or (suffix == ".mp4" and info.file_size > MAX_VIDEO):
            skipped += 1
            continue
        target = MEDIA / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with z.open(info) as source, open(target, "wb") as out:
            out.write(source.read())
        done += 1
    print(f"Estratti {done} (di cui {by_basename} trovati per nome in un'altra cartella), saltati {skipped}, non presenti nello zip {notfound}")
    (ROOT / "tools" / "media_not_in_zip.txt").write_text("\n".join(missing) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
