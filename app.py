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

# --- 3. WYGLĄD (CSS) - KLUCZOWA POPRAWKA SZEROKOŚCI ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #2c3e50 !important; }
    
    /* Główne kafelki */
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

    /* --- DOPASOWANIE SZEROKOŚCI OKIENKA DO KOLUMNY --- */
    /* Wymuszenie szerokości kontenera nadrzędnego */
    div[data-testid="stPopover"] {
        width: 100% !important;
    }
    
    /* Wymuszenie szerokości samego przycisku */
    div[data-testid="stPopover"] > button {
        width: 100% !important;
    }

    /* Wymuszenie szerokości wyskakującego body na 100% kolumny */
    div[data-testid="stPopoverBody"] {
        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
    }
    
    /* Dodatkowa poprawka pozycjonowania ramki okienka */
    div[data-testid="stPopoverBody"] > div {
        width: 100% !important;
    }

    /* KOLOROWE PRZYCISKI */
    div[data-testid="stColumn"]:nth-of-type(1) button[kind="secondary"] {
        background-color: #2980b9 !important; color: white !important; border: none !important; width: 100%;
    }
    div[data-testid="stColumn"]:nth-of-type(2) button[kind="secondary"] {
        background-color: #27ae60 !important; color: white !important; border: none !important; width: 100%;
    }
    div[data-testid="stColumn"]:nth-of-type(3) button[kind="secondary"] {
        background-color: #e67e22 !important; color: white !important; border: none !important; width: 100%;
    }

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

# --- 5. MENU BOCZNE ---
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

# --- 6. KOLUMNY ---
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f'<div class="card bg-p">PRZYCHÓD<span class="card-val">{s_p:.2f} zł</span></div>', unsafe_allow_html=True)
    with st.popover("➕ DODAJ", use_container_width=True):
        val = st.number_input("Kwota", value=None, key="pk", placeholder="0.00", label_visibility="collapsed")
        if st.button("Zatwierdź", key="bp", use_container_width=True):
            if val:
                n = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), "Przychód", val, ""]], columns=df.columns)
                st.session_state.data_log = pd.concat([n, st.session_state.data_log], ignore_index=True)
                zapisz_dane(st.session_state.data_log); st.rerun()

with c2:
    st.markdown(f'<div class="card bg-g">GOTÓWKA<span class="card-val">{s_g:.2f} zł</span></div>', unsafe_allow_html=True)
    with st.popover("➕ DODAJ", use_container_width=True):
        val = st.number_input("Kwota", value=None, key="gk", placeholder="0.00", label_visibility="collapsed")
        if st.button("Zatwierdź", key="bg", use_container_width=True):
            if val:
                n = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), "Gotówka", val, ""]], columns=df.columns)
                st.session_state.data_log = pd.concat([n, st.session_state.data_log], ignore_index=True)
                zapisz_dane(st.session_state.data_log); st.rerun()

with c3:
    st.markdown(f'<div class="card bg-w">WYDATKI<span class="card-val">{s_w:.2f} zł</span></div>', unsafe_allow_html=True)
    with st.popover("➕ DODAJ", use_container_width=True):
        val = st.number_input("Kwota", value=None, key="wk", placeholder="0.00", label_visibility="collapsed")
        opis = st.text_input("Opisz wydatek", key="wo", placeholder="na co poszło?")
        if st.button("Zatwierdź", key="bw", use_container_width=True):
            if val:
                n = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), "Wydatek", val, opis]], columns=df.columns)
                st.session_state.data_log = pd.concat([n, st.session_state.data_log], ignore_index=True)
                zapisz_dane(st.session_state.data_log); st.rerun()

# --- 7. PODSUMOWANIE I HISTORIA ---
st.markdown("---")
st.subheader(f"DO ROZLICZENIA: {bilans:.2f} zł")
st.dataframe(st.session_state.data_log, use_container_width=True, hide_index=True)
