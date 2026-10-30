import streamlit as st
from notizie_spaziali import mostra_notizie
from cielo_notturno import mostra_cielo
from quiz_dati import mostra_quiz
from database import inizializza_db

# Configurazione iniziale della pagina in Dark Mode
st.set_page_config(
    page_title="AstroMissioni - Archivio Spaziale",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inizializza il database se necessario
inizializza_db()

# --- BARRA LATERALE (SIDEBAR) ---
st.sidebar.image("https://icons8.com", width=80)
st.sidebar.title("CosmosHub")
st.sidebar.markdown("*Il tuo archivio di esplorazione cosmica*")
st.sidebar.markdown("---")

# Menu di navigazione principale
opzione = st.sidebar.radio(
    "🧭 NAVIGAZIONE",
    ["🏠 Home Archivio", "📰 News Spaziali", "🌌 Osservatorio Astronomico", "🎯 Quiz Spaziale"]
)

# --- IL PONTE SPAZIALE (Collegamento a Base44) ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🛰️ Monitora i Lanci Live!")
st.sidebar.info("Vuoi vedere i prossimi vettori e razzi pronti sulla rampa in tempo reale?")
st.sidebar.link_button("👉 Entra su CosmosDB Live", "https://base44.app")

st.sidebar.markdown("---")
st.sidebar.caption("Sviluppato con 💙 da Mattia | v2.0")


# --- CONTENUTO PRINCIPALE ---
if opzione == "🏠 Home Archivio":
    st.title("📚 Archivio Missioni Spaziali")
    st.markdown("### Cronologia dei voli spaziali, dal programma Mercury alle missioni odierne.")
    
    # Box delle statistiche in evidenza
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Missioni Totali", value="34", delta="🚀")
    with col2:
        st.metric(label="Successi globali", value="29", delta="✅", delta_color="normal")
    with col3:
        st.metric(label="Fallimenti storici", value="4", delta="❌", delta_color="inverse")
        
    st.markdown("---")
    
    # Tabella esplorativa delle missioni storiche
    st.subheader("🎵 Primi passi nel cosmo")
    st.info("Usa il motore di ricerca integrato per filtrare i dati storici dei lanci.")
    
    # Esempio grafico di tabella interattiva
    missioni_es = [
        {"Data": "1957-10-04", "Missione": "Sputnik 1", "Programma": "Sovietico", "Tipo": "Senza Equipaggio", "Esito": "SUCCESS"},
        {"Data": "1961-04-12", "Missione": "Vostok 1", "Programma": "Vostok", "Tipo": "Con Equipaggio (Yuri Gagarin)", "Esito": "SUCCESS"}
    ]
    st.table(missioni_es)

elif opzione == "📰 News Spaziali":
    st.title("📰 Giornale di Bordo Spaziale")
    mostra_notizie()

elif opzione == "🌌 Osservatorio Astronomico":
    st.title("🌌 Mappa del Cielo e Costellazioni")
    mostra_cielo()

elif opzione == "🎯 Quiz Spaziale":
    st.title("🎯 Sfida Spaziale per Astronauti")
    st.markdown("Metti alla prova le tue conoscenze del sistema solare e scala la classifica!")
    mostra_quiz()
