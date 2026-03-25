import streamlit as st
import pandas as pd
import os
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

# --- 3. GENERATOR PDF (STABILNY) ---
def create_pdf(df, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m.%Y')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Helvetica", 'B', 12)
    # Wyświetlamy główne sumy na górze PDF
    podsumowanie = f"Przychod: {s_og:.2f} zl | Gotowka: {s_got:.2f} zl | Wydatki: {s_wyd:.2f} zl"
    pdf.cell(0, 10, bez_ogonkow(podsumowanie), ln=True)
    pdf.ln(5)

    pdf.set_font("Helvetica", size=10)
    for _, row in df.iterrows():
        linia = f"{row['Data zdarzenia']} | {row['Typ']} | {row['Kwota']} zl | {row['Opis']}"
        pdf.cell(0, 10, bez_ogonkow(linia), ln=True, border=1)
    
    return bytes(pdf.output())

# --- 4. LOGIKA DANYCH ---
def load_data():
    if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df): df.to_csv(DB_FILE, index=False)

data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- 5. LOGOWANIE ---
if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    if st.text_input("Hasło", type="password") == MOJE_HASLO:
        if st.button("Zaloguj"): cookies["is_logged"] = "true"; cookies.save(); st.rerun()
    st.stop()

# --- 6. WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:15px; border-radius:10px; text-align:center;">Przychód: <b>{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="p"): st.session_state.s = "P"; st.rerun()
    if getattr(st.session_state, "s", "") == "P":
        kw = st.number_input("Kwota", value=None)
        if st.button("ZAPISZ"):
            n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': datetime.now().strftime("%d.%m")}
            save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
            st.session_state.s = ""; st.rerun()

with c2:
    st.markdown(f'<div style="background-color:#fff3cd; padding:15px; border-radius:10px; text-align:center;">Gotówka: <b>{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
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
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                st.session_state.s = ""; st.rerun()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:15px; border-radius:10px; text-align:center;">Wydatki: <b>{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="w"): st.session_state.s = "W"; st.rerun()
    if getattr(st.session_state, "s", "") == "W":
        kw = st.number_input("Kwota", value=None); op = st.text_input("Opis")
        if st.button("ZAPISZ W"):
            n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': datetime.now().strftime("%d.%m")}
            save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
            st.session_state.s = ""; st.rerun()

# --- 7. PASEK BOCZNY ---
with st.sidebar:
    st.header("⚙️ Menu")
    st.download_button("📥 Pobierz CSV", data=df_active.to_csv(index=False).encode('utf-8'), file_name="raport.csv", use_container_width=True)
    
    # Przycisk PDF z ochroną przed UnicodeError
    pdf_file = create_pdf(df_active, s_og, s_got, s_wyd)
    st.download_button("📥 Pobierz PDF", data=pdf_file, file_name="raport.pdf", use_container_width=True)

    if st.button("🗑️ USUŃ HISTORIĘ", type="primary", use_container_width=True):
        full = load_data(); full.loc[df_active.index, 'Status'] = 'Archiwum'; save_data(full); st.rerun()

st.divider()
st.dataframe(df_active[['Data zdarzenia', 'Typ', 'Kwota', 'Opis']].iloc[::-1], use_container_width=True, hide_index=True)
