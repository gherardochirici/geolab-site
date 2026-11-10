"""Anteprima visiva di una bozza social (cartella social/): solo libreria standard.

Uso: python tools/preview_social.py social/2026-11-10_titolo.md [--out CARTELLA]
Scrive un unico file HTML (immagini incorporate) con i mock-up di Facebook, Instagram e LinkedIn:
testo completo, immagine nel feed e nelle miniature (ritaglio), anteprima del link, lunghezze e controlli
sull'immagine. Serve a chi approva: si guarda PRIMA di dire sì alla pubblicazione.
Non pubblica nulla e non tocca il repository. I mock-up sono approssimazioni: le piattaforme cambiano grafica e limiti.
"""
import argparse
import base64
import html
import mimetypes
import re
import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_pr import ROOT, page_to_content, parse  # noqa: E402
from ogimage import DEFAULT, og_image  # noqa: E402

FB_NAME = "Geolab - Laboratorio di Geomatica"
LI_NAME = "geoLAB - Laboratory of Forest Geomatics"
IG_NAME = "geolabforest"
SITE = "https://geolabforest.com"
TAGS = "@UNIFIOFFICIAL @dagriunifi"
TITLES = {"facebook": "Facebook", "instagram": "Instagram", "linkedin": "LinkedIn"}


def image_size(path):
    """(larghezza, altezza) di un PNG o JPEG, senza librerie esterne; None se non riconosciuto."""
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return None


def find_image(ref):
    rel = ref.lstrip("/")
    for base in (ROOT / "docs", ROOT / "static"):
        if (base / rel).exists():
            return base / rel
    return None


def data_uri(path):
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def section(body, title):
    m = re.search(rf"^## {title}\s*\n(.*?)(?=^## |\Z)", body, re.S | re.M | re.I)
    return m.group(1).strip() if m else ""


def paragraphs(text):
    return "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in text.split("\n\n") if p.strip())


def with_hashtags(escaped):
    return re.sub(r"(?<!\w)(#\w+)", r'<span class="tag">\1</span>', escaped)


def truncated(text, visible):
    """Testo con la parte visibile prima di 'altro' e il resto attenuato."""
    flat = text
    if len(flat) <= visible:
        return with_hashtags(html.escape(flat).replace("\n", "<br>")), False
    cut = flat.rfind(" ", 0, visible)
    cut = cut if cut > 0 else visible
    head, tail = flat[:cut], flat[cut:]
    h = with_hashtags(html.escape(head).replace("\n", "<br>"))
    t = with_hashtags(html.escape(tail).replace("\n", "<br>"))
    return f'<span class="vis">{h}</span><span class="more-mark"> … altro</span><span class="rest">{t}</span>', True


def link_card(page, page_meta):
    """Anteprima del link come la mostreranno Facebook e LinkedIn: usa l'og:image che build.py scrive nella pagina."""
    title = html.escape(page_meta.get("title", page))
    ref = og_image(page_meta, page.strip("/").split("/")[-1], ROOT)
    path = find_image(ref)
    note = ""
    extra = ""
    if ref == DEFAULT:
        note = " warn"
        extra = '<div class="noimg">La pagina usa la scheda di ripiego del laboratorio: per un\'anteprima giusta aggiungi `social_image:` (scheda 1200x630 con il logo del progetto) o `image:`.</div>'
    img = f'<img src="{data_uri(path)}" alt="">' if path else ""
    return f'<div class="linkcard{note}">{img}{extra}<div class="lc-text"><small>GEOLABFOREST.COM</small><b>{title}</b></div></div>'


def checks_for(platform, post, img_path, size, meta, page_meta):
    out = []

    def add(level, msg):
        out.append((level, msg))

    n = len(post)
    tags = len(re.findall(r"(?<!\w)#\w+", post))
    add("ok", f"{n} caratteri, {tags} hashtag")
    if img_path and size:
        w, h = size
        ratio = w / h
        add("ok", f"immagine {w}x{h} px, rapporto {ratio:.2f}:1")
        if platform == "instagram":
            if w < 1080:
                add("warn", "meno di 1080 px di larghezza: Instagram la sfocherà")
            if not 0.8 <= ratio <= 1.91:
                add("bad", "rapporto fuori dai limiti del feed di Instagram (4:5 verticale ... 1.91:1 orizzontale)")
            if abs(ratio - 1) > 0.01:
                add("warn", "nella griglia del profilo Instagram viene ritagliata al centro (1:1 o 3:4): controlla che logo ed emblema UE restino interi nelle miniature sotto")
        else:
            if ratio < 0.8:
                add("warn", "immagine molto alta: nel feed viene tagliata e occupa molto spazio")
            lost = round((1 - min(ratio, 1 / ratio)) * 100)
            if lost > 5:
                add("warn", f"nelle miniature (griglia Foto, risultati) viene ritagliata al quadrato e perde il {lost}% dell'immagine: controlla che logo ed emblema UE restino interi nella miniatura sotto")
    elif platform == "instagram":
        add("bad", "Instagram richiede un'immagine")
    if meta.get("alt") and img_path:
        add("ok", "testo alternativo presente")
    elif img_path:
        add("bad", "manca il testo alternativo (alt)")
    if platform == "facebook" and not img_path:
        add("warn", "nessuna immagine nella bozza: l'aspetto dipende dall'anteprima del link (vedi riquadro)")
    return out


def card(platform, post, meta, img_path, size, page, page_meta):
    link = f"{SITE}{page}"
    img_html = ""
    if img_path:
        img_html = f'<img class="media" src="{data_uri(img_path)}" alt="{html.escape(meta.get("alt", ""))}">'
    thumb = ""
    if img_path:
        thumb = f'<div class="thumbs"><div><div class="sq"><img src="{data_uri(img_path)}" alt=""></div><small>miniatura 1:1</small></div>'
        if platform == "instagram":
            thumb += f'<div><div class="r34"><img src="{data_uri(img_path)}" alt=""></div><small>griglia 3:4</small></div>'
        thumb += "</div>"
    if platform == "facebook":
        body, _ = truncated(post, 200)
        extra = f'<div class="added">Aggiunti alla pubblicazione: {html.escape(link)} {TAGS}</div>'
        card_link = "" if img_path else link_card(page, page_meta)
        head = f'<div class="head"><div class="av fb"></div><div><b>{FB_NAME}</b><small>Adesso · pubblico</small></div></div>'
        inner = f'{head}<div class="text">{body}</div>{extra}{img_html}{card_link}{thumb}'
    elif platform == "linkedin":
        body, _ = truncated(post, 210)
        extra = f'<div class="added">Aggiunto alla pubblicazione: {html.escape(link)}</div>'
        head = f'<div class="head"><div class="av li"></div><div><b>{LI_NAME}</b><small>0 follower · Adesso · pubblico</small></div></div>'
        inner = f'{head}<div class="text">{body}</div>{extra}{img_html}{thumb}'
    else:
        body, _ = truncated(post, 125)
        head = f'<div class="head"><div class="av ig"></div><div><b>{IG_NAME}</b></div></div>'
        frame = f'<div class="igframe">{img_html}</div>' if img_path else '<div class="noimg">Manca l\'immagine</div>'
        inner = f'{head}{frame}<div class="text"><b>{IG_NAME}</b> {body}</div>{thumb}'
    marks = "".join(f'<li class="{lvl}">{html.escape(msg)}</li>' for lvl, msg in checks_for(platform, post, img_path, size, meta, page_meta))
    return f'<section class="post {platform}"><h2>{TITLES[platform]}</h2><div class="card">{inner}</div><ul class="checks">{marks}</ul></section>'


CSS = """
:root{color-scheme:light dark;--bg:#f3f2ef;--card:#fff;--ink:#1c1e21;--mute:#65676b;--line:#dadde1;--ok:#1a7f37;--warn:#9a6700;--bad:#cf222e}
@media(prefers-color-scheme:dark){:root{--bg:#18191a;--card:#242526;--ink:#e4e6eb;--mute:#b0b3b8;--line:#3a3b3c;--ok:#3fb950;--warn:#d29922;--bad:#f85149}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,Segoe UI,sans-serif}
header{padding:20px 16px 4px;max-width:1500px;margin:auto}header h1{font-size:20px;margin:0 0 4px}header p{margin:0;color:var(--mute)}
.wrap{display:flex;flex-wrap:wrap;gap:20px;padding:16px;max-width:1500px;margin:auto;align-items:flex-start}
.post{flex:1 1 380px;max-width:520px}.post h2{font-size:15px;margin:0 0 8px;color:var(--mute);text-transform:uppercase;letter-spacing:.06em}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;overflow:hidden}
.head{display:flex;gap:10px;align-items:center;margin-bottom:8px}.head small{display:block;color:var(--mute);font-size:12px}
.av{width:40px;height:40px;border-radius:50%;background:#b6c92e;flex:none}.av.li{border-radius:4px}.av.ig{background:linear-gradient(45deg,#f9a03f,#d6249f,#285aeb)}
.text{white-space:normal;word-wrap:break-word}.vis{}.more-mark{color:var(--mute);font-weight:600}.rest{opacity:.38}.tag{color:#1877f2}.linkedin .tag{color:#0a66c2;font-weight:600}
.added{margin:8px 0;padding:6px 8px;border:1px dashed var(--line);border-radius:6px;font-size:12px;color:var(--mute)}
.media{display:block;width:calc(100% + 24px);margin:8px -12px 0;max-height:640px;object-fit:contain;background:#eee}
.igframe{margin:0 -12px;background:#eee}.igframe .media{margin:0;width:100%;aspect-ratio:4/5;object-fit:cover}
.linkcard{margin:8px -12px 0;border-top:1px solid var(--line);background:rgba(127,127,127,.08)}.linkcard img{width:100%;display:block}.linkcard.warn{outline:2px solid var(--warn);outline-offset:-2px}
.lc-text{padding:8px 12px}.lc-text small{display:block;color:var(--mute);font-size:11px}.noimg{padding:18px 12px;color:var(--warn);font-size:13px}
.thumbs{display:flex;gap:14px;margin-top:12px;padding-top:10px;border-top:1px solid var(--line);align-items:flex-end}.thumbs small{display:block;color:var(--mute);font-size:11px;margin-top:3px}
.sq,.r34{width:110px;overflow:hidden;background:#eee;border:1px solid var(--line)}.sq{aspect-ratio:1}.r34{aspect-ratio:3/4}.sq img,.r34 img{width:100%;height:100%;object-fit:cover;display:block}
.checks{list-style:none;padding:0;margin:10px 2px;font-size:13px}.checks li{padding:2px 0 2px 18px;position:relative}.checks li:before{content:"";position:absolute;left:2px;top:9px;width:8px;height:8px;border-radius:50%;background:var(--ok)}
.checks li.warn:before{background:var(--warn)}.checks li.bad:before{background:var(--bad)}.checks li.warn{color:var(--warn)}.checks li.bad{color:var(--bad);font-weight:600}
footer{max-width:1500px;margin:auto;padding:0 16px 24px;color:var(--mute);font-size:12px}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="bozza in social/, es. social/2026-11-10_titolo.md")
    ap.add_argument("--out", help="cartella di destinazione (default: cartella temporanea)")
    args = ap.parse_args()
    path = Path(args.file)
    path = path if path.is_absolute() else ROOT / path
    text = path.read_text(encoding="utf-8-sig")
    meta, body = parse(text)
    platforms = [x.strip().lower() for x in meta.get("platforms", "").split(",") if x.strip()]
    page = meta.get("page", "")
    target = page_to_content(page)
    page_meta = parse((ROOT / target).read_text(encoding="utf-8-sig"))[0] if target and (ROOT / target).exists() else {}
    img_path = find_image(meta["image"]) if meta.get("image") else None
    size = image_size(img_path) if img_path else None
    cards = "".join(
        card(p, section(body, "LinkedIn" if p == "linkedin" else TITLES[p]), meta, img_path, size, page, page_meta)
        for p in platforms if p in TITLES
    )
    doc = f"""<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Anteprima social: {html.escape(path.name)}</title><style>{CSS}</style></head><body>
<header><h1>Anteprima social: {html.escape(path.name)}</h1>
<p>Pagina del sito: {html.escape(SITE + page)} · stato: {html.escape(meta.get("status", ""))} · le parti attenuate sono nascoste dietro "altro"</p></header>
<div class="wrap">{cards}</div>
<footer>Mock-up approssimativi: grafica e limiti delle piattaforme cambiano. L'approvazione vale per il testo e l'immagine mostrati qui.</footer></body></html>"""
    out_dir = Path(args.out) if args.out else Path(tempfile.gettempdir()) / "geolab-social-preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"preview_{path.stem}.html"
    out.write_text(doc, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
