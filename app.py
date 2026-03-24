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

# --- STYLIZACJA CSS (DOPASOWANIE SZEROKOŚCI) ---
st.markdown("""
    <style>
    /* Szerokość okienka popover na 100% kolumny */
    div[data-testid="stPopover"] { width: 100% !important; }
    div[data-testid="stPopover"] > button { 
        width: 100% !important; 
        border-radius: 10px !important;
        height: 40px !important;
        font-weight: bold !important;
    }
    div[data-testid="stPopoverBody"] {
        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
        left: 0 !important;
    }
    
    /* Kolory przycisków wewnątrz popoverów */
    div[data-testid="stColumn"]:nth-of-type(1) button[kind="secondary"] { background-color: #d4edda; color: #155724; border: 1px solid #28a745; }
    div[data-testid="stColumn"]:nth-of-type(2) button[kind="secondary"] { background-color: #fff3cd; color: #856404; border: 1px solid #ffc107; }
    div[data-testid="stColumn"]:nth-of-type(3) button[kind="secondary"] { background-color: #f8d7da; color: #721c24; border: 1px solid #dc3545; }
    </style>
""", unsafe_allow_html=True)

data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px 10px 0 0; text-align:center; border-bottom: 5px solid #28a745; height: 80px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:18px;">{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    with st.popover("➕ DODAJ", use_container_width=True):
        kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None, placeholder=" ", key="p_kw")
        da = st.date_input("Z dnia", datetime.now(), key="p_da")
        if st.button("ZAPISZ PRZYCHÓD", use_container_width=True):
            if kw:
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True)); st.rerun()

with c2:
    bg_got = "#fff3cd" if s_got >= 0 else "#f8d7da"; brd_got = "#ffc107" if s_got >= 0 else "#dc3545"
    st.markdown(f'<div style="background-color:{bg_got}; padding:10px; border-radius:10px 10px 0 0; text-align:center; border-bottom: 5px solid {brd_got}; height: 80px;"><span style="color:#856404; font-size:11px; font-weight:bold;">GOTÓWKA (SUMA)</span><br><b style="color:#856404; font-size:18px;">{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    with st.popover("➕ DODAJ", use_container_width=True):
        osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
        wybrana = st.selectbox("Wybierz osobę", osoby)
        kw = st.number_input(f"Kwota ({wybrana})", min_value=0.0, format="%.2f", value=None, placeholder=" ")
        da = st.date_input("Z dnia", datetime.now(), key="g_da")
        if st.button("ZAPISZ GOTÓWKĘ", use_container_width=True):
            if kw:
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {wybrana}", 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True)); st.rerun()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px 10px 0 0; text-align:center; border-bottom: 5px solid #dc3545; height: 80px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI GOTÓWKOWE</span><br><b style="color:#721c24; font-size:18px;">{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    with st.popover("➕ DODAJ", use_container_width=True):
        kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None, placeholder=" ", key="w_kw")
        da = st.date_input("Z dnia", datetime.now(), key="w_da")
        op = st.text_input("Opis wydatku", placeholder="np. paliwo, zakupy...")
        if st.button("ZAPISZ WYDATEK", use_container_width=True):
            if kw:
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True)); st.rerun()

# --- TABELA I USUWANIE ---
st.divider()
def apply_row_styles(row):
    color = ''
    if row['Typ'] == 'Przychód ogólny': color = 'background-color: #d4edda; color: #155724'
    elif row['Typ'] == 'Wydatki gotówkowe': color = 'background-color: #f8d7da; color: #721c24'
    elif 'Gotówka' in row['Typ']: color = 'background-color: #fff3cd; color: #856404'
    return [color] * len(row)

df_h = df_active[['Data', 'Typ', 'Kwota', 'Data zdarzenia', 'Opis']].iloc[::-1]
sel = st.dataframe(df_h.style.apply(apply_row_styles, axis=1), use_container_width=True, on_select="rerun", selection_mode="multi-row", column_config={"Kwota": st.column_config.NumberColumn(format="%.2f zł")})

with st.sidebar:
    st.header("⚙️ Opcje")
    if sel.selection.rows:
        if st.button("🗑️ USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            curr = load_data()
            curr.loc[df_h.index[sel.selection.rows], 'Status'] = 'Usunięty'
            save_data(curr); st.rerun()
    st.divider()
    if st.button("🔄 ODŚWIEŻ", use_container_width=True): st.rerun()
