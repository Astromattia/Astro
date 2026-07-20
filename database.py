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
