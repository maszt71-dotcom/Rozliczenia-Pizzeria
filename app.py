import streamlit as st
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF
from datetime import datetime
import pytz
from streamlit_cookies_manager import CookieManager
from supabase import create_client, Client

# --- 0. POŁĄCZENIE Z SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

def get_now():
    return datetime.now(pytz.timezone('Europe/Warsaw'))

def pdf_safe(txt):
    if not txt: return ""
    rep = {"ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ź":"z","ż":"z",
           "Ą":"A","Ć":"C","Ę":"E","Ł":"L","Ń":"N","Ó":"O","Ś":"S","Ź":"Z","Ż":"Z"}
    t = str(txt)
    for k, v in rep.items(): t = t.replace(k, v)
    return t.encode('ascii', 'ignore').decode('ascii')

def send_email_with_reports(pdf_data, csv_data):
    receiver_email = "mange929598@gmail.com"
    sender_email = "mange929598@gmail.com"
    password = "hlqivtidxgchoqdi" 
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"Raport Pizzeria - {get_now().strftime('%d.%m.%Y %H:%M')}"
    msg.attach(MIMEText("Automatyczny raport z zamkniętego okresu.", 'plain'))
    for content, name, ext in [(pdf_data, "raport", "pdf"), (csv_data, "raport", "csv")]:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(content)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename={name}.{ext}")
        msg.attach(part)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        return True
    except: return False

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

# --- 2. DANE I FILTR ROZLICZENIA ---
def load_data():
    res = supabase.table("finanse").select("*").order("id").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=['id','data','typ','kwota','opis','data_zdarzenia'])

def get_last_reset_id():
    res = supabase.table("ustawienia").select("ostatnie_id").eq("id", 1).execute()
    return res.data[0]['ostatnie_id'] if res.data else 0

data = load_data()
last_id = get_last_reset_id()

# --- FILTROWANIE DANYCH (BIEŻĄCY OKRES) ---
if not data.empty:
    aktywne = data[data['id'] > last_id].copy()
    aktywne['kwota'] = pd.to_numeric(aktywne['kwota'], errors='coerce').fillna(0)
    s_og = aktywne[aktywne['typ'] == 'Przychód ogólny']['kwota'].sum()
    s_wyd = aktywne[aktywne['typ'] == 'Wydatki gotówkowe']['kwota'].sum()
    s_got = aktywne[aktywne['typ'].astype(str).str.contains('Gotówka', na=False)]['kwota'].sum() - s_wyd
else:
    aktywne = pd.DataFrame(columns=['id','data','typ','kwota','opis','data_zdarzenia'])
    s_og = s_wyd = s_got = 0.0

# --- 3. GENERATOR PDF ---
def create_pdf(df, p, g, w):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, pdf_safe(f"RAPORT PIZZERIA - {get_now().strftime('%d.%m.%Y')}"), ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, pdf_safe(f"Przychod: {p:.2f} zl"), ln=True)
    pdf.cell(0, 10, pdf_safe(f"Gotowka: {g:.2f} zl"), ln=True)
    pdf.cell(0, 10, pdf_safe(f"Wydatki: {w:.2f} zl"), ln=True)
    pdf.ln(5); pdf.set_font("Helvetica", size=9)
    for _, row in df.iterrows():
        l = f"{row['data_zdarzenia']} | {row['typ']} | {row['kwota']:.2f} zl | {row['opis']}"
        pdf.cell(0, 8, pdf_safe(l), ln=True, border=1)
    return pdf.output(dest="S").encode("latin-1")

# --- 4. WIDOK GŁÓWNY (BEZ ZMIAN W UKŁADZIE) ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)
with c1: st.success(f"Przychód: {s_og:,.2f} zł")
with c2: st.warning(f"Gotówka: {s_got:,.2f} zł")
with c3: st.error(f"Wydatki: {s_wyd:,.2f} zł")

if 's' not in st.session_state: st.session_state.s = ""
if 'os' not in st.session_state: st.session_state.os = None

col1, col2, col3 = st.columns(3)
if col1.button("➕ DODAJ PRZYCHÓD"): st.session_state.s = "P"; st.rerun()
if col2.button("➕ DODAJ GOTÓWKĘ"): st.session_state.s = "G"; st.rerun()
if col3.button("➕ DODAJ WYDATEK"): st.session_state.s = "W"; st.rerun()

# --- LOGIKA DODAWANIA ---
if st.session_state.s == "P":
    kw = st.number_input("Kwota", step=1.0)
    if st.button("ZAPISZ"):
        supabase.table("finanse").insert({'data': get_now().strftime("%d.%m %H:%M"), 'typ': 'Przychód ogólny', 'kwota': float(kw), 'data_zdarzenia': get_now().strftime("%d.%m")}).execute()
        st.session_state.s = ""; st.rerun()

if st.session_state.s == "G":
    osoba = st.selectbox("Kto?", ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"])
    kw = st.number_input("Kwota", step=1.0)
    if st.button("ZAPISZ"):
        supabase.table("finanse").insert({'data': get_now().strftime("%d.%m %H:%M"), 'typ': f"Gotówka - {osoba}", 'kwota': float(kw), 'data_zdarzenia': get_now().strftime("%d.%m")}).execute()
        st.session_state.s = ""; st.rerun()

if st.session_state.s == "W":
    kw = st.number_input("Kwota", step=1.0)
    op = st.text_input("Na co?")
    if st.button("ZAPISZ"):
        supabase.table("finanse").insert({'data': get_now().strftime("%d.%m %H:%M"), 'typ': 'Wydatki gotówkowe', 'kwota': float(kw), 'opis': op, 'data_zdarzenia': get_now().strftime("%d.%m")}).execute()
        st.session_state.s = ""; st.rerun()

# --- 5. ROZBUDOWANE MENU BOCZNE ---
with st.sidebar:
    st.header("⚙️ Centrum Sterowania")
    
    # SEKCJA: RAPORTY
    with st.expander("📊 Raporty i Eksport", expanded=False):
        if st.button("📧 Wyślij raport na e-mail", use_container_width=True):
            pdf_b = create_pdf(aktywne, s_og, s_got, s_wyd)
            csv_b = aktywne.to_csv(index=False).encode('utf-8')
            if send_email_with_reports(pdf_b, csv_b): st.success("Wysłano!")
        st.download_button("📥 Pobierz PDF", create_pdf(aktywne, s_og, s_got, s_wyd), "raport.pdf", use_container_width=True)
        st.download_button("📥 Pobierz CSV", aktywne.to_csv(index=False).encode('utf-8'), "raport.csv", use_container_width=True)

    # SEKCJA: ZARZĄDZANIE HISTORIĄ
    with st.expander("🗑️ Usuwanie Wpisów", expanded=False):
        if 'selected_ids' in st.session_state and len(st.session_state.selected_ids) > 0:
            st.write(f"Zaznaczono: {len(st.session_state.selected_ids)}")
            if st.button("Usuń zaznaczone", type="primary", use_container_width=True):
                for rid in st.session_state.selected_ids:
                    supabase.table("finanse").delete().eq("id", int(rid)).execute()
                st.session_state.selected_ids = []
                st.rerun()
        else:
            st.info("Zaznacz wpisy w tabeli poniżej, aby je usunąć.")

    # SEKCJA: ROZLICZENIE OKRESU (TRZYSTOPNIOWE)
    st.divider()
    if st.button("🔒 ZAMKNIJ I ROZLICZ OKRES", type="primary", use_container_width=True):
        st.session_state.lock = 1

    if st.session_state.get('lock') == 1:
        with st.container(border=True):
            st.error("KROK 1: Autoryzacja")
            h = st.text_input("Hasło Szefa:", type="password")
            if h == "szef123":
                st.warning("KROK 2: Potwierdź")
                if st.button("✅ TAK, WYŚLIJ I ZERUJ", use_container_width=True):
                    # KROK 3: Wykonanie
                    if not aktywne.empty:
                        p_f = create_pdf(aktywne, s_og, s_got, s_wyd)
                        c_f = aktywne.to_csv(index=False).encode('utf-8')
                        send_email_with_reports(p_f, c_f)
                        nid = int(data['id'].max())
                        supabase.table("ustawienia").update({"ostatnie_id": nid}).eq("id", 1).execute()
                        st.session_state.lock = 0; st.success("Rozliczono!"); st.rerun()
            elif h != "": st.error("Złe hasło")
            if st.button("Anuluj", use_container_width=True): st.session_state.lock = 0; st.rerun()

    st.divider()
    if st.button("🔓 Wyloguj", use_container_width=True):
        cookies["is_logged"] = "false"; cookies.save(); st.rerun()

# --- 6. HISTORIA (W APCE TYLKO OBECNY OKRES) ---
st.divider()
st.subheader("📋 Historia bieżącego okresu")
if not aktywne.empty:
    df_display = aktywne.iloc[::-1].copy()
    df_editor = df_display[["id", "data", "data_zdarzenia", "typ", "kwota", "opis"]].copy()
    df_editor.insert(0, "Wybierz", False)
    res = st.data_editor(
        df_editor,
        column_config={"Wybierz": st.column_config.CheckboxColumn("Wybierz", width="small"), "id": None},
        disabled=["data", "data_zdarzenia", "typ", "kwota", "opis"],
        hide_index=True, use_container_width=True, key="p_editor"
    )
    st.session_state.selected_ids = res[res["Wybierz"] == True]["id"].tolist()
else:
    st.info("Brak wpisów w bieżącym okresie.")
