"""Generatore del sito geoLAB: legge i file Markdown in content/ e scrive il sito statico in docs/.

Uso: python build.py
Nessuna dipendenza esterna (solo libreria standard).
"""
import html
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
OUT = ROOT / "docs"  # cartella servita da GitHub Pages

SITE = {
    "name": "geoLAB",
    "tagline": "Laboratory of Forest Geomatics",
    "affiliation": "Department of Agriculture, Food, Environment and Forestry (DAGRI), University of Florence",
    "facebook": "https://www.facebook.com/geolab.unifi.it",
    "address": "via San Bonaventura 13, 50145 Florence, Italy",
}


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


def page(title, body, description=""):
    desc = f'<meta name="description" content="{html.escape(description)}">' if description else ""
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
    <a href="/#projects">Projects</a>
    <a href="/#news">News</a>
    <a href="/#publications">Publications</a>
    <a href="/#people">People</a>
    <a href="/#contact">Contact</a>
  </nav>
</header>
<main>
{body}
</main>
<footer class="foot" id="contact">
  <img class="foot-logo" src="/img/logo/geolab-logo-full.png" alt="{SITE['name']}, {SITE['tagline']}">
  <div>
    <strong>{SITE['name']}, {SITE['tagline']}</strong><br>
    {SITE['affiliation']}<br>
    {SITE['address']}
  </div>
  <div>
    <a href="{SITE['facebook']}">Facebook</a>
  </div>
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


def load(folder):
    items = []
    for path in sorted((CONTENT / folder).glob("*.md")):
        meta, body = parse(path)
        meta["slug"] = path.stem
        items.append((meta, body))
    return items


def write(rel, content):
    target = OUT / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def build():
    # Svuota docs/ file per file: una cartella tenuta aperta da Dropbox o dall'anteprima non deve bloccare la build.
    if OUT.exists():
        for path in sorted(OUT.rglob("*"), reverse=True):
            try:
                path.unlink() if path.is_file() else path.rmdir()
            except OSError:
                pass
    shutil.copytree(STATIC, OUT, dirs_exist_ok=True)

    projects = sorted(load("projects"), key=lambda p: p[0].get("year", ""), reverse=True)
    news = sorted(load("news"), key=lambda n: n[0].get("date", ""), reverse=True)
    pubs = sorted(load("publications"), key=lambda n: n[0].get("date", ""), reverse=True)
    people = load("people")
    _, about = parse(CONTENT / "about.md")
    intro = [markdown(chunk) for chunk in about.split("\n\n---\n\n")]

    tiles = ""
    for meta, _ in projects:
        logo = meta.get("logo")
        art = f'<img src="{logo}" alt="">' if logo else f'<span class="tile-text">{html.escape(meta["title"])}</span>'
        tiles += (
            f'<a class="tile" href="/projects/{meta["slug"]}/">'
            f'<span class="tile-art">{art}</span>'
            f'<span class="tile-title">{html.escape(meta["title"])}</span>'
            f'<span class="tile-year">{meta.get("year", "")}</span></a>\n'
        )

    news_html = "".join(
        f'<li><a href="/news/{m["slug"]}/">{html.escape(m["title"])}</a><span class="muted">{m["date"]}</span></li>'
        for m, _ in news
    )
    pubs_html = "".join(
        f'<li>{html.escape(m["title"])}<span class="muted">{m["date"][:4]}</span></li>' for m, _ in pubs
    )
    people_html = "".join(
        f'<li><strong>{html.escape(m["title"])}</strong><span class="muted">{html.escape(m.get("role", ""))}</span></li>'
        for m, _ in people
    )

    home = f"""
<section class="intro">
  <p class="lead-tag">Forests, remote sensing and geomatics for monitoring and management.</p>
  <div class="cols">{''.join(f'<div>{c}</div>' for c in intro)}</div>
</section>
<section id="projects">
  <h2>Projects</h2>
  <div class="tiles">{tiles}</div>
</section>
<section class="three">
  <div id="news"><h2>News</h2><ul class="list">{news_html}</ul></div>
  <div id="publications"><h2>Publications</h2><ul class="list">{pubs_html}</ul></div>
  <div id="people"><h2>People</h2><ul class="list">{people_html}</ul></div>
</section>
<div class="pattern"><img src="/img/logo/geolab-pattern.webp" alt=""></div>
"""
    write("index.html", page(f"{SITE['name']}, {SITE['tagline']}", home, SITE["affiliation"]))

    for meta, body in projects:
        logo = f'<img class="project-logo" src="{meta["logo"]}" alt="{html.escape(meta["title"])} logo">' if meta.get("logo") else ""
        link = f'<p><a href="{meta["website"]}">Project website</a></p>' if meta.get("website") else ""
        html_body = f"""
<article class="single">
  <p class="kicker">Project, {meta.get('year', '')}</p>
  <h1>{html.escape(meta['title'])}</h1>
  <p class="sub">{html.escape(meta.get('subtitle', ''))}</p>
  {logo}
  {markdown(body)}
  {link}
  {funding_box(meta)}
</article>"""
        write(f"projects/{meta['slug']}/index.html", page(f"{meta['title']} | {SITE['name']}", html_body, meta.get("subtitle", "")))

    for meta, body in news:
        image = f'<figure class="hero"><img src="{meta["image"]}" alt="{html.escape(meta.get("alt", ""))}"></figure>' if meta.get("image") else ""
        html_body = f"""
<article class="single">
  <p class="kicker">News, {meta['date']}</p>
  <h1>{html.escape(meta['title'])}</h1>
  {image}
  {markdown(body)}
  {funding_box(meta)}
</article>"""
        write(f"news/{meta['slug']}/index.html", page(f"{meta['title']} | {SITE['name']}", html_body))

    print(f"Sito costruito in {OUT} ({len(projects)} progetti, {len(news)} news)")


if __name__ == "__main__":
    build()
