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

# --- FUNKCJA NAPRAWCZA (ZAMIANA POLSKICH LITER TYLKO DLA PDF) ---
def bez_ogonkow(tekst):
    if not tekst: return ""
    z = {"ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ź":"z","ż":"z",
         "Ą":"A","Ć":"C","Ę":"E","Ł":"L","Ń":"N","Ó":"O","Ś":"S","Ź":"Z","Ż":"Z"}
    t = str(tekst)
    for pol, ang in z.items(): t = t.replace(pol, ang)
    return t

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Rozliczenie Pizzerii", layout="wide", page_icon="🍕")

cookies = CookieManager()
if not cookies.ready(): st.stop()

# --- 2. DANE ---
MOJE_HASLO = "dup@"
DB_FILE = 'finanse_data.csv'
EMAIL_KONTO = "mange929598@gmail.com"  
HASLO_APP = "hlqivtidxgchoqdi" 

# --- 3. GENERATOR PDF (PROSTY I STABILNY) ---
def create_pdf(df, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m.%Y')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, bez_ogonkow(f"Przychod: {s_og:.2f} zl | Gotowka: {s_got:.2f} zl | Wydatki: {s_wyd:.2f} zl"), ln=True)
    pdf.ln(5)

    pdf.set_font("Helvetica", size=10)
    for _, row in df.iterrows():
        linia = f"{row['Data zdarzenia']} | {row['Typ']} | {row['Kwota']} zl | {row['Opis']}"
        pdf.cell(0, 10, bez_ogonkow(linia), ln=True, border=1)
    
    return bytes(pdf.output())

# --- 4. WYSYŁKA ---
def wyslij_raporty_final(df, s_og, s_got, s_wyd):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_KONTO
        msg['To'] = EMAIL_KONTO
        msg['Subject'] = f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m %H:%M')}"
        msg.attach(MIMEText("Raporty w zalaczniku.", 'plain'))

        csv_data = df.to_csv(index=False).encode('utf-8')
        pdf_data = create_pdf(df, s_og, s_got, s_wyd)

        for filename, data in [("raport.csv", csv_data), ("raport.pdf", pdf_data)]:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(data)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={filename}")
            msg.attach(part)

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_KONTO, HASLO_APP)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"Blad: {e}")
        return False

# --- 5. LOGIKA DANYCH ---
def load_data():
    if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- 6. STYLE ---
st.markdown("""<style>
    div[data-testid="stColumn"] .stButton > button { width: 100% !important; border-radius: 10px !important; font-weight: bold !important; height: 45px !important; }
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button { background-color: #d4edda !important; }
    div[data-testid="stColumn"]:nth-of-type(2) .stButton > button { background-color: #fff3cd !important; }
    div[data-testid="stColumn"]:nth-of-type(3) .stButton > button { background-color: #f8d7da !important; }
</style>""", unsafe_allow_html=True)

# --- 7. LOGOWANIE ---
if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    if st.text_input("Haslo", type="password") == MOJE_HASLO:
        if st.button("Zaloguj"): cookies["is_logged"] = "true"; cookies.save(); st.rerun()
    st.stop()

# --- 8. WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

with c1:
    st.success(f"Przychod: {s_og:.2f} zl")
    if st.button("➕ DODAJ", key="p"): st.session_state.s = "P"; st.rerun()
    if getattr(st.session_state, "s", "") == "P":
        kw = st.number_input("Kwota", value=None)
        if st.button("ZAPISZ"):
            n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': datetime.now().strftime("%d.%m")}
            pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True).to_csv(DB_FILE, index=False)
            st.session_state.s = ""; st.rerun()

with c2:
    st.warning(f"Gotowka: {s_got:.2f} zl")
    if st.button("➕ DODAJ", key="g"): st.session_state.s = "G"; st.session_state.os = None; st.rerun()
    if getattr(st.session_state, "s", "") == "G":
        osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
        if not getattr(st.session_state, "os", None):
            for o in osoby:
                if st.button(o): st.session_state.os = o; st.rerun()
        else:
            kw = st.number_input(f"Kwota ({st.session_state.os})", value=None)
            if st.button("ZAPISZ G"):
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {st.session_state.os}", 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': datetime.now().strftime("%d.%m")}
                pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True).to_csv(DB_FILE, index=False)
                st.session_state.s = ""; st.rerun()

with c3:
    st.error(f"Wydatki: {s_wyd:.2f} zl")
    if st.button("➕ DODAJ", key="w"): st.session_state.s = "W"; st.rerun()
    if getattr(st.session_state, "s", "") == "W":
        kw = st.number_input("Kwota", value=None); op = st.text_input("Opis")
        if st.button("ZAPISZ W"):
            n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': datetime.now().strftime("%d.%m")}
            pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True).to_csv(DB_FILE, index=False)
            st.session_state.s = ""; st.rerun()

# --- 9. PASEK BOCZNY ---
with st.sidebar:
    st.header("⚙️ Menu")
    st.download_button("📥 Pobierz CSV", data=df_active.to_csv(index=False).encode('utf-8'), file_name="raport.csv", use_container_width=True)
    st.download_button("📥 Pobierz PDF", data=create_pdf(df_active, s_og, s_got, s_wyd), file_name="raport.pdf", use_container_width=True)
    if st.button("📧 Wyslij raport", use_container_width=True):
        if wyslij_raporty_final(df_active, s_og, s_got, s_wyd): st.success("WYSLANO!")

    st.divider()
    if st.button("🗑️ USUN HISTORIE", type="primary", use_container_width=True): st.session_state.conf = True; st.rerun()
    if getattr(st.session_state, "conf", False):
        if st.button("TAK, USUN"):
            full = load_data(); full.loc[df_active.index, 'Status'] = 'Archiwum'; full.to_csv(DB_FILE, index=False)
            st.session_state.conf = False; st.rerun()
        if st.button("NIE"): st.session_state.conf = False; st.rerun()

st.divider()
st.dataframe(df_active[['Data zdarzenia', 'Typ', 'Kwota', 'Opis']].iloc[::-1], use_container_width=True, hide_index=True)
