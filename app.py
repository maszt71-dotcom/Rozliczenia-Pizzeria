import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from fpdf import FPDF
from streamlit_cookies_manager import CookieManager

# --- KONFIGURACJA ---
st.set_page_config(page_title="Rozliczenie Pizzerii", layout="wide", page_icon="🍕")

cookies = CookieManager()
if not cookies.ready():
    st.stop()

# --- DANE POCZTOWE ---
EMAIL_WYSYLKOWY = "kontakt@coolpizza.pl" 
EMAIL_HASLO = "pizz@123" 
EMAIL_DOCELOWY = "mange929598@gmail.com" 
SMTP_SERVER = "mail.cyberfolks.pl" 
SMTP_PORT = 587
MOJE_HASLO = "dup@"
DB_FILE = 'finanse_data.csv'

# --- FUNKCJA WYSYŁANIA ---
def wyslij_na_mail(pdf_data, csv_path, temat_prefix="RAPORT"):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_WYSYLKOWY
        msg['To'] = EMAIL_DOCELOWY
        msg['Subject'] = f"🚀 {temat_prefix} - {datetime.now().strftime('%d.%m.%Y')}"
        
        msg.attach(MIMEText("W zalaczniku raport PDF oraz plik bazy danych CSV.", 'plain'))

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

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_WYSYLKOWY, EMAIL_HASLO)
        server.sendmail(EMAIL_WYSYLKOWY, EMAIL_DOCELOWY, msg.as_string())
        server.quit()
        return True
    except:
        return False

# --- POMOCNICZE ---
def load_data():
    if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df): df.to_csv(DB_FILE, index=False)

def b_t(tekst):
    return str(tekst).replace('ą','a').replace('ć','c').replace('ę','e').replace('ł','l').replace('ń','n').replace('ó','o').replace('ś','s').replace('ź','z').replace('ż','z').replace('Ą','A').replace('Ć','C').replace('Ę','E').replace('Ł','L').replace('Ń','N').replace('Ó','O').replace('Ś','S').replace('Ź','Z').replace('Ż','Z')

def create_pdf(dataframe, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", "B", 14)
    pdf.cell(190, 10, b_t(f"RAPORT - {datetime.now().strftime('%d.%m.%Y %H:%M')}"), ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Courier", "B", 10)
    pdf.cell(95, 10, b_t(f"PRZYCHOD: {s_og:.2f} zl"), 1); pdf.cell(95, 10, b_t(f"GOTOWKA: {s_got:.2f} zl"), 1, 1)
    pdf.cell(190, 10, b_t(f"WYDATKI: {s_wyd:.2f} zl"), 1, 1)
    pdf.ln(5)
    for _, r in dataframe.iterrows():
        txt = f"{r['Data']} | {r['Typ']} | {r['Kwota']:.2f} | {r['Opis']}"
        pdf.cell(190, 8, b_t(txt), 1, 1)
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIKA ---
if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    if st.text_input("Haslo", type="password") == MOJE_HASLO:
        if st.button("Zaloguj"):
            cookies["is_logged"] = "true"; cookies.save(); st.rerun()
    st.stop()

data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
s_og = pd.to_numeric(df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota']).sum()
s_wyd = pd.to_numeric(df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota']).sum()
s_got = pd.to_numeric(df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota']).sum() - s_wyd

# --- PROCEDURA RESETU (KROK PO KROKU) ---
@st.dialog("Procedura Zamknięcia Dnia")
def modal_reset():
    if "step" not in st.session_state: st.session_state.step = "pobierz"
    
    pdf_file = create_pdf(df_active, s_og, s_got, s_wyd)

    if st.session_state.step == "pobierz":
        st.write("1️⃣ KROK: Pobierz raport PDF na telefon/komputer.")
        if st.download_button("📥 POBIERZ PDF", pdf_file, "raport.pdf", use_container_width=True):
            st.session_state.step = "wyslij"
            st.rerun()

    elif st.session_state.step == "wyslij":
        st.write("2️⃣ KROK: Wyslij kopie bezpieczenstwa na Gmail.")
        if st.button("📧 WYSLIJ NA MAIL", use_container_width=True):
            if wyslij_na_mail(pdf_file, DB_FILE, "RECZNY-RESET"):
                st.session_state.step = "reset"
                st.success("Wyslano!")
                st.rerun()

    elif st.session_state.step == "reset":
        st.write("3️⃣ KROK: Czy chcesz wyczyscic dane w aplikacji?")
        if st.button("🔥 RESETUJ DANE", use_container_width=True, type="primary"):
            st.session_state.step = "potwierdz"
            st.rerun()

    elif st.session_state.step == "potwierdz":
        st.error("4️⃣ KROK: CZY NA PEWNO? Danych nie da sie zwrocic bez pliku z maila.")
        if st.button("✅ TAK, JESTEM PEWIEN", use_container_width=True, type="primary"):
            empty_df = pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])
            save_data(empty_df)
            st.session_state.step = "pobierz"
            st.session_state.show_reset = False
            st.rerun()

st.title("🍕 Pizzeria")
c1, c2, c3 = st.columns(3)
with c1: st.metric("Przychód", f"{s_og:.2f} zł")
with c2: st.metric("Gotówka", f"{s_got:.2f} zł")
with c3: st.metric("Wydatki", f"{s_wyd:.2f} zł")

# Historia
st.dataframe(df_active[['Data', 'Typ', 'Kwota', 'Opis']].iloc[::-1], use_container_width=True)

# Przycisk startu procedury
if st.sidebar.button("💾 ZAMKNIJ OKRES / RESET", use_container_width=True, type="primary"):
    st.session_state.step = "pobierz"
    modal_reset()

# Automatyczna wysyłka o 02:00 rano
# (Zaplanowane jako zadanie systemowe wywołujące wyslij_na_mail o 02:00)
