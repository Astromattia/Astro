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

# --- IL PONTE SPAZIALE ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🛰️ Lanci in Tempo Reale")

# Il bottone magico con il tuo link di Base44
st.sidebar.link_button("🚀 Apri CosmosDB Live", "https://archiviospaziale.base44.app/")

st.sidebar.markdown("---")
st.sidebar.caption("Sviluppato con 💙 da Mattia | v2.3")


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

# --- NUOVA SEZIONE: SEGRETI E CURIOSITÀ DELLO SPAZIO ---
st.subheader("👨‍🚀 Lo sapevi che? Curiosità dalla Stazione Spaziale")

col_info1, col_info2 = st.columns(2)

with col_info1:
    st.markdown("""
    #### 🛰️ La casa umana tra le stelle
    La **Stazione Spaziale Internazionale (ISS)** è un laboratorio grandissimo (come un campo da calcio!) che si trova in orbita intorno alla Terra a circa **400 chilometri di altezza**. 
    
    * **Velocità pazzesca:** Viaggia a ben **27.600 km/h**! 
    * **Viaggio nel tempo:** Compie un giro completo intorno alla Terra ogni 90 minuti. Questo significa che gli astronauti a bordo vedono ben **16 albe e 16 tramonti** ogni singolo giorno!
    """)

with col_info2:
    st.markdown("""
    #### 🧊 Vivere a gravità zero
    Nello spazio il corpo umano si comporta in modo strano e gli scienziati devono allenarsi tantissimo:
    
    * **Si diventa più alti:** Senza la gravità della Terra che schiaccia la colonna vertebrale, gli astronauti possono diventare fino a **5 centimetri più alti** mentre si trovano nello spazio!
    * **Niente lacrime:** Se piangi nello spazio, le lacrime non scivolano via sulle guance, ma formano una bollicina d'acqua attorno all'occhio!
    """)

st.markdown("---")

st.subheader("🪐 Primi passi nel cosmo")
st.success("Scegli le voci dal menu per esplorare i dati dello Sputnik, i quiz e l'assistente spaziale!")
