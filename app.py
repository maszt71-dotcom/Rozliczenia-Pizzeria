import streamlit as st
import pandas as pd
import os
import io
import zipfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from streamlit_cookies_manager import CookieManager

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Rozliczenie Pizzerii", layout="wide", page_icon="🍕")

cookies = CookieManager()
if not cookies.ready():
    st.stop()

# --- 2. DANE DO WYSYŁKI (WPISANE TWOJE HASŁO) ---
MOJE_HASLO = "dup@"
DB_FILE = 'finanse_data.csv'
EMAIL_KONTO = "mange929598@gmail.com"  
HASLO_APP = "hlqivtidxgchoqdi" # <--- TWOJE NOWE HASŁO BEZ SPACJI

# --- 3. FUNKCJA WYSYŁANIA ---
def wyslij_raport_final(dane_zip):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_KONTO
        msg['To'] = EMAIL_KONTO
        msg['Subject'] = f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m %H:%M')}"
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(dane_zip)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename=raporty.zip")
        msg.attach(part)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_KONTO, HASLO_APP)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"Błąd wysyłki: {e}")
        return False

# --- 4. STYLE CSS ---
st.markdown("""
    <style>
    div[data-testid="stColumn"] .stButton { width: 100% !important; }
    div[data-testid="stColumn"] .stButton > button {
        width: 100% !important; border-radius: 10px !important;
        font-weight: bold !important; height: 45px !important;
        margin-top: 5px !important; border: none !important;
    }
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button { background-color: #d4edda !important; color: #155724 !important; }
    div[data-testid="stColumn"]:nth-of-type(2) .stButton > button { background-color: #fff3cd !important; color: #856404 !important; }
    div[data-testid="stColumn"]:nth-of-type(3) .stButton > button { background-color: #f8d7da !important; color: #721c24 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 5. LOGIKA DANYCH ---
def load_data():
    if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

def prepare_zip(df):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "x") as csv_zip:
        csv_zip.writestr("raport.pdf", df.to_csv().encode('utf-8'))
        csv_zip.writestr("raport.csv", df.to_csv().encode('utf-8'))
    return buf.getvalue()

data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- 6. LOGOWANIE ---
if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    wpisane = st.text_input("Hasło", type="password")
    if st.button("Zaloguj się"):
        if wpisane == MOJE_HASLO:
            cookies["is_logged"] = "true"; cookies.save(); st.rerun()
    st.stop()

# --- 7. WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; height: 100px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:18px;">{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="btn_p"): st.session_state.open_section = "P"; st.rerun()

with c2:
    bg = "#fff3cd" if s_got >= 0 else "#ff0000"; txt = "#856404" if s_got >= 0 else "#ffffff"
    st.markdown(f'<div style="background-color:{bg}; color:{txt}; padding:10px; border-radius:10px; text-align:center; height: 100px;"><span style="font-size:11px; font-weight:bold;">GOTÓWKA (SUMA)</span><br><b style="font-size:18px;">{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="btn_g"): st.session_state.open_section = "G"; st.session_state.selected_person = None; st.rerun()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; height: 100px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI GOTÓWKOWE</span><br><b style="color:#721c24; font-size:18px;">{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="btn_w"): st.session_state.open_section = "W"; st.rerun()

# --- 8. PASEK BOCZNY ---
if "cleanup_step" not in st.session_state: st.session_state.cleanup_step = 0

with st.sidebar:
    st.header("⚙️ Menu Raportów")
    zip_data = prepare_zip(df_active[['Data', 'Typ', 'Kwota', 'Data zdarzenia', 'Opis']])

    if st.session_state.cleanup_step == 0:
        if st.download_button("🔥 POBIERZ RAPORT I USUŃ DANE", data=zip_data, file_name="raport.zip", type="primary", use_container_width=True):
            st.session_state.cleanup_step = 1; st.rerun()

    if st.session_state.cleanup_step == 1:
        if st.button("📧 Wyślij raport", use_container_width=True):
            if wyslij_raport_final(zip_data):
                st.session_state.cleanup_step = 2; st.rerun()

    if st.session_state.cleanup_step == 2:
        if st.button("🗑️ USUŃ DANE", type="primary", use_container_width=True):
            st.session_state.cleanup_step = 3; st.rerun()

    if st.session_state.cleanup_step == 3:
        st.error("⚠️ CZY JESTEŚ PEWIEN?")
        col1, col2 = st.columns(2)
        if col1.button("TAK"):
            full = load_data()
            full.loc[df_active.index, 'Status'] = 'Archiwum'
            save_data(full)
            st.session_state.cleanup_step = 0; st.rerun()
        if col2.button("NIE"): st.session_state.cleanup_step = 0; st.rerun()

    st.divider()
    if st.button("🔄 ODŚWIEŻ", use_container_width=True): st.rerun()

# --- 9. TABELA ---
st.divider()
st.dataframe(df_active[['Data', 'Typ', 'Kwota', 'Data zdarzenia', 'Opis']].iloc[::-1], use_container_width=True, hide_index=True)
