"""Scarica la pagina LIVE (dashboard) da un link riservato e la mette in static/live/app/index.html.

Uso (solo nel workflow, prima di build.py): LIVE_DASHBOARD_URL=<link> python -I tools/fetch_live.py
Il link sta in un secret del repository, mai nel codice. Se la variabile manca, se il download
fallisce o se il file non supera i controlli, NON si scrive nulla: resta la copia già nel repository
e lo script esce con 0 (il sito si pubblica comunque), stampando un avviso. Solo libreria standard.
"""
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / "static" / "live" / "app" / "index.html"
TITLE = "<title>The geoLAB at work</title>"
MIN_BYTES, MAX_BYTES = 100_000, 600_000
FORBIDDEN = ("niccoli", "cruscotto_progetti", "hpo_repeat", "gherardo", "unifi", "gmail", "dropbox", "c:\\")
TIMEOUT = 30


def direct(url):
    """Un link di condivisione Dropbox diventa un download diretto (dl=1)."""
    parts = urllib.parse.urlsplit(url)
    if parts.netloc.endswith("dropbox.com"):
        query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k not in ("dl", "raw")] + [("dl", "1")]
        parts = parts._replace(query=urllib.parse.urlencode(query))
    return urllib.parse.urlunsplit(parts)


def problems(data):
    """Elenco dei motivi per cui il file scaricato non va pubblicato (vuoto se è a posto)."""
    out = []
    if not MIN_BYTES <= len(data) <= MAX_BYTES:
        out.append(f"size {len(data)} bytes outside {MIN_BYTES}-{MAX_BYTES}")
    text = data.decode("utf-8", errors="replace")
    if not text.lstrip().lower().startswith("<!doctype html"):
        out.append("not an HTML page")
    if TITLE not in text:
        out.append("title is not 'The geoLAB at work'")
    low = text.lower()
    out += [f"contains forbidden text '{w}'" for w in FORBIDDEN if w in low]
    return out


def main():
    url = os.environ.get("LIVE_DASHBOARD_URL", "").strip()
    if not url:
        print("LIVE page: LIVE_DASHBOARD_URL not set, keeping the copy in the repository.")
        return 0
    try:
        req = urllib.request.Request(direct(url), headers={"User-Agent": "geolab-site-build"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read(MAX_BYTES + 1)
    except Exception as exc:  # il testo dell'errore può contenere il link: non stamparlo
        print(f"::warning::LIVE page: download failed ({type(exc).__name__}), keeping the copy in the repository.")
        return 0
    bad = problems(data)
    if bad:
        print("::warning::LIVE page: downloaded file rejected (" + "; ".join(bad) + "), keeping the copy in the repository.")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_bytes(data)
    print(f"LIVE page updated ({len(data)} bytes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
