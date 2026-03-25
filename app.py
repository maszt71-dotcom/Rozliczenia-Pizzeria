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

# --- KONFIGURACJA POCZTY ---
EMAIL_ADRES = "mange929598@gmail.com"
EMAIL_HASLO = "hlqivtidxgchoqdi"

# --- FUNKCJA AUTO-BACKUP (Wysyła kopię bazy przy każdym zapisie) ---
def send_auto_backup(df):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADRES
    msg['To'] = EMAIL_ADRES
    msg['Subject'] = f"AUTO-BACKUP PIZZERIA - {datetime.now().strftime('%d.%m %H:%M')}"
    msg.attach(MIMEText("W załączniku aktualna kopia bazy danych (CSV).", 'plain'))

    part = MIMEBase('application', 'octet-stream')
    part.set_payload(df.to_csv(index=False).encode('utf-8'))
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="pizzeria_db_backup.csv"')
    msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADRES, EMAIL_HASLO)
        server.send_message(msg)
        server.quit()
    except:
        pass

# --- FUNKCJA BEZPIECZEŃSTWA DLA PDF ---
def pdf_safe(txt):
    if not txt: return ""
    rep = {"ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ź":"z","ż":"z",
           "Ą":"A","Ć":"C","Ę":"E","Ł":"L","Ń":"N","Ó":"O","Ś":"S","Ź":"Z","Ż":"Z"}
    t = str(txt)
    for k, v in rep.items(): t = t.replace(k, v)
    return t.encode('ascii', 'ignore').decode('ascii')

# --- FUNKCJA RĘCZNEJ WYSYŁKI RAPORTU ---
def send_email_with_reports(pdf_data, csv_data):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADRES
    msg['To'] = EMAIL_ADRES
    msg['Subject'] = f"Raport Pizzeria - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    msg.attach(MIMEText("W załączniku przesyłam aktualny raport finansowy.", 'plain'))

    for data, name in [(pdf_data, "raport.pdf"), (csv_data, "raport.csv")]:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(data)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename={name}")
        msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADRES, EMAIL_HASLO)
        server.send_message(msg)
        server.quit()
        return True
    except:
        return False

# --- 1. KONFIGURACJA I LOGOWANIE ---
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

# --- 2. DANE ---
DB_FILE = 'finanse_data.csv'

def load_data():
    if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)
    send_auto_backup(df) # Wysyła kopię na maila przy każdym zapisie!

if 'main_df' not in st.session_state:
    st.session_state.main_df = load_data()

data = st.session_state.main_df
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].astype(str).str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- 3. GENERATOR PDF ---
def create_pdf(df, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, pdf_safe(f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m.%Y')}"), ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.set_fill_color(212, 237, 218); pdf.cell(60, 10, pdf_safe(f"Przychod: {s_og:.2f} zl"), border=1, fill=True, align='C')
    pdf.set_fill_color(255, 243, 205); pdf.cell(60, 10, pdf_safe(f"Gotowka: {s_got:.2f} zl"), border=1, fill=True, align='C')
    pdf.set_fill_color(248, 215, 218); pdf.cell(60, 10, pdf_safe(f"Wydatki: {s_wyd:.2f} zl"), border=1, ln=1, fill=True, align='C')
    pdf.ln(5)
    pdf.set_font("Helvetica", size=10)
    for _, row in df.iterrows():
        pdf.cell(0, 10, pdf_safe(f"{row['Data zdarzenia']} | {row['Typ']} | {row['Kwota']:.2f} zl | {row['Opis']}"), ln=True, border=1)
    return pdf.output(dest="S").encode("latin-1")

# --- 4. WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

if 's' not in st.session_state: st.session_state.s = ""

with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:15px; border-radius:10px; text-align:center;">Przychód: <b>{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="p"): st.session_state.s = "P" if st.session_state.s != "P" else ""; st.rerun()
    if st.session_state.s == "P":
        with st.container(border=True):
            d_p = st.date_input("Data zdarzenia", datetime.now(), key="date_p")
            kw_p = st.number_input("Kwota", value=None, step=1.0, key="p_v")
            if st.button("DODAJ", key="save_p", use_container_width=True, type="primary"):
                if kw_p:
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw_p), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_p.strftime("%d.%m")}
                    st.session_state.main_df = pd.concat([st.session_state.main_df, pd.DataFrame([n])], ignore_index=True)
                    save_data(st.session_state.main_df); st.session_state.s = ""; st.rerun()

with c2:
    st.markdown(f'<div style="background-color:#fff3cd; padding:15px; border-radius:10px; text-align:center;">Gotówka: <b>{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="g"): st.session_state.s = "G" if st.session_state.s != "G" else ""; st.rerun()
    if st.session_state.s == "G":
        with st.container(border=True):
            os = st.selectbox("Dla:", ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"])
            kw = st.number_input("Kwota", value=None, step=1.0, key="g_v")
            if st.button("DODAJ", key="save_g", use_container_width=True, type="primary"):
                if kw:
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {os}", 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': datetime.now().strftime("%d.%m")}
                    st.session_state.main_df = pd.concat([st.session_state.main_df, pd.DataFrame([n])], ignore_index=True)
                    save_data(st.session_state.main_df); st.session_state.s = ""; st.rerun()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:15px; border-radius:10px; text-align:center;">Wydatki: <b>{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="w"): st.session_state.s = "W" if st.session_state.s != "W" else ""; st.rerun()
    if st.session_state.s == "W":
        with st.container(border=True):
            kw = st.number_input("Kwota", value=None, step=1.0, key="w_v")
            op = st.text_input("Opis", key="desc_w")
            if st.button("DODAJ", key="save_w", use_container_width=True, type="primary"):
                if kw:
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': datetime.now().strftime("%d.%m")}
                    st.session_state.main_df = pd.concat([st.session_state.main_df, pd.DataFrame([n])], ignore_index=True)
                    save_data(st.session_state.main_df); st.session_state.s = ""; st.rerun()

# --- 5. BOCZNY PANEL ---
with st.sidebar:
    st.header("⚙️ Menu")
    if st.button("📧 WYŚLIJ RAPORT PDF", use_container_width=True, type="primary"):
        if send_email_with_reports(create_pdf(df_active, s_og, s_got, s_wyd), df_active.to_csv(index=False).encode('utf-8')):
            st.success("Wysłano!")

    st.divider()
    if 'selected_indices' in st.session_state and len(st.session_state.selected_indices) > 0:
        if st.button(f"🗑️ USUŃ LINIE ({len(st.session_state.selected_indices)})", use_container_width=True):
            full = st.session_state.main_df
            full.loc[st.session_state.selected_indices, 'Status'] = 'Archiwum'
            save_data(full); st.session_state.selected_indices = []; st.rerun()

st.divider()

# --- 6. HISTORIA ---
st.subheader("Historia wpisów")
if not df_active.empty:
    df_editor = df_active.copy()
    df_editor = df_editor[["Data zdarzenia", "Typ", "Kwota", "Opis"]]
    df_editor.insert(0, "Wybierz", False)
    
    res = st.data_editor(
        df_editor.iloc[::-1],
        column_config={
            "Wybierz": st.column_config.CheckboxColumn("Wybierz", width="small", default=False),
            "Opis": st.column_config.TextColumn("Opis", width="large")
        },
        disabled=["Data zdarzenia", "Typ", "Kwota", "Opis"],
        hide_index=True,
        use_container_width=True,
        key="pizza_editor"
    )
    
    current_selected = res[res["Wybierz"] == True].index.tolist()
    if 'selected_indices' not in st.session_state or st.session_state.selected_indices != current_selected:
        st.session_state.selected_indices = current_selected; st.rerun()
