"""Scarica in docs/media/ i file citati dai contenuti (tools/media_needed.txt) dalla CDN pubblica di Jetpack (i0.wp.com).

Uso: python tools/fetch_media.py
Scarica solo immagini e PDF (controlla il tipo di file ricevuto); salta i file già presenti.
Scrive l'esito in tools/media_fetch_report.txt. I file non trovati sulla CDN vanno copiati a mano (zip di wp-content/uploads).
"""
import concurrent.futures as cf
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEDIA = ROOT / "docs" / "media"
ALLOWED_EXT = {"jpg", "jpeg", "png", "gif", "webp", "pdf"}
ALLOWED_TYPES = ("image/", "application/pdf")
MAX_BYTES = 40_000_000  # per singolo file
CDN = "https://i0.wp.com/geolabforest.com/wp-content/uploads/"


def fetch(path):
    target = MEDIA / path
    if target.exists():
        return path, "presente", 0
    ext = path.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        return path, "saltato (tipo non scaricato)", 0
    # Si usa curl: la CDN risponde 404 alle richieste di urllib anche per file che esistono.
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".part")
    try:
        out = subprocess.run(
            ["curl", "-s", "--max-time", "60", "--max-filesize", str(MAX_BYTES), "-o", str(tmp),
             "-w", "%{http_code} %{content_type}", CDN + path],
            capture_output=True, text=True, timeout=90,
        ).stdout.strip()
    except Exception as e:  # rete, timeout
        tmp.unlink(missing_ok=True)
        return path, f"errore: {str(e)[:60]}", 0
    code, _, ctype = out.partition(" ")
    if code != "200":
        tmp.unlink(missing_ok=True)
        return path, f"non trovato sulla CDN (HTTP {code})", 0
    if not ctype.startswith(ALLOWED_TYPES):
        tmp.unlink(missing_ok=True)
        return path, f"saltato (tipo ricevuto {ctype})", 0
    size = tmp.stat().st_size
    tmp.replace(target)
    return path, "scaricato", size


def main():
    paths = [p.strip() for p in (ROOT / "tools" / "media_needed.txt").read_text(encoding="utf-8").splitlines() if p.strip()]
    with cf.ThreadPoolExecutor(6) as ex:
        results = list(ex.map(fetch, paths))
    report = ["{}\t{}".format(status, path) for path, status, _ in sorted(results, key=lambda r: r[1])]
    (ROOT / "tools" / "media_fetch_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    counts = {}
    for _, status, _ in results:
        key = status.split(" (")[0]
        counts[key] = counts.get(key, 0) + 1
    total = sum(size for _, _, size in results)
    print(counts, f"scaricati {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
