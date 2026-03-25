import streamlit as st
import pandas as pd
import os
import io
import smtplib
from fpdf import FPDF
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import datetime
from streamlit_cookies_manager import CookieManager

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Rozliczenie Pizzerii", layout="wide", page_icon="🍕")

cookies = CookieManager()
if not cookies.ready():
    st.stop()

# --- 2. DANE DO WYSYŁKI ---
MOJE_HASLO = "dup@"
DB_FILE = 'finanse_data.csv'
EMAIL_KONTO = "mange929598@gmail.com"  
HASLO_APP = "hlqivtidxgchoqdi" 

# --- 3. GENERATOR PRAWDZIWEGO PDF ---
def create_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('Arial', '', 'Arial.ttf', uni=True) # Opcjonalnie dla polskich znaków
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Raport Pizzeria - {datetime.now().strftime('%d.%m.%Y')}", ln=1, align='C')
    pdf.ln(10)
    
    # Nagłówki
    pdf.set_font("Arial", size=10)
    cols = ["Data", "Typ", "Kwota", "Opis"]
    for col in cols:
        pdf.cell(45, 10, col, border=1)
    pdf.ln()
    
    # Dane
    for i, row in df.iterrows():
        pdf.cell(45, 10, str(row['Data zdarzenia']), border=1)
        pdf.cell(45, 10, str(row['Typ'])[:15], border=1)
        pdf.cell(45, 10, f"{row['Kwota']:.2f} zl", border=1)
        pdf.cell(45, 10, str(row['Opis'])[:15], border=1)
        pdf.ln()
    
    return pdf.output(dest='S').encode('latin-1', errors='replace')

# --- 4. FUNKCJA WYSYŁANIA ---
def wyslij_raporty_final(df):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_KONTO
        msg['To'] = EMAIL_KONTO
        msg['Subject'] = f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m %H:%M')}"
        msg.attach(MIMEText("W zalaczniku raporty PDF i CSV.", 'plain'))

        # Pliki
        csv_data = df.to_csv(index=False).encode('utf-8')
        pdf_data = create_pdf(df)

        for filename, data in [("raport.csv", csv_data), ("raport.pdf", pdf_data)]:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(data)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={filename}")
            msg.attach(part)

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465) # Zmiana na bezpieczniejszy SSL
        server.login(EMAIL_KONTO, HASLO_APP)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"Blad: {e}")
        return False

# --- 5. STYLE ---
st.markdown("""
    <style>
    div[data-testid="stColumn"] .stButton { width: 100% !important; }
    div[data-testid="stColumn"] .stButton > button {
        width: 100% !important; border-radius: 10px !important;
        font-weight: bold !important; height: 45px !important;
    }
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button { background-color: #d4edda !important; color: #155724 !important; }
    div[data-testid="stColumn"]:nth-of-type(2) .stButton > button { background-color: #fff3cd !important; color: #856404 !important; }
    div[data-testid="stColumn"]:nth-of-type(3) .stButton > button { background-color: #f8d7da !important; color: #721c24 !important; }
    </style>
""", unsafe_allow_html=True)

def load_data():
    if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- 6. LOGOWANIE ---
if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    wpisane = st.text_input("Haslo", type="password")
    if st.button("Zaloguj sie"):
        if wpisane == MOJE_HASLO:
            cookies["is_logged"] = "true"; cookies.save(); st.rerun()
    st.stop()

# --- 7. WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; height: 100px;">Przychod: {s_og:,.2f} zl</div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="p"): st.session_state.open_section = "P"; st.rerun()
    if getattr(st.session_state, "open_section", None) == "P":
        kw = st.number_input("Kwota", value=None)
        if st.button("ZAPISZ P"):
            n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': datetime.now().strftime("%d.%m")}
            pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True).to_csv(DB_FILE, index=False)
            st.session_state.open_section = None; st.rerun()

# (Sekcje c2 i c3 analogicznie...)
# [Dla zwięzłości pominąłem pełny kod c2/c3, ale w Twoim pliku zostaw je bez zmian]

with c2:
    bg = "#fff3cd" if s_got >= 0 else "#ff0000"; txt = "#856404" if s_got >= 0 else "#ffffff"
    st.markdown(f'<div style="background-color:{bg}; color:{txt}; padding:10px; border-radius:10px; text-align:center; height: 100px;">Gotowka: {s_got:,.2f} zl</div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="g"): st.session_state.open_section = "G"; st.rerun()
    # [Tutaj Twój kod dodawania gotówki...]

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; height: 100px;">Wydatki: {s_wyd:,.2f} zl</div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="w"): st.session_state.open_section = "W"; st.rerun()
    # [Tutaj Twój kod dodawania wydatków...]

# --- 8. PASEK BOCZNY ---
with st.sidebar:
    st.header("⚙️ Menu Raportów")
    
    csv_data = df_active.to_csv(index=False).encode('utf-8')
    pdf_data = create_pdf(df_active)

    st.download_button("📥 Pobierz CSV", data=csv_data, file_name="raport.csv", use_container_width=True)
    st.download_button("📥 Pobierz PDF", data=pdf_data, file_name="raport.pdf", use_container_width=True)

    if st.button("📧 Wyslij raport", use_container_width=True):
        if wyslij_raporty_final(df_active):
            st.success("✅ RAPORTY WYSLANE!")

    st.divider()
    if st.button("🗑️ USUN HISTORIE", type="primary", use_container_width=True):
        st.session_state.confirm = True; st.rerun()
    
    if getattr(st.session_state, "confirm", False):
        st.warning("NA PEWNO? Nie mozna cofnac!")
        if st.button("TAK, USUN"):
            full = load_data(); full.loc[df_active.index, 'Status'] = 'Archiwum'
            full.to_csv(DB_FILE, index=False); st.session_state.confirm = False; st.rerun()
        if st.button("NIE"): st.session_state.confirm = False; st.rerun()

st.divider()
st.dataframe(df_active[['Data zdarzenia', 'Typ', 'Kwota', 'Opis']].iloc[::-1], use_container_width=True, hide_index=True)
