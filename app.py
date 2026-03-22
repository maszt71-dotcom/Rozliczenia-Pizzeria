import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. USTAWIENIA STRONY ---
st.set_page_config(page_title="System Pizza", layout="wide")

# --- 2. BAZA DANYCH ---
DB_FILE = "baza_pizza.csv"

def wczytaj_dane():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE)
        except:
            return pd.DataFrame(columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
    return pd.DataFrame(columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])

def zapisz_dane(df):
    df.to_csv(DB_FILE, index=False)

if 'data_log' not in st.session_state:
    st.session_state.data_log = wczytaj_dane()

# --- 3. WYGLĄD (CSS) - KLUCZOWA POPRAWKA WARSTWY WYŻSZEJ ---
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
    
    .bg-p { background: #2980b9 !important; } 
    .bg-g { background: #27ae60 !important; } 
    .bg-w { background: #e67e22 !important; } 
    
    .card-val { font-size: 30px; display: block; margin-top: 5px; }

    /* --- TO JEST ROZWIĄZANIE TWOJEGO PROBLEMU --- */
    
    /* Celujemy w "pływający" kontener Streamlit, który trzyma okienko popover */
    div[data-testid="stPopoverBody"] {
        /* Ustawiamy szerokość na sztywno, żeby pasowała do kolumny (ok. 30% szerokości przy layout wide) */
        width: 30vw !important; 
        min-width: 250px !important;
        max-width: 450px !important;
        position: relative !important;
    }

    /* Rozciągnięcie przycisków w kolumnach */
    div[data-testid="stPopover"] { width: 100% !important; }
    div[data-testid="stPopover"] > button { width: 100% !important; }

    /* Kolory przycisków */
    div[data-testid="stColumn"]:nth-of-type(1) button { background-color: #2980b9 !important; color: white !important; }
    div[data-testid="stColumn"]:nth-of-type(2) button { background-color: #27ae60 !important; color: white !important; }
    div[data-testid="stColumn"]:nth-of-type(3) button { background-color: #e67e22 !important; color: white !important; }

    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    </style>
""", unsafe_allow_html=True)

# --- 4. OBLICZENIA ---
df = st.session_state.data_log.copy()
df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)

s_p = df[df['Typ'] == "Przychód"]['Kwota'].sum()
s_g = df[df['Typ'] == "Gotówka"]['Kwota'].sum()
s_w = df[df['Typ'] == "Wydatek"]['Kwota'].sum()
bilans = s_p + s_g - s_w

# --- 5. MENU BOCZNE ---
with st.sidebar:
    st.markdown('<h2 style="color:white; text-align:center;">MENU</h2>', unsafe_allow_html=True)
    st.markdown("---")
    if not st.session_state.data_log.empty:
        lista = st.session_state.data_log.apply(lambda x: f"{x['Godzina']} | {x['Kwota']} zł", axis=1).tolist()
        wybrane = st.multiselect("Usuń wpis:", lista)
        if st.button("WYCZYŚĆ ZAZNACZONE", use_container_width=True):
            idx = [lista.index(w) for w in wybrane]
            st.session_state.data_log = st.session_state.data_log.drop(st.session_state.data_log.index[idx]).reset_index(drop=True)
            zapisz_dane(st.session_state.data_log); st.rerun()

# --- 6. KOLUMNY ---
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f'<div class="card bg-p">PRZYCHÓD<span class="card-val">{s_p:.2f} zł</span></div>', unsafe_allow_html=True)
    with st.popover("➕ DODAJ", use_container_width=True):
        val = st.number_input("P", value=None, key="pk", placeholder="0.00", label_visibility="collapsed")
        if st.button("Zatwierdź Przychód", use_container_width=True):
            if val:
                n = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), "Przychód", val, ""]], columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
                st.session_state.data_log = pd.concat([n, st.session_state.data_log], ignore_index=True)
                zapisz_dane(st.session_state.data_log); st.rerun()

with c2:
    st.markdown(f'<div class="card bg-g">GOTÓWKA<span class="card-val">{s_g:.2f} zł</span></div>', unsafe_allow_html=True)
    with st.popover("➕ DODAJ", use_container_width=True):
        val = st.number_input("G", value=None, key="gk", placeholder="0.00", label_visibility="collapsed")
        if st.button("Zatwierdź Gotówkę", use_container_width=True):
            if val:
                n = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), "Gotówka", val, ""]], columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
                st.session_state.data_log = pd.concat([n, st.session_state.data_log], ignore_index=True)
                zapisz_dane(st.session_state.data_log); st.rerun()

with c3:
    st.markdown(f'<div class="card bg-w">WYDATKI<span class="card-val">{s_w:.2f} zł</span></div>', unsafe_allow_html=True)
    with st.popover("➕ DODAJ", use_container_width=True):
        val = st.number_input("W", value=None, key="wk", placeholder="0.00", label_visibility="collapsed")
        opis = st.text_input("Opisz wydatek", key="wo", placeholder="na co poszło?")
        if st.button("Zatwierdź Wydatek", use_container_width=True):
            if val:
                n = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), "Wydatek", val, opis]], columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
                st.session_state.data_log = pd.concat([n, st.session_state.data_log], ignore_index=True)
                zapisz_dane(st.session_state.data_log); st.rerun()

# --- 7. HISTORIA ---
st.markdown("---")
st.subheader(f"BILANS: {bilans:.2f} zł")
st.dataframe(st.session_state.data_log, use_container_width=True, hide_index=True)
