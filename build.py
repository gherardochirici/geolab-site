"""Generatore del sito geoLAB: legge i file Markdown in content/ e scrive il sito statico in docs/.

Uso: python build.py
Nessuna dipendenza esterna (solo libreria standard).

Cartelle di content/: projects, research, publications, news, courses, pages, people (+ about.md).
Un file con `format: html` nell'intestazione ha il corpo già in HTML (contenuti importati da WordPress).
"""
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "tools"))
from langcheck import italian_ratio  # noqa: E402  (il sito è solo in inglese)
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
OUT = ROOT / "docs"  # cartella servita da GitHub Pages

SITE = {
    "name": "geoLAB",
    "tagline": "Laboratory of Forest Geomatics",
    "affiliation": "Department of Agriculture, Food, Environment and Forestry (DAGRI), University of Florence",
    "facebook": "https://www.facebook.com/geolab.unifi.it",
    "instagram": "https://www.instagram.com/geolabforest/",
    "address": "via San Bonaventura 13, 50145 Florence, Italy",
}

# Sezioni con pagina elenco: cartella -> (titolo, ordine nel menu)
SECTIONS = {
    "projects": "Projects",
    "research": "Research",
    "publications": "Publications",
    "news": "News",
    "courses": "Courses",
}
HOME_LIST = ("news", "publications")  # elenchi mostrati nella home, con questo numero di voci
HOME_COUNT = 6
SITE_BASE = os.environ.get("SITE_BASE", "").rstrip("/")  # es. /geolab-site; vuoto se il sito sta alla radice del dominio
ARCHIVE_BEFORE = "2025-01-01"  # le news precedenti vanno nella pagina "News archive"

missing_media = set()


def parse(path):
    """Restituisce (metadati, corpo) di un file Markdown con intestazione `chiave: valore` tra due righe ---."""
    text = path.read_text(encoding="utf-8")
    meta = {}
    if text.startswith("---"):
        _, head, body = text.split("---", 2)
        for line in head.strip().splitlines():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    else:
        body = text
    return meta, body.strip()


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1" loading="lazy">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def markdown(body):
    out = []
    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        if block.startswith("## "):
            out.append(f"<h2>{inline(block[3:])}</h2>")
        elif block.startswith("# "):
            out.append(f"<h1>{inline(block[2:])}</h1>")
        elif all(line.startswith("- ") for line in lines):
            items = "".join(f"<li>{inline(line[2:])}</li>" for line in lines)
            out.append(f"<ul>{items}</ul>")
        elif block.startswith("!["):
            out.append(f"<figure>{inline(block)}</figure>")
        else:
            out.append(f"<p>{inline(' '.join(lines))}</p>")
    return "\n".join(out)


def exists(src):
    """Il file citato c'è? Le immagini della libreria vivono in docs/media (non si cancellano a ogni build)."""
    rel = src.lstrip("/")
    return (OUT / rel).exists() or (STATIC / rel).exists()


def render_body(meta, body):
    if meta.get("format") == "html":
        for src in re.findall(r'src="(/media/[^"]+)"', body):
            if not exists(src):
                missing_media.add(src)
        return body
    return markdown(body)


def page(title, body, description="", nav_extra=""):
    desc = f'<meta name="description" content="{html.escape(description)}">' if description else ""
    nav = "".join(f'<a href="/{key}/">{label}</a>' for key, label in SECTIONS.items())
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
{desc}
<link rel="icon" type="image/png" href="/img/logo/favicon-64.png">
<link rel="stylesheet" href="/css/site.css">
</head>
<body>
<header class="top">
  <a class="brand" href="/"><img src="/img/logo/geolab-logo.png" alt="{SITE['name']}"><span class="brand-tag">{SITE['tagline']}</span></a>
  <nav aria-label="Main">
    {nav}
    <a href="/pages/people/">People</a>
    <a href="/#contact">Contact</a>
  </nav>
</header>
<main>
{body}
</main>
<footer class="foot" id="contact">
  <img class="foot-logo" src="/img/logo/geolab-logo-full.png" alt="{SITE['name']}, {SITE['tagline']}">
  <div>
    <a class="foot-unifi" href="https://www.unifi.it/"><img src="/img/logo/unifi-logo-white.png" alt="University of Florence (Università degli Studi Firenze)"></a>
    <strong>{SITE['name']}, {SITE['tagline']}</strong><br>
    {SITE['affiliation']}<br>
    {SITE['address']}
  </div>
  <div>
    <a href="{SITE['facebook']}">Facebook</a><br>
    <a href="{SITE['instagram']}">Instagram</a>
  </div>
  {nav_extra}
</footer>
</body>
</html>
"""


def funding_box(meta):
    text = meta.get("funding", "")
    if not text:
        return ""
    emblem = '<img class="emblem" src="/img/EU_emblem_funded.png" alt="Funded by the European Union">' if meta.get("emblem") == "yes" else ""
    todo = " todo" if "[DA COMPLETARE" in text else ""
    return f'<aside class="funding{todo}">{emblem}<p>{html.escape(text)}</p></aside>'


excluded_italian = []
suspect_italian = []


def load(folder):
    items = []
    for path in sorted((CONTENT / folder).glob("*.md")):
        meta, body = parse(path)
        # Il sito è solo in inglese: `lang: it` nell'intestazione toglie il contenuto dal sito (finché non è tradotto).
        if meta.get("lang") == "it":
            excluded_italian.append(path.name)
            continue
        if italian_ratio(meta.get("title", "") + " " + body) >= 0.5:
            suspect_italian.append(f"{folder}/{path.name}")
        meta["slug"] = path.stem
        meta["folder"] = folder
        meta.setdefault("date", path.stem[:10] if re.match(r"\d{4}-\d{2}-\d{2}", path.stem) else "")
        meta.setdefault("year", meta["date"][:4])
        items.append((meta, body))
    return items


def write(rel, content):
    # Con un dominio proprio il sito sta alla radice (SITE_BASE vuoto); su gherardochirici.github.io/geolab-site serve il prefisso.
    if SITE_BASE:
        content = re.sub(r'(href|src)="/(?!/)', rf'\1="{SITE_BASE}/', content)
    target = OUT / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def tile(meta):
    image = meta.get("logo") or meta.get("image")
    if image and image.startswith("/media/") and not exists(image):
        image = ""
    art = f'<img src="{image}" alt="" loading="lazy">' if image else f'<span class="tile-text">{html.escape(meta["title"])}</span>'
    return (
        f'<a class="tile" href="/{meta["folder"]}/{meta["slug"]}/">'
        f'<span class="tile-art">{art}</span>'
        f'<span class="tile-title">{html.escape(meta["title"])}</span>'
        f'<span class="tile-year">{meta.get("year", "")}</span></a>\n'
    )


def list_items(items, limit=None):
    rows = ""
    for meta, _ in items[:limit]:
        rows += (
            f'<li><a href="/{meta["folder"]}/{meta["slug"]}/">{html.escape(meta["title"])}</a>'
            f'<span class="muted">{meta.get("date", "")}</span></li>'
        )
    return f'<ul class="list">{rows}</ul>'


def build():
    # Svuota docs/ file per file: una cartella tenuta aperta da Dropbox o dall'anteprima non deve bloccare la build.
    if OUT.exists():
        for path in sorted(OUT.rglob("*"), reverse=True):
            if (OUT / "media") in path.parents or path == OUT / "media":
                continue  # la libreria immagini resta: è la sola copia nel repository
            try:
                path.unlink() if path.is_file() else path.rmdir()
            except OSError:
                pass
    shutil.copytree(STATIC, OUT, dirs_exist_ok=True, ignore=shutil.ignore_patterns("media"))

    data = {name: sorted(load(name), key=lambda p: (p[0].get("date") or p[0].get("year", ""), p[0]["title"]), reverse=True)
            for name in list(SECTIONS) + ["pages", "people"]}
    # I progetti si ordinano per anno di inizio.
    data["projects"].sort(key=lambda p: p[0].get("year", ""), reverse=True)
    _, about = parse(CONTENT / "about.md")
    intro = [markdown(chunk) for chunk in about.split("\n\n---\n\n")]

    people_html = "".join(
        f'<li><strong>{html.escape(m["title"])}</strong><span class="muted">{html.escape(m.get("role", ""))}</span></li>'
        for m, _ in data["people"]
    )
    pages_nav = "".join(
        f'<a href="/pages/{m["slug"]}/">{html.escape(m["title"])}</a>' for m, _ in sorted(data["pages"], key=lambda p: p[0]["title"])
    )
    pages_nav = f'<nav class="foot-pages" aria-label="More pages">{pages_nav}</nav>' if pages_nav else ""

    def wrap(title, body, description=""):
        return page(title, body, description, pages_nav)

    recent_news = [n for n in data["news"] if n[0].get("date", "") >= ARCHIVE_BEFORE]
    archive_news = [n for n in data["news"] if n[0].get("date", "") < ARCHIVE_BEFORE]
    shown = {name: (recent_news if name == "news" else data[name]) for name in SECTIONS}

    home_lists = "".join(
        f'<div id="{name}"><h2><a href="/{name}/">{SECTIONS[name]}</a></h2>{list_items(shown[name], HOME_COUNT)}</div>'
        for name in HOME_LIST
    )
    home = f"""
<section class="intro">
  <p class="lead-tag">The Laboratory of Forest Geomatics at the University of Florence. Earth observation, modelling and geomatics for sustainable forest management.</p>
  <div class="cols">{''.join(f'<div>{c}</div>' for c in intro)}</div>
</section>
<section id="projects">
  <h2><a href="/projects/">Projects</a></h2>
  <div class="tiles">{''.join(tile(m) for m, _ in data['projects'])}</div>
</section>
<section class="three">
  {home_lists}
  <div id="people"><h2>Director</h2><ul class="list">{people_html}</ul></div>
</section>
<div class="pattern"><img src="/img/logo/geolab-pattern.webp" alt=""></div>
"""
    write("index.html", wrap(f"{SITE['name']}, {SITE['tagline']}", home, SITE["affiliation"]))

    for name, label in SECTIONS.items():
        if name == "projects":
            body = f'<section><h1 class="section-title">{label}</h1><div class="tiles">{"".join(tile(m) for m, _ in data[name])}</div></section>'
        elif name == "news":
            more = f'<p class="more"><a href="/news/archive/">News archive: {len(archive_news)} items before {ARCHIVE_BEFORE[:4]}</a></p>' if archive_news else ""
            body = f'<section><h1 class="section-title">{label}</h1>{list_items(shown[name])}{more}</section>'
        else:
            body = f'<section><h1 class="section-title">{label}</h1>{list_items(data[name])}</section>'
        write(f"{name}/index.html", wrap(f"{label} | {SITE['name']}", body))
    if archive_news:
        body = (f'<section><h1 class="section-title">News archive</h1><p class="sub">News published before {ARCHIVE_BEFORE[:4]}. '
                f'<a href="/news/">Back to recent news</a></p>{list_items(archive_news)}</section>')
        write("news/archive/index.html", wrap(f"News archive | {SITE['name']}", body))

    for folder in list(SECTIONS) + ["pages"]:
        for meta, body in data[folder]:
            kicker = SECTIONS.get(folder, "").rstrip("s") or ""
            date = meta.get("date", "")
            kicker_text = ", ".join(x for x in (kicker, "" if folder == "pages" else (date if folder != "projects" else meta.get("year", ""))) if x)
            logo = f'<img class="project-logo" src="{meta["logo"]}" alt="{html.escape(meta["title"])} logo">' if meta.get("logo") else ""
            image = ""
            if folder == "news" and meta.get("image") and exists(meta["image"]):
                image = f'<figure class="hero"><img src="{meta["image"]}" alt="{html.escape(meta.get("alt", ""))}"></figure>'
            sub = f'<p class="sub">{html.escape(meta["subtitle"])}</p>' if meta.get("subtitle") else ""
            link = f'<p><a href="{meta["website"]}">Project website</a></p>' if meta.get("website") else ""
            html_body = f"""
<article class="single">
  <p class="kicker">{html.escape(kicker_text)}</p>
  <h1>{html.escape(meta['title'])}</h1>
  {sub}
  {logo}
  {image}
  {render_body(meta, body)}
  {link}
  {funding_box(meta)}
</article>"""
            write(f"{folder}/{meta['slug']}/index.html", wrap(f"{meta['title']} | {SITE['name']}", html_body, meta.get("subtitle", "")))

    # Reindirizzamenti dai vecchi indirizzi WordPress (redirects.json, prodotto da tools/import_wp.py): GitHub Pages non ha
    # redirect del server, quindi ogni vecchio indirizzo diventa una piccola pagina che rimanda al nuovo.
    redirects_file = ROOT / "redirects.json"
    made = 0
    if redirects_file.exists():
        for old, new in json.loads(redirects_file.read_text(encoding="utf-8")).items():
            index = OUT / old.strip("/") / "index.html"
            if index.exists():  # non si sovrascrive una pagina vera
                continue
            # href e src con percorso dalla radice ricevono il prefisso in write(); nel meta refresh va messo a mano.
            write(
                f"{old.strip('/')}/index.html",
                f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>Page moved</title>\n'
                f'<meta name="robots" content="noindex">\n<meta http-equiv="refresh" content="0; url={SITE_BASE}{new}">\n'
                f'<link rel="canonical" href="{new}">\n</head>\n<body>\n'
                f'<p>This page has moved to <a href="{new}">the new address</a>.</p>\n</body>\n</html>\n',
            )
            made += 1
        print(f"Reindirizzamenti creati: {made}")

    total = sum(len(v) for v in data.values())
    print(f"Sito costruito in {OUT} ({total} contenuti: " + ", ".join(f"{k} {len(v)}" for k, v in data.items()) + ")")
    if excluded_italian:
        print(f"Esclusi dal sito perché in italiano (lang: it): {len(excluded_italian)}")
    if suspect_italian:
        print("ATTENZIONE, testo che sembra italiano e non è escluso (il sito è solo in inglese):")
        for name in suspect_italian:
            print("  ", name)
    if missing_media:
        (ROOT / "tools" / "media_missing.txt").write_text("\n".join(sorted(missing_media)) + "\n", encoding="utf-8")
        print(f"Attenzione: {len(missing_media)} immagini citate non sono in docs/media/ (elenco in tools/media_missing.txt)")


if __name__ == "__main__":
    build()
