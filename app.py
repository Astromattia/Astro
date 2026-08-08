"""
Archivio Missioni Spaziali - versione Streamlit
-------------------------------------------------
Applicazione web multiutente per consultare e gestire un database di
missioni spaziali (Apollo e non solo). Il primo utente che si registra
diventa automaticamente amministratore.

Avvio:
    streamlit run streamlit_app.py
"""

from datetime import datetime

import base64
import csv
import io
import re
import requests
from urllib.parse import quote, urlencode, urlparse, parse_qs
import streamlit as st

import database as db
from auth import genera_hash_password, verifica_password
from voli_esterni import voli_precedenti, voli_programmati, voli_per_parola_chiave
from email_utils import invia_a_iscritti
from cielo_notturno import (
    geocodifica_indirizzo, passaggi_satelliti, pianeti_visibili, stelle_visibili,
    satelliti_vicini, sole_settimana, fase_lunare, si_vede_stasera,
)
from notizie_spaziali import recupera_tutte_le_notizie
from quiz_dati import DOMANDE, SOGLIE_BADGE

# ---------------------------------------------------------------------------
# Configurazione pagina
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Archivio Missioni Spaziali",
    page_icon=":rocket:",
    layout="wide",
)

PROGRAMMI = [
    "Apollo", "Mercury", "Gemini", "Apollo-Soyuz", "Skylab", "Space Shuttle",
    "Programma sovietico", "Vostok", "Soyuz", "Commercial Crew (SpaceX)",
    "Starship", "Artemis", "Stazione Spaziale Internazionale", "Altro",
]
TIPI = ["con equipaggio", "senza equipaggio"]
ESITI = ["pianificata", "in corso", "successo", "fallita", "parziale"]

COLORE_ESITO = {
    "successo": "#4FB286",
    "fallita": "#D9534F",
    "in corso": "#F2A65A",
    "pianificata": "#F2A65A",
    "parziale": "#F2A65A",
}


# ---------------------------------------------------------------------------
# CSS minimo per badge e coerenza visiva con il resto del progetto
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    .esito-pill {
        font-family: monospace;
        font-size: 0.72rem;
        text-transform: uppercase;
        padding: 2px 10px;
        border-radius: 999px;
        border: 1px solid;
        display: inline-block;
    }
    .programma-tag {
        color: #7C8AA3;
        font-size: 0.8rem;
    }
    .brand-title {
        font-size: 1.6rem;
        font-weight: 700;
        margin-bottom: 0;
    }
    div[data-testid="stMetricValue"] {
        color: #F2A65A;
    }
    [data-testid="stWidgetLabel"] p {
        color: #FFFFFF !important;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Inizializzazione database (idempotente: crea solo se non esiste)
# ---------------------------------------------------------------------------

db.init_db()
db.popola_dati_iniziali()


# ---------------------------------------------------------------------------
# Stato di sessione
# ---------------------------------------------------------------------------

if "utente" not in st.session_state:
    st.session_state.utente = None
if "view" not in st.session_state:
    st.session_state.view = "dashboard"
if "missione_selezionata" not in st.session_state:
    st.session_state.missione_selezionata = None
if "conferma_elimina_missione" not in st.session_state:
    st.session_state.conferma_elimina_missione = None
if "conferma_elimina_utente" not in st.session_state:
    st.session_state.conferma_elimina_utente = None
if "utente_in_modifica" not in st.session_state:
    st.session_state.utente_in_modifica = None
if "prefill_esterno" not in st.session_state:
    st.session_state.prefill_esterno = None
if "ultima_registrazione" not in st.session_state:
    st.session_state.ultima_registrazione = None
if "astronauta_in_modifica" not in st.session_state:
    st.session_state.astronauta_in_modifica = None
if "conferma_elimina_astronauta" not in st.session_state:
    st.session_state.conferma_elimina_astronauta = None
if "guida_in_modifica" not in st.session_state:
    st.session_state.guida_in_modifica = None
if "conferma_elimina_guida" not in st.session_state:
    st.session_state.conferma_elimina_guida = None


def vai_a(view, **kwargs):
    st.session_state.view = view
    for chiave, valore in kwargs.items():
        st.session_state[chiave] = valore
    st.rerun()


def e_admin():
    return st.session_state.utente is not None and st.session_state.utente["ruolo"] == "admin"


def _indovina_programma(nome_missione):
    n = (nome_missione or "").lower()
    if "starship" in n:
        return "Starship"
    if "artemis" in n:
        return "Artemis"
    return None


# Le richieste all'API sono limitate: i risultati restano validi 1 ora
# cosi da non superare i limiti del servizio esterno.
@st.cache_data(ttl=3600, show_spinner=False)
def _cache_voli_precedenti():
    return voli_precedenti()


@st.cache_data(ttl=3600, show_spinner=False)
def _cache_voli_programmati():
    return voli_programmati()


@st.cache_data(ttl=3600, show_spinner=False)
def _cache_voli_starship():
    return voli_per_parola_chiave("Starship")


@st.cache_data(ttl=3600, show_spinner=False)
def _cache_voli_artemis():
    return voli_per_parola_chiave("Artemis")


@st.cache_data(ttl=3600, show_spinner=False)
def _cache_passaggi_satelliti(lat, lon):
    return passaggi_satelliti(lat, lon)


@st.cache_data(ttl=900, show_spinner=False)
def _cache_pianeti_visibili(lat, lon):
    return pianeti_visibili(lat, lon)


@st.cache_data(ttl=900, show_spinner=False)
def _cache_stelle_visibili(lat, lon):
    return stelle_visibili(lat, lon)


@st.cache_data(ttl=900, show_spinner=False)
def _cache_satelliti_vicini(lat, lon):
    return satelliti_vicini(lat, lon)


@st.cache_data(ttl=21600, show_spinner=False)
def _cache_sole_settimana(lat, lon):
    return sole_settimana(lat, lon)


@st.cache_data(ttl=3600, show_spinner=False)
def _cache_fase_lunare(lat, lon):
    return fase_lunare(lat, lon)


@st.cache_data(ttl=1800, show_spinner=False)
def _cache_si_vede_stasera(lat, lon):
    return si_vede_stasera(lat, lon)


@st.cache_data(ttl=1800, show_spinner=False)
def _cache_prossimi_lanci_estesi():
    return voli_programmati(limite=40)


@st.cache_data(ttl=1800, show_spinner=False)
def _cache_notizie_spaziali():
    return recupera_tutte_le_notizie()


# ---------------------------------------------------------------------------
# Pagine: autenticazione
# ---------------------------------------------------------------------------

def pagina_autenticazione():
    sfondo_b64 = db.leggi_impostazione("sfondo_login_b64")
    if sfondo_b64:
        sfondo_mime = db.leggi_impostazione("sfondo_login_mime", "image/png")
        st.markdown(f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image: linear-gradient(rgba(11,18,32,0.55), rgba(11,18,32,0.55)),
                               url("data:{sfondo_mime};base64,{sfondo_b64}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        /* Pannello scuro semi-opaco dietro a titolo, form di login e newsletter,
           cosi il testo resta leggibile indipendentemente dall'immagine caricata. */
        [data-testid="stAppViewContainer"] .block-container {{
            background: rgba(11, 18, 32, 0.86);
            border: 1px solid rgba(242, 166, 90, 0.2);
            border-radius: 14px;
            max-width: 620px;
            margin: 3rem auto 4rem;
            padding: 2rem 2.5rem 2.5rem;
        }}
        [data-testid="stForm"] {{
            background: rgba(19, 27, 46, 0.95);
            border: 1px solid rgba(242, 166, 90, 0.25);
            border-radius: 10px;
            padding: 1.25rem 1.25rem 0.25rem;
        }}
        </style>
        """, unsafe_allow_html=True)

    st.markdown('<p class="brand-title">🚀 Archivio Missioni Spaziali</p>', unsafe_allow_html=True)

    conn = db.get_connection()
    numero_utenti = conn.execute("SELECT COUNT(*) AS c FROM utenti").fetchone()["c"]
    conn.close()

    if numero_utenti == 0:
        # Nessun utente esiste ancora: consenti di creare SOLO il primo
        # account, che diventa automaticamente amministratore. Dopo questo
        # passaggio la registrazione pubblica non sara piu disponibile.
        st.caption("Nessun account esistente. Crea il tuo account amministratore per iniziare.")
        with st.form("form_setup_admin"):
            username_r = st.text_input("Scegli uno username")
            password_r = st.text_input("Scegli una password (minimo 6 caratteri)", type="password")
            conferma_r = st.text_input("Conferma password", type="password")
            invia_r = st.form_submit_button("Crea account amministratore", type="primary", use_container_width=True)

        if invia_r:
            username_r = username_r.strip()
            if not username_r or not password_r:
                st.error("Username e password sono obbligatori.")
            elif password_r != conferma_r:
                st.error("Le due password non coincidono.")
            elif len(password_r) < 6:
                st.error("La password deve avere almeno 6 caratteri.")
            else:
                conn = db.get_connection()
                conn.execute(
                    "INSERT INTO utenti (username, password_hash, ruolo, creato_il) VALUES (?, ?, 'admin', ?)",
                    (username_r, genera_hash_password(password_r),
                     datetime.utcnow().isoformat(timespec="seconds")),
                )
                conn.commit()
                nuovo = conn.execute("SELECT * FROM utenti WHERE username = ?", (username_r,)).fetchone()
                conn.close()
                st.session_state.utente = dict(nuovo)
                st.success("Account amministratore creato.")
                vai_a("dashboard")
        return

    # Da qui in poi esiste gia almeno un utente: solo login, niente
    # registrazione pubblica. I nuovi utenti li crea l'amministratore
    # dalla pagina "Gestione utenti".
    st.caption("Accedi per consultare l'archivio delle missioni.")
    with st.form("form_login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        invia = st.form_submit_button("Accedi", type="primary", use_container_width=True)

    if invia:
        conn = db.get_connection()
        utente = conn.execute("SELECT * FROM utenti WHERE username = ?", (username,)).fetchone()
        conn.close()
        if utente is None or not verifica_password(password, utente["password_hash"]):
            st.error("Credenziali non valide.")
        elif not utente["approvato"]:
            st.warning(
                "Il tuo account e' stato creato ma e' ancora in attesa di approvazione "
                "da parte dell'amministratore. Riprova ad accedere piu tardi."
            )
        else:
            st.session_state.utente = dict(utente)
            st.success(f"Bentornato, {utente['username']}.")
            vai_a("dashboard")

    st.divider()
    with st.expander("📝 Registrati per consultare l'archivio",
                      expanded=bool(st.session_state.ultima_registrazione)):
        st.caption(
            "Crea il tuo account per consultare, cercare e filtrare le missioni. Il nuovo "
            "account potra solo consultare l'archivio (sola lettura): se in futuro ti "
            "servono permessi da amministratore, chiedilo a chi gestisce l'app."
        )

        if st.session_state.ultima_registrazione:
            info = st.session_state.ultima_registrazione
            st.success(
                "Richiesta inviata! Il tuo account non e' ancora attivo: manca solo "
                "un ultimo passaggio qui sotto, poi l'amministratore dovra' approvarti."
            )
            link_gmail_registrazione = "https://mail.google.com/mail/?" + urlencode({
                "view": "cm", "fs": 1, "to": info["email_notifica"],
                "su": info["oggetto"], "body": info["corpo"],
            })
            st.link_button(
                "📧 Apri Gmail e invia la richiesta di approvazione",
                link_gmail_registrazione, type="primary", use_container_width=True,
            )
            st.caption(
                "Si apre Gmail con destinatario, oggetto e testo gia compilati: devi "
                "solo premere 'Invia' dentro Gmail (serve essere gia loggato nel browser)."
            )
            if st.button("Ho gia inviato, chiudi questo riquadro", key="chiudi_reg_ok"):
                st.session_state.ultima_registrazione = None
                st.rerun()
            st.divider()

        with st.form("form_registrazione", clear_on_submit=True):
            r_username = st.text_input("Nome utente", key="reg_username")
            r_password = st.text_input("Password (minimo 6 caratteri)", type="password", key="reg_password")
            r_conferma = st.text_input("Conferma password", type="password", key="reg_conferma")
            r_nascita = st.date_input(
                "Data di nascita", key="reg_nascita",
                min_value=datetime(1900, 1, 1), max_value=datetime.utcnow(),
                value=None,
            )
            r_professione = st.text_input("Professione", key="reg_professione")
            r_invia = st.form_submit_button("Registrati", type="primary", use_container_width=True)

        if r_invia:
            r_username_p = r_username.strip()
            r_professione_p = r_professione.strip()
            if not r_username_p or not r_password or not r_professione_p or r_nascita is None:
                st.error("Tutti i campi sono obbligatori.")
            elif r_password != r_conferma:
                st.error("Le due password non coincidono.")
            elif len(r_password) < 6:
                st.error("La password deve avere almeno 6 caratteri.")
            else:
                conn = db.get_connection()
                esistente = conn.execute(
                    "SELECT id FROM utenti WHERE username = ?", (r_username_p,)
                ).fetchone()
                if esistente:
                    conn.close()
                    st.error("Questo nome utente e gia in uso, scegline un altro.")
                else:
                    conn.execute(
                        "INSERT INTO utenti (username, password_hash, ruolo, data_nascita, "
                        "professione, approvato, creato_il) VALUES (?, ?, 'utente', ?, ?, 0, ?)",
                        (r_username_p, genera_hash_password(r_password), r_nascita.isoformat(),
                         r_professione_p, datetime.utcnow().isoformat(timespec="seconds")),
                    )
                    conn.commit()
                    conn.close()

                    # Tentativo automatico via SMTP, se configurato: non blocca
                    # ne mostra errori tecnici al nuovo utente in caso di fallimento.
                    email_notifica = db.leggi_impostazione("email_notifica_registrazioni", "laudandomattia@gmail.com")
                    smtp_pronto = bool(
                        db.leggi_impostazione("smtp_host") and db.leggi_impostazione("smtp_utente")
                        and db.leggi_impostazione("smtp_password") and db.leggi_impostazione("smtp_mittente")
                    )
                    corpo_notifica = (
                        f"Un nuovo utente si e' registrato all'Archivio Missioni Spaziali "
                        f"e attende la tua approvazione.\n\n"
                        f"Username: {r_username_p}\n"
                        f"Data di nascita: {r_nascita.isoformat()}\n"
                        f"Professione: {r_professione_p}\n"
                        f"Registrato il: {datetime.utcnow().isoformat(timespec='seconds')} UTC\n\n"
                        f"Vai su 'Gestione utenti' nell'app per approvarlo."
                    )
                    if email_notifica and smtp_pronto:
                        try:
                            invia_a_iscritti(
                                host=db.leggi_impostazione("smtp_host"),
                                porta=int(db.leggi_impostazione("smtp_porta", "587")),
                                utente_smtp=db.leggi_impostazione("smtp_utente"),
                                password_smtp=db.leggi_impostazione("smtp_password"),
                                mittente=db.leggi_impostazione("smtp_mittente"),
                                ssl_diretto=db.leggi_impostazione("smtp_ssl_diretto", "0") == "1",
                                destinatari=[email_notifica],
                                oggetto=f"Nuova registrazione: {r_username_p}",
                                corpo=corpo_notifica,
                            )
                        except Exception:
                            pass

                    st.session_state.ultima_registrazione = {
                        "email_notifica": email_notifica,
                        "oggetto": f"Nuova registrazione: {r_username_p}",
                        "corpo": corpo_notifica,
                    }
                    st.rerun()

    st.divider()
    with st.expander("📰 Iscriviti alla newsletter per restare sempre aggiornato"):
        st.caption(
            "Ricevi aggiornamenti sui nuovi voli aggiunti all'archivio. Non serve avere gia "
            "un account per consultare il sito: e solo per essere avvisato."
        )
        with st.form("form_newsletter", clear_on_submit=True):
            n_username = st.text_input("Nome utente", key="news_username")
            n_password = st.text_input("Password (minimo 6 caratteri)", type="password", key="news_password")
            n_telefono = st.text_input("Numero di telefono", key="news_telefono")
            n_email = st.text_input("Email", key="news_email")
            n_invia = st.form_submit_button("Iscriviti", type="primary", use_container_width=True)

        if n_invia:
            n_username_p = n_username.strip()
            n_email_p = n_email.strip()
            n_telefono_p = n_telefono.strip()
            if not n_username_p or not n_password or not n_telefono_p or not n_email_p:
                st.error("Tutti i campi sono obbligatori.")
            elif len(n_password) < 6:
                st.error("La password deve avere almeno 6 caratteri.")
            elif "@" not in n_email_p or "." not in n_email_p.split("@")[-1]:
                st.error("Inserisci un indirizzo email valido.")
            else:
                conn = db.get_connection()
                esistente = conn.execute(
                    "SELECT id FROM iscritti_newsletter WHERE username = ?", (n_username_p,)
                ).fetchone()
                if esistente:
                    conn.close()
                    st.error("Questo nome utente e gia iscritto alla newsletter.")
                else:
                    conn.execute(
                        "INSERT INTO iscritti_newsletter (username, password_hash, telefono, email, creato_il) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (n_username_p, genera_hash_password(n_password), n_telefono_p, n_email_p,
                         datetime.utcnow().isoformat(timespec="seconds")),
                    )
                    conn.commit()
                    conn.close()
                    st.success("Iscrizione completata! Riceverai gli aggiornamenti sui nuovi voli.")


# ---------------------------------------------------------------------------
# Barra laterale (solo per utenti autenticati)
# ---------------------------------------------------------------------------

def barra_laterale():
    utente = st.session_state.utente
    with st.sidebar:
        st.markdown('<p class="brand-title">🚀 Missioni</p>', unsafe_allow_html=True)
        st.caption(f"{utente['username']} · {utente['ruolo']}")
        st.divider()

        if st.button("📋 Elenco missioni", use_container_width=True):
            vai_a("dashboard")
        if st.button("🌌 Osservatorio Astronomico", use_container_width=True):
            vai_a("cielo")
        if st.button("🚀 Prossimi lanci", use_container_width=True):
            vai_a("lanci")
        if st.button("📰 News spaziali", use_container_width=True):
            vai_a("news")
        if st.button("👨‍🚀 Astronauti", use_container_width=True):
            vai_a("astronauti")
        if st.button("🎯 Quiz spaziali", use_container_width=True):
            vai_a("quiz")
        if st.button("🔴 Live", use_container_width=True):
            vai_a("live")
        if st.button("📚 Guide", use_container_width=True):
            vai_a("guide")
        if e_admin():
            if st.button("➕ Nuova missione", use_container_width=True):
                vai_a("form_missione", missione_selezionata=None)
            if st.button("👥 Gestione utenti", use_container_width=True):
                vai_a("utenti")
            if st.button("📰 Iscritti newsletter", use_container_width=True):
                vai_a("newsletter")
            if st.button("🖼️ Sfondo login", use_container_width=True):
                vai_a("impostazioni")

        st.divider()
        st.caption("Aggiornamenti da nextspaceflight.com")
        _sezione_voli_esterni()

        st.divider()
        if st.button("Esci", use_container_width=True):
            st.session_state.utente = None
            vai_a("dashboard")


def _riga_volo_esterno(v, chiave):
    st.markdown(f"**{v['nome']}**")
    dettagli = " · ".join(x for x in [v["data"], v["stato"], v["veicolo"]] if x)
    if dettagli:
        st.caption(dettagli)
    if e_admin():
        if st.button("+ Aggiungi all'archivio", key=chiave, use_container_width=True):
            vai_a("form_missione", missione_selezionata=None, prefill_esterno=v)
    st.markdown("<hr style='margin: 0.4rem 0; opacity: 0.15;'>", unsafe_allow_html=True)


def _blocco_voli(titolo, funzione_cache, prefisso_chiave, messaggio_vuoto):
    with st.expander(titolo):
        try:
            elenco = funzione_cache()
        except Exception:
            elenco = None
        if elenco is None:
            st.caption("Dati non disponibili al momento (servizio esterno non raggiungibile).")
        elif not elenco:
            st.caption(messaggio_vuoto)
        else:
            for i, v in enumerate(elenco):
                _riga_volo_esterno(v, f"{prefisso_chiave}_{i}")


def _sezione_voli_esterni():
    _blocco_voli("🛬 Voli precedenti (60 giorni)", _cache_voli_precedenti,
                  "imp_prec", "Nessun volo negli ultimi 60 giorni.")
    _blocco_voli("🛫 Voli programmati", _cache_voli_programmati,
                  "imp_prog", "Nessun volo programmato trovato.")
    _blocco_voli("🛰️ Starship - tutti gli aggiornamenti", _cache_voli_starship,
                  "imp_star", "Nessun aggiornamento trovato.")
    _blocco_voli("🌕 Artemis - tutti gli aggiornamenti", _cache_voli_artemis,
                  "imp_art", "Nessun aggiornamento trovato.")


# ---------------------------------------------------------------------------
# Pagina: dashboard con ricerca e filtri
# ---------------------------------------------------------------------------

def pagina_dashboard():
    st.title("Archivio missioni")
    st.caption("Cronologia dei voli spaziali, dal programma Mercury alle missioni odierne.")

    conn = db.get_connection()
    totale = conn.execute("SELECT COUNT(*) AS c FROM missioni").fetchone()["c"]
    successi = conn.execute("SELECT COUNT(*) AS c FROM missioni WHERE esito='successo'").fetchone()["c"]
    fallite = conn.execute("SELECT COUNT(*) AS c FROM missioni WHERE esito='fallita'").fetchone()["c"]
    programmi_presenti = [r["programma"] for r in conn.execute(
        "SELECT DISTINCT programma FROM missioni ORDER BY programma"
    ).fetchall()]
    conn.close()

    c1, c2, c3 = st.columns(3)
    c1.metric("Missioni totali", totale)
    c2.metric("Successi", successi)
    c3.metric("Fallite", fallite)

    with st.container(border=True):
        fc1, fc2, fc3, fc4 = st.columns([2, 1, 1, 1])
        ricerca = fc1.text_input("Cerca", placeholder="Nome, equipaggio, descrizione...")
        programma_f = fc2.selectbox("Programma", ["Tutti"] + programmi_presenti)
        tipo_f = fc3.selectbox("Tipo", ["Tutti"] + TIPI)
        esito_f = fc4.selectbox("Esito", ["Tutti"] + ESITI)

    query = "SELECT * FROM missioni WHERE 1=1"
    parametri = []
    if ricerca:
        query += " AND (nome LIKE ? OR equipaggio LIKE ? OR descrizione LIKE ?)"
        like = f"%{ricerca}%"
        parametri += [like, like, like]
    if programma_f != "Tutti":
        query += " AND programma = ?"
        parametri.append(programma_f)
    if tipo_f != "Tutti":
        query += " AND tipo = ?"
        parametri.append(tipo_f)
    if esito_f != "Tutti":
        query += " AND esito = ?"
        parametri.append(esito_f)
    query += " ORDER BY data_lancio ASC"

    conn = db.get_connection()
    missioni = conn.execute(query, parametri).fetchall()
    conn.close()

    st.write("")

    if not missioni:
        st.info("Nessuna missione trovata con questi filtri.")
        return

    for m in missioni:
        colore = COLORE_ESITO.get(m["esito"], "#F2A65A")
        with st.container(border=True):
            col_data, col_nome, col_veicolo, col_esito, col_azione = st.columns([1.1, 3, 1.6, 1.2, 1])
            col_data.markdown(f"`{m['data_lancio'] or '—'}`")
            col_nome.markdown(f"**{m['nome']}**  \n<span class='programma-tag'>{m['programma']} · {m['tipo']}</span>",
                               unsafe_allow_html=True)
            col_veicolo.markdown(f"<span class='programma-tag'>{m['veicolo'] or '—'}</span>", unsafe_allow_html=True)
            col_esito.markdown(
                f"<span class='esito-pill' style='color:{colore}; border-color:{colore};'>{m['esito']}</span>",
                unsafe_allow_html=True,
            )
            if col_azione.button("Apri", key=f"apri_{m['id']}", use_container_width=True):
                vai_a("dettaglio", missione_selezionata=m["id"])


# ---------------------------------------------------------------------------
# Pagina: dettaglio missione
# ---------------------------------------------------------------------------

def pagina_dettaglio():
    conn = db.get_connection()
    m = conn.execute("SELECT * FROM missioni WHERE id = ?", (st.session_state.missione_selezionata,)).fetchone()
    conn.close()

    if st.button("← Torna all'archivio"):
        vai_a("dashboard")

    if m is None:
        st.error("Missione non trovata.")
        return

    colore = COLORE_ESITO.get(m["esito"], "#F2A65A")
    with st.container(border=True):
        st.caption(m["programma"])
        st.title(m["nome"])
        st.markdown(
            f"<span class='esito-pill' style='color:{colore}; border-color:{colore};'>{m['esito']}</span>",
            unsafe_allow_html=True,
        )

        st.write("")
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Data di lancio")
            st.write(m["data_lancio"] or "non specificata")
            st.caption("Veicolo di lancio")
            st.write(m["veicolo"] or "non specificato")
        with c2:
            st.caption("Tipo")
            st.write(m["tipo"])
            st.caption("Equipaggio")
            st.write(m["equipaggio"] or "nessuno")

        if m["descrizione"]:
            st.write("")
            st.subheader("Descrizione")
            st.write(m["descrizione"])

        st.caption(
            f"Aggiunta da {m['creato_da'] or 'sistema'} il {m['creato_il']}"
            + (f" · ultima modifica il {m['aggiornato_il']}" if m["aggiornato_il"] else "")
        )

        if e_admin():
            st.write("")
            bc1, bc2 = st.columns([1, 1])
            if bc1.button("Modifica missione", use_container_width=True):
                vai_a("form_missione", missione_selezionata=m["id"])
            if bc2.button("Elimina missione", type="secondary", use_container_width=True):
                st.session_state.conferma_elimina_missione = m["id"]
                st.rerun()

    if st.session_state.conferma_elimina_missione == m["id"]:
        st.warning(f"Confermi l'eliminazione definitiva di **{m['nome']}**?")
        cc1, cc2 = st.columns(2)
        if cc1.button("Si, elimina", type="primary"):
            conn = db.get_connection()
            conn.execute("DELETE FROM missioni WHERE id = ?", (m["id"],))
            conn.commit()
            conn.close()
            st.session_state.conferma_elimina_missione = None
            st.success("Missione eliminata.")
            vai_a("dashboard")
        if cc2.button("Annulla"):
            st.session_state.conferma_elimina_missione = None
            st.rerun()


# ---------------------------------------------------------------------------
# Pagina: form nuova / modifica missione (solo admin)
# ---------------------------------------------------------------------------

def pagina_form_missione():
    if not e_admin():
        st.error("Non hai i permessi per accedere a questa pagina.")
        return

    missione_id = st.session_state.missione_selezionata
    m = None
    if missione_id:
        conn = db.get_connection()
        m = conn.execute("SELECT * FROM missioni WHERE id = ?", (missione_id,)).fetchone()
        conn.close()

    prefill = st.session_state.get("prefill_esterno")
    st.session_state.prefill_esterno = None

    if st.button("← Torna all'archivio"):
        vai_a("dashboard")

    st.title("Modifica missione" if m else "Nuova missione")
    if prefill and not m:
        st.info(f"Campi precompilati dal volo '{prefill['nome']}' (nextspaceflight.com). Controlla e completa i dati.")

    with st.form("form_missione"):
        c1, c2 = st.columns(2)
        nome_default = m["nome"] if m else (prefill["nome"] if prefill else "")
        nome = c1.text_input("Nome missione *", value=nome_default)

        programma_indovinato = _indovina_programma(prefill["nome"]) if (prefill and not m) else None
        if m and m["programma"] in PROGRAMMI:
            indice_programma = PROGRAMMI.index(m["programma"])
        elif programma_indovinato:
            indice_programma = PROGRAMMI.index(programma_indovinato)
        else:
            indice_programma = len(PROGRAMMI) - 1
        programma_scelta = c2.selectbox("Programma *", PROGRAMMI, index=indice_programma)
        programma_altro = c2.text_input(
            "Se hai scelto 'Altro', specifica qui",
            value=m["programma"] if m and m["programma"] not in PROGRAMMI else "",
        )

        c3, c4 = st.columns(2)
        data_default = m["data_lancio"] if m else (prefill["data"] if prefill else "")
        data_lancio = c3.text_input("Data di lancio (AAAA-MM-GG)", value=data_default,
                                     placeholder="1969-07-16")
        veicolo_default = m["veicolo"] if m else (prefill["veicolo"] if prefill else "")
        veicolo = c4.text_input("Veicolo di lancio", value=veicolo_default)

        c5, c6 = st.columns(2)
        tipo = c5.selectbox("Tipo", TIPI, index=TIPI.index(m["tipo"]) if m and m["tipo"] in TIPI else 0)
        esito = c6.selectbox("Esito", ESITI, index=ESITI.index(m["esito"]) if m and m["esito"] in ESITI else 0)

        equipaggio = st.text_input("Equipaggio (nomi separati da virgola)", value=m["equipaggio"] if m else "")
        descrizione_default = m["descrizione"] if m else (
            f"Sito di lancio: {prefill['sito']}. Stato: {prefill['stato']}." if prefill else ""
        )
        descrizione = st.text_area("Descrizione", value=descrizione_default, height=140)

        invia = st.form_submit_button(
            "Salva modifiche" if m else "Aggiungi missione", type="primary", use_container_width=True
        )

    if invia:
        programma_finale = programma_altro.strip() if programma_scelta == "Altro" and programma_altro.strip() else programma_scelta
        if not nome.strip() or not programma_finale.strip():
            st.error("Nome e programma della missione sono obbligatori.")
            return

        conn = db.get_connection()
        if m:
            conn.execute(
                """UPDATE missioni SET nome=?, programma=?, tipo=?, data_lancio=?, veicolo=?,
                   equipaggio=?, esito=?, descrizione=?, aggiornato_il=? WHERE id=?""",
                (nome.strip(), programma_finale, tipo, data_lancio.strip(), veicolo.strip(),
                 equipaggio.strip(), esito, descrizione.strip(),
                 datetime.utcnow().isoformat(timespec="seconds"), m["id"]),
            )
            conn.commit()
            conn.close()
            st.success(f"Missione '{nome}' aggiornata.")
            vai_a("dettaglio", missione_selezionata=m["id"])
        else:
            conn.execute(
                """INSERT INTO missioni
                   (nome, programma, tipo, data_lancio, veicolo, equipaggio, esito,
                    descrizione, creato_da, creato_il)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (nome.strip(), programma_finale, tipo, data_lancio.strip(), veicolo.strip(),
                 equipaggio.strip(), esito, descrizione.strip(),
                 st.session_state.utente["username"], datetime.utcnow().isoformat(timespec="seconds")),
            )
            conn.commit()
            conn.close()
            st.success(f"Missione '{nome}' aggiunta all'archivio.")
            vai_a("dashboard")


# ---------------------------------------------------------------------------
# Pagina: gestione utenti (solo admin)
# ---------------------------------------------------------------------------

def pagina_utenti():
    if not e_admin():
        st.error("Non hai i permessi per accedere a questa pagina.")
        return

    if st.button("← Torna all'archivio"):
        vai_a("dashboard")

    st.title("Gestione utenti")
    st.caption("Crea gli account per le persone che devono consultare l'archivio, e gestisci i ruoli esistenti.")

    with st.expander("➕ Crea nuovo utente", expanded=False):
        with st.form("form_nuovo_utente", clear_on_submit=True):
            nuovo_username = st.text_input("Username")
            nuova_password = st.text_input("Password (minimo 6 caratteri)", type="password")
            nuovo_ruolo = st.selectbox(
                "Ruolo",
                ["utente", "admin"],
                index=0,
                help="'utente' puo solo consultare l'archivio. 'admin' puo anche aggiungere, modificare, "
                     "eliminare missioni e gestire gli altri utenti.",
            )
            nuova_nascita = st.date_input(
                "Data di nascita (opzionale)", value=None,
                min_value=datetime(1900, 1, 1), max_value=datetime.utcnow(),
            )
            nuova_professione = st.text_input("Professione (opzionale)")
            crea = st.form_submit_button("Crea utente", type="primary", use_container_width=True)

        if crea:
            nuovo_username = nuovo_username.strip()
            if not nuovo_username or not nuova_password:
                st.error("Username e password sono obbligatori.")
            elif len(nuova_password) < 6:
                st.error("La password deve avere almeno 6 caratteri.")
            else:
                conn = db.get_connection()
                esistente = conn.execute("SELECT id FROM utenti WHERE username = ?", (nuovo_username,)).fetchone()
                if esistente:
                    conn.close()
                    st.error("Username gia in uso, scegline un altro.")
                else:
                    conn.execute(
                        "INSERT INTO utenti (username, password_hash, ruolo, data_nascita, "
                        "professione, creato_il) VALUES (?, ?, ?, ?, ?, ?)",
                        (nuovo_username, genera_hash_password(nuova_password), nuovo_ruolo,
                         nuova_nascita.isoformat() if nuova_nascita else None,
                         nuova_professione.strip() or None,
                         datetime.utcnow().isoformat(timespec="seconds")),
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Utente '{nuovo_username}' creato con ruolo '{nuovo_ruolo}'.")
                    st.rerun()

    st.divider()

    conn = db.get_connection()
    utenti = conn.execute("SELECT * FROM utenti WHERE approvato=1 ORDER BY creato_il ASC").fetchall()
    in_attesa = conn.execute("SELECT * FROM utenti WHERE approvato=0 ORDER BY creato_il ASC").fetchall()
    numero_admin = conn.execute("SELECT COUNT(*) AS c FROM utenti WHERE ruolo='admin'").fetchone()["c"]
    conn.close()

    io = st.session_state.utente

    if in_attesa:
        st.subheader(f"🕓 In attesa di approvazione ({len(in_attesa)})")
        st.caption("Richieste arrivate dall'auto-registrazione pubblica: non possono ancora accedere.")
        for u in in_attesa:
            with st.container(border=True):
                a1, a2, a3, a4 = st.columns([1.8, 2, 1, 1])
                a1.markdown(f"**{u['username']}**")
                info_extra = " · ".join(filter(None, [u["professione"], u["data_nascita"]]))
                a2.caption(info_extra or "—")
                if a3.button("✅ Approva", key=f"approva_{u['id']}", type="primary",
                              use_container_width=True):
                    conn = db.get_connection()
                    conn.execute("UPDATE utenti SET approvato=1 WHERE id=?", (u["id"],))
                    conn.commit()
                    conn.close()
                    st.success(f"'{u['username']}' approvato: ora puo' accedere.")
                    st.rerun()
                if a4.button("❌ Rifiuta", key=f"rifiuta_{u['id']}", use_container_width=True):
                    conn = db.get_connection()
                    conn.execute("DELETE FROM utenti WHERE id=?", (u["id"],))
                    conn.commit()
                    conn.close()
                    st.warning(f"Richiesta di '{u['username']}' rifiutata ed eliminata.")
                    st.rerun()
        st.divider()

    st.subheader("Utenti attivi")

    for u in utenti:
        with st.container(border=True):
            c1, c2, c3, c4, c5, c6 = st.columns([1.8, 1, 1.6, 1.5, 1.1, 1])
            etichetta = u["username"] + (" (tu)" if u["id"] == io["id"] else "")
            c1.markdown(f"**{etichetta}**")
            c2.markdown(f"`{u['ruolo']}`")
            info_extra = " · ".join(filter(None, [u["professione"], u["data_nascita"]]))
            c3.caption(info_extra or "—")

            if u["ruolo"] == "admin":
                disabilita = (u["id"] == io["id"] and numero_admin <= 1)
                if c4.button("Rendi utente", key=f"ruolo_{u['id']}", disabled=disabilita,
                              use_container_width=True):
                    conn = db.get_connection()
                    conn.execute("UPDATE utenti SET ruolo='utente' WHERE id=?", (u["id"],))
                    conn.commit()
                    conn.close()
                    st.rerun()
            else:
                if c4.button("Rendi admin", key=f"ruolo_{u['id']}", use_container_width=True):
                    conn = db.get_connection()
                    conn.execute("UPDATE utenti SET ruolo='admin' WHERE id=?", (u["id"],))
                    conn.commit()
                    conn.close()
                    st.rerun()

            if c5.button("Modifica", key=f"modifica_{u['id']}", use_container_width=True):
                st.session_state.utente_in_modifica = (
                    None if st.session_state.get("utente_in_modifica") == u["id"] else u["id"]
                )
                st.rerun()

            if u["id"] != io["id"]:
                if c6.button("Elimina", key=f"elimina_{u['id']}", use_container_width=True):
                    st.session_state.conferma_elimina_utente = u["id"]
                    st.rerun()

            if st.session_state.get("utente_in_modifica") == u["id"]:
                with st.form(f"form_modifica_{u['id']}"):
                    m_username = st.text_input("Username", value=u["username"])
                    valore_nascita = None
                    if u["data_nascita"]:
                        try:
                            valore_nascita = datetime.fromisoformat(u["data_nascita"])
                        except ValueError:
                            valore_nascita = None
                    m_nascita = st.date_input(
                        "Data di nascita", value=valore_nascita,
                        min_value=datetime(1900, 1, 1), max_value=datetime.utcnow(),
                    )
                    m_professione = st.text_input("Professione", value=u["professione"] or "")
                    m_nuova_password = st.text_input(
                        "Nuova password (lascia vuoto per non cambiarla)", type="password"
                    )
                    cc1, cc2 = st.columns(2)
                    salva_modifica = cc1.form_submit_button(
                        "Salva modifiche", type="primary", use_container_width=True
                    )
                    annulla_modifica = cc2.form_submit_button("Annulla", use_container_width=True)

                if annulla_modifica:
                    st.session_state.utente_in_modifica = None
                    st.rerun()

                if salva_modifica:
                    m_username_p = m_username.strip()
                    if not m_username_p:
                        st.error("Lo username non puo essere vuoto.")
                    elif m_nuova_password and len(m_nuova_password) < 6:
                        st.error("La nuova password deve avere almeno 6 caratteri.")
                    else:
                        conn = db.get_connection()
                        duplicato = conn.execute(
                            "SELECT id FROM utenti WHERE username = ? AND id != ?",
                            (m_username_p, u["id"]),
                        ).fetchone()
                        if duplicato:
                            conn.close()
                            st.error("Username gia in uso da un altro account.")
                        else:
                            if m_nuova_password:
                                conn.execute(
                                    "UPDATE utenti SET username=?, data_nascita=?, professione=?, "
                                    "password_hash=? WHERE id=?",
                                    (m_username_p, m_nascita.isoformat() if m_nascita else None,
                                     m_professione.strip() or None,
                                     genera_hash_password(m_nuova_password), u["id"]),
                                )
                            else:
                                conn.execute(
                                    "UPDATE utenti SET username=?, data_nascita=?, professione=? "
                                    "WHERE id=?",
                                    (m_username_p, m_nascita.isoformat() if m_nascita else None,
                                     m_professione.strip() or None, u["id"]),
                                )
                            conn.commit()
                            conn.close()
                            st.session_state.utente_in_modifica = None
                            if u["id"] == io["id"]:
                                # Se ho appena modificato il mio stesso account,
                                # aggiorno anche i dati in sessione.
                                conn = db.get_connection()
                                st.session_state.utente = dict(
                                    conn.execute("SELECT * FROM utenti WHERE id=?", (u["id"],)).fetchone()
                                )
                                conn.close()
                            st.success("Dati utente aggiornati.")
                            st.rerun()

    if st.session_state.conferma_elimina_utente:
        target_id = st.session_state.conferma_elimina_utente
        conn = db.get_connection()
        target = conn.execute("SELECT username FROM utenti WHERE id=?", (target_id,)).fetchone()
        conn.close()
        if target:
            st.warning(f"Confermi l'eliminazione dell'utente **{target['username']}**?")
            cc1, cc2 = st.columns(2)
            if cc1.button("Si, elimina", type="primary"):
                conn = db.get_connection()
                conn.execute("DELETE FROM utenti WHERE id=?", (target_id,))
                conn.commit()
                conn.close()
                st.session_state.conferma_elimina_utente = None
                st.success("Utente eliminato.")
                st.rerun()
            if cc2.button("Annulla"):
                st.session_state.conferma_elimina_utente = None
                st.rerun()


# ---------------------------------------------------------------------------
# Pagina: sfondo della schermata di login (solo admin)
# ---------------------------------------------------------------------------

def pagina_impostazioni():
    if not e_admin():
        st.error("Non hai i permessi per accedere a questa pagina.")
        return

    if st.button("← Torna all'archivio"):
        vai_a("dashboard")

    st.title("Sfondo pagina di accesso")
    st.caption("Carica un'immagine da mostrare come sfondo nella schermata di login.")

    attuale = db.leggi_impostazione("sfondo_login_b64")
    if attuale:
        st.image(base64.b64decode(attuale), caption="Sfondo attuale", use_container_width=True)
        if st.button("Rimuovi sfondo attuale"):
            db.elimina_impostazione("sfondo_login_b64")
            db.elimina_impostazione("sfondo_login_mime")
            st.success("Sfondo rimosso.")
            st.rerun()

    st.write("")
    file_caricato = st.file_uploader("Carica una nuova immagine (JPG o PNG, max 5 MB)", type=["png", "jpg", "jpeg"])
    if file_caricato is not None:
        dati = file_caricato.getvalue()
        if len(dati) > 5 * 1024 * 1024:
            st.error("Il file supera i 5 MB. Scegline uno piu leggero.")
        else:
            st.image(dati, caption="Anteprima", use_container_width=True)
            if st.button("Salva come sfondo login", type="primary"):
                db.scrivi_impostazione("sfondo_login_b64", base64.b64encode(dati).decode("ascii"))
                db.scrivi_impostazione("sfondo_login_mime", file_caricato.type or "image/png")
                st.success("Sfondo login aggiornato.")
                st.rerun()


# ---------------------------------------------------------------------------
# Pagina: osservatorio astronomico (satelliti, pianeti, stelle, sole, luna, meteo)
# ---------------------------------------------------------------------------

def pagina_cielo():
    if st.button("← Torna all'archivio"):
        vai_a("dashboard")

    st.title("🌌 Osservatorio Astronomico")

    lat = db.leggi_impostazione("cielo_lat")
    lon = db.leggi_impostazione("cielo_lon")
    localita = db.leggi_impostazione("cielo_localita")

    if e_admin():
        with st.expander("📍 Imposta il luogo di osservazione", expanded=not lat):
            st.caption(
                "Inserisci la via/indirizzo da cui si osserva il cielo: verra usato "
                "per calcolare cosa e' davvero visibile da li, in questo momento."
            )
            valore_attuale = db.leggi_impostazione("cielo_indirizzo", "")
            nuovo_indirizzo = st.text_input(
                "Indirizzo (via, citta)", value=valore_attuale,
                placeholder="Es. Via Roma 1, Piano di Sorrento",
            )
            if st.button("Trova e salva questa posizione", type="primary"):
                if not nuovo_indirizzo.strip():
                    st.error("Inserisci un indirizzo.")
                else:
                    with st.spinner("Cerco la posizione..."):
                        trovato = geocodifica_indirizzo(nuovo_indirizzo.strip())
                    if trovato is None:
                        st.error(
                            "Indirizzo non trovato. Prova a scrivere in modo piu generico "
                            "(es. solo la citta), o controlla la connessione internet."
                        )
                    else:
                        db.scrivi_impostazione("cielo_indirizzo", nuovo_indirizzo.strip())
                        db.scrivi_impostazione("cielo_lat", str(trovato["lat"]))
                        db.scrivi_impostazione("cielo_lon", str(trovato["lon"]))
                        db.scrivi_impostazione("cielo_localita", trovato["nome"])
                        st.success(f"Posizione salvata: {trovato['nome']}")
                        st.rerun()
            if lat:
                st.caption(f"Posizione attuale: {localita}")

    if not lat or not lon:
        st.info(
            "Il luogo di osservazione non e' ancora stato impostato. "
            + ("Usa il pannello qui sopra per impostarlo." if e_admin()
               else "Chiedi a un amministratore di impostarlo da qui.")
        )
        return

    lat_f, lon_f = float(lat), float(lon)
    st.caption(f"📍 Osservazione da: {localita}")
    st.caption(
        "I dati si basano su effemeridi ufficiali (NASA/NORAD): la prima volta "
        "il calcolo puo richiedere qualche secondo in piu per scaricare i dati necessari."
    )

    try:
        with st.spinner("Valuto le condizioni..."):
            verdetto = _cache_si_vede_stasera(lat_f, lon_f)
        st.info(verdetto["verdetto"])
        vc1, vc2 = st.columns(2)
        if verdetto["nuvolosita_percento"] is not None:
            vc1.metric("☁️ Nuvolosita prevista", f"{verdetto['nuvolosita_percento']}%")
        vc2.metric("🌙 Illuminazione lunare", f"{verdetto['illuminazione_lunare_percento']}%")
    except Exception:
        st.warning("Previsioni meteo non disponibili al momento.")

    st.divider()

    col_satelliti, col_pianeti, col_stelle = st.columns(3)

    with col_satelliti:
        st.subheader("🛰️ Stazioni spaziali")
        st.caption("Prossimi passaggi visibili a occhio nudo (prossime 48 ore)")
        try:
            with st.spinner("Calcolo i passaggi..."):
                passaggi = _cache_passaggi_satelliti(lat_f, lon_f)
            if not passaggi:
                st.write("Nessun passaggio visibile previsto nelle prossime 48 ore.")
            else:
                for p in passaggi:
                    st.markdown(f"**{p['satellite']}**")
                    st.caption(
                        f"{p['inizio'].strftime('%d/%m %H:%M')} - "
                        f"{p['fine'].strftime('%H:%M')} UTC · "
                        f"fino a {p['altezza_massima']}° verso {p['direzione']}"
                    )
                    st.markdown("<hr style='margin:0.4rem 0; opacity:0.15;'>", unsafe_allow_html=True)
        except Exception:
            st.warning("Dati sui satelliti non disponibili al momento. Riprova piu tardi.")

    with col_pianeti:
        st.subheader("🪐 Pianeti")
        st.caption("Sopra l'orizzonte in questo momento")
        try:
            with st.spinner("Calcolo le posizioni..."):
                pianeti = _cache_pianeti_visibili(lat_f, lon_f)
            for p in pianeti:
                if p["visibile_ora"]:
                    st.markdown(f"**{p['nome']}** ✅")
                    st.caption(f"Altezza {p['altezza']}° verso {p['direzione']}")
                else:
                    st.markdown(f"{p['nome']}")
                    st.caption("Sotto l'orizzonte ora")
                st.markdown("<hr style='margin:0.4rem 0; opacity:0.15;'>", unsafe_allow_html=True)
        except Exception:
            st.warning("Dati sui pianeti non disponibili al momento. Riprova piu tardi.")

    with col_stelle:
        st.subheader("✨ Stelle principali")
        st.caption("Le piu luminose sopra l'orizzonte ora")
        try:
            with st.spinner("Calcolo le posizioni..."):
                stelle = _cache_stelle_visibili(lat_f, lon_f)
            if not stelle:
                st.write("Nessuna delle stelle principali e' sopra l'orizzonte ora.")
            else:
                for s in stelle:
                    st.markdown(f"**{s['nome']}**")
                    st.caption(f"Altezza {s['altezza']}° verso {s['direzione']}")
                    st.markdown("<hr style='margin:0.4rem 0; opacity:0.15;'>", unsafe_allow_html=True)
        except Exception:
            st.warning("Dati sulle stelle non disponibili al momento. Riprova piu tardi.")

    st.divider()

    st.subheader("🛰️ Satelliti piu vicini ora")
    st.caption("Dal catalogo dei satelliti noti per essere visibili a occhio nudo")
    try:
        with st.spinner("Cerco i satelliti piu vicini..."):
            vicini = _cache_satelliti_vicini(lat_f, lon_f)
        if not vicini:
            st.write("Nessun satellite sopra l'orizzonte al momento, tra quelli noti come visibili.")
        else:
            colonne_vicini = st.columns(len(vicini))
            for colonna, sat in zip(colonne_vicini, vicini):
                with colonna:
                    st.markdown(f"**{sat['nome']}**")
                    st.caption(
                        f"{sat['distanza_km']:,} km · {sat['altezza']}° verso {sat['direzione']}"
                        .replace(",", ".")
                    )
    except Exception:
        st.warning("Dati sui satelliti vicini non disponibili al momento.")

    st.divider()

    col_sole, col_luna = st.columns(2)

    with col_sole:
        st.subheader("☀️ Sole — prossimi 7 giorni")
        try:
            with st.spinner("Calcolo alba e tramonto..."):
                settimana = _cache_sole_settimana(lat_f, lon_f)
            if not settimana:
                st.write("Dati non disponibili.")
            else:
                for giorno in settimana:
                    st.write(f"**{giorno['data']}** · 🌅 {giorno['alba']} — 🌇 {giorno.get('tramonto', '—')}")
        except Exception:
            st.warning("Dati sul sole non disponibili al momento.")

    with col_luna:
        st.subheader("🌙 Luna")
        try:
            with st.spinner("Calcolo la fase lunare..."):
                luna = _cache_fase_lunare(lat_f, lon_f)
            st.write(f"**Fase attuale:** {luna['fase_attuale']}")
            st.write(f"**Illuminazione:** {luna['illuminazione_percento']}%")
            if luna["prossime_fasi"]:
                st.caption("Prossime fasi principali:")
                for f in luna["prossime_fasi"]:
                    st.caption(f"· {f['fase']} — {f['data']}")
        except Exception:
            st.warning("Dati sulla luna non disponibili al momento.")


# ---------------------------------------------------------------------------
# Pagina: prossimi lanci (con countdown)
# ---------------------------------------------------------------------------

def _countdown(data_iso):
    """Trasforma una data ISO (YYYY-MM-DD) in un countdown leggibile in italiano."""
    if not data_iso:
        return "Data da confermare"
    try:
        data_lancio = datetime.strptime(data_iso, "%Y-%m-%d").date()
    except ValueError:
        return "Data da confermare"

    giorni = (data_lancio - datetime.utcnow().date()).days
    if giorni < 0:
        return "Gia lanciato"
    if giorni == 0:
        return "🔴 Oggi!"
    if giorni == 1:
        return "🟠 Domani"
    if giorni <= 7:
        return f"🟡 Tra {giorni} giorni"
    return f"Tra {giorni} giorni"


def pagina_lanci():
    if st.button("← Torna all'archivio"):
        vai_a("dashboard")

    st.title("🚀 Prossimi lanci")
    st.caption(
        "Dati aggiornati ogni 30 minuti, dalla stessa fonte gratuita usata per "
        "i pannelli dei voli in sidebar (Launch Library 2 / The Space Devs)."
    )
    st.divider()

    try:
        with st.spinner("Carico i prossimi lanci..."):
            lanci = _cache_prossimi_lanci_estesi()
    except Exception:
        st.warning(
            "Non riesco a recuperare i prossimi lanci in questo momento "
            "(servizio esterno non raggiungibile). Riprova piu tardi."
        )
        return

    if not lanci:
        st.info("Nessun lancio programmato trovato al momento.")
        return

    for volo in lanci:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1.3])
            with c1:
                st.markdown(f"**{volo['nome']}**")
                dettagli = " · ".join(filter(None, [volo["veicolo"], volo["sito"]]))
                if dettagli:
                    st.caption(dettagli)
                st.caption(f"Stato: {volo['stato'] or 'Non specificato'}")
            with c2:
                st.markdown(f"**{_countdown(volo['data'])}**")
                if volo["data"]:
                    st.caption(volo["data"])


# ---------------------------------------------------------------------------
# Pagina: news spaziali (NASA / ESA)
# ---------------------------------------------------------------------------

def pagina_news():
    if st.button("← Torna all'archivio"):
        vai_a("dashboard")

    st.title("📰 News spaziali")
    st.caption("Ultime notizie dai feed ufficiali di NASA ed ESA, aggiornate ogni 30 minuti.")
    st.divider()

    try:
        with st.spinner("Carico le notizie..."):
            notizie_per_fonte = _cache_notizie_spaziali()
    except Exception:
        st.warning("Non riesco a recuperare le notizie in questo momento. Riprova piu tardi.")
        return

    col_nasa, col_esa = st.columns(2)
    intestazioni = {"NASA": ("🇺🇸 NASA", col_nasa), "ESA": ("🇪🇺 ESA", col_esa)}

    for fonte, (etichetta, colonna) in intestazioni.items():
        with colonna:
            st.subheader(etichetta)
            notizie = notizie_per_fonte.get(fonte, [])
            if not notizie:
                st.info(f"Nessuna notizia {fonte} disponibile al momento.")
                continue
            for n in notizie:
                with st.container(border=True):
                    st.markdown(f"**[{n['titolo']}]({n['link']})**")
                    if n["data"]:
                        st.caption(n["data"])


# ---------------------------------------------------------------------------
# Pagina: archivio astronauti
# ---------------------------------------------------------------------------

def pagina_astronauti():
    if st.button("← Torna all'archivio"):
        vai_a("dashboard")

    st.title("👨‍🚀 Archivio astronauti")

    if e_admin():
        if st.button("⭐ Carica astronauti famosi (Parmitano, Cristoforetti, Gagarin, ecc.)"):
            aggiunti = db.popola_astronauti_famosi()
            if aggiunti:
                st.success(f"Aggiunti {aggiunti} nuovi astronauti all'archivio.")
                st.rerun()
            else:
                st.info("Sono gia tutti presenti nell'archivio.")

        with st.expander("➕ Aggiungi astronauta"):
            with st.form("form_nuovo_astronauta", clear_on_submit=True):
                nome = st.text_input("Nome")
                c1, c2 = st.columns(2)
                nazionalita = c1.text_input("Nazionalita")
                agenzia = c2.text_input("Agenzia (es. NASA, ESA, Roscosmos)")
                missioni_effettuate = st.text_input("Missioni effettuate (elenco separato da virgole)")
                ore_nello_spazio = st.number_input("Ore totali nello spazio", min_value=0.0, step=1.0)
                biografia = st.text_area("Breve biografia", height=100)
                crea = st.form_submit_button("Aggiungi", type="primary", use_container_width=True)

            if crea:
                if not nome.strip():
                    st.error("Il nome e' obbligatorio.")
                else:
                    db.inserisci_astronauta(
                        nome.strip(), nazionalita.strip() or None, agenzia.strip() or None,
                        missioni_effettuate.strip() or None, ore_nello_spazio,
                        biografia.strip() or None, st.session_state.utente["username"],
                    )
                    st.success(f"'{nome}' aggiunto all'archivio.")
                    st.rerun()

    st.divider()
    ricerca = st.text_input("🔎 Cerca per nome, nazionalita o agenzia", key="ricerca_astronauti")

    astronauti = db.elenco_astronauti()
    if ricerca.strip():
        chiave = ricerca.strip().lower()
        astronauti = [
            a for a in astronauti
            if chiave in (a["nome"] or "").lower()
            or chiave in (a["nazionalita"] or "").lower()
            or chiave in (a["agenzia"] or "").lower()
        ]

    if not astronauti:
        st.info("Nessun astronauta trovato." if ricerca.strip() else
                 "Nessun astronauta ancora nell'archivio.")
        return

    for a in astronauti:
        with st.container(border=True):
            st.markdown(f"### {a['nome']}")
            info = " · ".join(filter(None, [a["nazionalita"], a["agenzia"]]))
            if info:
                st.caption(info)
            if a["missioni_effettuate"]:
                st.write(f"**Missioni:** {a['missioni_effettuate']}")
            if a["ore_nello_spazio"]:
                st.write(f"**Ore nello spazio:** {a['ore_nello_spazio']:.0f}")
            if a["biografia"]:
                st.write(a["biografia"])

            if e_admin():
                bc1, bc2 = st.columns(2)
                if bc1.button("Modifica", key=f"mod_astro_{a['id']}", use_container_width=True):
                    st.session_state.astronauta_in_modifica = (
                        None if st.session_state.astronauta_in_modifica == a["id"] else a["id"]
                    )
                    st.rerun()
                if bc2.button("Elimina", key=f"elim_astro_{a['id']}", use_container_width=True):
                    st.session_state.conferma_elimina_astronauta = a["id"]
                    st.rerun()

            if st.session_state.conferma_elimina_astronauta == a["id"]:
                st.warning(f"Confermi l'eliminazione di **{a['nome']}**?")
                cc1, cc2 = st.columns(2)
                if cc1.button("Si, elimina", key=f"conferma_elim_astro_{a['id']}", type="primary"):
                    db.elimina_astronauta(a["id"])
                    st.session_state.conferma_elimina_astronauta = None
                    st.success("Astronauta eliminato.")
                    st.rerun()
                if cc2.button("Annulla", key=f"annulla_elim_astro_{a['id']}"):
                    st.session_state.conferma_elimina_astronauta = None
                    st.rerun()

            if e_admin() and st.session_state.astronauta_in_modifica == a["id"]:
                with st.form(f"form_modifica_astro_{a['id']}"):
                    m_nome = st.text_input("Nome", value=a["nome"])
                    mc1, mc2 = st.columns(2)
                    m_nazionalita = mc1.text_input("Nazionalita", value=a["nazionalita"] or "")
                    m_agenzia = mc2.text_input("Agenzia", value=a["agenzia"] or "")
                    m_missioni = st.text_input("Missioni effettuate", value=a["missioni_effettuate"] or "")
                    m_ore = st.number_input("Ore nello spazio", min_value=0.0, step=1.0,
                                             value=float(a["ore_nello_spazio"] or 0))
                    m_bio = st.text_area("Biografia", value=a["biografia"] or "", height=100)
                    salva, annulla = st.columns(2)
                    salva_click = salva.form_submit_button("Salva", type="primary", use_container_width=True)
                    annulla_click = annulla.form_submit_button("Annulla", use_container_width=True)

                if salva_click:
                    if not m_nome.strip():
                        st.error("Il nome e' obbligatorio.")
                    else:
                        db.aggiorna_astronauta(
                            a["id"], m_nome.strip(), m_nazionalita.strip() or None,
                            m_agenzia.strip() or None, m_missioni.strip() or None,
                            m_ore, m_bio.strip() or None,
                        )
                        st.session_state.astronauta_in_modifica = None
                        st.success("Dati aggiornati.")
                        st.rerun()
                if annulla_click:
                    st.session_state.astronauta_in_modifica = None
                    st.rerun()


# ---------------------------------------------------------------------------
# Pagina: live streaming (Starbase, ISS, Volare Space) — incorporate nel sito
# ---------------------------------------------------------------------------

# Pagine "/live" dei canali: YouTube reindirizza sempre alla diretta in
# corso in quel momento su quel canale, quindi restano valide nel tempo
# anche quando il video specifico cambia.
CANALI_LIVE = [
    {
        "titolo": "🛰️ ISS — vista dalla Terra (NASA ufficiale)",
        "descrizione": "Diretta ufficiale NASA dalla Stazione Spaziale Internazionale, 24 ore su 24.",
        "url_live": "https://www.youtube.com/@NASA/live",
    },
    {
        "titolo": "🚀 Starbase 24/7 (NASASpaceflight)",
        "descrizione": "Diretta continua del sito Starship/Super Heavy di SpaceX in Texas.",
        "url_live": "https://www.youtube.com/@NASASpaceflight/live",
    },
    {
        "titolo": "🚀 Starbase 24/7 — multi camera (LabPadre)",
        "descrizione": "Altra diretta continua di Starbase, con piu telecamere.",
        "url_live": "https://www.youtube.com/@LabPadre/live",
    },
    {
        "titolo": "🇮🇹 Volare Space",
        "descrizione": "Canale italiano dedicato allo spazio: lanci, dirette e approfondimenti.",
        "url_live": "https://www.youtube.com/@volarespace/live",
    },
]


_sessione_youtube = requests.Session()
_sessione_youtube.cookies.set("CONSENT", "YES+cb.20210328-17-p0.en", domain=".youtube.com")


def _richiesta_youtube(url):
    """Richiesta HTTP a una pagina YouTube, con un cookie che indica di
    aver gia' accettato l'informativa cookie: senza, dall'Europa Google
    restituisce spesso una pagina di consenso (consent.youtube.com)
    invece del contenuto vero, e la ricerca del video fallirebbe sempre.

    Se nonostante il cookie arriva comunque il reindirizzamento alla
    pagina di consenso, recupera l'indirizzo originale nascosto nel
    parametro "continue" e riprova direttamente su quello."""
    intestazioni = {"User-Agent": "Mozilla/5.0 (compatibile; ArchivioMissioniSpaziali/1.0)"}
    risposta = _sessione_youtube.get(url, timeout=12, headers=intestazioni)

    if "consent.youtube.com" in risposta.url:
        parametri = parse_qs(urlparse(risposta.url).query)
        url_originale = (parametri.get("continue") or [None])[0]
        if url_originale:
            risposta = _sessione_youtube.get(url_originale, timeout=12, headers=intestazioni)

    return risposta


@st.cache_data(ttl=300, show_spinner=False)
def _video_live_attuale(url_pagina_live):
    """Trova il video attualmente in diretta su una pagina canale/live di
    YouTube, cosi' si puo' incorporare nel sito senza uscire su YouTube.

    Restituisce l'ID dell'11 caratteri del video, oppure None se il
    canale non e' in diretta in questo momento o non e' raggiungibile.
    """
    try:
        risposta = _richiesta_youtube(url_pagina_live)
        risposta.raise_for_status()
    except Exception:
        return None

    corrispondenza = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', risposta.text)
    return corrispondenza.group(1) if corrispondenza else None


def _scarica_pagina_streams(url_pagina_streams):
    try:
        risposta = _richiesta_youtube(url_pagina_streams)
        risposta.raise_for_status()
        return risposta.text
    except Exception:
        return None


def _corrispondenza_successiva(pattern, testo, posizione, raggio=500):
    """Cerca 'pattern' solo in avanti rispetto a 'posizione' (mai indietro),
    entro 'raggio' caratteri, e restituisce il primo gruppo trovato.
    L'ID video e' quasi sempre il primo campo di un blocco nella pagina di
    YouTube, con titolo e stato subito dopo: cercare solo in avanti evita
    di associare per errore titolo/stato del blocco precedente quando le
    voci sono ravvicinate nel testo della pagina."""
    finestra = testo[posizione: posizione + raggio]
    m = re.search(pattern, finestra)
    return m.group(1) if m else None


@st.cache_data(ttl=300, show_spinner=False)
def _video_live_multipli(url_pagina_streams, escludi_parole=None, limite=4):
    """Trova piu' video attualmente in diretta contemporaneamente, dalla
    pagina "/streams" di un canale (utile per canali che trasmettono piu'
    dirette insieme, come NASA o NASASpaceflight).

    Approccio euristico sulla struttura della pagina pubblica di YouTube:
    se in futuro YouTube cambia formato potrebbe smettere di funzionare
    e andare aggiustato.
    """
    testo = _scarica_pagina_streams(url_pagina_streams)
    if not testo:
        return []

    risultati, visti = [], set()
    for m in re.finditer(r'"videoId":"([a-zA-Z0-9_-]{11})"', testo):
        video_id = m.group(1)
        if video_id in visti:
            continue

        stile = _corrispondenza_successiva(r'"style":"(LIVE|UPCOMING)"', testo, m.end())
        if stile != "LIVE":
            continue

        titolo = _corrispondenza_successiva(
            r'"title":\{"runs":\[\{"text":"([^"]{1,150})"', testo, m.end()
        ) or "Diretta senza titolo"

        if escludi_parole and any(p.lower() in titolo.lower() for p in escludi_parole):
            continue
        visti.add(video_id)
        risultati.append({"video_id": video_id, "titolo": titolo})
        if len(risultati) >= limite:
            break
    return risultati


@st.cache_data(ttl=1800, show_spinner=False)
def _video_programmati(url_pagina_streams, limite=5):
    """Dirette programmate (non ancora iniziate) elencate nella pagina
    "/streams" di un canale."""
    testo = _scarica_pagina_streams(url_pagina_streams)
    if not testo:
        return []

    risultati, visti = [], set()
    for m in re.finditer(r'"videoId":"([a-zA-Z0-9_-]{11})"', testo):
        video_id = m.group(1)
        if video_id in visti:
            continue

        stile = _corrispondenza_successiva(r'"style":"(LIVE|UPCOMING)"', testo, m.end())
        if stile != "UPCOMING":
            continue

        titolo = _corrispondenza_successiva(
            r'"title":\{"runs":\[\{"text":"([^"]{1,150})"', testo, m.end()
        ) or "Diretta programmata"

        visti.add(video_id)
        risultati.append({"video_id": video_id, "titolo": titolo})
        if len(risultati) >= limite:
            break
    return risultati


def _diagnostica_richiesta(url):
    """Esegue la stessa richiesta usata per cercare i video live, ma
    restituendo informazioni grezze utili a capire un eventuale blocco
    (pagina di consenso cookie, blocco anti-bot, redirect, errore HTTP),
    invece del solo risultato finale gia elaborato."""
    try:
        risposta = _richiesta_youtube(url)
        return {
            "codice_stato": risposta.status_code,
            "url_finale": risposta.url,
            "lunghezza_pagina": len(risposta.text),
            "contiene_videoId": '"videoId"' in risposta.text,
            "anteprima": risposta.text[:300],
        }
    except Exception as e:
        return {"errore": str(e)}


def pagina_live():
    if st.button("← Torna all'archivio"):
        vai_a("dashboard")

    st.title("🔴 Live")
    st.caption(
        "Dirette ufficiali o 24/7 conosciute, mostrate direttamente qui. Alcune sono "
        "attive solo quando c'e' un evento in corso: se un canale non e' in diretta "
        "in questo momento, te lo segnalo."
    )

    if e_admin():
        with st.expander("🔧 Diagnostica (solo admin) — perche' un canale risulta offline"):
            st.caption(
                "Mostra cosa risponde davvero il server quando contatta YouTube: utile "
                "per capire se il canale e' davvero offline o se c'e' un blocco/redirect."
            )
            if st.button("Esegui diagnostica ora"):
                for canale in CANALI_LIVE:
                    st.write(f"**{canale['titolo']}**")
                    info = _diagnostica_richiesta(canale["url_live"])
                    st.json(info)

    st.divider()

    for canale in CANALI_LIVE:
        with st.container(border=True):
            st.subheader(canale["titolo"])
            st.caption(canale["descrizione"])
            id_video = _video_live_attuale(canale["url_live"])
            if id_video:
                st.video(f"https://www.youtube.com/watch?v={id_video}")
            else:
                st.info("Questo canale non risulta in diretta in questo momento.")
                st.link_button("Apri il canale su YouTube", canale["url_live"])

    st.divider()
    st.subheader("📡 Altre dirette NASA in corso")
    st.caption("Dirette NASA diverse dalla webcam ISS qui sopra (es. lanci, eventi, conferenze).")
    altre_nasa = _video_live_multipli(
        "https://www.youtube.com/@NASA/streams",
        escludi_parole=["Space Station", "ISS", "Stazione Spaziale"],
    )
    if not altre_nasa:
        st.caption("Nessun'altra diretta NASA in corso al momento.")
    else:
        for v in altre_nasa:
            with st.container(border=True):
                st.write(f"**{v['titolo']}**")
                st.video(f"https://www.youtube.com/watch?v={v['video_id']}")

    st.divider()
    st.subheader("📡 NASASpaceflight — Starbase, Space Coast e altre dirette")
    altre_nsf = _video_live_multipli("https://www.youtube.com/@NASASpaceflight/streams")
    if not altre_nsf:
        st.caption("Nessuna diretta NASASpaceflight in corso al momento.")
    else:
        for v in altre_nsf:
            with st.container(border=True):
                st.write(f"**{v['titolo']}**")
                st.video(f"https://www.youtube.com/watch?v={v['video_id']}")

    programmate = _video_programmati("https://www.youtube.com/@NASASpaceflight/streams")
    if programmate:
        st.write("**🗓️ Prossime dirette programmate (NASASpaceflight):**")
        for v in programmate:
            st.write(f"· [{v['titolo']}](https://www.youtube.com/watch?v={v['video_id']})")


# ---------------------------------------------------------------------------
# Pagina: guide (raccolta di link utili, gestita dall'amministratore)
# ---------------------------------------------------------------------------

def pagina_guide():
    if st.button("← Torna all'archivio"):
        vai_a("dashboard")

    st.title("📚 Guide")

    if e_admin():
        with st.expander("➕ Aggiungi guida"):
            with st.form("form_nuova_guida", clear_on_submit=True):
                titolo = st.text_input("Titolo")
                categoria = st.text_input("Categoria (es. Osservatorio, Live, Missioni)")
                url = st.text_input("Link (https://...)")
                descrizione = st.text_area("Descrizione (facoltativa)", height=80)
                crea = st.form_submit_button("Aggiungi", type="primary", use_container_width=True)

            if crea:
                if not titolo.strip() or not url.strip():
                    st.error("Titolo e link sono obbligatori.")
                else:
                    db.inserisci_guida(
                        titolo.strip(), descrizione.strip() or None, url.strip(),
                        categoria.strip() or "Generale", st.session_state.utente["username"],
                    )
                    st.success(f"Guida '{titolo}' aggiunta.")
                    st.rerun()

    st.divider()

    guide = db.elenco_guide()
    if not guide:
        st.info("Nessuna guida ancora presente.")
        return

    categorie = {}
    for g in guide:
        categorie.setdefault(g["categoria"] or "Generale", []).append(g)

    for categoria, elenco in categorie.items():
        st.subheader(categoria)
        for g in elenco:
            with st.container(border=True):
                st.markdown(f"**{g['titolo']}**")
                if g["descrizione"]:
                    st.caption(g["descrizione"])
                if g["url"]:
                    st.link_button("Apri la guida", g["url"])

                if e_admin():
                    bc1, bc2 = st.columns(2)
                    if bc1.button("Modifica", key=f"mod_guida_{g['id']}", use_container_width=True):
                        st.session_state.guida_in_modifica = (
                            None if st.session_state.guida_in_modifica == g["id"] else g["id"]
                        )
                        st.rerun()
                    if bc2.button("Elimina", key=f"elim_guida_{g['id']}", use_container_width=True):
                        st.session_state.conferma_elimina_guida = g["id"]
                        st.rerun()

                if st.session_state.conferma_elimina_guida == g["id"]:
                    st.warning(f"Confermi l'eliminazione di **{g['titolo']}**?")
                    cc1, cc2 = st.columns(2)
                    if cc1.button("Si, elimina", key=f"conferma_elim_guida_{g['id']}", type="primary"):
                        db.elimina_guida(g["id"])
                        st.session_state.conferma_elimina_guida = None
                        st.success("Guida eliminata.")
                        st.rerun()
                    if cc2.button("Annulla", key=f"annulla_elim_guida_{g['id']}"):
                        st.session_state.conferma_elimina_guida = None
                        st.rerun()

                if e_admin() and st.session_state.guida_in_modifica == g["id"]:
                    with st.form(f"form_modifica_guida_{g['id']}"):
                        m_titolo = st.text_input("Titolo", value=g["titolo"])
                        m_categoria = st.text_input("Categoria", value=g["categoria"] or "Generale")
                        m_url = st.text_input("Link", value=g["url"] or "")
                        m_descrizione = st.text_area("Descrizione", value=g["descrizione"] or "", height=80)
                        salva, annulla = st.columns(2)
                        salva_click = salva.form_submit_button("Salva", type="primary", use_container_width=True)
                        annulla_click = annulla.form_submit_button("Annulla", use_container_width=True)

                    if salva_click:
                        if not m_titolo.strip() or not m_url.strip():
                            st.error("Titolo e link sono obbligatori.")
                        else:
                            db.aggiorna_guida(
                                g["id"], m_titolo.strip(), m_descrizione.strip() or None,
                                m_url.strip(), m_categoria.strip() or "Generale",
                            )
                            st.session_state.guida_in_modifica = None
                            st.success("Guida aggiornata.")
                            st.rerun()
                    if annulla_click:
                        st.session_state.guida_in_modifica = None
                        st.rerun()


# ---------------------------------------------------------------------------
# Pagina: quiz spaziali e badge
# ---------------------------------------------------------------------------

def _badge_da_assegnare(punti_totali):
    """Elenco dei badge che spettano a un utente in base ai punti totali."""
    return [nome for soglia, nome in SOGLIE_BADGE if punti_totali >= soglia]


def pagina_quiz():
    if st.button("← Torna all'archivio"):
        vai_a("dashboard")

    st.title("🎯 Quiz spaziali")

    utente_id = st.session_state.utente["id"]
    punti_totali = db.punti_totali_utente(utente_id)
    badge_posseduti = {b["badge"] for b in db.badge_utente(utente_id)}

    col_punti, col_badge = st.columns([1, 3])
    col_punti.metric("Punti totali", punti_totali)
    with col_badge:
        st.write("**🏅 I tuoi badge:**")
        if badge_posseduti:
            st.write(" · ".join(sorted(badge_posseduti,
                                        key=lambda b: [s for s, n in SOGLIE_BADGE if n == b])))
        else:
            st.caption("Nessun badge ancora — rispondi a un quiz per iniziare a guadagnarli.")

    with st.expander("Come funzionano i badge"):
        for soglia, nome in SOGLIE_BADGE:
            st.write(f"{nome} — da {soglia} punti totali in su")

    st.divider()

    argomento = st.selectbox("Scegli un argomento", list(DOMANDE.keys()), key="quiz_argomento")
    domande = DOMANDE[argomento]

    with st.form(f"form_quiz_{argomento}"):
        risposte_scelte = []
        for i, (domanda, opzioni, _) in enumerate(domande):
            scelta = st.radio(f"{i + 1}. {domanda}", opzioni, key=f"quiz_{argomento}_{i}", index=None)
            risposte_scelte.append(scelta)
        invia_quiz = st.form_submit_button("Correggi il quiz", type="primary", use_container_width=True)

    if invia_quiz:
        if any(r is None for r in risposte_scelte):
            st.error("Rispondi a tutte le domande prima di correggere il quiz.")
        else:
            punteggio = sum(
                1 for (domanda, opzioni, indice_corretto), scelta in zip(domande, risposte_scelte)
                if opzioni.index(scelta) == indice_corretto
            )
            db.salva_risultato_quiz(utente_id, argomento, punteggio, len(domande))

            nuovo_totale = db.punti_totali_utente(utente_id)
            badge_da_avere = _badge_da_assegnare(nuovo_totale)
            nuovi_badge = [b for b in badge_da_avere if b not in badge_posseduti]
            for b in nuovi_badge:
                db.assegna_badge(utente_id, b)

            st.success(f"Hai risposto correttamente a {punteggio} domande su {len(domande)}.")
            if nuovi_badge:
                st.balloons()
                st.success("Nuovo badge sbloccato: " + ", ".join(nuovi_badge))


# ---------------------------------------------------------------------------
# Pagina: iscritti alla newsletter (solo admin)
# ---------------------------------------------------------------------------

def pagina_newsletter():
    if not e_admin():
        st.error("Non hai i permessi per accedere a questa pagina.")
        return

    if st.button("← Torna all'archivio"):
        vai_a("dashboard")

    st.title("Iscritti alla newsletter")
    st.caption("Le persone che hanno chiesto di essere aggiornate sui nuovi voli.")

    with st.expander("⚙️ Configura invio email (da fare una sola volta)"):
        st.caption(
            "Inserisci i dati del server SMTP che userai per inviare i messaggi (es. Gmail, "
            "Outlook, o quello del tuo provider). Per Gmail usa una 'password per le app', "
            "non la password normale del tuo account. Questi dati restano salvati solo nel "
            "database locale di questa app."
        )
        smtp_host = db.leggi_impostazione("smtp_host", "")
        smtp_porta = db.leggi_impostazione("smtp_porta", "587")
        smtp_utente = db.leggi_impostazione("smtp_utente", "")
        smtp_mittente = db.leggi_impostazione("smtp_mittente", "")
        smtp_ssl_diretto = db.leggi_impostazione("smtp_ssl_diretto", "0") == "1"
        email_notifica_reg = db.leggi_impostazione("email_notifica_registrazioni", "laudandomattia@gmail.com")

        with st.form("form_smtp"):
            c1, c2 = st.columns([2, 1])
            n_host = c1.text_input("Server SMTP", value=smtp_host, placeholder="smtp.gmail.com")
            n_porta = c2.text_input("Porta", value=smtp_porta, placeholder="587")
            n_utente = st.text_input("Username SMTP (di solito la tua email)", value=smtp_utente)
            n_password = st.text_input("Password SMTP", type="password",
                                        placeholder="lascia vuoto per non modificarla")
            n_mittente = st.text_input("Indirizzo mittente mostrato ai destinatari", value=smtp_mittente)
            n_ssl_diretto = st.checkbox("Usa connessione SSL diretta (porta 465) invece di STARTTLS",
                                         value=smtp_ssl_diretto)
            n_email_notifica = st.text_input(
                "Email a cui avvisarti delle nuove registrazioni", value=email_notifica_reg,
                help="Ogni volta che qualcuno crea un account da solo dalla schermata di "
                     "login, riceverai qui un'email con i suoi dati.",
            )
            salva_smtp = st.form_submit_button("Salva configurazione", type="primary", use_container_width=True)

        if salva_smtp:
            if not n_host.strip() or not n_porta.strip() or not n_utente.strip() or not n_mittente.strip():
                st.error("Server, porta, username e mittente sono obbligatori.")
            else:
                db.scrivi_impostazione("smtp_host", n_host.strip())
                db.scrivi_impostazione("smtp_porta", n_porta.strip())
                db.scrivi_impostazione("smtp_utente", n_utente.strip())
                db.scrivi_impostazione("smtp_mittente", n_mittente.strip())
                db.scrivi_impostazione("smtp_ssl_diretto", "1" if n_ssl_diretto else "0")
                db.scrivi_impostazione("email_notifica_registrazioni", n_email_notifica.strip())
                if n_password:
                    db.scrivi_impostazione("smtp_password", n_password)
                st.success("Configurazione email salvata.")
                st.rerun()

    st.divider()

    conn = db.get_connection()
    iscritti = conn.execute("SELECT * FROM iscritti_newsletter ORDER BY creato_il DESC").fetchall()
    conn.close()

    if not iscritti:
        st.info("Nessun iscritto per ora.")
        return

    st.metric("Iscritti totali", len(iscritti))

    st.write("")
    st.subheader("📧 Invio rapido tramite Gmail (senza configurare SMTP)")
    st.caption(
        "Apre una bozza su Gmail con tutti gli iscritti gia inseriti in CCN (nascosti "
        "tra loro), oggetto e testo gia compilati. Devi essere gia loggato su Gmail nel "
        "browser; a quel punto ti basta premere 'Invia' dentro Gmail."
    )
    oggetto_rapido = st.text_input("Oggetto", key="oggetto_rapido",
                                    placeholder="Novita nell'Archivio Missioni Spaziali")
    corpo_rapido = st.text_area("Testo del messaggio", key="corpo_rapido", height=150,
                                 placeholder="Scrivi qui il testo che vuoi inviare a tutti gli iscritti...")
    bcc_lista = ",".join(i["email"] for i in iscritti)
    link_gmail_tutti = "https://mail.google.com/mail/?" + urlencode({
        "view": "cm", "fs": 1, "bcc": bcc_lista,
        "su": oggetto_rapido, "body": corpo_rapido,
    })
    st.link_button(
        f"📧 Apri bozza su Gmail per tutti gli iscritti ({len(iscritti)})",
        link_gmail_tutti, type="primary", use_container_width=True,
    )
    if len(iscritti) > 300:
        st.caption(
            "⚠️ Con molti iscritti il link potrebbe risultare troppo lungo per essere "
            "aperto correttamente dal browser: in quel caso usa l'invio via SMTP qui sotto."
        )

    st.divider()

    st.subheader("✉️ Invia un messaggio a tutti gli iscritti (via SMTP)")
    st.caption(
        "I destinatari vengono letti automaticamente dall'elenco iscritti qui sotto: non serve "
        "scrivere nessun indirizzo a mano. Per escludere qualcuno, eliminalo dall'elenco prima di inviare."
    )
    with st.expander(f"Vedi chi ricevera' il messaggio ({len(iscritti)} destinatari)"):
        for i in iscritti:
            st.caption(f"{i['username']} · {i['email']}")

    configurazione_pronta = bool(
        db.leggi_impostazione("smtp_host") and db.leggi_impostazione("smtp_utente")
        and db.leggi_impostazione("smtp_password") and db.leggi_impostazione("smtp_mittente")
    )

    if not configurazione_pronta:
        st.info("Configura prima l'invio email nel pannello '⚙️ Configura invio email' qui sopra.")
    else:
        with st.form("form_invio_newsletter"):
            oggetto = st.text_input("Oggetto", placeholder="Novita nell'Archivio Missioni Spaziali")
            corpo = st.text_area(
                "Testo del messaggio", height=180,
                placeholder="Scrivi qui il testo che vuoi inviare a tutti gli iscritti...",
            )
            invia_a_tutti = st.form_submit_button(
                f"Invia a tutti gli iscritti ({len(iscritti)})", type="primary", use_container_width=True
            )

        if invia_a_tutti:
            if not oggetto.strip() or not corpo.strip():
                st.error("Oggetto e testo del messaggio sono obbligatori.")
            else:
                destinatari = [i["email"] for i in iscritti]
                with st.spinner(f"Invio in corso a {len(destinatari)} iscritti..."):
                    inviate, errori = invia_a_iscritti(
                        host=db.leggi_impostazione("smtp_host"),
                        porta=int(db.leggi_impostazione("smtp_porta", "587")),
                        utente_smtp=db.leggi_impostazione("smtp_utente"),
                        password_smtp=db.leggi_impostazione("smtp_password"),
                        mittente=db.leggi_impostazione("smtp_mittente"),
                        ssl_diretto=db.leggi_impostazione("smtp_ssl_diretto", "0") == "1",
                        destinatari=destinatari,
                        oggetto=oggetto.strip(),
                        corpo=corpo.strip(),
                    )
                if inviate:
                    st.success(f"Messaggio inviato a {inviate} iscritti su {len(destinatari)}.")
                if errori:
                    st.warning("Alcuni invii non sono riusciti:")
                    for e in errori:
                        st.caption(e)

    st.divider()

    buffer = io.StringIO()
    scrittore = csv.writer(buffer)
    scrittore.writerow(["username", "telefono", "email", "iscritto_il"])
    for i in iscritti:
        scrittore.writerow([i["username"], i["telefono"], i["email"], i["creato_il"]])
    st.download_button(
        "⬇️ Scarica elenco (CSV)", data=buffer.getvalue(),
        file_name="iscritti_newsletter.csv", mime="text/csv",
    )

    st.write("")
    for i in iscritti:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([1.5, 1.3, 2, 1.2, 1])
            c1.markdown(f"**{i['username']}**")
            c2.write(i["telefono"])
            c3.write(i["email"])
            link_gmail = (
                "https://mail.google.com/mail/?view=cm&fs=1&to="
                + quote(i["email"])
            )
            c4.link_button("📧 Invia email", link_gmail, use_container_width=True)
            if c5.button("Elimina", key=f"del_newsletter_{i['id']}", use_container_width=True):
                conn = db.get_connection()
                conn.execute("DELETE FROM iscritti_newsletter WHERE id=?", (i["id"],))
                conn.commit()
                conn.close()
                st.rerun()


# ---------------------------------------------------------------------------
# Instradamento principale
# ---------------------------------------------------------------------------

if st.session_state.utente is None:
    pagina_autenticazione()
else:
    barra_laterale()
    view = st.session_state.view
    if view == "dashboard":
        pagina_dashboard()
    elif view == "dettaglio":
        pagina_dettaglio()
    elif view == "form_missione":
        pagina_form_missione()
    elif view == "utenti":
        pagina_utenti()
    elif view == "newsletter":
        pagina_newsletter()
    elif view == "impostazioni":
        pagina_impostazioni()
    elif view == "cielo":
        pagina_cielo()
    elif view == "lanci":
        pagina_lanci()
    elif view == "news":
        pagina_news()
    elif view == "astronauti":
        pagina_astronauti()
    elif view == "quiz":
        pagina_quiz()
    elif view == "live":
        pagina_live()
    elif view == "guide":
        pagina_guide()
    else:
        pagina_dashboard()
