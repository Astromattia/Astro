"""
Osservatorio Astronomico - modulo dati
-------------------------------------------------
Tutte le funzioni interrogano fonti reali (Nominatim/OSM, Celestrak/NORAD,
effemeridi JPL via Skyfield, Astral, Open-Meteo). Nessun dato fittizio o
placeholder: se una fonte non risponde, la funzione restituisce None o una
lista vuota e la UI mostra un avviso.
"""

from datetime import timedelta, date, datetime
import requests

from astral import LocationInfo
from astral.sun import sun
from astral import moon as astral_moon

from skyfield.api import Loader, wgs84, EarthSatellite, Star
from skyfield import almanac

TIMEOUT = 12

_load = Loader(".skyfield_cache")

STAZIONI = {
    "Stazione Spaziale Internazionale (ISS)": 25544,
    "Stazione Spaziale Cinese (Tiangong)": 48274,
    "Hubble Space Telescope": 20580,
}

PIANETI = {
    "Mercurio": "mercury",
    "Venere": "venus",
    "Marte": "mars",
    "Giove": "jupiter barycenter",
    "Saturno": "saturn barycenter",
}

STELLE_PRINCIPALI = [
    ("Sirio", 6.7525, -16.7161, -1.46),
    ("Canopo", 6.3992, -52.6957, -0.72),
    ("Arturo", 14.2610, 19.1825, -0.05),
    ("Vega", 18.6156, 38.7837, 0.03),
    ("Capella", 5.2782, 45.9980, 0.08),
    ("Rigel", 5.2423, -8.2016, 0.13),
    ("Procione", 7.6550, 5.2250, 0.34),
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

SCIAMI_METEORICI = [
    {"nome": "Quadrantidi", "inizio": (12, 28), "fine": (1, 12), "picco": "3-4 gennaio", "periodo": "28 dicembre - 12 gennaio"},
    {"nome": "Lyridi", "inizio": (4, 14), "fine": (4, 30), "picco": "22 aprile", "periodo": "14-30 aprile"},
    {"nome": "Eta Aquaridi", "inizio": (4, 19), "fine": (5, 28), "picco": "5 maggio", "periodo": "19 aprile - 28 maggio"},
    {"nome": "Delta Aquaridi Sud", "inizio": (7, 12), "fine": (8, 23), "picco": "30 luglio", "periodo": "12 luglio - 23 agosto"},
    {"nome": "Perseidi", "inizio": (7, 17), "fine": (8, 24), "picco": "12-13 agosto", "periodo": "17 luglio - 24 agosto"},
    {"nome": "Tauridi Sud", "inizio": (9, 10), "fine": (11, 20), "picco": "5 novembre", "periodo": "10 settembre - 20 novembre"},
    {"nome": "Orionidi", "inizio": (10, 2), "fine": (11, 7), "picco": "21 ottobre", "periodo": "2 ottobre - 7 novembre"},
    {"nome": "Tauridi Nord", "inizio": (10, 20), "fine": (12, 10), "picco": "12 novembre", "periodo": "20 ottobre - 10 dicembre"},
    {"nome": "Leonidi", "inizio": (11, 6), "fine": (11, 30), "picco": "17-18 novembre", "periodo": "6-30 novembre"},
    {"nome": "Geminidi", "inizio": (12, 4), "fine": (12, 17), "picco": "14 dicembre", "periodo": "4-17 dicembre"},
    {"nome": "Ursidi", "inizio": (12, 17), "fine": (12, 26), "picco": "22 dicembre", "periodo": "17-26 dicembre"},
]

URL_STARLINK_TLE = "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=TLE"


def _direzione_bussola(azimut):
    punti = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    return punti[round(azimut / 45) % 8]


def _geocodifica_nominatim(indirizzo):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": indirizzo, "format": "json", "limit": 1},
            headers={
                "User-Agent": "ArchivioMissioniSpaziali/1.0 (app osservazione astronomica)",
                "Accept-Language": "it",
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        dati = r.json()
        if not dati:
            return None, "Nominatim: nessun risultato per questo indirizzo"
        p = dati[0]
        return {"lat": float(p["lat"]), "lon": float(p["lon"]), "nome": p["display_name"]}, None
    except Exception as e:
        return None, f"Nominatim: {type(e).__name__}: {e}"


def _geocodifica_open_meteo(indirizzo):
    termine = indirizzo.split(",")[-1].strip() or indirizzo

    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": termine, "count": 1, "language": "it", "format": "json"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        dati = r.json()
        risultati = dati.get("results")
        if not risultati:
            return None, f"Open-Meteo: nessun risultato per '{termine}'"
        p = risultati[0]
        parti = [p.get("name"), p.get("admin1"), p.get("country")]
        nome = ", ".join(x for x in parti if x)
        return {"lat": float(p["latitude"]), "lon": float(p["longitude"]), "nome": nome}, None
    except Exception as e:
        return None, f"Open-Meteo: {type(e).__name__}: {e}"


def geocodifica_indirizzo(indirizzo):
    risultato, _ = _geocodifica_nominatim(indirizzo)
    if risultato:
        return risultato
    risultato, _ = _geocodifica_open_meteo(indirizzo)
    return risultato


def geocodifica_indirizzo_debug(indirizzo):
    """Come geocodifica_indirizzo, ma restituisce anche i messaggi di errore
    reali di ciascun tentativo, per capire perche' online non funziona."""

    errori = []

    risultato, errore = _geocodifica_nominatim(indirizzo)
    if risultato:
        return risultato, errori
    if errore:
        errori.append(errore)

    risultato, errore = _geocodifica_open_meteo(indirizzo)
    if risultato:
        return risultato, errori
    if errore:
        errori.append(errore)

    return None, errori


def _carica_satellite(norad_id, ts):
    r = requests.get(
        "https://celestrak.org/NORAD/elements/gp.php",
        params={"CATNR": norad_id, "FORMAT": "TLE"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    righe = [x.strip() for x in r.text.splitlines() if x.strip()]
    if len(righe) < 3:
        return None
    return EarthSatellite(righe[1], righe[2], righe[0], ts)


def _e_buio(eph, osservatore, t):
    terra = eph["earth"]
    sole = eph["sun"]
    posizione = (terra + osservatore).at(t).observe(sole).apparent()
    altezza, _, _ = posizione.altaz()
    return altezza.degrees < -6.0


def _prossimi_passaggi_satellite(sat, nome, eph, osservatore, ore=48, altezza_minima=10.0):
    t0 = _load.timescale().now()
    t1 = t0 + timedelta(hours=ore)
    try:
        tempi, eventi = sat.find_events(osservatore, t0, t1, altitude_degrees=altezza_minima)
    except Exception:
        return []

    passaggi = []
    inizio = None
    apice_t = None
    apice_alt = None
    apice_az = None

    for t, evento in zip(tempi, eventi):
        if evento == 0:
            inizio = t
            apice_t = None
            apice_alt = None
            apice_az = None
        elif evento == 1:
            topocentrico = (sat - osservatore).at(t)
            alt, az, _ = topocentrico.altaz()
            apice_t = t
            apice_alt = alt.degrees
            apice_az = az.degrees
        elif evento == 2 and inizio is not None:
            fine = t
            momento_verifica = apice_t or fine
            try:
                sunlit = sat.at(momento_verifica).is_sunlit(eph)
            except Exception:
                sunlit = False
            if sunlit and _e_buio(eph, osservatore, momento_verifica) and apice_alt is not None:
                passaggi.append({
                    "satellite": nome,
                    "inizio": inizio.utc_datetime(),
                    "fine": fine.utc_datetime(),
                    "altezza_massima": round(apice_alt),
                    "direzione": _direzione_bussola(apice_az),
                })
            inizio = None

    return passaggi


def previsioni_sole(lat, lon, giorni=7):
    luogo = LocationInfo(latitude=lat, longitude=lon)
    risultati = []
    oggi = date.today()
    for i in range(giorni):
        giorno = oggi + timedelta(days=i)
        dati = sun(luogo.observer, date=giorno)
        risultati.append({
            "data": giorno.strftime("%d/%m/%Y"),
            "alba": dati["sunrise"].strftime("%H:%M"),
            "tramonto": dati["sunset"].strftime("%H:%M"),
        })
    return risultati


_SOGLIE_FASE = [
    (1.0, "Luna nuova"),
    (6.5, "Luna crescente"),
    (7.5, "Primo quarto"),
    (13.5, "Gibbosa crescente"),
    (14.5, "Luna piena"),
    (20.5, "Gibbosa calante"),
    (21.5, "Ultimo quarto"),
    (27.0, "Luna calante"),
]


def _nome_fase(indice):
    for soglia, nome in _SOGLIE_FASE:
        if indice < soglia:
            return nome
    return "Luna nuova"


def dati_luna(lat, lon):
    try:
        ts = _load.timescale()
        eph = _load("de421.bsp")
        terra = eph["earth"]
        luna = eph["moon"]
        osservatore = wgs84.latlon(lat, lon)
        ora = ts.now()

        posizione = (terra + osservatore).at(ora).observe(luna).apparent()
        altezza, azimut, _ = posizione.altaz()

        illuminazione = almanac.fraction_illuminated(eph, "moon", ora) * 100
        indice_fase = astral_moon.phase(date=date.today())
        fase = _nome_fase(indice_fase)

        oggi = date.today()
        t_inizio = ts.utc(oggi.year, oggi.month, oggi.day)
        t_fine = ts.utc(oggi.year, oggi.month, oggi.day + 1)

        f = almanac.risings_and_settings(eph, luna, osservatore, radius_degrees=0.25)
        tempi, eventi = almanac.find_discrete(t_inizio, t_fine, f)

        alba_luna = None
        tramonto_luna = None
        for t, e in zip(tempi, eventi):
            orario = t.utc_datetime().strftime("%H:%M")
            if e == 1 and alba_luna is None:
                alba_luna = orario
            elif e == 0 and tramonto_luna is None:
                tramonto_luna = orario

        return {
            "altezza": round(altezza.degrees),
            "direzione": _direzione_bussola(azimut.degrees),
            "fase": fase,
            "illuminazione": round(illuminazione),
            "alba": alba_luna or "non sorge oggi",
            "tramonto": tramonto_luna or "non tramonta oggi",
        }
    except Exception:
        return None


def passaggi_satelliti(lat, lon):
    ts = _load.timescale()
    eph = _load("de421.bsp")
    osservatore = wgs84.latlon(lat, lon)
    risultati = []
    for nome, norad in STAZIONI.items():
        try:
            sat = _carica_satellite(norad, ts)
            if sat is None:
                continue
            risultati.extend(
                _prossimi_passaggi_satellite(sat, nome, eph, osservatore, ore=48, altezza_minima=10.0)
            )
        except Exception:
            pass
    risultati.sort(key=lambda p: p["inizio"])
    return risultati


def passaggi_starlink(lat, lon, limite=50):
    try:
        r = requests.get(URL_STARLINK_TLE, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception:
        return []

    righe = [x.rstrip("\n") for x in r.text.splitlines() if x.strip()]
    ts = _load.timescale()
    eph = _load("de421.bsp")
    osservatore = wgs84.latlon(lat, lon)
    ora = ts.now()

    candidati = []
    for i in range(0, len(righe) - 2, 3):
        nome = righe[i].strip()
        riga1 = righe[i + 1]
        riga2 = righe[i + 2]
        if not riga1.startswith("1 ") or not riga2.startswith("2 "):
            continue
        try:
            sat = EarthSatellite(riga1, riga2, nome, ts)
            subpunto = sat.at(ora).subpoint()
            dlat = subpunto.latitude.degrees - lat
            dlon = subpunto.longitude.degrees - lon
            distanza_approssimata = (dlat ** 2 + dlon ** 2) ** 0.5
            candidati.append((distanza_approssimata, nome, sat))
        except Exception:
            continue

    candidati.sort(key=lambda c: c[0])
    piu_vicini = candidati[:limite]

    risultati = []
    for _, nome, sat in piu_vicini:
        try:
            risultati.extend(
                _prossimi_passaggi_satellite(sat, nome, eph, osservatore, ore=24, altezza_minima=20.0)
            )
        except Exception:
            continue

    risultati.sort(key=lambda p: p["inizio"])
    return risultati[:20]


def pianeti_visibili(lat, lon):
    ts = _load.timescale()
    eph = _load("de421.bsp")
    osservatore = wgs84.latlon(lat, lon)
    terra = eph["earth"]
    ora = ts.now()
    risultati = []
    for nome, corpo in PIANETI.items():
        try:
            posizione = (terra + osservatore).at(ora).observe(eph[corpo]).apparent()
            alt, az, _ = posizione.altaz()
            risultati.append({
                "nome": nome,
                "visibile_ora": alt.degrees > 0,
                "altezza": round(alt.degrees),
                "direzione": _direzione_bussola(az.degrees),
            })
        except Exception:
            pass
    return risultati


def stelle_visibili(lat, lon, limite=10):
    ts = _load.timescale()
    eph = _load("de421.bsp")
    osservatore = wgs84.latlon(lat, lon)
    terra = eph["earth"]
    ora = ts.now()
    visibili = []
    for nome, ra, dec, mag in STELLE_PRINCIPALI:
        try:
            stella = Star(ra_hours=ra, dec_degrees=dec)
            posizione = (terra + osservatore).at(ora).observe(stella).apparent()
            alt, az, _ = posizione.altaz()
            if alt.degrees > 0:
                visibili.append({
                    "nome": nome,
                    "altezza": round(alt.degrees),
                    "direzione": _direzione_bussola(az.degrees),
                    "magnitudine": mag,
                })
        except Exception:
            pass
    visibili.sort(key=lambda x: x["magnitudine"])
    return visibili[:limite]


def _in_intervallo_md(md_oggi, md_inizio, md_fine):
    if md_inizio <= md_fine:
        return md_inizio <= md_oggi <= md_fine
    return md_oggi >= md_inizio or md_oggi <= md_fine


def sciami_attivi(oggi=None):
    oggi = oggi or date.today()
    md_oggi = (oggi.month, oggi.day)
    attivi = []
    for s in SCIAMI_METEORICI:
        if _in_intervallo_md(md_oggi, s["inizio"], s["fine"]):
            attivi.append({"nome": s["nome"], "periodo": s["periodo"], "picco": s["picco"]})
    return attivi


def meteo_osservativo(lat, lon):
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "cloudcover,visibility",
                "forecast_days": 1,
                "timezone": "UTC",
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        dati = r.json()
        orari = dati["hourly"]["time"]
        nuvole = dati["hourly"]["cloudcover"]
        visibilita = dati["hourly"]["visibility"]

        ora_corrente = datetime.utcnow().strftime("%Y-%m-%dT%H:00")
        idx = orari.index(ora_corrente) if ora_corrente in orari else 0

        copertura = nuvole[idx]
        vis_metri = visibilita[idx]

        if copertura <= 25 and vis_metri >= 15000:
            valutazione = "🟢 Ottima"
        elif copertura <= 60 and vis_metri >= 8000:
            valutazione = "🟡 Discreta"
        else:
            valutazione = "🔴 Scarsa"

        return {
            "copertura_nuvole": copertura,
            "visibilita_km": round(vis_metri / 1000, 1),
            "valutazione": valutazione,
        }
    except Exception:
        return None
