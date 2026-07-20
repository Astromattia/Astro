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
import streamlit as st

import database as db
from auth import genera_hash_password, verifica_password
from voli_esterni import voli_precedenti, voli_programmati, voli_per_parola_chiave
from email_utils import invia_a_iscritti

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
    /* Forza lo sfondo scuro dell'app e i campi di input a prescindere dal
       tema (chiaro/scuro) impostato nel browser di chi visita la pagina. */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"], .stApp {
        background-color: #0B1220 !important;
    }
    [data-testid="stHeader"] {
        background-color: transparent !important;
    }
    [data-testid="stSidebar"] {
        background-color: #0E1626 !important;
    }
    input, textarea, select,
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
        background-color: #182238 !important;
        color: #E8ECF4 !important;
        border: 1px solid #26324A !important;
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
if "prefill_esterno" not in st.session_state:
    st.session_state.prefill_esterno = None


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
        else:
            st.session_state.utente = dict(utente)
            st.success(f"Bentornato, {utente['username']}.")
            vai_a("dashboard")

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
                        "INSERT INTO utenti (username, password_hash, ruolo, creato_il) VALUES (?, ?, ?, ?)",
                        (nuovo_username, genera_hash_password(nuova_password), nuovo_ruolo,
                         datetime.utcnow().isoformat(timespec="seconds")),
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Utente '{nuovo_username}' creato con ruolo '{nuovo_ruolo}'.")
                    st.rerun()

    st.divider()

    conn = db.get_connection()
    utenti = conn.execute("SELECT * FROM utenti ORDER BY creato_il ASC").fetchall()
    numero_admin = conn.execute("SELECT COUNT(*) AS c FROM utenti WHERE ruolo='admin'").fetchone()["c"]
    conn.close()

    io = st.session_state.utente

    for u in utenti:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 2, 1.3, 1])
            etichetta = u["username"] + (" (tu)" if u["id"] == io["id"] else "")
            c1.markdown(f"**{etichetta}**")
            c2.markdown(f"`{u['ruolo']}`")
            c3.caption(u["creato_il"])

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

            if u["id"] != io["id"]:
                if c5.button("Elimina", key=f"elimina_{u['id']}", use_container_width=True):
                    st.session_state.conferma_elimina_utente = u["id"]
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
    st.subheader("✉️ Invia un messaggio a tutti gli iscritti")
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
            c1, c2, c3, c4 = st.columns([1.5, 1.3, 2, 1])
            c1.markdown(f"**{i['username']}**")
            c2.write(i["telefono"])
            c3.write(i["email"])
            if c4.button("Elimina", key=f"del_newsletter_{i['id']}", use_container_width=True):
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
    else:
        pagina_dashboard()
