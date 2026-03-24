import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_cookies_manager import CookieManager

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Rozliczenie Pizzerii", layout="wide", page_icon="🍕")

cookies = CookieManager()
if not cookies.ready():
    st.stop()

# --- USTAWIENIA ---
MOJE_HASLO = "dup@"
DB_FILE = 'finanse_data.csv'

# --- LOGIKA DOSTĘPU ---
if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    wpisane = st.text_input("Hasło", type="password")
    if st.button("Zaloguj się"):
        if wpisane == MOJE_HASLO:
            cookies["is_logged"] = "true"; cookies.save(); st.rerun()
    st.stop()

# --- OBSŁUGA DANYCH ---
def load_data():
    if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# --- WYGLĄD (CSS) ---
st.markdown("""
    <style>
    /* Styl przycisków otwierających (DODAJ) */
    .stButton > button {
        border-radius: 0 0 10px 10px !important;
        border: none !important;
        font-weight: bold !important;
        margin-top: -5px !important;
    }
    /* Kolory przycisków dopasowane do kafelków */
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button { background-color: #d4edda !important; color: #155724 !important; }
    div[data-testid="stColumn"]:nth-of-type(2) .stButton > button { background-color: #fff3cd !important; color: #856404 !important; }
    div[data-testid="stColumn"]:nth-of-type(3) .stButton > button { background-color: #f8d7da !important; color: #721c24 !important; }
    </style>
""", unsafe_allow_html=True)

data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- INICJALIZACJA STANU (Która szufladka otwarta) ---
if "menu_open" not in st.session_state:
    st.session_state.menu_open = None

# --- WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")

c1, c2, c3 = st.columns(3)

# KOLUMNA 1: PRZYCHÓD
with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px 10px 0 0; text-align:center; border-bottom: 5px solid #28a745; height: 80px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:18px;">{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="btn_p", use_container_width=True):
        st.session_state.menu_open = "P" if st.session_state.menu_open != "P" else None
        st.rerun()
    
    if st.session_state.menu_open == "P":
        with st.container(border=True):
            kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None, key="p_kw")
            da = st.date_input("Z dnia", datetime.now(), key="p_da")
            if st.button("ZAPISZ", type="primary", use_container_width=True):
                if kw:
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                    st.session_state.menu_open = None; st.rerun()

# KOLUMNA 2: GOTÓWKA
with c2:
    bg_got = "#fff3cd" if s_got >= 0 else "#f8d7da"; brd_got = "#ffc107" if s_got >= 0 else "#dc3545"
    st.markdown(f'<div style="background-color:{bg_got}; padding:10px; border-radius:10px 10px 0 0; text-align:center; border-bottom: 5px solid {brd_got}; height: 80px;"><span style="color:#856404; font-size:11px; font-weight:bold;">GOTÓWKA (SUMA)</span><br><b style="color:#856404; font-size:18px;">{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="btn_g", use_container_width=True):
        st.session_state.menu_open = "G" if st.session_state.menu_open != "G" else None
        st.rerun()
    
    if st.session_state.menu_open == "G":
        with st.container(border=True):
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            wybrana = st.selectbox("Wybierz osobę", osoby)
            kw = st.number_input(f"Kwota", min_value=0.0, format="%.2f", value=None, key="g_kw")
            da = st.date_input("Z dnia", datetime.now(), key="g_da")
            if st.button("ZAPISZ", type="primary", use_container_width=True):
                if kw:
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {wybrana}", 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                    st.session_state.menu_open = None; st.rerun()

# KOLUMNA 3: WYDATKI
with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px 10px 0 0; text-align:center; border-bottom: 5px solid #dc3545; height: 80px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI GOTÓWKOWE</span><br><b style="color:#721c24; font-size:18px;">{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="btn_w", use_container_width=True):
        st.session_state.menu_open = "W" if st.session_state.menu_open != "W" else None
        st.rerun()
    
    if st.session_state.menu_open == "W":
        with st.container(border=True):
            kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None, key="w_kw")
            da = st.date_input("Z dnia", datetime.now(), key="w_da")
            op = st.text_input("Opis wydatku")
            if st.button("ZAPISZ", type="primary", use_container_width=True):
                if kw:
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                    st.session_state.menu_open = None; st.rerun()

# --- TABELA ---
st.divider()
def apply_row_styles(row):
    color = ''
    if row['Typ'] == 'Przychód ogólny': color = 'background-color: #d4edda; color: #155724'
    elif row['Typ'] == 'Wydatki gotówkowe': color = 'background-color: #f8d7da; color: #721c24'
    elif 'Gotówka' in row['Typ']: color = 'background-color: #fff3cd; color: #856404'
    return [color] * len(row)

df_h = df_active[['Data', 'Typ', 'Kwota', 'Data zdarzenia', 'Opis']].iloc[::-1]
st.dataframe(df_h.style.apply(apply_row_styles, axis=1), use_container_width=True, hide_index=True, column_config={"Kwota": st.column_config.NumberColumn(format="%.2f zł")})

with st.sidebar:
    if st.button("🔄 ODŚWIEŻ", use_container_width=True): st.rerun()
