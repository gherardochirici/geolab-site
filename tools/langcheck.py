"""Controllo di lingua: il sito è SOLO in inglese. Stima la quota di parole italiane in un testo.

Euristica a parole funzionali: non è un riconoscitore di lingua perfetto, ma separa bene testi italiani e inglesi.
"""
import re

ITALIAN = set(
    "il lo la i gli le un una uno di del dello della dei degli delle da dal dalla dai dalle in nel nella nei nelle "
    "su sul sulla con per tra fra che e è ed ma o non si sono come anche più alla questo questa essere stato stata "
    "nuovo nuova nuovi nuove progetto convegno incontro università foreste foresta forestale forestali albero alberi "
    "presso al alle agli allo ai suo sua loro cui dove quando mentre perché cosa dell dall nell sull all verso "
    "giorno sarà si terrà tenuto svolge".split()
)
ENGLISH = set(
    "the of and to in for with on a an is are was were by from at as this that it its be has have will which or not "
    "new our we their these".split()
)


def italian_ratio(text):
    """Quota (0-1) di parole funzionali italiane sul totale di quelle italiane e inglesi. Meno di 5 parole: 0."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    words = re.findall(r"[a-zàèéìòù']+", text.lower())
    if len(words) < 5:
        return 0.0
    it = sum(w in ITALIAN for w in words)
    en = sum(w in ENGLISH for w in words)
    return it / (it + en + 1)
