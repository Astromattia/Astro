"""
Notizie spaziali recenti, recuperate dai feed RSS ufficiali di NASA ed ESA.

Sono entrambe fonti pubbliche e gratuite, senza bisogno di alcuna chiave
API. Il parsing usa la libreria "feedparser", che gestisce da sola le
tante piccole differenze tra i vari formati RSS/Atom in circolazione.
"""

import feedparser

TIMEOUT = 12

FONTI = {
    "NASA": "https://www.nasa.gov/feed/",
    "ESA": "https://www.esa.int/rssfeed/Our_Activities/Space_News",
}


def _data_leggibile(voce):
    """Estrae una data leggibile (o stringa vuota se non disponibile)."""
    for campo in ("published", "updated"):
        valore = getattr(voce, campo, None)
        if valore:
            return valore[:16]  # taglia l'eventuale fuso orario finale
    return ""


def recupera_notizie(fonte, limite=8):
    """Scarica e normalizza le ultime notizie da una fonte ('NASA' o 'ESA').

    Restituisce una lista di dict {titolo, data, link, fonte}, oppure
    lista vuota se il feed non e' raggiungibile (mai un'eccezione che
    blocchi il resto della pagina).
    """
    url = FONTI.get(fonte)
    if not url:
        return []

    try:
        feed = feedparser.parse(url)
    except Exception:
        return []

    if getattr(feed, "bozo", False) and not getattr(feed, "entries", None):
        return []

    notizie = []
    for voce in feed.entries[:limite]:
        notizie.append({
            "titolo": getattr(voce, "title", "Senza titolo"),
            "data": _data_leggibile(voce),
            "link": getattr(voce, "link", ""),
            "fonte": fonte,
        })
    return notizie


def recupera_tutte_le_notizie(limite_per_fonte=8):
    """Notizie da tutte le fonti configurate, ordinate per fonte."""
    tutte = {}
    for fonte in FONTI:
        tutte[fonte] = recupera_notizie(fonte, limite_per_fonte)
    return tutte
