"""Immagine di anteprima (og:image) di una pagina del sito: solo libreria standard.

Ordine di scelta, usato da build.py e da tools/preview_social.py:
1. `social_image:` nell'intestazione della pagina (scheda orizzontale 1200x630 preparata apposta);
2. `image:` della pagina (la foto di una news), se il file esiste;
3. static/img/og/<nome-del-file>.jpg, la scheda del progetto (logo grande + emblema UE se finanziato);
4. static/img/og-default.jpg, la scheda di ripiego del laboratorio.
Facebook, LinkedIn e i messaggi mostrano questa immagine quando si condivide il link.
"""
from pathlib import Path

SITE_URL = "https://geolabforest.com"
DEFAULT = "/img/og-default.jpg"


def og_image(meta, slug, root):
    """Percorso (dalla radice del sito) dell'immagine di anteprima della pagina."""
    root = Path(root)

    def exists(ref):
        rel = ref.lstrip("/")
        return (root / "docs" / rel).exists() or (root / "static" / rel).exists()

    for key in ("social_image", "image"):
        ref = meta.get(key, "")
        if ref.startswith("/") and exists(ref):
            return ref
    card = f"/img/og/{slug}.jpg"
    return card if exists(card) else DEFAULT
