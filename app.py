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
st.sidebar.info("Usa il menu principale per viaggiare tra le sezioni del sito!")

# --- IL PONTE SPAZIALE (Collegamento corretto a Base44) ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🛰️ Lanci in Tempo Reale")

# Il bottone magico con il link GIUSTO del tuo sito
st.sidebar.link_button("🚀 Apri CosmosDB Live", "https://archiviospaziale.base44.app/")

st.sidebar.markdown("---")
st.sidebar.caption("Sviluppato con 💙 da Mattia | v2.2")


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
