import streamlit as st
import pandas as pd
import os
import smtplib
import ssl
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

# --- DANE POCZTOWE (Aftermarket) ---
EMAIL_WYSYLKOWY = "biuro@vantivo.pl" 
EMAIL_HASLO = "Jebaltopsiak123!" 
EMAIL_DOCELOWY = "mange929598@gmail.com" 

SMTP_SERVER = "smtp.aftermarket.pl" 
SMTP_PORT = 465 
MOJE_HASLO = "dup@"
DB_FILE = 'finanse_data.csv'

# --- FUNKCJA WYSYŁANIA ---
def wyslij_na_mail(pdf_data, csv_path, temat_prefix="RAPORT"):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_WYSYLKOWY
        msg['To'] = EMAIL_DOCELOWY
        msg['Subject'] = f"🚀 {temat_prefix} - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        body = f"Raport wygenerowany: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        msg.attach(MIMEText(body, 'plain'))

        part1 = MIMEBase('application', "octet-stream")
        part1.set_payload(pdf_data)
        encoders.encode_base64(part1)
        part1.add_header('Content-Disposition', f'attachment; filename=Raport_{datetime.now().strftime("%d_%m")}.pdf')
        msg.attach(part1)

        if os.path.exists(csv_path):
            with open(csv_path, "rb") as f:
                part2 = MIMEBase('application', "octet-stream")
                part2.set_payload(f.read())
                encoders.encode_base64(part2)
                part2.add_header('Content-Disposition', f'attachment; filename=finanse_data.csv')
                msg.attach(part2)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context, timeout=20) as server:
            server.login(EMAIL_WYSYLKOWY, EMAIL_HASLO)
            server.sendmail(EMAIL_WYSYLKOWY, EMAIL_DOCELOWY, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Blad poczty: {e}")
        return False

# --- GENERATOR PDF ---
def create_pdf(dataframe, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page()
    def b_t(tekst):
        return str(tekst).replace('ą','a').replace('ć','c').replace('ę','e').replace('ł','l').replace('ń','n').replace('ó','o').replace('ś','s').replace('ź','z').replace('ż','z').replace('Ą','A').replace('Ć','C').replace('Ę','E').replace('Ł','L').replace('Ń','N').replace('Ó','O').replace('Ś','S').replace('Ź','Z').replace('Ż','Z')
    pdf.set_font("Courier", "B", 14)
    pdf.cell(190, 10, b_t(f"RAPORT FINANSOWY - {datetime.now().strftime('%d.%m.%Y %H:%M')}"), ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Courier", "B", 10)
    pdf.set_fill_color(212, 237, 218); pdf.cell(95, 10, b_t("PRZYCHOD OGOLNY:"), 1, 0, 'L', True); pdf.cell(95, 10, f"{s_og:.2f} zl", 1, 1, 'R', True)
    pdf.set_fill_color(248, 215, 218); pdf.cell(95, 10, b_t("WYDATKI GOTOWKOWE:"), 1, 0, 'L', True); pdf.cell(95, 10, f"{s_wyd:.2f} zl", 1, 1, 'R', True)
    pdf.set_fill_color(255, 243, 205); pdf.cell(95, 10, b_t("GOTOWKA (SUMA):"), 1, 0, 'L', True); pdf.cell(95, 10, f"{s_got:.2f} zl", 1, 1, 'R', True)
    pdf.ln(10)
    for _, row in dataframe.iterrows():
        txt = f"{row['Data']} | {row['Typ']} | {row['Kwota']:.2f} | {row['Data zdarzenia']} | {row['Opis']}"
        pdf.cell(190, 8, b_t(txt), 1, 1)
    return pdf.output(dest='S').encode('latin-1')

def apply_row_styles(row):
    color = ''
    if row['Typ'] == 'Przychód ogólny': color = 'background-color: #d4edda; color: #155724'
    elif row['Typ'] == 'Wydatki gotówkowe': color = 'background-color: #f8d7da; color: #721c24'
    elif 'Gotówka' in row['Typ']: color = 'background-color: #fff3cd; color: #856404'
    return [color] * len(row)

# --- ŁADOWANIE DANYCH ---
def load_data():
    if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])
def save_data(df): df.to_csv(DB_FILE, index=False)

# --- LOGOWANIE ---
if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    wpisane = st.text_input("Hasło", type="password")
    if st.button("Zaloguj się"):
        if wpisane == MOJE_HASLO:
            cookies["is_logged"] = "true"; cookies.save(); st.rerun()
    st.stop()

st.session_state.data = load_data()
df_active = st.session_state.data[st.session_state.data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- MODALE ---
@st.dialog("Szybki Raport na Mail")
def modal_quick():
    pdf = create_pdf(df_active, s_og, s_got, s_wyd)
    st.download_button("📥 POBIERZ PDF", pdf, "raport_kopia.pdf", use_container_width=True)
    if st.button("📧 WYŚLIJ NA GMAIL", use_container_width=True, type="primary"):
        if wyslij_na_mail(pdf, DB_FILE, "SZYBKI-RAPORT"):
            st.success("Wysłano na Gmail!")

@st.dialog("Procedura Zamknięcia Okresu")
def modal_reset():
    if "step" not in st.session_state: st.session_state.step = 1
    pdf = create_pdf(df_active, s_og, s_got, s_wyd)
    if st.session_state.step == 1:
        st.write("1. Pobierz raport PDF.")
        if st.download_button("📥 POBIERZ PDF", pdf, "raport.pdf", use_container_width=True, type="primary"):
            st.session_state.step = 2; st.rerun()
    elif st.session_state.step == 2:
        st.write("2. Wyślij kopię na Gmail.")
        if st.button("📧 WYŚLIJ NA MAIL", use_container_width=True, type="primary"):
            if wyslij_na_mail(pdf, DB_FILE, "RECZNY-RESET"):
                st.session_state.step = 3; st.rerun()
    elif st.session_state.step == 3:
        st.write("3. Czy wyczyścić dane?")
        if st.button("🔥 RESETUJ TABELĘ", use_container_width=True, type="primary"):
            st.session_state.step = 4; st.rerun()
    elif st.session_state.step == 4:
        st.error("4. JESTEŚ PEWIEN?")
        if st.button("✅ TAK, JESTEM PEWIEN", use_container_width=True, type="primary"):
            save_data(pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia']))
            st.session_state.step = 1; st.rerun()

# --- WYGLĄD GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:16px;">{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ Dodaj", key="b1", use_container_width=True):
        @st.dialog("Dodaj Przychód")
        def d1():
            kw = st.number_input("Kwota", min_value=0.0, format="%.2f")
            da = st.date_input("Z dnia", datetime.now())
            if st.button("ZAPISZ"):
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True)); st.rerun()
        d1()
with c2:
    bg_got, brd_got, txt_got = ("#fff3cd", "#ffc107", "#856404") if s_got >= 0 else ("#ff0000", "#8b0000", "#ffffff")
    st.markdown(f'<div style="background-color:{bg_got}; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid {brd_got}; height: 100px;"><span style="color:{txt_got}; font-size:11px; font-weight:bold;">GOTÓWKA (SUMA)</span><br><b style="color:{txt_got}; font-size:16px;">{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ Dodaj ", key="b2", use_container_width=True):
        @st.dialog("Rozlicz Gotówkę")
        def d2():
            osoba = st.selectbox("Kto?", ["Bufet", "Kierowca 1", "Kierowca 2", "Kierowca 3", "Kierowca 4"])
            kw = st.number_input("Kwota", min_value=0.0, format="%.2f")
            da = st.date_input("Z dnia", datetime.now())
            if st.button("ZAPISZ"):
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {osoba}", 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True)); st.rerun()
        d2()
with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI GOTÓWKOWE</span><br><b style="color:#721c24; font-size:16px;">{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➖ Dodaj", key="b3", use_container_width=True):
        @st.dialog("Dodaj Wydatek")
        def d3():
            kw = st.number_input("Kwota", min_value=0.0, format="%.2f")
            da = st.date_input("Z dnia", datetime.now())
            op = st.text_input("Opis")
            if st.button("ZAPISZ"):
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True)); st.rerun()
        d3()

st.divider(); st.subheader("📂 Historia")
df_h = df_active[['Data', 'Typ', 'Kwota', 'Data zdarzenia', 'Opis']].iloc[::-1]
sel = st.dataframe(df_h.style.apply(apply_row_styles, axis=1), use_container_width=True, on_select="rerun", selection_mode="multi-row", column_config={"Kwota": st.column_config.NumberColumn(format="%.2f zł"), "Opis": st.column_config.TextColumn(width="large")})

with st.sidebar:
    if st.button("📧 POBIERZ I WYŚLIJ RAPORT", use_container_width=True): modal_quick()
    st.divider()
    if st.button("💾 POBIERZ RAPORT I RESETUJ TABELE", type="primary", use_container_width=True): modal_reset()
    if st.button("🔄 ODŚWIEŻ", use_container_width=True): st.rerun()
