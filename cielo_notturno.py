"""
Osservatorio Astronomico: cosa e' visibile in cielo da un luogo indicato,
piu sole, luna e condizioni meteo per capire se stasera conviene guardare
in su o no.

Calcola, usando dati astronomici reali (non approssimati):
- Passaggi visibili di ISS e Tiangong nelle prossime ore.
- Satelliti attualmente piu vicini sopra l'orizzonte (dal catalogo
  "satelliti visibili a occhio nudo" di Celestrak).
- Pianeti attualmente sopra l'orizzonte, con altezza e direzione.
- Le stelle piu luminose attualmente visibili.
- Alba e tramonto del sole per i prossimi 7 giorni.
- Fase lunare attuale e prossime fasi principali.
- Copertura nuvolosa prevista stanotte, e un verdetto sintetico se
  conviene osservare o no.

Usa la libreria "skyfield" per i calcoli di meccanica celeste, insieme
a tre fonti di dati pubbliche e gratuite, senza bisogno di alcuna
chiave API:
- Nominatim (OpenStreetMap) per trasformare un indirizzo in
  coordinate geografiche.
- Celestrak per le effemeridi orbitali (TLE) aggiornate dei satelliti.
- Open-Meteo per le previsioni di copertura nuvolosa.

La prima chiamata in assoluto scarica un file di effemeridi planetarie
(~17 MB, "de421.bsp", fonte JPL/NASA): richiede una connessione
internet reale e puo' rendere il primo caricamento un po' piu lento.
Le chiamate successive lo riusano dalla cache locale.
"""

import math
import requests
from datetime import timedelta, datetime

from skyfield.api import Loader, wgs84, EarthSatellite, Star
from skyfield import almanac

TIMEOUT = 12
_load = Loader(".skyfield_cache")

# Satelliti/stazioni abitate seguite: nome mostrato -> numero di catalogo NORAD.
STAZIONI = {
    "Stazione Spaziale Internazionale (ISS)": 25544,
    "Stazione Spaziale Cinese (Tiangong)": 48274,
}

# Pianeti seguiti: nome mostrato -> nome del corpo nelle effemeridi de421.
PIANETI = {
    "Mercurio": "mercury",
    "Venere": "venus",
    "Marte": "mars",
    "Giove": "jupiter barycenter",
    "Saturno": "saturn barycenter",
}

# Le stelle piu' luminose visibili dalla Terra (nome, ascensione retta in
# ore, declinazione in gradi, magnitudine apparente). Posizioni J2000,
# stabili per uso amatoriale.
STELLE_PRINCIPALI = [
    ("Sirio", 6.7525, -16.7161, -1.46),
    ("Canopo", 6.3992, -52.6957, -0.72),
    ("Arturo", 14.2610, 19.1825, -0.05),
    ("Vega", 18.6156, 38.7837, 0.03),
    ("Capella", 5.2782, 45.9980, 0.08),
    ("Rigel", 5.2423, -8.2016, 0.13),
    ("Procione", 7.6550, 5.2250, 0.34),
    ("Achernar", 1.6286, -57.2367, 0.46),
    ("Betelgeuse", 5.9195, 7.4071, 0.50),
    ("Altair", 19.8464, 8.8683, 0.77),
    ("Aldebaran", 4.5987, 16.5093, 0.85),
    ("Antares", 16.4901, -26.4320, 1.09),
    ("Spica", 13.4199, -11.1613, 0.97),
    ("Polluce", 7.7553, 28.0262, 1.14),
    ("Fomalhaut", 22.9608, -29.6222, 1.16),
    ("Deneb", 20.6905, 45.2803, 1.25),
    ("Stella Polare", 2.5303, 89.2641, 1.98),
]


def _direzione_bussola(azimut_gradi):
    """Converte un azimut in gradi nel punto cardinale piu vicino."""
    punti = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    indice = round(azimut_gradi / 45) % 8
    return punti[indice]


def geocodifica_indirizzo(indirizzo):
    """Trasforma un indirizzo (via, citta, ecc.) in coordinate geografiche.

    Usa Nominatim (OpenStreetMap), gratuito e senza chiave API, ma con
    l'obbligo di dichiarare un User-Agent identificabile.
    Restituisce {"lat":.., "lon":.., "nome":..} oppure None se non trovato.
    """
    try:
        risposta = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": indirizzo, "format": "json", "limit": 1},
            headers={"User-Agent": "ArchivioMissioniSpaziali/1.0"},
            timeout=TIMEOUT,
        )
        risposta.raise_for_status()
        risultati = risposta.json()
    except Exception:
        return None

    if not risultati:
        return None

    primo = risultati[0]
    return {
        "lat": float(primo["lat"]),
        "lon": float(primo["lon"]),
        "nome": primo.get("display_name", indirizzo),
    }


def _carica_satellite(norad_id, nome_predefinito, timescale):
    """Scarica le effemeridi orbitali (TLE) aggiornate di un satellite da Celestrak."""
    risposta = requests.get(
        "https://celestrak.org/NORAD/elements/gp.php",
        params={"CATNR": norad_id, "FORMAT": "TLE"},
        timeout=TIMEOUT,
    )
    risposta.raise_for_status()
    righe = [r for r in risposta.text.strip().splitlines() if r.strip()]
    if len(righe) < 3:
        return None
    nome, riga1, riga2 = righe[0].strip(), righe[1], righe[2]
    return EarthSatellite(riga1, riga2, nome or nome_predefinito, timescale)


def passaggi_satelliti(lat, lon, ore_finestra=48, altezza_minima_gradi=10):
    """Prossimi passaggi visibili a occhio nudo di ISS e Tiangong.

    Un passaggio e' considerato "visibile" solo se il satellite e'
    illuminato dal sole E il cielo dell'osservatore e' abbastanza
    scuro (crepuscolo civile o oltre) — altrimenti il satellite c'e'
    ma non si vede, oppure e' giorno pieno e non si vede comunque.
    """
    ts = _load.timescale()
    eph = _load("de421.bsp")
    osservatore = wgs84.latlon(lat, lon)
    sole = eph["sun"]
    terra = eph["earth"]

    t0 = ts.now()
    t1 = ts.from_datetime(t0.utc_datetime() + timedelta(hours=ore_finestra))

    risultati = []
    for nome_mostrato, norad_id in STAZIONI.items():
        try:
            satellite = _carica_satellite(norad_id, nome_mostrato, ts)
            if satellite is None:
                continue
            t_eventi, eventi = satellite.find_events(
                osservatore, t0, t1, altitude_degrees=altezza_minima_gradi
            )
        except Exception:
            continue

        # Raggruppa gli eventi (0=sorge, 1=culmine, 2=tramonta) in passaggi.
        passaggio_corrente = {}
        for t, codice_evento in zip(t_eventi, eventi):
            if codice_evento == 0:
                passaggio_corrente = {"inizio": t}
            elif codice_evento == 1:
                passaggio_corrente["culmine"] = t
            elif codice_evento == 2 and "inizio" in passaggio_corrente:
                passaggio_corrente["fine"] = t
                t_culmine = passaggio_corrente.get("culmine", t)

                satellite_illuminato = satellite.at(t_culmine).is_sunlit(eph)
                posizione_sole = (terra + osservatore).at(t_culmine).observe(sole).apparent()
                altezza_sole, _, _ = posizione_sole.altaz()
                cielo_abbastanza_scuro = altezza_sole.degrees < -6

                if satellite_illuminato and cielo_abbastanza_scuro:
                    # Direzione e altezza al culmine, per dare un riferimento pratico.
                    diff = satellite - osservatore
                    alt_culm, az_culm, _ = diff.at(t_culmine).altaz()
                    risultati.append({
                        "satellite": nome_mostrato,
                        "inizio": passaggio_corrente["inizio"].utc_datetime(),
                        "fine": t.utc_datetime(),
                        "altezza_massima": round(alt_culm.degrees),
                        "direzione": _direzione_bussola(az_culm.degrees),
                    })
                passaggio_corrente = {}

    risultati.sort(key=lambda p: p["inizio"])
    return risultati


def pianeti_visibili(lat, lon):
    """Pianeti attualmente sopra l'orizzonte, con altezza e direzione.

    Include anche quelli sotto l'orizzonte in questo momento, segnalati
    come tali, cosi' si vede a colpo d'occhio cosa manca stanotte.
    """
    ts = _load.timescale()
    eph = _load("de421.bsp")
    osservatore = wgs84.latlon(lat, lon)
    terra = eph["earth"]
    ora = ts.now()

    risultati = []
    for nome_mostrato, nome_corpo in PIANETI.items():
        try:
            corpo = eph[nome_corpo]
        except KeyError:
            continue
        astrometria = (terra + osservatore).at(ora).observe(corpo).apparent()
        altezza, azimut, _ = astrometria.altaz()
        risultati.append({
            "nome": nome_mostrato,
            "visibile_ora": altezza.degrees > 0,
            "altezza": round(altezza.degrees),
            "direzione": _direzione_bussola(azimut.degrees),
        })

    risultati.sort(key=lambda p: (-p["visibile_ora"], -p["altezza"]))
    return risultati


def stelle_visibili(lat, lon, limite=10):
    """Le stelle piu luminose attualmente sopra l'orizzonte, dalla piu alla meno luminosa."""
    ts = _load.timescale()
    eph = _load("de421.bsp")
    osservatore = wgs84.latlon(lat, lon)
    terra = eph["earth"]
    ora = ts.now()

    visibili = []
    for nome, ascensione_retta, declinazione, magnitudine in STELLE_PRINCIPALI:
        stella = Star(ra_hours=ascensione_retta, dec_degrees=declinazione)
        astrometria = (terra + osservatore).at(ora).observe(stella).apparent()
        altezza, azimut, _ = astrometria.altaz()
        if altezza.degrees > 0:
            visibili.append({
                "nome": nome,
                "altezza": round(altezza.degrees),
                "direzione": _direzione_bussola(azimut.degrees),
                "magnitudine": magnitudine,
            })

    visibili.sort(key=lambda s: s["magnitudine"])
    return visibili[:limite]


def satelliti_vicini(lat, lon, limite=5):
    """I satelliti (dal catalogo dei visibili a occhio nudo) attualmente
    piu vicini, tra quelli sopra l'orizzonte in questo momento.

    Usa il gruppo "visual" di Celestrak (satelliti noti per essere
    luminosi abbastanza da vedersi a occhio nudo, non solo ISS/Tiangong).
    """
    ts = _load.timescale()
    osservatore = wgs84.latlon(lat, lon)
    ora = ts.now()

    try:
        risposta = requests.get(
            "https://celestrak.org/NORAD/elements/gp.php",
            params={"GROUP": "visual", "FORMAT": "TLE"},
            timeout=TIMEOUT,
        )
        risposta.raise_for_status()
        righe = [r for r in risposta.text.strip().splitlines() if r.strip()]
    except Exception:
        return []

    visibili = []
    for i in range(0, len(righe) - 2, 3):
        nome, riga1, riga2 = righe[i].strip(), righe[i + 1], righe[i + 2]
        try:
            satellite = EarthSatellite(riga1, riga2, nome, ts)
            diff = satellite - osservatore
            altezza, azimut, distanza = diff.at(ora).altaz()
        except Exception:
            continue
        if altezza.degrees > 0:
            visibili.append({
                "nome": nome,
                "altezza": round(altezza.degrees),
                "direzione": _direzione_bussola(azimut.degrees),
                "distanza_km": round(distanza.km),
            })

    visibili.sort(key=lambda s: s["distanza_km"])
    return visibili[:limite]


def sole_settimana(lat, lon, giorni=7):
    """Orari di alba e tramonto del sole per i prossimi N giorni."""
    ts = _load.timescale()
    eph = _load("de421.bsp")
    osservatore = wgs84.latlon(lat, lon)

    t0 = ts.now()
    t1 = ts.from_datetime(t0.utc_datetime() + timedelta(days=giorni))
    f = almanac.sunrise_sunset(eph, osservatore)
    tempi, sorge = almanac.find_discrete(t0, t1, f)

    risultati = []
    giorno_corrente = {}
    for t, e_alba in zip(tempi, sorge):
        dt = t.utc_datetime()
        if e_alba:
            giorno_corrente = {"data": dt.strftime("%d/%m"), "alba": dt.strftime("%H:%M")}
        else:
            giorno_corrente["tramonto"] = dt.strftime("%H:%M")
            if "alba" in giorno_corrente:
                risultati.append(giorno_corrente)
            giorno_corrente = {}

    return risultati[:giorni]


_NOMI_FASI = ["Luna nuova", "Primo quarto", "Luna piena", "Ultimo quarto"]


def fase_lunare(lat, lon):
    """Fase lunare attuale (nome e percentuale illuminata) e prossime
    quattro fasi principali nei giorni a venire."""
    ts = _load.timescale()
    eph = _load("de421.bsp")
    ora = ts.now()

    angolo_fase = almanac.moon_phase(eph, ora).degrees
    illuminazione = round(almanac.fraction_illuminated(eph, "moon", ora) * 100)

    if angolo_fase < 45 or angolo_fase >= 315:
        nome_fase = "Luna nuova"
    elif angolo_fase < 135:
        nome_fase = "Luna crescente (primo quarto)"
    elif angolo_fase < 225:
        nome_fase = "Luna piena"
    else:
        nome_fase = "Luna calante (ultimo quarto)"

    t0 = ts.now()
    t1 = ts.from_datetime(t0.utc_datetime() + timedelta(days=30))
    tempi, codici_fase = almanac.find_discrete(t0, t1, almanac.moon_phases(eph))

    prossime_fasi = [
        {"fase": _NOMI_FASI[codice], "data": t.utc_datetime().strftime("%d/%m")}
        for t, codice in zip(tempi[:4], codici_fase[:4])
    ]

    return {
        "fase_attuale": nome_fase,
        "illuminazione_percento": illuminazione,
        "prossime_fasi": prossime_fasi,
    }


def meteo_stanotte(lat, lon):
    """Copertura nuvolosa media prevista nelle prossime ore (Open-Meteo,
    gratuito, nessuna chiave richiesta)."""
    try:
        risposta = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "hourly": "cloudcover", "forecast_days": 1, "timezone": "auto",
            },
            timeout=TIMEOUT,
        )
        risposta.raise_for_status()
        dati = risposta.json()
        valori = dati.get("hourly", {}).get("cloudcover", [])
    except Exception:
        return None

    if not valori:
        return None

    # Nuvolosita media sulle prossime ore disponibili nella previsione,
    # come stima approssimativa delle condizioni di "stanotte".
    prossime_ore = valori[:12]
    return round(sum(prossime_ore) / len(prossime_ore))


def si_vede_stasera(lat, lon):
    """Verdetto sintetico: conviene osservare il cielo stasera o no,
    in base soprattutto alla nuvolosita prevista."""
    nuvolosita = meteo_stanotte(lat, lon)
    dati_luna = fase_lunare(lat, lon)

    if nuvolosita is None:
        return {
            "verdetto": "Condizioni meteo non disponibili al momento.",
            "nuvolosita_percento": None,
            "illuminazione_lunare_percento": dati_luna["illuminazione_percento"],
        }

    if nuvolosita < 30:
        verdetto = "✅ Sì, condizioni ottime per osservare stasera."
    elif nuvolosita < 70:
        verdetto = "🟡 Parzialmente: nuvolosita media prevista, potrebbe schiarire a tratti."
    else:
        verdetto = "❌ Difficile stasera: cielo previsto molto nuvoloso."

    return {
        "verdetto": verdetto,
        "nuvolosita_percento": nuvolosita,
        "illuminazione_lunare_percento": dati_luna["illuminazione_percento"],
    }
