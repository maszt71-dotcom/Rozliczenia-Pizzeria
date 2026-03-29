import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF
from datetime import datetime
from streamlit_cookies_manager import CookieManager

# --- KONFIGURACJA PDF ---
def pdf_safe(txt):
    if not txt: return ""
    rep = {"ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ź":"z","ż":"z",
           "Ą":"A","Ć":"C","Ę":"E","Ł":"L","Ń":"N","Ó":"O","Ś":"S","Ź":"Z","Ż":"Z"}
    t = str(txt)
    for k, v in rep.items(): t = t.replace(k, v)
    return t.encode('ascii', 'ignore').decode('ascii')

# --- WYSYŁKA E-MAIL ---
def send_email_with_reports(pdf_data, csv_data):
    receiver_email = "mange929598@gmail.com"
    sender_email = "mange929598@gmail.com"
    password = "hlqivtidxgchoqdi"
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"Raport Pizzeria - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    msg.attach(MIMEText("Raport w załączniku.", 'plain'))
    for data, name in [(pdf_data, f"raport_{datetime.now().strftime('%d_%m')}.pdf"), 
                       (csv_data, f"raport_{datetime.now().strftime('%d_%m')}.csv")]:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(data)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename={name}")
        msg.attach(part)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls()
        server.login(sender_email, password); server.send_message(msg); server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"Błąd: {e}"); return False

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

# --- POŁĄCZENIE GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(ttl=0)
        return df
    except:
        return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df):
    conn.update(data=df)
    st.cache_data.clear()

data = load_data()
if data.empty:
    data = pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

# OBLICZENIA
s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].astype(str).str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- INTERFEJS GŁÓWNY (PRZYWRÓCONY) ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)
if 's' not in st.session_state: st.session_state.s = ""
if 'os' not in st.session_state: st.session_state.os = None

with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:15px; border-radius:10px; text-align:center;">Przychód: <b>{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="p"): st.session_state.s = "P" if st.session_state.s != "P" else ""; st.rerun()
    if st.session_state.s == "P":
        with st.container(border=True):
            d_p = st.date_input("Data", datetime.now(), key="d_p")
            kw_p = st.number_input("Kwota", value=None, key="k_p")
            if st.button("ZAPISZ", key="s_p", type="primary"):
                n = pd.DataFrame([{'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw_p), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_p.strftime("%d.%m")}])
                save_data(pd.concat([data, n], ignore_index=True)); st.session_state.s = ""; st.rerun()

with c2:
    bg, txt = ("#FF0000", "white") if s_got < 0 else ("#fff3cd", "black")
    st.markdown(f'<div style="background-color:{bg}; color:{txt}; padding:15px; border-radius:10px; text-align:center;">Gotówka: <b>{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="g"): st.session_state.s = "G" if st.session_state.s != "G" else ""; st.rerun()
    if st.session_state.s == "G":
        for o in ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]:
            if st.button(o, use_container_width=True):
                st.session_state.os = o; st.rerun()
            if st.session_state.os == o:
                with st.container(border=True):
                    d_g = st.date_input("Data", key="d_g")
                    kw_g = st.number_input("Kwota", key="k_g")
                    if st.button("ZAPISZ WPIS", type="primary"):
                        n = pd.DataFrame([{'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {o}", 'Kwota': float(kw_g), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_g.strftime("%d.%m")}])
                        save_data(pd.concat([data, n], ignore_index=True)); st.session_state.s = ""; st.session_state.os = None; st.rerun()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:15px; border-radius:10px; text-align:center;">Wydatki: <b>{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="w"): st.session_state.s = "W" if st.session_state.s != "W" else ""; st.rerun()
    if st.session_state.s == "W":
        with st.container(border=True):
            d_w = st.date_input("Data", key="d_w")
            kw_w = st.number_input("Kwota", key="k_w")
            op_w = st.text_input("Opis")
            if st.button("ZAPISZ WYDATEK", type="primary"):
                n = pd.DataFrame([{'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw_w), 'Opis': op_w, 'Status': 'Aktywny', 'Data zdarzenia': d_w.strftime("%d.%m")}])
                save_data(pd.concat([data, n], ignore_index=True)); st.session_state.s = ""; st.rerun()

# --- HISTORIA (STARY WYGLĄD) ---
st.divider()
st.subheader("Historia")
# Pokazujemy tylko aktywne w tabeli, żeby nie śmiecić
st.table(df_active[['Data zdarzenia', 'Typ', 'Kwota', 'Opis']].iloc[::-1])

# MENU BOCZNE
with st.sidebar:
    if st.button("📧 WYŚLIJ RAPORT", type="primary", use_container_width=True):
        pdf = create_pdf(df_active, s_og, s_got, s_wyd)
        if send_email_with_reports(pdf, df_active.to_csv(index=False).encode('utf-8')):
            st.success("Wysłano!")
