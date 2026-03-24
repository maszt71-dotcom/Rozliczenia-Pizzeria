
import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from streamlit_cookies_manager import CookieManager
from fpdf import FPDF

# --- KONFIGURACJA ---
st.set_page_config(page_title="Pizzeria System", layout="wide")
cookies = CookieManager()
if not cookies.ready(): st.stop()

EMAIL_ADRES = "mange929598@gmail.com"
EMAIL_HASLO = "pxonwcimblzuwaou"
DB_FILE = 'finanse_data.csv'

# --- FUNKCJE POMOCNICZE ---
def load_data():
    if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df): df.to_csv(DB_FILE, index=False)

def send_email_backup(pdf, csv, date_str):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f"🍕 RAPORT - {date_str}"
        msg.attach(MIMEText("Raport i kopia zapasowa.", 'plain'))
        p1 = MIMEBase('application', 'octet-stream'); p1.set_payload(pdf); encoders.encode_base64(p1)
        p1.add_header('Content-Disposition', f"attachment; filename=raport.pdf"); msg.attach(p1)
        p2 = MIMEBase('application', 'octet-stream'); p2.set_payload(csv.encode('utf-8')); encoders.encode_base64(p2)
        p2.add_header('Content-Disposition', f"attachment; filename=backup.csv"); msg.attach(p2)
        s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); s.login(EMAIL_ADRES, EMAIL_HASLO)
        s.send_message(msg); s.quit()
        return True
    except: return False

# --- LOGOWANIE ---
if cookies.get("is_logged") != "true":
    wpisane = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        if wpisane == "dup@": cookies["is_logged"] = "true"; cookies.save(); st.rerun()
    st.stop()

# --- DANE ---
data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)
s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- WIDOK GŁÓWNY (BEZ OKIEN DIALOGOWYCH) ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

with c1:
    st.success(f"**PRZYCHÓD:** {s_og:.2f} zł")
    with st.expander("➕ Dodaj Przychód"):
        k = st.number_input("Kwota", key="p_k", min_value=0.0)
        d = st.date_input("Data", key="p_d")
        if st.button("ZAPISZ PRZYCHÓD"):
            n = pd.DataFrame([{'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': k, 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d.strftime("%Y-%m-%d")}])
            save_data(pd.concat([load_data(), n], ignore_index=True)); st.rerun()

with c2:
    st.warning(f"**GOTÓWKA:** {s_got:.2f} zł")
    with st.expander("➕ Dodaj Gotówkę"):
        if "os" not in st.session_state: st.session_state.os = None
        if st.session_state.os is None:
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            for o in osoby:
                if st.button(o, key=f"btn_{o}", use_container_width=True):
                    st.session_state.os = o; st.rerun()
        else:
            st.write(f"Wpisujesz dla: **{st.session_state.os}**")
            kg = st.number_input("Kwota", key="g_k", min_value=0.0)
            dg = st.date_input("Data", key="g_d")
            col_z, col_c = st.columns(2)
            if col1.button("ZAPISZ"):
                n = pd.DataFrame([{'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Typ': f"Gotówka - {st.session_state.os}", 'Kwota': kg, 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': dg.strftime("%Y-%m-%d")}])
                save_data(pd.concat([load_data(), n], ignore_index=True)); st.session_state.os = None; st.rerun()
            if col2.button("⬅️ COFNIJ"):
                st.session_state.os = None; st.rerun()

with c3:
    st.error(f"**WYDATKI:** {s_wyd:.2f} zł")
    with st.expander("➖ Dodaj Wydatek"):
        kw = st.number_input("Kwota", key="w_k", min_value=0.0)
        dw = st.date_input("Data", key="w_d")
        op = st.text_input("Opis", key="w_o")
        if st.button("ZAPISZ WYDATEK"):
            n = pd.DataFrame([{'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': kw, 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': dw.strftime("%Y-%m-%d")}])
            save_data(pd.concat([load_data(), n], ignore_index=True)); st.rerun()

# --- TABELA I SIDEBAR --- (Logika zostaje ta sama co wcześniej)
st.divider()
st.dataframe(df_active[['Data zdarzenia', 'Typ', 'Kwota', 'Opis']].iloc[::-1], use_container_width=True)

with st.sidebar:
    st.header("⚙️ Opcje")
    if st.button("🚀 POBIERZ RAPORT I WYŚLIJ", use_container_width=True):
        # Tutaj wywołanie Twojej funkcji send_email_backup
        st.info("Logika wysyłki raportu...")
    if st.button("🔄 ODŚWIEŻ", use_container_width=True): st.rerun()
