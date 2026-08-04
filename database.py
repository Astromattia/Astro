"""
Gestione del database SQLite per l'archivio missioni spaziali.
Contiene la creazione dello schema e il popolamento iniziale con
le missioni Apollo e altre missioni storiche dei voli spaziali.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "missioni.db")


def get_connection():
    """Restituisce una connessione al database con le righe accessibili come dizionari."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Crea le tabelle se non esistono ancora."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS utenti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            ruolo TEXT NOT NULL DEFAULT 'utente' CHECK (ruolo IN ('admin', 'utente')),
            data_nascita TEXT,
            professione TEXT,
            approvato INTEGER NOT NULL DEFAULT 1,
            creato_il TEXT NOT NULL
        )
    """)

    # Migrazione: se il database esisteva gia prima dell'introduzione di
    # questi campi, aggiungili senza perdere gli utenti gia presenti.
    colonne_utenti = {riga["name"] for riga in cur.execute("PRAGMA table_info(utenti)")}
    if "data_nascita" not in colonne_utenti:
        cur.execute("ALTER TABLE utenti ADD COLUMN data_nascita TEXT")
    if "professione" not in colonne_utenti:
        cur.execute("ALTER TABLE utenti ADD COLUMN professione TEXT")
    if "approvato" not in colonne_utenti:
        # Gli utenti gia esistenti (creati prima di questa funzionalita)
        # sono considerati automaticamente approvati.
        cur.execute("ALTER TABLE utenti ADD COLUMN approvato INTEGER NOT NULL DEFAULT 1")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS missioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            programma TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'con equipaggio',
            data_lancio TEXT,
            veicolo TEXT,
            equipaggio TEXT,
            esito TEXT NOT NULL DEFAULT 'pianificata',
            descrizione TEXT,
            creato_da TEXT,
            creato_il TEXT NOT NULL,
            aggiornato_il TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS impostazioni (
            chiave TEXT PRIMARY KEY,
            valore TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS iscritti_newsletter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            telefono TEXT NOT NULL,
            email TEXT NOT NULL,
            creato_il TEXT NOT NULL
        )
    """)

    # --- Nuove tabelle: archivio astronauti, quiz, badge -------------------
    # Aggiunte in coda, senza toccare nulla di esistente sopra: il database
    # gia' presente su un deploy precedente si aggiorna da solo, senza
    # perdere nulla (missioni, utenti, iscritti, impostazioni cielo/SMTP).

    cur.execute("""
        CREATE TABLE IF NOT EXISTS astronauti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            nazionalita TEXT,
            agenzia TEXT,
            missioni_effettuate TEXT,
            ore_nello_spazio REAL DEFAULT 0,
            biografia TEXT,
            creato_da TEXT,
            creato_il TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_risultati (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            utente_id INTEGER NOT NULL REFERENCES utenti(id) ON DELETE CASCADE,
            argomento TEXT NOT NULL,
            punteggio INTEGER NOT NULL,
            totale_domande INTEGER NOT NULL,
            creato_il TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS badge_assegnati (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            utente_id INTEGER NOT NULL REFERENCES utenti(id) ON DELETE CASCADE,
            badge TEXT NOT NULL,
            assegnato_il TEXT NOT NULL,
            UNIQUE(utente_id, badge)
        )
    """)

    conn.commit()
    conn.close()


def leggi_impostazione(chiave, default=None):
    """Legge il valore di un'impostazione (es. sfondo login). Restituisce default se assente."""
    conn = get_connection()
    riga = conn.execute("SELECT valore FROM impostazioni WHERE chiave = ?", (chiave,)).fetchone()
    conn.close()
    return riga["valore"] if riga else default


def scrivi_impostazione(chiave, valore):
    """Crea o aggiorna un'impostazione."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO impostazioni (chiave, valore) VALUES (?, ?) "
        "ON CONFLICT(chiave) DO UPDATE SET valore = excluded.valore",
        (chiave, valore),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Astronauti
# ---------------------------------------------------------------------------

def elenco_astronauti():
    conn = get_connection()
    righe = conn.execute("SELECT * FROM astronauti ORDER BY nome ASC").fetchall()
    conn.close()
    return righe


# Astronauti famosi proposti per il caricamento rapido. Le ore nello spazio
# sono cifre storiche approssimative (arrotondate dai giorni cumulativi
# noti pubblicamente): l'amministratore puo' sempre correggerle a mano
# dopo il caricamento, dalla scheda "Modifica" di ciascun astronauta.
ASTRONAUTI_FAMOSI = [
    ("Luca Parmitano", "Italiana", "ESA", "Expedition 36/37, Expedition 60/61 (comandante ISS)",
     8800, "Primo italiano a comandare la Stazione Spaziale Internazionale (Expedition 61)."),
    ("Samantha Cristoforetti", "Italiana", "ESA", "Expedition 42/43, Minerva (Expedition 68/69)",
     8800, "Prima donna italiana nello spazio; detentrice per anni del record europeo di permanenza continua nello spazio."),
    ("Paolo Nespoli", "Italiana", "ESA", "STS-120, Expedition 26/27, Expedition 52/53",
     7500, "Tra gli astronauti italiani con piu tempo cumulativo nello spazio, su tre missioni diverse."),
    ("Umberto Guidoni", "Italiana", "ESA", "STS-75, STS-100",
     650, "Primo astronauta europeo a bordo della Stazione Spaziale Internazionale."),
    ("Yuri Gagarin", "Sovietica", "URSS", "Vostok 1",
     2, "Primo essere umano nello spazio e a orbitare la Terra, 12 aprile 1961."),
    ("Valentina Tereshkova", "Sovietica", "URSS", "Vostok 6",
     71, "Prima donna nello spazio, 1963."),
    ("Neil Armstrong", "Statunitense", "NASA", "Gemini 8, Apollo 11",
     200, "Primo essere umano a camminare sulla Luna, 20 luglio 1969."),
    ("Buzz Aldrin", "Statunitense", "NASA", "Gemini 12, Apollo 11",
     290, "Secondo uomo a camminare sulla Luna, insieme a Neil Armstrong nella missione Apollo 11."),
    ("Sally Ride", "Statunitense", "NASA", "STS-7, STS-41-G",
     343, "Prima donna statunitense nello spazio, 1983."),
    ("Chris Hadfield", "Canadese", "CSA", "STS-74, STS-100, Expedition 34/35 (comandante ISS)",
     4000, "Primo canadese a comandare la Stazione Spaziale Internazionale; noto anche per i video musicali dallo spazio."),
    ("Scott Kelly", "Statunitense", "NASA", "STS-103, STS-118, Expedition 25/26, Expedition 43/44/45/46 (Anno nello Spazio)",
     12400, "Ha trascorso quasi un anno consecutivo sulla ISS in un celebre studio di medicina spaziale sui gemelli."),
    ("Peggy Whitson", "Statunitense", "NASA", "Expedition 5, Expedition 16, Expedition 50/51/52, Axiom Mission 2",
     16000, "Detentrice del record statunitense di tempo cumulativo nello spazio tra gli astronauti."),
]


def popola_astronauti_famosi():
    """Carica gli astronauti famosi proposti, saltando quelli gia presenti
    (confronto per nome esatto), cosi' si puo' premere piu volte senza
    creare doppioni. Restituisce quanti ne ha effettivamente aggiunti."""
    esistenti = {a["nome"] for a in elenco_astronauti()}
    aggiunti = 0
    for nome, nazionalita, agenzia, missioni, ore, bio in ASTRONAUTI_FAMOSI:
        if nome not in esistenti:
            inserisci_astronauta(nome, nazionalita, agenzia, missioni, ore, bio, "sistema")
            aggiunti += 1
    return aggiunti


def inserisci_astronauta(nome, nazionalita, agenzia, missioni_effettuate,
                          ore_nello_spazio, biografia, creato_da):
    conn = get_connection()
    conn.execute(
        "INSERT INTO astronauti (nome, nazionalita, agenzia, missioni_effettuate, "
        "ore_nello_spazio, biografia, creato_da, creato_il) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (nome, nazionalita, agenzia, missioni_effettuate, ore_nello_spazio, biografia,
         creato_da, datetime.utcnow().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def aggiorna_astronauta(id_astronauta, nome, nazionalita, agenzia, missioni_effettuate,
                         ore_nello_spazio, biografia):
    conn = get_connection()
    conn.execute(
        "UPDATE astronauti SET nome=?, nazionalita=?, agenzia=?, missioni_effettuate=?, "
        "ore_nello_spazio=?, biografia=? WHERE id=?",
        (nome, nazionalita, agenzia, missioni_effettuate, ore_nello_spazio, biografia,
         id_astronauta),
    )
    conn.commit()
    conn.close()


def elimina_astronauta(id_astronauta):
    conn = get_connection()
    conn.execute("DELETE FROM astronauti WHERE id=?", (id_astronauta,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Quiz e badge
# ---------------------------------------------------------------------------

def salva_risultato_quiz(utente_id, argomento, punteggio, totale_domande):
    conn = get_connection()
    conn.execute(
        "INSERT INTO quiz_risultati (utente_id, argomento, punteggio, totale_domande, "
        "creato_il) VALUES (?, ?, ?, ?, ?)",
        (utente_id, argomento, punteggio, totale_domande,
         datetime.utcnow().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def cronologia_quiz_utente(utente_id):
    conn = get_connection()
    righe = conn.execute(
        "SELECT * FROM quiz_risultati WHERE utente_id=? ORDER BY creato_il DESC",
        (utente_id,),
    ).fetchall()
    conn.close()
    return righe


def punti_totali_utente(utente_id):
    """Somma di tutti i punti guadagnati nei quiz da un utente (usata per i badge)."""
    conn = get_connection()
    riga = conn.execute(
        "SELECT COALESCE(SUM(punteggio), 0) AS totale FROM quiz_risultati WHERE utente_id=?",
        (utente_id,),
    ).fetchone()
    conn.close()
    return riga["totale"]


def badge_utente(utente_id):
    conn = get_connection()
    righe = conn.execute(
        "SELECT badge, assegnato_il FROM badge_assegnati WHERE utente_id=? ORDER BY assegnato_il ASC",
        (utente_id,),
    ).fetchall()
    conn.close()
    return righe


def assegna_badge(utente_id, badge):
    """Assegna un badge se l'utente non lo ha gia (UNIQUE evita i duplicati)."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO badge_assegnati (utente_id, badge, assegnato_il) VALUES (?, ?, ?) "
        "ON CONFLICT(utente_id, badge) DO NOTHING",
        (utente_id, badge, datetime.utcnow().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def elimina_impostazione(chiave):
    conn = get_connection()
    conn.execute("DELETE FROM impostazioni WHERE chiave = ?", (chiave,))
    conn.commit()
    conn.close()


def missioni_esistenti():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) AS c FROM missioni").fetchone()["c"]
    conn.close()
    return count


SEED_MISSIONI = [
    # (nome, programma, tipo, data_lancio, veicolo, equipaggio, esito, descrizione)
    ("Apollo 1", "Apollo", "con equipaggio", "1967-02-21", "Saturn IB",
     "Virgil Grissom, Edward White, Roger Chaffee",
     "fallita",
     "Test a terra terminato in tragedia: un incendio nella capsula durante una prova "
     "pre-lancio uccise i tre astronauti. La missione non decollò mai; l'evento portò "
     "a una profonda revisione della sicurezza del programma Apollo."),
    ("Apollo 7", "Apollo", "con equipaggio", "1968-10-11", "Saturn IB",
     "Walter Schirra, Donn Eisele, Walter Cunningham",
     "successo",
     "Primo volo con equipaggio del programma Apollo, in orbita terrestre. Verificò il "
     "modulo di comando dopo l'incidente dell'Apollo 1."),
    ("Apollo 8", "Apollo", "con equipaggio", "1968-12-21", "Saturn V",
     "Frank Borman, James Lovell, William Anders",
     "successo",
     "Primo volo umano a orbitare la Luna. Celebre per la fotografia 'Earthrise' e la "
     "lettura del Genesi in diretta durante la vigilia di Natale."),
    ("Apollo 9", "Apollo", "con equipaggio", "1969-03-03", "Saturn V",
     "James McDivitt, David Scott, Russell Schweickart",
     "successo",
     "Primo test in orbita terrestre del modulo lunare completo, incluso l'aggancio "
     "con il modulo di comando."),
    ("Apollo 10", "Apollo", "con equipaggio", "1969-05-18", "Saturn V",
     "Thomas Stafford, John Young, Eugene Cernan",
     "successo",
     "Prova generale dello sbarco lunare: il modulo lunare scese fino a circa 15 km "
     "dalla superficie senza allunare."),
    ("Apollo 11", "Apollo", "con equipaggio", "1969-07-16", "Saturn V",
     "Neil Armstrong, Michael Collins, Edwin 'Buzz' Aldrin",
     "successo",
     "Primo sbarco umano sulla Luna. Neil Armstrong e Buzz Aldrin camminarono sul Mare "
     "della Tranquillita il 20 luglio 1969, mentre Michael Collins rimaneva in orbita."),
    ("Apollo 12", "Apollo", "con equipaggio", "1969-11-14", "Saturn V",
     "Charles Conrad, Richard Gordon, Alan Bean",
     "successo",
     "Secondo allunaggio, con atterraggio di precisione vicino alla sonda Surveyor 3."),
    ("Apollo 13", "Apollo", "con equipaggio", "1970-04-11", "Saturn V",
     "James Lovell, Jack Swigert, Fred Haise",
     "fallita",
     "L'esplosione di un serbatoio di ossigeno costrinse ad annullare l'allunaggio. "
     "L'equipaggio rientrò sano e salvo usando il modulo lunare come scialuppa di "
     "salvataggio, in quella che divenne nota come un 'fallimento di successo'."),
    ("Apollo 14", "Apollo", "con equipaggio", "1971-01-31", "Saturn V",
     "Alan Shepard, Stuart Roosa, Edgar Mitchell",
     "successo",
     "Terzo allunaggio, nella regione di Fra Mauro. Alan Shepard giocò a golf sulla "
     "superficie lunare."),
    ("Apollo 15", "Apollo", "con equipaggio", "1971-07-26", "Saturn V",
     "David Scott, Alfred Worden, James Irwin",
     "successo",
     "Prima missione a utilizzare il rover lunare, con esplorazioni estese della "
     "regione degli Appennini lunari."),
    ("Apollo 16", "Apollo", "con equipaggio", "1972-04-16", "Saturn V",
     "John Young, Thomas Mattingly, Charles Duke",
     "successo",
     "Esplorazione degli altopiani lunari nella regione di Descartes."),
    ("Apollo 17", "Apollo", "con equipaggio", "1972-12-07", "Saturn V",
     "Eugene Cernan, Ronald Evans, Harrison Schmitt",
     "successo",
     "Ultima missione Apollo con sbarco lunare. Harrison Schmitt fu il primo geologo "
     "professionista sulla Luna. Eugene Cernan resta l'ultimo uomo ad aver camminato "
     "sulla Luna."),

    ("Mercury-Redstone 3 (Freedom 7)", "Mercury", "con equipaggio", "1961-05-05",
     "Redstone", "Alan Shepard", "successo",
     "Primo volo suborbitale statunitense con equipaggio: Alan Shepard divenne il "
     "primo americano nello spazio."),
    ("Mercury-Atlas 6 (Friendship 7)", "Mercury", "con equipaggio", "1962-02-20",
     "Atlas LV-3B", "John Glenn", "successo",
     "John Glenn divenne il primo americano a orbitare la Terra, compiendo tre orbite."),
    ("Mercury-Atlas 9 (Faith 7)", "Mercury", "con equipaggio", "1963-05-15",
     "Atlas LV-3B", "Gordon Cooper", "successo",
     "Ultimo volo del programma Mercury: 22 orbite terrestri, il volo americano più "
     "lungo fino ad allora."),

    ("Gemini 3", "Gemini", "con equipaggio", "1965-03-23", "Titan II",
     "Virgil Grissom, John Young", "successo",
     "Primo volo con equipaggio del programma Gemini, con la prima manovra orbitale "
     "controllata della storia."),
    ("Gemini 4", "Gemini", "con equipaggio", "1965-06-03", "Titan II",
     "James McDivitt, Edward White", "successo",
     "Edward White compi la prima passeggiata spaziale statunitense."),
    ("Gemini 6A", "Gemini", "con equipaggio", "1965-12-15", "Titan II",
     "Walter Schirra, Thomas Stafford", "successo",
     "Primo rendez-vous orbitale della storia, con Gemini 7."),
    ("Gemini 7", "Gemini", "con equipaggio", "1965-12-04", "Titan II",
     "Frank Borman, James Lovell", "successo",
     "Missione di quasi 14 giorni per studiare gli effetti della permanenza "
     "prolungata nello spazio."),
    ("Gemini 8", "Gemini", "con equipaggio", "1966-03-16", "Titan II",
     "Neil Armstrong, David Scott", "successo",
     "Primo aggancio tra due veicoli spaziali, con l'Agena Target Vehicle. Un "
     "malfunzionamento causò un pericoloso avvitamento, gestito con un rientro "
     "d'emergenza."),
    ("Gemini 12", "Gemini", "con equipaggio", "1966-11-11", "Titan II",
     "James Lovell, Edwin 'Buzz' Aldrin", "successo",
     "Ultimo volo del programma Gemini. Aldrin dimostro che le attivita extraveicolari "
     "erano gestibili in modo efficace."),

    ("Apollo-Soyuz Test Project", "Apollo-Soyuz", "con equipaggio", "1975-07-15",
     "Saturn IB / Soyuz", "Thomas Stafford, Vance Brand, Donald Slayton "
     "(equipaggio USA); Alexei Leonov, Valeri Kubasov (equipaggio URSS)",
     "successo",
     "Primo aggancio in orbita tra veicoli statunitensi e sovietici, simbolo della "
     "distensione nella Guerra Fredda."),

    ("Skylab 2", "Skylab", "con equipaggio", "1973-05-25", "Saturn IB",
     "Charles Conrad, Paul Weitz, Joseph Kerwin", "successo",
     "Primo equipaggio a bordo della stazione spaziale Skylab; riparo i danni "
     "riportati al lancio della stazione."),
    ("Skylab 4", "Skylab", "con equipaggio", "1973-11-16", "Saturn IB",
     "Gerald Carr, William Pogue, Edward Gibson", "successo",
     "Missione piu lunga a bordo di Skylab, quasi 84 giorni in orbita."),

    ("STS-1 (Columbia)", "Space Shuttle", "con equipaggio", "1981-04-12",
     "Space Shuttle Columbia", "John Young, Robert Crippen", "successo",
     "Primo volo orbitale dello Space Shuttle, inaugura l'era dei veicoli spaziali "
     "riutilizzabili."),
    ("STS-51-L (Challenger)", "Space Shuttle", "con equipaggio", "1986-01-28",
     "Space Shuttle Challenger",
     "Francis Scobee, Michael Smith, Judith Resnik, Ellison Onizuka, Ronald McNair, "
     "Gregory Jarvis, Christa McAuliffe",
     "fallita",
     "Lo Shuttle esplose 73 secondi dopo il lancio a causa del cedimento di una "
     "guarnizione, causando la morte di tutti e sette i membri dell'equipaggio."),
    ("STS-107 (Columbia)", "Space Shuttle", "con equipaggio", "2003-01-16",
     "Space Shuttle Columbia",
     "Rick Husband, William McCool, Michael Anderson, David Brown, Kalpana Chawla, "
     "Laurel Clark, Ilan Ramon",
     "fallita",
     "Il Columbia si disintegro durante il rientro atmosferico a causa di un danno "
     "allo scudo termico, causando la morte di tutto l'equipaggio."),
    ("STS-135 (Atlantis)", "Space Shuttle", "con equipaggio", "2011-07-08",
     "Space Shuttle Atlantis",
     "Christopher Ferguson, Douglas Hurley, Sandra Magnus, Rex Walheim", "successo",
     "Ultima missione del programma Space Shuttle, dopo 30 anni di attivita."),

    ("Sputnik 1", "Programma sovietico", "senza equipaggio", "1957-10-04",
     "Sputnik 8K71PS", "nessuno", "successo",
     "Primo satellite artificiale della storia, diede inizio alla corsa allo spazio."),
    ("Vostok 1", "Vostok", "con equipaggio", "1961-04-12", "Vostok-K",
     "Yuri Gagarin", "successo",
     "Yuri Gagarin divenne il primo essere umano nello spazio e a orbitare la Terra."),

    ("Soyuz TMA (varie)", "Soyuz", "con equipaggio", "1967-01-01",
     "Soyuz", "equipaggi variabili nel corso del programma", "in corso",
     "Famiglia di veicoli sovietici e poi russi tuttora in uso per il trasporto di "
     "equipaggi verso la ISS."),

    ("Crew Dragon Demo-2", "Commercial Crew (SpaceX)", "con equipaggio",
     "2020-05-30", "Falcon 9 / Crew Dragon Endeavour",
     "Robert Behnken, Douglas Hurley", "successo",
     "Primo volo con equipaggio di una capsula commerciale statunitense verso la "
     "ISS, primo lancio umano dagli USA dal 2011."),
    ("Artemis I", "Artemis", "senza equipaggio", "2022-11-16",
     "Space Launch System / Orion", "nessuno (volo di collaudo)", "successo",
     "Primo volo del razzo SLS e della capsula Orion, missione senza equipaggio "
     "attorno alla Luna in preparazione al ritorno umano sul suolo lunare."),

    ("ISS - Expedition 1", "Stazione Spaziale Internazionale", "con equipaggio",
     "2000-10-31", "Soyuz TM-31",
     "William Shepherd, Yuri Gidzenko, Sergei Krikalev", "successo",
     "Primo equipaggio permanente della Stazione Spaziale Internazionale, inizio di "
     "una presenza umana continua nello spazio che dura tuttora."),
]


def popola_dati_iniziali():
    """Inserisce le missioni di partenza se il database e vuoto."""
    if missioni_esistenti() > 0:
        return

    conn = get_connection()
    ora = datetime.utcnow().isoformat(timespec="seconds")
    for nome, programma, tipo, data_lancio, veicolo, equipaggio, esito, descrizione in SEED_MISSIONI:
        conn.execute(
            """INSERT INTO missioni
               (nome, programma, tipo, data_lancio, veicolo, equipaggio, esito,
                descrizione, creato_da, creato_il)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (nome, programma, tipo, data_lancio, veicolo, equipaggio, esito,
             descrizione, "sistema", ora),
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    popola_dati_iniziali()
    print(f"Database pronto in: {DB_PATH}")
    print(f"Missioni presenti: {missioni_esistenti()}")
