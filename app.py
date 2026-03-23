import streamlit as st
import pandas as pd
import os
import smtplib
import ssl
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from fpdf import FPDF
from streamlit_cookies_manager import CookieManager

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Rozliczenie Pizzerii", layout="wide", page_icon="🍕")

cookies = CookieManager()
if not cookies.ready():
    st.stop()

# --- TWOJE DANE POCZTOWE (Cyberfolks -> Gmail) ---
EMAIL_WYSYLKOWY = "kontakt@coolpizza.pl" 
EMAIL_HASLO = "pizz@123" 
EMAIL_DOCELOWY = "mange929598@gmail.com" 

# Przechodzimy na port 587 - najbardziej elastyczny dla Cyberfolks
SMTP_SERVER = "mail.cyberfolks.pl" 
SMTP_PORT = 587 
MOJE_HASLO = "dup@"
DB_FILE = 'finanse_data.csv'

# --- FUNKCJA WYSYŁANIA (METODA STARTTLS - NAJBARDZIEJ ODPORNA) ---
def wyslij_na_mail(pdf_data, csv_path, temat_prefix="RAPORT"):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_WYSYLKOWY
        msg['To'] = EMAIL_DOCELOWY
        msg['Subject'] = f"🚀 {temat_prefix} - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        body = f"Raport wygenerowany: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        msg.attach(MIMEText(body, 'plain'))

        # Załącznik PDF
        part1 = MIMEBase('application', "octet-stream")
        part1.set_payload(pdf_data)
        encoders.encode_base64(part1)
        part1.add_header('Content-Disposition', f'attachment; filename=Raport_{datetime.now().strftime("%d_%m")}.pdf')
        msg.attach(part1)

        # Załącznik CSV
        if os.path.exists(csv_path):
            with open(csv_path, "rb") as f:
                part2 = MIMEBase('application', "octet-stream")
                part2.set_payload(f.read())
                encoders.encode_base64(part2)
                part2.add_header('Content-Disposition', f'attachment; filename=finanse_data.csv')
                msg.attach(part2)

        # --- PANCERNA PROCEDURA POŁĄCZENIA ---
        context = ssl.create_default_context()
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
        server.set_debuglevel(1) # To wypisze błędy w konsoli jeśli dalej nie będzie działać
        server.ehlo()            # Przedstawienie się serwerowi
        server.starttls(context=context) # Wymuszenie szyfrowania
        server.ehlo()            # Ponowne przedstawienie się po zaszyfrowaniu
        server.login(EMAIL_WYSYLKOWY, EMAIL_HASLO)
        server.sendmail(EMAIL_WYSYLKOWY, EMAIL_DOCELOWY, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Błąd krytyczny poczty: {e}")
        return False

# --- GENERATOR PDF ---
def create_pdf(dataframe, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page()
    def b_t(tekst):
        return str(tekst).replace('ą','a').replace('ć','c').replace('ę','e').replace('ł','l').replace('ń','n').replace('ó','o').replace('ś','s').replace('ź','z').replace('ż','z').replace('Ą','A').replace('Ć','C').replace('Ę','E').replace('Ł','L').replace('Ń','N').replace('Ó','O').replace('Ś','S').replace('Ź','Z').replace('Ż','Z')
    pdf.set_font("Courier", "B", 14)
    pdf.cell(190, 10, b_t(f"RAPORT - {datetime.now().strftime('%d.%m.%Y %H:%M')}"), ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Courier", "B", 10)
    pdf.set_fill_color(212, 237, 218); pdf.cell(95, 10, b_t(f"PRZYCHOD: {s_og:.2f} zl"), 1, 0, 'L', True)
    pdf.set_fill_color(248, 215, 218); pdf.cell(95, 10, b_t(f"WYDATKI: {s_wyd:.2f} zl"), 1, 1, 'R', True)
    pdf.set_fill_color(255, 243, 205); pdf.cell(190, 10, b_t(f"GOTOWKA: {s_got:.2f} zl"), 1, 1, 'C', True)
    pdf.ln(5)
    for _, row in dataframe.iterrows():
        pdf.cell(190, 8, b_t(f"{row['Data']} | {row['Typ']} | {row['Kwota']:.2f} | {row['Opis']}"), 1, 1)
    return pdf.output(dest='S').encode('latin-1')

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
def save_data(df): df.to_csv(DB_FILE, index=False)

st.session_state.data = load_data()
df_active = st.session_state.data[st.session_state.data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- PROCEDURY (MODALE) ---
@st.dialog("Szybki Raport na Mail")
def modal_quick():
    pdf = create_pdf(df_active, s_og, s_got, s_wyd)
    st.download_button("📥 POBIERZ PDF", pdf, "raport_kopia.pdf", use_container_width=True)
    if st.button("📧 WYŚLIJ NA GMAIL", use_container_width=True, type="primary"):
        with st.spinner("Wysyłanie..."):
            if wyslij_na_mail(pdf, DB_FILE, "SZYBKI-RAPORT"):
                st.success("Wysłano pomyślnie!")

@st.dialog("Zamknij Okres i Reset")
def modal_reset():
    if "step" not in st.session_state: st.session_state.step = 1
    pdf = create_pdf(df_active, s_og, s_got, s_wyd)
    if st.session_state.step == 1:
        if st.download_button("📥 1. POBIERZ PDF", pdf, "raport_koncowy.pdf", use_container_width=True):
            st.session_state.step = 2; st.rerun()
    elif st.session_state.step == 2:
        if st.button("📧 2. WYŚLIJ NA GMAIL", use_container_width=True):
            if wyslij_na_mail(pdf, DB_FILE, "RECZNY-RESET"):
                st.session_state.step = 3; st.rerun()
    elif st.session_state.step == 3:
        if st.button("🔥 3. RESETUJ TABELĘ", use_container_width=True, type="primary"):
            st.session_state.step = 4; st.rerun()
    elif st.session_state.step == 4:
        if st.button("✅ 4. POTWIERDZAM RESET", use_container_width=True, type="primary"):
            save_data(pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia']))
            st.session_state.step = 1; st.rerun()

# --- WYGLĄD ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD</span><br><b style="color:#155724; font-size:16px;">{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ Dodaj Przychód", use_container_width=True):
        @st.dialog("Dodaj")
        def d_p():
            kw = st.number_input("Kwota", min_value=0.0)
            if st.button("ZAPISZ"):
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': datetime.now().strftime("%d.%m")}
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True)); st.rerun()
        d_p()
# ... [reszta kafelków identycznie jak wcześniej] ...

st.divider()
st.dataframe(df_active[['Data', 'Typ', 'Kwota', 'Opis']].iloc[::-1], use_container_width=True)

with st.sidebar:
    if st.button("📧 POBIERZ I WYŚLIJ RAPORT", use_container_width=True): modal_quick()
    st.divider()
    if st.button("💾 POBIERZ RAPORT I RESETUJ TABELĘ", type="primary", use_container_width=True): modal_reset()
    if st.button("🔄 ODŚWIEŻ", use_container_width=True): st.rerun()
