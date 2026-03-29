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

# --- KONFIGURACJA DANYCH ---
DB_FILE = 'finanse_data.csv'

# --- FUNKCJE POMOCNICZE ---

def load_data():
    """Wczytuje dane z pliku CSV lub tworzy nową tabelę."""
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE) [cite: 5]
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia']) [cite: 5]

def save_data(df):
    """Zapisuje tabelę do pliku CSV."""
    df.to_csv(DB_FILE, index=False) [cite: 5]

def pdf_safe(txt):
    """Usuwa polskie znaki dla poprawnego generowania PDF."""
    if not txt: return ""
    rep = {"ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ź":"z","ż":"z",
           "Ą":"A","Ć":"C","Ę":"E","Ł":"L","N":"N","Ó":"O","Ś":"S","Ź":"Z","Ż":"Z"}
    t = str(txt)
    for k, v in rep.items(): t = t.replace(k, v)
    return t.encode('ascii', 'ignore').decode('ascii') [cite: 1]

def send_email_with_reports(pdf_data, csv_data):
    """Wysyła e-mail z raportami PDF i CSV."""
    receiver_email = "mange929598@gmail.com" [cite: 1]
    sender_email = "mange929598@gmail.com" [cite: 2]
    password = "hlqivtidxgchoqdi" [cite: 2]

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"Raport Pizzeria - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    msg.attach(MIMEText("W załączniku przesyłam aktualny raport finansowy.", 'plain')) [cite: 2]

    for data, name in [(pdf_data, f"raport_{datetime.now().strftime('%d_%m')}.pdf"), 
                       (csv_data, f"raport_{datetime.now().strftime('%d_%m')}.csv")]:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(data)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename={name}")
        msg.attach(part) [cite: 2, 3]

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"Błąd wysyłki: {e}") [cite: 3, 4]
        return False

def create_pdf(df, s_og, s_got, s_wyd):
    """Generuje dokument PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, pdf_safe(f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m.%Y')}"), ln=True, align='C') [cite: 6]
    
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.set_fill_color(212, 237, 218)
    pdf.cell(60, 10, pdf_safe(f"Przychod: {s_og:.2f} zl"), border=1, fill=True, align='C')
    pdf.set_fill_color(255, 243, 205)
    pdf.cell(60, 10, pdf_safe(f"Gotowka: {s_got:.2f} zl"), border=1, fill=True, align='C')
    pdf.set_fill_color(248, 215, 218)
    pdf.cell(60, 10, pdf_safe(f"Wydatki: {s_wyd:.2f} zl"), border=1, ln=1, fill=True, align='C') [cite: 6]
    
    pdf.ln(5)
    pdf.set_font("Helvetica", size=10)
    for _, row in df.iterrows():
        linia = f"{row['Data zdarzenia']} | {row['Typ']} | {row['Kwota']:.2f} zl | {row['Opis']}"
        pdf.cell(0, 10, pdf_safe(linia), ln=True, border=1) [cite: 6, 7]
    return pdf.output(dest="S").encode("latin-1")

# --- APLIKACJA ---

st.set_page_config(page_title="Pizzeria", layout="wide")
cookies = CookieManager()

if not cookies.ready(): st.stop()

# Logowanie z Twoim hasłem "dup@"
if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    haslo = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        if haslo == "dup@": [cite: 4]
            cookies["is_logged"] = "true"
            cookies.save()
            st.rerun() [cite: 5]
    st.stop()

# Dane
data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0) [cite: 5]

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd [cite: 5]

st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

# Stan menu
if 's' not in st.session_state: st.session_state.s = ""

with c1:
    st.success(f"### Przychód\n**{s_og:,.2f} zł**")
    if st.button("➕ DODAJ PRZYCHÓD", use_container_width=True): st.session_state.s = "P"; st.rerun()
    if st.session_state.s == "P":
        with st.form("p_form"):
            d = st.date_input("Data", datetime.now())
            kw = st.number_input("Kwota", min_value=0.0)
            if st.form_submit_button("ZAPISZ"):
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d.strftime("%d.%m")}
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                st.session_state.s = ""; st.rerun() [cite: 8, 9]

with c2:
    st.warning(f"### Gotówka\n**{s_got:,.2f} zł**")
    if st.button("➕ DODAJ GOTÓWKĘ", use_container_width=True): st.session_state.s = "G"; st.rerun()
    if st.session_state.s == "G":
        osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
        wybor = st.selectbox("Dla kogo?", osoby)
        with st.form("g_form"):
            d = st.date_input("Data", datetime.now())
            kw = st.number_input("Kwota", min_value=0.0)
            if st.form_submit_button("ZAPISZ"):
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {wybor}", 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d.strftime("%d.%m")}
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                st.session_state.s = ""; st.rerun() [cite: 12, 15]

with c3:
    st.error(f"### Wydatki\n**{s_wyd:,.2f} zł**")
    if st.button("➕ DODAJ WYDATEK", use_container_width=True): st.session_state.s = "W"; st.rerun()
    if st.session_state.s == "W":
        with st.form("w_form"):
            d = st.date_input("Data", datetime.now())
            kw = st.number_input("Kwota", min_value=0.0)
            op = st.text_input("Opis (na co?)")
            if st.form_submit_button("ZAPISZ"):
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': d.strftime("%d.%m")}
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                st.session_state.s = ""; st.rerun() [cite: 19, 20]

# Sidebar i Historia
with st.sidebar:
    st.header("⚙️ Menu")
    if st.button("📧 WYŚLIJ RAPORT", type="primary", use_container_width=True):
        pdf = create_pdf(df_active, s_og, s_got, s_wyd)
        csv = df_active.to_csv(index=False).encode('utf-8')
        if send_email_with_reports(pdf, csv): st.success("✅ Wysłano!") [cite: 22]
    
    st.divider()
    if st.button("🔓 Wyloguj", use_container_width=True):
        cookies["is_logged"] = "false"
        cookies.save()
        st.rerun()

st.divider()
st.subheader("Historia wpisów")
if not df_active.empty:
    st.dataframe(df_active.iloc[::-1][["Data zdarzenia", "Typ", "Kwota", "Opis"]], use_container_width=True, hide_index=True)
else:
    st.info("Brak wpisów.")
