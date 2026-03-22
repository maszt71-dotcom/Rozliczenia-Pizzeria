import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. USTAWIENIA STRONY ---
st.set_page_config(page_title="System Pizza", layout="wide")

# --- 2. BAZA DANYCH (Żeby nic nie zginęło) ---
DB_FILE = "baza_pizza.csv"

def wczytaj_dane():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])

def zapisz_dane(df):
    df.to_csv(DB_FILE, index=False)

if 'data_log' not in st.session_state:
    st.session_state.data_log = wczytaj_dane()

# --- 3. WYGLĄD (CSS) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #2c3e50 !important; }
    
    /* Styl kontenerów na górze */
    .card {
        padding: 20px;
        border-radius: 12px 12px 0 0;
        color: white;
        text-align: center;
        font-weight: bold;
    }
    .card-przychod { background: #27ae60; } /* Zielony */
    .card-gotowka { background: #2980b9; }  /* Niebieski */
    .card-wydatki { background: #c0392b; }  /* Czerwony */
    
    .card-val { font-size: 26px; display: block; margin-top: 5px; }
    
    /* Ukrycie zer i strzałek w polach kwot */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    </style>
""", unsafe_allow_html=True)

# --- 4. OBLICZENIA ---
df = st.session_state.data_log
df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)

suma_przychodu = df[df['Typ'] == "Przychód"]['Kwota'].sum()
suma_gotowki = df[df['Typ'] == "Gotówka"]['Kwota'].sum()
suma_wydatkow = df[df['Typ'] == "Wydatek"]['Kwota'].sum()
bilans = suma_przychodu + suma_gotowki - suma_wydatkow

# --- 5. MENU BOCZNE ---
with st.sidebar:
    st.markdown('<h2 style="color:white; text-align:center;">MENU</h2>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Usuwanie wpisów
    st.markdown("### 🗑️ Usuń błędy")
    if not st.session_state.data_log.empty:
        lista = st.session_state.data_log.apply(lambda x: f"{x['Godzina']} | {x['Kwota']} zł", axis=1).tolist()
        wybrane = st.multiselect("Zaznacz do usunięcia:", lista)
        if st.button("USUŃ ZAZNACZONE", use_container_width=True):
            idx = [lista.index(w) for w in wybrane]
            st.session_state.data_log = st.session_state.data_log.drop(st.session_state.data_log.index[idx]).reset_index(drop=True)
            zapisz_dane(st.session_state.data_log)
            st.rerun()

# --- 6. TRZY KONTENERY Z WYSUWANYMI TABELAMI ---
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f'<div class="card card-przychod">PRZYCHÓD<span class="card-val">{suma_przychodu:.2f} zł</span></div>', unsafe_allow_html=True)
    with st.expander("➕ Dopisz Przychód"):
        kw = st.number_input("Kwota:", value=None, key="p_kw", placeholder="0.00")
        op = st.text_input("Opis:", key="p_op")
        if st.button("Zatwierdź Przychód", use_container_width=True):
            if kw:
                now = datetime.now()
                nowy = pd.DataFrame([[now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), "Przychód", kw, op]], columns=df.columns)
                st.session_state.data_log = pd.concat([nowy, st.session_state.data_log], ignore_index=True)
                zapisz_dane(st.session_state.data_log); st.rerun()

with col2:
    st.markdown(f'<div class="card card-gotowka">GOTÓWKA<span class="card-val">{suma_gotowki:.2f} zł</span></div>', unsafe_allow_html=True)
    with st.expander("➕ Dopisz Gotówkę"):
        kw = st.number_input("Kwota:", value=None, key="g_kw", placeholder="0.00")
        op = st.text_input("Opis:", key="g_op")
        if st.button("Zatwierdź Gotówkę", use_container_width=True):
            if kw:
                now = datetime.now()
                nowy = pd.DataFrame([[now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), "Gotówka", kw, op]], columns=df.columns)
                st.session_state.data_log = pd.concat([nowy, st.session_state.data_log], ignore_index=True)
                zapisz_dane(st.session_state.data_log); st.rerun()

with col3:
    st.markdown(f'<div class="card card-wydatki">WYDATKI<span class="card-val">{suma_wydatkow:.2f} zł</span></div>', unsafe_allow_html=True)
    with st.expander("➕ Dopisz Wydatek"):
        kw = st.number_input("Kwota:", value=None, key="w_kw", placeholder="0.00")
        op = st.text_input("Opis:", key="w_op")
        if st.button("Zatwierdź Wydatek", use_container_width=True):
            if kw:
                now = datetime.now()
                nowy = pd.DataFrame([[now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), "Wydatek", kw, op]], columns=df.columns)
                st.session_state.data_log = pd.concat([nowy, st.session_state.data_log], ignore_index=True)
                zapisz_dane(st.session_state.data_log); st.rerun()

# --- 7. PODSUMOWANIE NETTO I HISTORIA ---
st.divider()
st.metric("DO ODDANIA (BILANS)", f"{bilans:.2f} zł")

st.markdown("### 📂 Historia wpisów")
st.dataframe(st.session_state.data_log, use_container_width=True, hide_index=True)
