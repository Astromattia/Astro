import streamlit as st
import requests

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
st.sidebar.caption("Sviluppato con 💙 da Mattia | v2.4")


# --- CONTENUTO DELLA PAGINA DI BENVENUTO ---
st.title("📚 Archivio Missioni Spaziali")
st.markdown("### Cronologia dei voli spaziali, dal programma Mercury alle missioni odierne.")

# Box delle statistiche storiche (queste sono fisse nel codice)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Missioni Totali", value="34", delta="🚀")
with col2:
    st.metric(label="Successi globali", value="29", delta="✅")
with col3:
    st.metric(label="Fallimenti storici", value="4", delta="❌", delta_color="inverse")
    
st.markdown("---")

# --- NUOVA SEZIONE AUTOMATICA: DATI LIVE DALLO SPAZIO ---
st.subheader("🛰️ Dati in Tempo Reale dalla Stazione Spaziale (ISS)")

try:
    # Chiamata API gratuita per scoprire quante persone ci sono nello spazio
    risposta = requests.get("http://open-notify.org", timeout=5).json()
    numero_astronauti = risposta["number"]
    
    col_live1, col_live2 = st.columns(2)
    with col_live1:
        st.success(f"👨‍🚀 In questo preciso momento ci sono **{numero_astronauti} astronauti** nello spazio in orbita intorno a noi!")
    with col_live2:
        st.info("🌍 La ISS compie un giro completo della Terra ogni 90 minuti a 27.600 km/h!")
except:
    st.write("Impossibile connettersi con la Stazione Spaziale al momento. Riprova più tardi!")

st.markdown("---")

# --- SEZIONE CURIOSITÀ DELLO SPAZIO ---
st.subheader("💡 Curiosità dal Cosmo")
col_info1, col_info2 = st.columns(2)

with col_info1:
    st.markdown("""
    #### 🧊 Vivere a gravità zero
    Nello spazio il corpo umano si comporta in modo strano e gli scienziati devono allenarsi tantissimo:
    * **Si diventa più alti:** Senza la gravità della Terra che schiaccia la colonna vertebrale, gli astronauti possono diventare fino a **5 centimetri più alti**!
    """)

with col_info2:
    st.markdown("""
    #### 🌌 Il silenzio del vuoto
    * **Niente suoni:** Nello spazio profondo c'è un silenzio totale. Il suono ha bisogno dell'aria per viaggiare, e dato che nello spazio non c'è atmosfera, le esplosioni stellari avvengono nel silenzio più assoluto!
    """)

st.markdown("---")
st.subheader("🪐 Primi passi nel cosmo")
st.caption("Scegli le voci dal menu per esplorare i dati dello Sputnik, i quiz e l'assistente spaziale!")
