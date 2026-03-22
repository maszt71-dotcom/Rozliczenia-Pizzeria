import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. USTAWIENIA STRONY ---
st.set_page_config(page_title="System Pizza", layout="wide")

# --- 2. BAZA DANYCH (Automatyczny odczyt/zapis) ---
DB_FILE = "baza_pizza.csv"

def wczytaj_dane():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE)
        except:
            return pd.DataFrame(columns=['Data', 'Godzina', 'Typ', 'Kwota'])
    return pd.DataFrame(columns=['Data', 'Godzina', 'Typ', 'Kwota'])

def zapisz_dane(df):
    df.to_csv(DB_FILE, index=False)

if 'data_log' not in st.session_state:
    st.session_state.data_log = wczytaj_dane()

# --- 3. WYGLĄD (CSS) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #2c3e50 !important; }
    
    .card {
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        font-weight: bold;
        margin-bottom: 5px;
    }
    
    /* Kolory: Niebieski, Zielony, Pomarańczowy */
    .bg-p { background: #2980b9; }
    .bg-g { background: #27ae60; }
    .bg-w { background: #e67e22; }
    
    .card-val { font-size: 30px; display: block; margin-top: 5px; }

    /* Ukrycie strzałek w polach, które pojawią się w okienkach */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    </style>
""", unsafe_allow_html=True)

# --- 4. OBLICZENIA ---
df = st.session_state.data_log
df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)

s_p = df[df['Typ'] == "Przychód"]['Kwota'].sum()
s_g = df[df['Typ'] == "Gotówka"]['Kwota'].sum()
s_w = df[df['Typ'] == "Wydatek"]['Kwota'].sum()
bilans = s_p + s_g - s_w

# --- 5. MENU BOCZNE (USUWANIE) ---
with st.sidebar:
    st.markdown('<h2 style="color:white; text-align:center;">MENU</h2>', unsafe_allow_html=True)
    st.markdown("---")
    if not st.session_state.data_log.empty:
        st.markdown("### 🗑️ Usuń wpis")
        lista = st.session_state.data_log.apply(lambda x: f"{x['Godzina']} | {x['Kwota']} zł", axis=1).tolist()
        wybrane = st.multiselect("Zaznacz:", lista)
        if st.button("USUŃ WYBRANE", use_container_width=True):
            idx = [lista.index(w) for w in wybrane]
            st.session_state.data_log = st.session_state.data_log.drop(st.session_state.data_log.index[idx]).reset_index(drop=True)
            zapisz_dane(st.session_state.data_log); st.rerun()

# --- 6. TRZY KOLUMNY (SAME KAFELKI + PRZYCISKI WYWOŁUJĄCE) ---
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f'<div class="card bg-p">PRZYCHÓD<span class="card-val">{s_p:.2f} zł</span></div>', unsafe_allow_html=True)
    with st.popover("➕ DODAJ", use_container_width=True):
        val = st.number_input("Wpisz kwotę przychodu", value=None, key="pk", placeholder="0.00")
        if st.button("Zatwierdź", key="bp"):
            if val:
                n = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), "Przychód", val]], columns=df.columns)
                st.session_state.data_log = pd.concat([n, st.session_state.data_log], ignore_index=True)
                zapisz_dane(st.session_state.data_log); st.rerun()

with c2:
    st.markdown(f'<div class="card bg-g">GOTÓWKA<span class="card-val">{s_g:.2f} zł</span></div>', unsafe_allow_html=True)
    with st.popover("➕ DODAJ", use_container_width=True):
        val = st.number_input("Wpisz kwotę gotówki", value=None, key="gk", placeholder="0.00")
        if st.button("Zatwierdź", key="bg"):
            if val:
                n = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), "Gotówka", val]], columns=df.columns)
                st.session_state.data_log = pd.concat([n, st.session_state.data_log], ignore_index=True)
                zapisz_dane(st.session_state.data_log); st.rerun()

with c3:
    st.markdown(f'<div class="card bg-w">WYDATKI<span class="card-val">{s_w:.2f} zł</span></div>', unsafe_allow_html=True)
    with st.popover("➕ DODAJ", use_container_width=True):
        val = st.number_input("Wpisz kwotę wydatku", value=None, key="wk", placeholder="0.00")
        if st.button("Zatwierdź", key="bw"):
            if val:
                n = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), "Wydatek", val]], columns=df.columns)
                st.session_state.data_log = pd.concat([n, st.session_state.data_log], ignore_index=True)
                zapisz_dane(st.session_state.data_log); st.rerun()

# --- 7. PODSUMOWANIE I HISTORIA ---
st.markdown("---")
st.subheader(f"DO ROZLICZENIA: {bilans:.2f} zł")
st.dataframe(st.session_state.data_log, use_container_width=True, hide_index=True)
