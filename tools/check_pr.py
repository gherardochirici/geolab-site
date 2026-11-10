"""Controlli automatici su una pull request del sito geoLAB (solo libreria standard).

Uso: python -I tools/check_pr.py --base origin/main
Confronta HEAD con la base, controlla solo i file modificati e stampa annotazioni GitHub
(::error / ::warning). Esce con 1 se trova errori. Gli avvisi non bloccano: li valuta chi approva.
Le regole sono quelle di CLAUDE.md: solo inglese, fatti pubblici, emblema UE, dati personali.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from langcheck import italian_ratio  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_PREFIXES = ("content/", "static/", "docs/media/", "social/")
INFRA_PREFIXES = (".github/", "tools/", "build.py", "CLAUDE.md", "README.md", "redirects.json", ".gitignore")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<!\d)(?:\+\d{1,3}[\s.-]?)?(?:\d[\s.-]?){9,12}\d(?!\d)")
SENSITIVE = re.compile(r"\b(budget|embargo|confidential|not (?:yet )?public|draft deliverable|internal use)\b", re.I)
FUNDING_HINT = re.compile(r"horizon europe|horizon 2020|LIFE programme|grant agreement|funded by the european union", re.I)
REA_TEXT = "Funded by the European Union. Views and opinions expressed are however those of the author(s) only"
MAX_IMAGE_BYTES = 1_500_000

errors, warnings = [], []


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def report(level, path, msg):
    (errors if level == "error" else warnings).append((path, msg))
    print(f"::{level} file={path}::{msg}")


def parse(text):
    meta, body = {}, text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].strip().splitlines():
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
            body = parts[2]
    return meta, body


def check_markdown(path, status):
    text = (ROOT / path).read_text(encoding="utf-8-sig")
    meta, body = parse(text)
    if not text.startswith("---") or not meta.get("title"):
        report("error", path, "Missing front matter or title (see CLAUDE.md).")
        return
    if meta.get("lang") == "it":
        report("error", path, "`lang: it` is not allowed: the site is English only.")
    ratio = italian_ratio(meta.get("title", "") + " " + body)
    if ratio >= 0.5:
        report("error", path, f"The text looks Italian (ratio {ratio:.2f}). The site is English only: translate it.")
    elif ratio >= 0.3:
        report("warning", path, f"Some text may be Italian (ratio {ratio:.2f}). Please check.")
    section = path.split("/")[1] if path.startswith("content/") and path.count("/") >= 2 else ""
    if section == "news" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta.get("date", "")):
        report("error", path, "News need `date: YYYY-MM-DD` in the front matter.")
    if meta.get("image") and not meta.get("alt"):
        report("error", path, "`image` without `alt`: add an English alternative text.")
    for ref in re.findall(r"!\[[^\]]*\]\((/[^)\s]+)\)", body) + ([meta["image"]] if meta.get("image", "").startswith("/") else []):
        if not ((ROOT / "docs" / ref.lstrip("/")).exists() or (ROOT / "static" / ref.lstrip("/")).exists()):
            report("error", path, f"The image {ref} is not in docs/media/ or static/.")
    for alt in re.findall(r"!\[([^\]]*)\]\(", body):
        if not alt.strip():
            report("warning", path, "An image in the text has an empty alternative text.")
            break
    funded = bool(FUNDING_HINT.search(text)) or meta.get("emblem") == "yes"
    if funded and section in ("projects", "news"):
        if meta.get("emblem") != "yes" or not meta.get("funding"):
            report("warning", path, "Mentions EU/project funding but lacks `emblem: yes` and `funding:`. Funded projects need the EU emblem and the full funding text.")
        elif meta["funding"].startswith("Funded by the European Union") and REA_TEXT not in meta["funding"]:
            report("warning", path, "The funding text differs from the standard REA wording. Check it against the Grant Agreement.")
    if path.startswith("content/pages/people") is False:
        for addr in EMAIL.findall(text):
            report("error", path, f"Email address {addr}: do not publish emails. Use name.surname(at)unifi.it for colleagues.")
    if PHONE.search(re.sub(r"\d{4}-\d{2}-\d{2}", "", body)) and section != "publications":
        report("warning", path, "A phone-number-like string was found. Do not publish phone numbers of third parties.")
    if SENSITIVE.search(body):
        report("warning", path, "Wording suggests non-public information (budget, embargo, confidential...). Confirm the content is public.")


def page_to_content(page):
    """/news/2026-11-20-titolo/ -> content/news/2026-11-20-titolo.md (None se il formato non è valido)."""
    m = re.fullmatch(r"/(news|projects|publications|research|courses)/([\w.-]+)/?", page)
    return f"content/{m.group(1)}/{m.group(2)}.md" if m else None


def check_social(path):
    """Bozza di post social collegata a una pagina del sito (cartella social/)."""
    text = (ROOT / path).read_text(encoding="utf-8-sig")
    meta, body = parse(text)
    if meta.get("status") != "draft":
        report("error", path, "`status` must be `draft` in a pull request: only the owner publishes.")
    platforms = [x.strip().lower() for x in (meta.get("platforms") or "").split(",") if x.strip()]
    if not platforms or any(x not in ("facebook", "instagram", "linkedin") for x in platforms):
        report("error", path, "`platforms:` must list `facebook`, `instagram` and/or `linkedin` (the lab's accounts).")
    page = meta.get("page", "")
    target = page_to_content(page)
    target_meta = {}
    if not target:
        report("error", path, "`page:` must be the site path of the page, e.g. /news/2026-11-20-title/.")
    elif not (ROOT / target).exists():
        report("error", path, f"`page: {page}` does not match any file ({target}).")
    else:
        target_meta, _ = parse((ROOT / target).read_text(encoding="utf-8-sig"))
    if meta.get("image"):
        if not meta.get("alt"):
            report("error", path, "`image` without `alt`: add an English alternative text.")
        ref = meta["image"].lstrip("/")
        if not ((ROOT / "docs" / ref).exists() or (ROOT / "static" / ref).exists()):
            report("error", path, f"The image {meta['image']} is not in docs/media/ or static/.")
    for platform in platforms:
        if platform not in ("facebook", "instagram", "linkedin"):
            continue
        title = "LinkedIn" if platform == "linkedin" else platform.capitalize()
        m = re.search(rf"^## {title}\s*\n(.*?)(?=^## |\Z)", body, re.S | re.M | re.I)
        post = m.group(1).strip() if m else ""
        if not post:
            report("error", path, f"`platforms` lists {platform} but the `## {title}` section is missing or empty.")
            continue
        if re.search(r"\[(DA COMPLETARE|TODO|TBD)", post, re.I):
            report("error", path, f"The {title} post still has placeholders to complete.")
        ratio = italian_ratio(post)
        if ratio >= 0.5:
            report("error", path, f"The {title} post looks Italian (ratio {ratio:.2f}). English only.")
        if target_meta.get("emblem") == "yes" and target_meta.get("funding") and target_meta["funding"] not in post:
            report("error", path, f"The linked page is EU-funded: the {title} post must include the full funding text, unshortened.")
        hashtags = len(re.findall(r"(?<!\w)#\w+", post))
        if EMAIL.search(post):
            report("error", path, f"Do not publish email addresses in the {title} post.")
        if SENSITIVE.search(post):
            report("warning", path, f"Wording in the {title} post suggests non-public information. Confirm the content is public.")
        if platform == "facebook":
            if len(post) > 1500:
                report("warning", path, f"The Facebook post is long ({len(post)} characters). 300-600 characters plus the funding text work best.")
            if hashtags > 2:
                report("warning", path, "More than 2 hashtags: Facebook posts use 0-2.")
        elif platform == "linkedin":
            if len(post) < 500 or len(post) > 3000:
                report("warning", path, f"The LinkedIn post has {len(post)} characters: 800-1,500 work best, 3,000 is the limit.")
            if not 3 <= hashtags <= 5:
                report("warning", path, f"LinkedIn posts use 3-5 hashtags at the end ({hashtags} found).")
        else:
            if not meta.get("image"):
                report("error", path, "Instagram needs an image: add `image:` and `alt:` (square 1080x1080 or vertical 1080x1350).")
            if len(post) > 2200:
                report("error", path, f"The Instagram caption is {len(post)} characters: the limit is 2,200.")
            if not 5 <= hashtags <= 10:
                report("warning", path, f"Instagram captions use 5-10 hashtags at the end ({hashtags} found).")
            if re.search(r"https?://", post):
                report("warning", path, "Links in Instagram captions are not clickable: mention the site name instead.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="riferimento git della base, es. origin/main")
    args = ap.parse_args()
    changed = [line.split("\t") for line in git("diff", "--name-status", "--no-renames", f"{args.base}...HEAD").splitlines() if line]
    print(f"Checking {len(changed)} changed file(s) against {args.base}")
    for status, path in changed:
        if status == "D":
            continue
        if path.startswith(INFRA_PREFIXES):
            report("warning", path, "Infrastructure file changed (build, workflow, rules): the owner must review it carefully.")
            continue
        if not path.startswith(ALLOWED_PREFIXES):
            report("error", path, "File outside content/, static/, social/ and docs/media/. Generated files in docs/ must not be committed.")
            continue
        if path.startswith("content/") and path.endswith(".md"):
            check_markdown(path, status)
            section = path.split("/")[1]
            has_social = any(p.startswith("social/") and p.endswith(".md") and not p.startswith("social/_") for _, p in changed)
            if status == "A" and section in ("news", "projects") and not has_social:
                report("warning", path, "New page without a social post draft (social/): add one if it deserves a post on the lab's Facebook page.")
        elif path.startswith("social/") and path.endswith(".md") and not Path(path).name.startswith("_"):
            check_social(path)
        elif path.startswith("docs/media/"):
            if path.lower().endswith((".jpg", ".jpeg", ".png", ".webp")) and (ROOT / path).stat().st_size > MAX_IMAGE_BYTES:
                report("warning", path, "Image larger than 1.5 MB: run `python tools/optimize_media.py` (max 1600 px).")
            if not path.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".pdf", ".mp4")):
                report("warning", path, "Unusual file type in the image store.")
    summary = [f"### Automatic checks: {len(errors)} error(s), {len(warnings)} warning(s)", ""]
    summary += [f"- **error** `{p}`: {m}" for p, m in errors] + [f"- warning `{p}`: {m}" for p, m in warnings]
    if not errors and not warnings:
        summary.append("No issues found. A human review of facts, consent and tone is still required.")
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write("\n".join(summary) + "\n")
    print("\n".join(summary))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
