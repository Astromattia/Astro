import streamlit as st

# Configurazione iniziale della pagina in Dark Mode
st.set_page_config(
    page_title="AstroMissioni - Archivio Spaziale",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- BARRA LATERALE (SIDEBAR) ---
st.sidebar.image("https://icons8.com", width=80)
st.sidebar.title("CosmosHub")
st.sidebar.markdown("*Il tuo archivio di esplorazione cosmica*")
st.sidebar.markdown("---")

# Menu di navigazione principale semplice
st.sidebar.markdown("### 🧭 NAVIGAZIONE")
st.sidebar.info("Usa il menu principale del sito per viaggiare tra le sezioni storiche, l'osservatorio e i quiz!")

# --- IL PONTE SPAZIALE (Collegamento a Base44) ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🛰️ Monitora i Lanci Live!")
st.sidebar.warning("Mancano poche ore ai prossimi eventi spaziali! Controlla il countdown in tempo reale su CosmosDB:")

# Il bottone magico che si collega a Base44
st.sidebar.link_button("👉 Entra su CosmosDB Live", "https://base44.app")

st.sidebar.markdown("---")
st.sidebar.caption("Sviluppato con 💙 da Mattia | v2.0")


# --- CONTENUTO DELLA PAGINA DI BENVENUTO ---
st.title("📚 Archivio Missioni Spaziali")
st.markdown("### Cronologia dei voli spaziali, dal programma Mercury alle missioni odierne.")

# Box delle statistiche in evidenza
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Missioni Totali", value="34", delta="🚀")
with col2:
    st.metric(label="Successi globali", value="29", delta="✅")
with col3:
    st.metric(label="Fallimenti storici", value="4", delta="❌", delta_color="inverse")
    
st.markdown("---")

st.subheader("🪐 Primi passi nel cosmo")
st.success("Scegli le voci dal menu per esplorare i dati dello Sputnik, i quiz e l'assistente spaziale!")
