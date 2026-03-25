import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF
from datetime import datetime
from streamlit_cookies_manager import CookieManager

# --- USTAWIENIA ---
DB_FILE = 'pizzeria_db.csv'
EMAIL_ADRES = "mange929598@gmail.com"
EMAIL_HASLO = "hlqivtidxgchoqdi"

# --- FUNKCJA BACKUPU (WYSYŁA PLIK NA MAIL PRZY KAŻDYM ZAPISIE) ---
def send_email_backup(df, subject="BACKUP DANYCH"):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADRES
    msg['To'] = EMAIL_ADRES
    msg['Subject'] = f"{subject} - {datetime.now().strftime('%d.%m %H:%M')}"
    msg.attach(MIMEText("W załączniku aktualna baza danych.", 'plain'))
    
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(df.to_csv(index=False).encode('utf-8'))
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="pizzeria_db.csv"')
    msg.attach(part)
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADRES, EMAIL_HASLO)
        server.send_message(msg)
        server.quit()
    except: pass

# --- PDF SAFE ---
def pdf_safe(txt):
    if not txt: return ""
    rep = {"ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ź":"z","ż":"z",
           "Ą":"A","Ć":"C","Ę":"E","Ł":"L","Ń":"N","Ó":"O","Ś":"S","Ź":"Z","Ż":"Z"}
    t = str(txt)
    for k, v in rep.items(): t = t.replace(k, v)
    return t.encode('ascii', 'ignore').decode('ascii')

# --- DANE ---
def load_data():
    if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)
    send_email_backup(df) # KLUCZOWE: Wysyła kopię na maila przy każdym kliknięciu DODAJ

# --- LOGOWANIE ---
st.set_page_config(page_title="Pizzeria", layout="wide")
cookies = CookieManager()
if not cookies.ready(): st.stop()

if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    haslo = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        if haslo == "dup@":
            cookies["is_logged"] = "true"; cookies.save(); st.rerun()
    st.stop()

# --- START APLIKACJI ---
if 'main_df' not in st.session_state:
    st.session_state.main_df = load_data()

df = st.session_state.main_df
df_active = df[df['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].astype(str).str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- UI ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)
if 's' not in st.session_state: st.session_state.s = ""

with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:15px; border-radius:10px; text-align:center;">Przychód: <b>{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="p"): st.session_state.s = "P"
    if st.session_state.s == "P":
        kw = st.number_input("Kwota", key="kp", value=0.0)
        if st.button("OK", key="okp"):
            n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': datetime.now().strftime("%d.%m")}
            st.session_state.main_df = pd.concat([st.session_state.main_df, pd.DataFrame([n])], ignore_index=True)
            save_data(st.session_state.main_df); st.session_state.s = ""; st.rerun()

with c2:
    st.markdown(f'<div style="background-color:#fff3cd; padding:15px; border-radius:10px; text-align:center;">Gotówka: <b>{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="g"): st.session_state.s = "G"
    if st.session_state.s == "G":
        os = st.selectbox("Dla:", ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"])
        kw = st.number_input("Kwota", key="kg", value=0.0)
        if st.button("OK", key="okg"):
            n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {os}", 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': datetime.now().strftime("%d.%m")}
            st.session_state.main_df = pd.concat([st.session_state.main_df, pd.DataFrame([n])], ignore_index=True)
            save_data(st.session_state.main_df); st.session_state.s = ""; st.rerun()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:15px; border-radius:10px; text-align:center;">Wydatki: <b>{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="w"): st.session_state.s = "W"
    if st.session_state.s == "W":
        kw = st.number_input("Kwota", key="kw", value=0.0)
        op = st.text_input("Opis")
        if st.button("OK", key="okw"):
            n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': datetime.now().strftime("%d.%m")}
            st.session_state.main_df = pd.concat([st.session_state.main_df, pd.DataFrame([n])], ignore_index=True)
            save_data(st.session_state.main_df); st.session_state.s = ""; st.rerun()

st.divider()

# --- HISTORIA ---
st.subheader("Historia (Najszerszy Opis)")
if not df_active.empty:
    df_vis = df_active[["Data zdarzenia", "Typ", "Kwota", "Opis"]]
    st.data_editor(
        df_vis.iloc[::-1],
        column_config={"Opis": st.column_config.TextColumn("Opis", width="large")},
        hide_index=True,
        use_container_width=True
    )

# --- BOCZNY PANEL ---
with st.sidebar:
    st.header("Opcje")
    if st.button("📧 WYŚLIJ RAPORT PDF"):
        # Tu możesz dodać funkcję PDF z poprzednich wersji
        st.info("Raport CSV jest wysyłany automatycznie przy każdym wpisie na Twój e-mail.")
