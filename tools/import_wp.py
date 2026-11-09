"""Importa i contenuti PUBBLICATI di un'esportazione WordPress (WXR) in content/ come file Markdown con corpo HTML.

Uso: python tools/import_wp.py "<percorso>\\geolab.WordPress.AAAA-MM-GG.xml"

Bozze, contenuti privati e revisioni vengono ignorati. Gli articoli già scritti a mano (SKIP_SLUGS) non vengono sovrascritti.
Le immagini restano riferimenti a /media/<anno>/<mese>/<file>: i file veri vanno copiati in static/media/ (vedi media_needed.txt).
"""
import html
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from langcheck import italian_ratio  # noqa: E402

CONTENT = ROOT / "content"
# Tradotti o modificati a mano (source: wordpress-translated / wordpress-edited): l'importazione non li sovrascrive.
TRANSLATED = {"life-escapos", "pfit-toscana", "noos-geolab", "new-project-go-surf-supporto-decisionale-alla-pianificazione", "people"}
ITALIAN_THRESHOLD = 0.6  # oltre questa quota il contenuto riceve `lang: it` e resta fuori dal sito (solo inglese)
NS = {
    "wp": "http://wordpress.org/export/1.2/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
}

# Pagine e articoli scritti a mano nel nuovo sito, o che non servono più.
SKIP_SLUGS = {"monifun", "forwards", "forwards-project", "home", "projects", "project", "about-us", "contact", "contact-2", "sample-page", "privacy-policy", "francesca_giannetti"}
SKIP_TITLES = {"Merry Christmas", "Merry Christmas and happy New Year!"}

COLLECTION_BY_CATEGORY = [  # in ordine di priorità
    ("Projects", "projects"),
    ("Publications", "publications"),
    ("Research Field", "research"),
    ("Masters and Courses", "courses"),
    ("Didactics", "courses"),
]
UPLOADS = re.compile(
    r"https?://(?:geolabforest\.files\.wordpress\.com|(?:www\.)?geolabforest\.com/wp-content/uploads|i\d\.wp\.com/(?:www\.)?geolabforest\.com/wp-content/uploads)/"
    r"([^\s\"'?)]+)(?:\?[^\s\"')]*)?"
)


def media_path(path):
    """Percorso locale di un file della libreria: preferisce l'originale alla versione ridimensionata."""
    path = re.sub(r"-\d+x\d+(?=\.\w+$)", "", path)
    return "/media/" + path


def text(it, tag):
    el = it.find(tag, NS)
    return (el.text or "") if el is not None else ""


def clean(body, attachments, needed):
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"<script\b.*?</script>", "", body, flags=re.S | re.I)
    body = re.sub(r'\s(?:srcset|sizes|data-[a-z-]+)="[^"]*"', "", body)

    def gallery(match):
        ids = re.search(r'ids="([\d,]+)"', match.group(0))
        if not ids:
            return ""
        figs = []
        for i in ids.group(1).split(","):
            url = attachments.get(i)
            if url:
                figs.append(f'<figure><img src="{url}" alt=""></figure>')
        return '<div class="gallery">' + "".join(figs) + "</div>"

    body = re.sub(r"\[gallery[^\]]*\]", gallery, body)
    body = re.sub(r"\[wpvideo[^\]]*\]", '<p class="note">[Video not migrated]</p>', body)

    def rewrite(match):
        path = match.group(1)
        local = media_path(path)
        needed.add(local[len("/media/"):])
        return local

    body = UPLOADS.sub(rewrite, body)
    # Nel vecchio sito la chiocciola degli indirizzi email era un'immagine (anti-spam): diventa testo "(at)", accessibile.
    body = re.sub(r"<img[^>]*at29\.svg[^>]*>", "(at)", body)
    body = body.replace("\xa0", " ").replace("&nbsp;", " ")
    return body.strip()


def main(xml_path):
    root = ET.parse(xml_path).getroot()
    items = root.find("channel").findall("item")

    attachments = {}
    for it in items:
        if text(it, "wp:post_type") == "attachment":
            url = text(it, "wp:attachment_url")
            m = UPLOADS.match(url)
            attachments[text(it, "wp:post_id")] = media_path(m.group(1)) if m else url

    # Cancella le importazioni precedenti (marcate `source: wordpress`): non tocca i file scritti o tradotti a mano.
    for old in CONTENT.rglob("*.md"):
        head = old.read_text(encoding="utf-8").split("---", 2)[1] if old.read_text(encoding="utf-8").startswith("---") else ""
        if re.search(r"^source: wordpress$", head, re.M):
            old.unlink()

    needed = set()
    written = skipped = flagged = 0
    counts = {}
    for it in items:
        kind = text(it, "wp:post_type")
        if kind not in ("post", "page") or text(it, "wp:status") != "publish":
            continue
        title = html.unescape(text(it, "title")).strip()
        slug = text(it, "wp:post_name")
        slug_short = slug[:60].rstrip("-")  # evita percorsi troppo lunghi su Windows e Dropbox
        if slug in SKIP_SLUGS or slug_short in TRANSLATED or title in SKIP_TITLES or not title or title == "None":
            skipped += 1
            continue
        cats = [c.text for c in it.findall("category") if c.get("domain") == "category"]
        if kind == "page":
            collection = "pages"
        else:
            collection = next((col for cat, col in COLLECTION_BY_CATEGORY if cat in cats), "news")
            # Un articolo di cronaca (News, Event, Video) anche se etichettato Projects va tra le news.
            if collection == "projects" and {"News", "Event", "Video", "Personnel"} & set(cats):
                collection = "news"
        date = text(it, "wp:post_date")[:10]
        thumb = ""
        for meta in it.findall("wp:postmeta", NS):
            if text(meta, "wp:meta_key") == "_thumbnail_id":
                thumb = attachments.get(text(meta, "wp:meta_value"), "")
        body = clean(text(it, "content:encoded"), attachments, needed)
        if thumb.startswith("/media/"):
            needed.add(thumb[len("/media/"):])
        head = [
            "---",
            f"title: {title}",
            f"date: {date}",
            "format: html",
            "source: wordpress",
            f"categories: {', '.join(c for c in cats if c)}",
        ]
        if italian_ratio(title + " " + body) >= ITALIAN_THRESHOLD:
            head.append("lang: it")
            flagged += 1
        if thumb:
            head.append(f"image: {thumb}")
        head.append("---")
        # Pagine e progetti hanno indirizzi puliti (senza data); news, pubblicazioni e corsi li prefissano con la data.
        stem = slug_short or "untitled"
        if collection not in ("pages", "projects"):
            stem = f"{date}-{stem}"
        target = CONTENT / collection / f"{stem}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(head) + "\n\n" + body + "\n", encoding="utf-8")
        counts[collection] = counts.get(collection, 0) + 1
        written += 1

    (ROOT / "tools").mkdir(exist_ok=True)
    (ROOT / "tools" / "media_needed.txt").write_text("\n".join(sorted(needed)) + "\n", encoding="utf-8")
    print(f"Scritti {written} file, saltati {skipped}. Per cartella: {counts}")
    print(f"In italiano, esclusi dal sito (lang: it): {flagged}")
    print(f"File multimediali citati: {len(needed)} (elenco in tools/media_needed.txt)")


if __name__ == "__main__":
    main(sys.argv[1])
