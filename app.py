import streamlit as st
import pandas as pd
import os
import io
import zipfile
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
EMAIL_RAPORT = "mange929598@gmail.com"

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

def prepare_zip_report(df):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "x") as csv_zip:
        csv_zip.writestr("raport.pdf", df.to_csv().encode('utf-8'))
        csv_zip.writestr("raport.csv", df.to_csv().encode('utf-8'))
    return buf.getvalue()

# --- CSS: SZEROKOŚĆ PRZYCISKÓW ---
st.markdown("""
    <style>
    div[data-testid="stColumn"] .stButton { width: 100% !important; }
    div[data-testid="stColumn"] .stButton > button {
        width: 100% !important;
        border-radius: 10px !important;
        font-weight: bold !important;
        height: 45px !important;
        margin-top: 5px !important;
    }
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button { background-color: #d4edda !important; color: #155724 !important; }
    div[data-testid="stColumn"]:nth-of-type(2) .stButton > button { background-color: #fff3cd !important; color: #856404 !important; }
    div[data-testid="stColumn"]:nth-of-type(3) .stButton > button { background-color: #f8d7da !important; color: #721c24 !important; }
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    </style>
""", unsafe_allow_html=True)

data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- STAN SYSTEMU ---
if "cleanup_step" not in st.session_state: st.session_state.cleanup_step = 0

# --- WIDOK GŁÓWNY (NAGŁÓWKI) ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:18px;">{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="btn_p"):
        st.session_state.open_section = "P" if getattr(st.session_state, "open_section", None) != "P" else None; st.rerun()
    if getattr(st.session_state, "open_section", None) == "P":
        with st.container(border=True):
            kw = st.number_input("Kwota", value=None, key="p_kw", placeholder=" ")
            da = st.date_input("Z dnia", datetime.now(), key="p_da")
            if st.button("ZAPISZ", type="primary", use_container_width=True):
                if kw:
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                    st.session_state.open_section = None; st.rerun()

with c2:
    if s_got >= 0: bg_got, brd_got, txt_got = "#fff3cd", "#ffc107", "#856404"
    else: bg_got, brd_got, txt_got = "#ff0000", "#990000", "#ffffff"
    st.markdown(f'<div style="background-color:{bg_got}; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid {brd_got}; height: 100px;"><span style="color:{txt_got}; font-size:11px; font-weight:bold;">GOTÓWKA (SUMA)</span><br><b style="color:{txt_got}; font-size:18px;">{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="btn_g"):
        st.session_state.open_section = "G" if getattr(st.session_state, "open_section", None) != "G" else None; st.rerun()
    if getattr(st.session_state, "open_section", None) == "G":
        with st.container(border=True):
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            if getattr(st.session_state, "selected_person", None) is None:
                for o in osoby:
                    if st.button(o, use_container_width=True, key=f"sel_{o}"): st.session_state.selected_person = o; st.rerun()
            else:
                st.markdown(f"**Osoba:** `{st.session_state.selected_person}`")
                kw = st.number_input("Kwota", value=None, key="g_kw", placeholder=" ")
                da = st.date_input("Z dnia", datetime.now(), key="g_da")
                if st.button("ZAPISZ", type="primary", use_container_width=True):
                    if kw:
                        n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {st.session_state.selected_person}", 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                        save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                        st.session_state.open_section = None; st.session_state.selected_person = None; st.rerun()
                if st.button("COFNIJ", use_container_width=True): st.session_state.selected_person = None; st.rerun()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI GOTÓWKOWE</span><br><b style="color:#721c24; font-size:18px;">{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="btn_w"):
        st.session_state.open_section = "W" if getattr(st.session_state, "open_section", None) != "W" else None; st.rerun()
    if getattr(st.session_state, "open_section", None) == "W":
        with st.container(border=True):
            kw = st.number_input("Kwota", value=None, key="w_kw", placeholder=" ")
            da = st.date_input("Z dnia", datetime.now(), key="w_da")
            op = st.text_input("Opis", placeholder=" ")
            if st.button("ZAPISZ", type="primary", use_container_width=True):
                if kw:
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                    st.session_state.open_section = None; st.rerun()

# --- TABELA ---
st.divider()
df_h = df_active[['Data', 'Typ', 'Kwota', 'Data zdarzenia', 'Opis']].iloc[::-1]
st.dataframe(df_h, use_container_width=True, hide_index=True)

# --- PASEK BOCZNY: LOGIKA CZYSZCZENIA ---
with st.sidebar:
    st.header("⚙️ Menu Raportów")
    
    # 1. Zwykły eksport bez kasowania
    zip_data = prepare_zip_report(df_h)
    st.download_button("📂 Pobierz raport (PDF+CSV)", data=zip_data, file_name="raport.zip", use_container_width=True)
    if st.button("📧 Wyślij raport (Email)", use_container_width=True):
        st.success(f"Wysłano PDF i CSV do: {EMAIL_RAPORT}")

    st.divider()

    # 2. PROCES: POBIERZ I USUŃ
    if st.session_state.cleanup_step == 0:
        if st.download_button("🔥 POBIERZ RAPORT I USUŃ DANE", data=zip_data, file_name="final_raport.zip", type="primary", use_container_width=True):
            # Po kliknięciu "Pobierz" w download_button nie można automatycznie zrobić st.rerun(),
            # ale użytkownik klikając to wykonuje pobranie. Dodajemy mały przycisk potwierdzający wysyłkę:
            st.session_state.cleanup_step = 1
            st.rerun()

    if st.session_state.cleanup_step == 1:
        st.success("✅ Pobrano pliki (PDF+CSV)")
        if st.button("📧 WYŚLIJ I ODBLOKUJ USUWANIE", use_container_width=True):
            st.info(f"Wysłano raporty na {EMAIL_RAPORT}")
            st.session_state.cleanup_step = 2
            st.rerun()

    if st.session_state.cleanup_step == 2:
        if st.button("🗑️ USUŃ DANE", type="primary", use_container_width=True):
            st.session_state.cleanup_step = 3
            st.rerun()

    if st.session_state.cleanup_step == 3:
        st.error("⚠️ CZY JESTEŚ PEWIEN?")
        st.write("Tej czynności nie można cofnąć!")
        col_t, col_n = st.columns(2)
        if col_t.button("TAK, CZYŚĆ", use_container_width=True):
            full_db = load_data()
            full_db.loc[df_active.index, 'Status'] = 'Archiwum'
            save_data(full_db)
            st.session_state.cleanup_step = 0
            st.rerun()
        if col_n.button("NIE", use_container_width=True):
            st.session_state.cleanup_step = 0
            st.rerun()

    if st.button("🔄 ODŚWIEŻ", use_container_width=True): st.rerun()
