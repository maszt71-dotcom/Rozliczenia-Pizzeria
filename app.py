import streamlit as st
import pandas as pd
import os
import io
import smtplib
import unicodedata
from fpdf import FPDF
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import datetime
from streamlit_cookies_manager import CookieManager

# --- FUNKCJA ABSOLUTNEGO CZYSZCZENIA TEKSTU ---
def czysc_tekst(tekst):
    if not tekst:
        return ""
    # Zamienia ł na l, ó na o itd.
    tekst = str(tekst)
    nfkd_form = unicodedata.normalize('NFKD', tekst)
    # Pozostawia tylko znaki ASCII (podstawowe litery i cyfry)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).replace('ł', 'l').replace('Ł', 'L')

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

# --- 3. GENERATOR PDF (NAPRAWDĘ ODPORNY) ---
def create_pdf(df, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m.%Y')}", ln=True, align='C')
    pdf.ln(10)

    # KOLOROWE PODSUMOWANIE
    pdf.set_font("Helvetica", 'B', 12)
    pdf.set_fill_color(212, 237, 218)
    pdf.cell(60, 15, f"PRZYCHOD: {s_og:,.2f} zl", border=1, align='C', fill=True)
    pdf.set_fill_color(255, 243, 205)
    pdf.cell(60, 15, f"GOTOWKA: {s_got:,.2f} zl", border=1, align='C', fill=True)
    pdf.set_fill_color(248, 215, 218)
    pdf.cell(60, 15, f"WYDATKI: {s_wyd:,.2f} zl", border=1, ln=True, align='C', fill=True)
    pdf.ln(10)

    # TABELA
    pdf.set_font("Helvetica", 'B', 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(30, 10, "Data", border=1, fill=True)
    pdf.cell(60, 10, "Typ", border=1, fill=True)
    pdf.cell(40, 10, "Kwota", border=1, fill=True)
    pdf.cell(60, 10, "Opis", border=1, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", size=10)
    for _, row in df.iterrows():
        # Tu dzieje się magia czyszczenia znaków przed zapisem do PDF
        pdf.cell(30, 10, czysc_tekst(row['Data zdarzenia']), border=1)
        pdf.cell(60, 10, czysc_tekst(row['Typ'])[:25], border=1)
        pdf.cell(40, 10, f"{row['Kwota']:.2f} zl", border=1)
        pdf.cell(60, 10, czysc_tekst(row['Opis'])[:25], border=1)
        pdf.ln()
    
    # Konwersja do bajtów kompatybilna z nowym fpdf2
    return bytes(pdf.output())

# --- 4. FUNKCJA WYSYŁANIA ---
def wyslij_raporty_final(df, s_og, s_got, s_wyd):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_KONTO
        msg['To'] = EMAIL_KONTO
        msg['Subject'] = f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m %H:%M')}"
        msg.attach(MIMEText("W zalaczniku raport PDF oraz CSV.", 'plain'))

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

def save_data(df):
    df.to_csv(DB_FILE, index=False)

data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- 6. STYLE ---
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

# --- 7. LOGOWANIE ---
if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    wpisane = st.text_input("Haslo", type="password")
    if st.button("Zaloguj sie"):
        if wpisane == MOJE_HASLO:
            cookies["is_logged"] = "true"; cookies.save(); st.rerun()
    st.stop()

# --- 8. WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; height: 100px;">Przychod: {s_og:,.2f} zl</div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="p"):
        st.session_state.open_section = "P" if getattr(st.session_state, "open_section", None) != "P" else None; st.rerun()
    if getattr(st.session_state, "open_section", None) == "P":
        with st.container(border=True):
            d_zd = st.date_input("Data zdarzenia", datetime.now(), key="p_date")
            kw = st.number_input("Kwota", value=None, key="p_kw")
            if st.button("ZAPISZ", key="p_save"):
                if kw:
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_zd.strftime("%d.%m")}
                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                    st.session_state.open_section = None; st.rerun()

with c2:
    bg = "#fff3cd" if s_got >= 0 else "#ff0000"; txt = "#856404" if s_got >= 0 else "#ffffff"
    st.markdown(f'<div style="background-color:{bg}; color:{txt}; padding:10px; border-radius:10px; text-align:center; height: 100px;">Gotowka: {s_got:,.2f} zl</div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="g"):
        st.session_state.open_section = "G" if getattr(st.session_state, "open_section", None) != "G" else None; st.session_state.osoba_sel = None; st.rerun()
    if getattr(st.session_state, "open_section", None) == "G":
        with st.container(border=True):
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            if getattr(st.session_state, "osoba_sel", None) is None:
                for o in osoby:
                    if st.button(o, key=f"sel_{o}"): st.session_state.osoba_sel = o; st.rerun()
            else:
                st.markdown(f"**Wybrano:** `{st.session_state.osoba_sel}`")
                d_zd_g = st.date_input("Data zdarzenia", datetime.now(), key="g_date")
                kw_g = st.number_input("Kwota", value=None, key="g_kw")
                if st.button("ZAPISZ", key="g_save"):
                    if kw_g:
                        n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {st.session_state.osoba_sel}", 'Kwota': float(kw_g), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_zd_g.strftime("%d.%m")}
                        save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                        st.session_state.open_section = None; st.session_state.osoba_sel = None; st.rerun()
                if st.button("COFNIJ"): st.session_state.osoba_sel = None; st.rerun()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; height: 100px;">Wydatki: {s_wyd:,.2f} zl</div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="w"):
        st.session_state.open_section = "W" if getattr(st.session_state, "open_section", None) != "W" else None; st.rerun()
    if getattr(st.session_state, "open_section", None) == "W":
        with st.container(border=True):
            d_zd_w = st.date_input("Data zdarzenia", datetime.now(), key="w_date")
            kw_w = st.number_input("Kwota", value=None, key="w_kw")
            op_w = st.text_input("Opis wydatku", key="w_op")
            if st.button("ZAPISZ", key="w_save"):
                if kw_w:
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw_w), 'Opis': op_w, 'Status': 'Aktywny', 'Data zdarzenia': d_zd_w.strftime("%d.%m")}
                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                    st.session_state.open_section = None; st.rerun()

# --- 9. PASEK BOCZNY ---
with st.sidebar:
    st.header("⚙️ Menu Raportów")
    
    # Przygotowanie raportu i PDF (teraz bezpiecznie czyszczone ze znaków)
    pdf_rep = create_pdf(df_active, s_og, s_got, s_wyd)
    csv_rep = df_active.to_csv(index=False).encode('utf-8')

    st.download_button("📥 Pobierz CSV", data=csv_rep, file_name="raport.csv", use_container_width=True)
    st.download_button("📥 Pobierz PDF", data=pdf_rep, file_name="raport.pdf", use_container_width=True)

    if st.button("📧 Wyslij raporty", use_container_width=True):
        if wyslij_raporty_final(df_active, s_og, s_got, s_wyd):
            st.success("✅ RAPORTY WYSLANE!")

    st.divider()
    if st.button("🗑️ USUN HISTORIE", type="primary", use_container_width=True):
        st.session_state.confirm = True; st.rerun()
    
    if getattr(st.session_state, "confirm", False):
        st.error("NA PEWNO? Nie mozna cofnac!")
        if st.button("TAK, USUN"):
            full = load_data(); full.loc[df_active.index, 'Status'] = 'Archiwum'
            save_data(full); st.session_state.confirm = False; st.rerun()
        if st.button("NIE"): st.session_state.confirm = False; st.rerun()

st.divider()
st.dataframe(df_active[['Data zdarzenia', 'Typ', 'Kwota', 'Opis']].iloc[::-1], use_container_width=True, hide_index=True)
