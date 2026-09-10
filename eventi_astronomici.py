"""
Eventi astronomici: equinozi/solstizi (calcolati con precisione),
principali piogge di meteore annuali, ed eclissi del 2026.

Gli equinozi e i solstizi sono calcolati con "skyfield" (stesso motore
di calcolo usato per l'Osservatorio Astronomico), quindi sono esatti
per l'anno richiesto, non approssimati.

Le piogge di meteore hanno una data di picco che si ripete quasi
identica ogni anno (dipende dall'orbita terrestre, non cambia molto
nel tempo): sono quindi elencate come ricorrenze annuali.

Le date delle eclissi 2026 sono verificate da fonti pubbliche
astronomiche (in UTC); per la visibilita dall'Italia sono indicate
solo informazioni generali, non calcolate per una posizione specifica.
"""

from datetime import datetime, timezone
from skyfield.api import Loader
from skyfield import almanac

_load = Loader(".skyfield_cache")

# Piogge di meteore principali, con la data approssimativa del picco
# (giorno/mese, si ripete quasi identica ogni anno).
PIOGGE_METEORE = [
    ("Quadrantidi", 1, 3),
    ("Liridi", 4, 22),
    ("Eta Acquaridi", 5, 5),
    ("Perseidi", 8, 12),
    ("Orionidi", 10, 21),
    ("Leonidi", 11, 17),
    ("Geminidi", 12, 14),
    ("Ursidi", 12, 22),
]

# Eclissi del 2026, con date verificate (UTC). Le percentuali/durate
# sono indicazioni generali, non calcolate per un luogo specifico.
ECLISSI_2026 = [
    {
        "data": "2026-02-17",
        "titolo": "Eclissi solare anulare",
        "descrizione": "\"Anello di fuoco\": non visibile dall'Italia, osservabile soprattutto nell'emisfero sud.",
    },
    {
        "data": "2026-03-03",
        "titolo": "Eclissi lunare totale (\"Luna rossa\")",
        "descrizione": "Eclissi totale di Luna, visibile anche dall'Italia nelle ore notturne.",
    },
    {
        "data": "2026-08-12",
        "titolo": "Eclissi solare totale",
        "descrizione": "Totale in alcune aree artiche/Groenlandia/Islanda; dall'Italia visibile come parziale, con il Sole coperto per circa il 70-90% a seconda della zona, nel tardo pomeriggio.",
    },
    {
        "data": "2026-08-28",
        "titolo": "Eclissi lunare parziale",
        "descrizione": "Oltre il 90% del disco lunare coperto dall'ombra della Terra; visibile anche dall'Italia.",
    },
]


def equinozi_solstizi(anno):
    """Date e orari (UTC) di equinozi e solstizi per l'anno indicato,
    calcolati con precisione astronomica reale."""
    ts = _load.timescale()
    eph = _load("de421.bsp")

    t0 = ts.utc(anno, 1, 1)
    t1 = ts.utc(anno + 1, 1, 1)
    tempi, codici = almanac.find_discrete(t0, t1, almanac.seasons(eph))

    nomi = {
        0: "Equinozio di primavera",
        1: "Solstizio d'estate",
        2: "Equinozio d'autunno",
        3: "Solstizio d'inverno",
    }
    return [
        {"titolo": nomi[codice], "data": t.utc_datetime()}
        for t, codice in zip(tempi, codici)
    ]


def prossime_piogge_meteore(oggi=None, entro_giorni=365):
    """Prossime piogge di meteore in ordine cronologico, a partire da oggi."""
    if oggi is None:
        oggi = datetime.now(timezone.utc).date()

    risultati = []
    for nome, mese, giorno in PIOGGE_METEORE:
        prossima = datetime(oggi.year, mese, giorno, tzinfo=timezone.utc).date()
        if prossima < oggi:
            prossima = datetime(oggi.year + 1, mese, giorno, tzinfo=timezone.utc).date()
        risultati.append({"titolo": f"Picco pioggia di meteore: {nome}", "data": prossima})

    risultati.sort(key=lambda r: r["data"])
    return risultati


def prossime_eclissi(oggi=None):
    """Eclissi 2026 ancora da venire rispetto a oggi."""
    if oggi is None:
        oggi = datetime.now(timezone.utc).date()

    risultati = []
    for e in ECLISSI_2026:
        data_eclissi = datetime.strptime(e["data"], "%Y-%m-%d").date()
        if data_eclissi >= oggi:
            risultati.append({
                "titolo": e["titolo"],
                "data": data_eclissi,
                "descrizione": e["descrizione"],
            })
    return risultati
