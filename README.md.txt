# Archivio Missioni Spaziali - versione Streamlit

Stessa applicazione multiutente per l'archivio delle missioni spaziali,
riscritta per funzionare con **Streamlit** invece di Flask. Usa lo
stesso database SQLite (`missioni.db`) e le stesse missioni gia
caricate (Apollo, Mercury, Gemini, Skylab, Apollo-Soyuz, Space Shuttle,
Vostok, Soyuz, Crew Dragon, Artemis, ISS).

## Come avviarla

1. Installa le dipendenze:
   ```
   pip install -r requirements.txt
   ```

2. Avvia l'app:
   ```
   streamlit run streamlit_app.py
   ```

3. Si aprira automaticamente il browser su **http://localhost:8501**
   (se non si apre da solo, usa quell'indirizzo manualmente).

Al primo avvio viene creato il file `missioni.db`, gia popolato con le
missioni di partenza.

## Voli esterni in sidebar (da nextspaceflight.com)

nextspaceflight.com non ha un endpoint pubblico proprio: il sito e
alimentato dai dati di **Launch Library 2** (The Space Devs), quindi
l'app interroga direttamente quella fonte, molto piu stabile di uno
scraping della pagina HTML. Nella sidebar trovi quattro pannelli
sempre aggiornati (dati aggiornati ogni ora):

- **Voli precedenti (60 giorni)**
- **Voli programmati**
- **Starship - tutti gli aggiornamenti** (passati e futuri)
- **Artemis - tutti gli aggiornamenti** (passati e futuri)

Da amministratore, ogni volo elencato ha un pulsante **"+ Aggiungi
all'archivio"**: apre il modulo "Nuova missione" con nome, data,
veicolo e sito di lancio gia precompilati (per Starship e Artemis
viene anche proposto il programma corretto). Resta sempre possibile
aggiungere missioni manualmente da zero, come prima.

Serve una connessione internet sul computer dove gira l'app: se il
servizio esterno non e raggiungibile, i pannelli mostrano un avviso
invece di bloccare il resto dell'app.

## Sfondo della pagina di login

Da amministratore, vai su "🖼️ Sfondo login" nel menu laterale per
caricare un'immagine (JPG o PNG, max 5 MB) da mostrare come sfondo
nella schermata di accesso. Resta applicata anche dopo un riavvio
dell'app (e salvata nel database). Puoi sempre rimuoverla per tornare
allo sfondo scuro di default.

## Newsletter

Nella schermata di login, chiunque puo aprire "📰 Iscriviti alla
newsletter" e lasciare nome utente, password, numero di telefono ed
email per essere avvisato sui nuovi voli aggiunti — **senza che
questo crei un account per accedere all'app**: resta una lista di
contatti separata, gestibile solo da te. Da amministratore, la pagina
"📰 Iscritti newsletter" nel menu laterale mostra l'elenco completo con
possibilita di esportarlo in CSV o eliminare singoli iscritti.

### Inviare un messaggio a tutti gli iscritti

Dalla stessa pagina "📰 Iscritti newsletter":

1. Apri "⚙️ Configura invio email" (va fatto una sola volta) e inserisci
   i dati del tuo server SMTP: server, porta, username, password e
   l'indirizzo mittente. Per Gmail: server `smtp.gmail.com`, porta
   `587`, e **una password per le app** generata dalle impostazioni di
   sicurezza del tuo account Google — non la password normale.
   Per Outlook/Hotmail: server `smtp.office365.com`, porta `587`.
2. Scrivi oggetto e testo nel riquadro "✉️ Invia un messaggio a tutti
   gli iscritti" e premi il pulsante di invio: il messaggio parte con
   un invio separato per ciascun iscritto, cosi nessuno vede
   l'indirizzo email degli altri.

La password SMTP resta salvata solo nel file `missioni.db` sul tuo
computer: non condividere quel file con nessuno.

## Primo avvio: crea il tuo account amministratore

**Non esiste una registrazione pubblica.** Quando il database non ha
ancora nessun utente, l'app mostra una schermata unica di
configurazione iniziale: crea li' il tuo account, che diventa
automaticamente amministratore. Da quel momento in poi quella
schermata sparisce e resta visibile solo il modulo di accesso: nessun
altro potra crearsi un account da solo.

## Come creare gli account per gli altri utenti

Solo tu, da amministratore, puoi creare nuovi account: vai su
"Gestione utenti" nel menu laterale, apri "➕ Crea nuovo utente" e
imposta username, password e ruolo. Il ruolo di default e "utente"
(sola visualizzazione: possono consultare, cercare e filtrare le
missioni ma non modificarle). Comunica tu stesso le credenziali alla
persona interessata.

## Ruoli

- **Amministratore**: consulta, aggiunge, modifica ed elimina le
  missioni; crea nuovi utenti; promuove/retrocede/elimina gli utenti
  esistenti.
- **Utente**: consulta, cerca e filtra le missioni (sola lettura,
  nessuna possibilita di modifica).

## Differenze rispetto alla versione Flask

- L'interfaccia e quella nativa di Streamlit (niente HTML/CSS
  personalizzati da mantenere: form, tabelle e pulsanti sono generati
  automaticamente e restano coerenti anche su schermi piccoli).
- La navigazione avviene tramite la barra laterale invece che tramite
  URL distinte per ogni pagina.
- Il database e la logica di business (`database.py`, ruoli, regole di
  autenticazione) sono identici alla versione Flask: puoi passare
  dall'una all'altra senza perdere le missioni salvate, basta usare lo
  stesso file `missioni.db`.
- Le password sono comunque salvate come hash sicuri (PBKDF2-HMAC-SHA256
  tramite il modulo `auth.py`), mai in chiaro.

## Struttura del progetto

```
spacemissions_streamlit/
├── streamlit_app.py       # interfaccia e logica dell'app
├── database.py            # schema SQLite e dati iniziali (identico alla versione Flask)
├── auth.py                # hashing e verifica delle password
├── requirements.txt
├── .streamlit/
│   └── config.toml        # tema scuro coerente con il resto del progetto
└── missioni.db             # creato al primo avvio
```

## Note per l'uso in rete locale/condivisa

Se piu persone devono accedere dalla stessa rete (non solo dal tuo
computer), avvia con:
```
streamlit run streamlit_app.py --server.address 0.0.0.0
```
e comunica agli altri l'indirizzo IP del tuo computer seguito da
`:8501`. Ricorda che Streamlit non gestisce sessioni cifrate di
default: per un uso su internet aperto valuta HTTPS tramite un proxy
(es. Streamlit Community Cloud, oppure nginx con certificato SSL).
