"""
Recupero dei voli spaziali recenti e programmati.

nextspaceflight.com non offre un endpoint pubblico proprio: il sito e
alimentato dai dati di "Launch Library 2" (The Space Devs), la stessa
fonte usata anche da altri siti di tracking dei lanci. Interrogare
direttamente quell'API e molto piu affidabile che tentare di leggere
la pagina HTML di nextspaceflight.com, che cambierebbe struttura ad
ogni loro aggiornamento grafico e romperebbe l'importazione.

L'API pubblica ha un limite di richieste orario: per questo motivo le
funzioni qui sotto vanno sempre richiamate tramite una cache (vedi
streamlit_app.py, che le avvolge con st.cache_data).
"""

import requests
from datetime import datetime, timedelta, timezone

BASE_URL = "https://ll.thespacedevs.com/2.2.0/launch"
TIMEOUT = 12


def _normalizza(voce):
    rocket = (voce.get("rocket") or {}).get("configuration") or {}
    pad = (voce.get("pad") or {}) or {}
    location = pad.get("location") or {}
    stato = (voce.get("status") or {}).get("name", "")
    net = voce.get("net") or ""
    return {
        "nome": voce.get("name") or "Missione senza nome",
        "data": net[:10] if net else "",
        "stato": stato,
        "veicolo": rocket.get("name", ""),
        "sito": location.get("name", ""),
    }


def voli_precedenti(giorni=60, limite=30):
    """Voli avvenuti negli ultimi `giorni` giorni, dal piu recente al piu vecchio."""
    da_data = (datetime.now(timezone.utc) - timedelta(days=giorni)).strftime("%Y-%m-%dT%H:%M:%SZ")
    parametri = {"limit": limite, "ordering": "-net", "net__gte": da_data}
    risposta = requests.get(f"{BASE_URL}/previous/", params=parametri, timeout=TIMEOUT)
    risposta.raise_for_status()
    return [_normalizza(v) for v in risposta.json().get("results", [])]


def voli_programmati(limite=15):
    """Prossimi voli in programma, dal piu vicino nel tempo."""
    parametri = {"limit": limite, "ordering": "net"}
    risposta = requests.get(f"{BASE_URL}/upcoming/", params=parametri, timeout=TIMEOUT)
    risposta.raise_for_status()
    return [_normalizza(v) for v in risposta.json().get("results", [])]


def voli_per_parola_chiave(parola, limite=25):
    """Tutti i voli, passati e futuri, il cui nome contiene la parola indicata.

    Utile per programmi seguiti da vicino come Starship o Artemis, per i
    quali si vogliono tutti gli aggiornamenti e non solo l'ultimo periodo.
    """
    parametri = {"search": parola, "limit": limite, "ordering": "-net"}
    risposta = requests.get(f"{BASE_URL}/", params=parametri, timeout=TIMEOUT)
    risposta.raise_for_status()
    return [_normalizza(v) for v in risposta.json().get("results", [])]
