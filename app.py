import streamlit as st
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF
from datetime import datetime
from streamlit_cookies_manager import CookieManager
from supabase import create_client

# --- KONFIGURACJA SUPABASE ---
SUPABASE_URL = "https://bbztqjcllhbzboycougm.supabase.co"
SUPABASE_KEY = "TU_WKLEJ_ANON_KEY" # <--- Wklej swój klucz tutaj
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNKCJA BEZPIECZEŃSTWA DLA PDF ---
def pdf_safe(txt):
    if not txt: return ""
    rep = {"ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ź":"z","ż":"z",
           "Ą":"A","Ć":"C","Ę":"E","Ł":"L","N":"N","Ó":"O","Ś":"S","Ź":"Z","Ż":"Z"}
    t = str(txt)
    for k, v in rep.items(): t = t.replace(k, v)
    return t.encode('ascii', 'ignore').decode('ascii')

# --- FUNKCJA WYSYŁKI E-MAIL ---
def send_email_with_reports(pdf_data, csv_data, is_backup=False):
    receiver_email = "mange929598@gmail.com"
    sender_email = "mange929598@gmail.com"
    password = "hlqivtidxgchoqdi" 

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    subject = "AUTO-BACKUP" if is_backup else "Raport Pizzeria"
    msg['Subject'] = f"{subject} - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    msg.attach(MIMEText("Raport finansowy w załączniku.", 'plain'))

    for data, ext in [(pdf_data, "pdf"), (csv_data, "csv")]:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(data)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename=raport_{datetime.now().strftime('%d_%m')}.{ext}")
        msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls()
        server.login(sender_email, password); server.send_message(msg); server.quit()
        return True
    except: return False

# --- 1. LOGOWANIE ---
st.set_page_config(page_title="Pizzeria Supabase", layout="wide")
cookies = CookieManager()
if not cookies.ready(): st.stop()

if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    if st.text_input("Hasło", type="password") == "dup@":
        if st.button("Zaloguj"): cookies["is_logged"] = "true"; cookies.save(); st.rerun()
    st.stop()

# --- 2. OBSŁUGA DANYCH (SUPABASE) ---
def load_data_supabase():
    # Pobieramy tylko aktywne wpisy
    response = supabase.table("finanse").select("*").eq("Status", "Aktywny").execute()
    df = pd.DataFrame(response.data)
    if df.empty:
        return pd.DataFrame(columns=['id', 'Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])
    return df

def add_entry_supabase(entry):
    supabase.table("finanse").insert(entry).execute()

def archive_entries_supabase(ids):
    for entry_id in ids:
        supabase.table("finanse").update({"Status": "Archiwum"}).eq("id", entry_id).execute()

df_active = load_data_supabase()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].astype(str).str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- 3. GENERATOR PDF ---
def create_pdf(df, s_og, s_got, s_wyd):
    pdf = FPDF(orientation='L', unit='mm', format='A4'); pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16); pdf.cell(0, 10, pdf_safe(f"RAPORT - {datetime.now().strftime('%d.%m.%Y')}"), ln=True, align='C'); pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 11)
    # Przychod
    pdf.set_fill_color(212, 237, 218); pdf.cell(92, 10, pdf_safe(f"Przychod: {s_og:.2f} zl"), border=1, fill=True, align='C')
    # Gotowka
    if s_got < 0: pdf.set_fill_color(255, 0, 0); pdf.set_text_color(255, 255, 255)
    else: pdf.set_fill_color(255, 243, 205); pdf.set_text_color(0, 0, 0)
    pdf.cell(93, 10, pdf_safe(f"Gotowka: {s_got:.2f} zl"), border=1, fill=True, align='C')
    # Wydatki
    pdf.set_fill_color(248, 215, 218); pdf.set_text_color(0, 0, 0); pdf.cell(92, 10, pdf_safe(f"Wydatki: {s_wyd:.2f} zl"), border=1, ln=1, fill=True, align='C')
    pdf.ln(10); pdf.set_font("Helvetica", 'B', 9); pdf.set_fill_color(230, 230, 230)
    cols = [("Data wpisu", 35), ("Dzien", 20), ("Typ", 50), ("Kwota", 30), ("Opis", 142)]
    for txt, w in cols: pdf.cell(w, 8, pdf_safe(txt), border=1, fill=True, align='C')
    pdf.ln(); pdf.set_font("Helvetica", size=8); pdf.set_text_color(0, 0, 0)
    for _, r in df.iloc[::-1].iterrows():
        pdf.cell(35, 7, pdf_safe(r['Data']), border=1); pdf.cell(20, 7, pdf_safe(r['Data zdarzenia']), border=1)
        pdf.cell(50, 7, pdf_safe(r['Typ']), border=1); pdf.cell(30, 7, f"{r['Kwota']:.2f} zl", border=1, align='R')
        pdf.cell(142, 7, pdf_safe(r['Opis']), border=1, ln=1)
    return pdf.output(dest="S").encode("latin-1")

# --- 4. WIDOK GŁÓWNY ---
st.title("🍕 Pizzeria - Supabase")
c1, c2, c3 = st.columns(3)

if 's' not in st.session_state: st.session_state.s = ""
if 'os' not in st.session_state: st.session_state.os = None

with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:15px; border-radius:10px; text-align:center; color:black">Przychód: <b>{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="p"): st.session_state.s = "P" if st.session_state.s != "P" else ""; st.rerun()
    if st.session_state.s == "P":
        with st.container(border=True):
            d_p = st.date_input("z dnia", datetime.now(), key="date_p")
            kw_p = st.number_input("Kwota", value=None, step=1.0, key="p_v")
            if st.button("DODAJ", key="save_p", use_container_width=True, type="primary") and kw_p:
                add_entry_supabase({'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw_p), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_p.strftime("%d.%m")})
                st.session_state.s = ""; st.rerun()

with c2:
    bg_got = "#ff0000" if s_got < 0 else "#fff3cd"; txt_got = "white" if s_got < 0 else "black"
    st.markdown(f'<div style="background-color:{bg_got}; padding:15px; border-radius:10px; text-align:center; color:{txt_got}">Gotówka: <b>{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="g"): st.session_state.s = "G" if st.session_state.s != "G" else ""; st.session_state.os = None; st.rerun()
    if st.session_state.s == "G":
        osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
        for o in osoby:
            if st.button(o, key=f"os_{o}", use_container_width=True): st.session_state.os = o if st.session_state.os != o else None; st.rerun()
            if st.session_state.os == o:
                with st.container(border=True):
                    d_g = st.date_input("z dnia", datetime.now(), key=f"d_g_{o}")
                    kw_g = st.number_input("Kwota", value=None, key=f"k_g_{o}")
                    if st.button("ZAPISZ", key=f"s_g_{o}", type="primary") and kw_g:
                        add_entry_supabase({'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {o}", 'Kwota': float(kw_g), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_g.strftime("%d.%m")})
                        st.session_state.s = ""; st.session_state.os = None; st.rerun()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:15px; border-radius:10px; text-align:center; color:black">Wydatki: <b>{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="w"): st.session_state.s = "W" if st.session_state.s != "W" else ""; st.rerun()
    if st.session_state.s == "W":
        with st.container(border=True):
            d_w = st.date_input("z dnia", datetime.now(), key="date_w")
            kw_w = st.number_input("Kwota", value=None, key="w_v")
            op_w = st.text_input("Opis", key="desc_w")
            if st.button("DODAJ", key="save_w", type="primary") and kw_w:
                add_entry_supabase({'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw_w), 'Opis': op_w, 'Status': 'Aktywny', 'Data zdarzenia': d_w.strftime("%d.%m")})
                st.session_state.s = ""; st.rerun()

st.divider()

# --- 5. HISTORIA I MENU ---
st.subheader("Historia")
if not df_active.empty:
    df_editor = df_active[["Data", "Data zdarzenia", "Typ", "Kwota", "Opis"]].copy()
    df_editor.insert(0, "Wybierz", False)
    res = st.data_editor(df_editor.iloc[::-1], hide_index=True, use_container_width=True, key="p_ed")

    with st.sidebar:
        st.header("Menu")
        if st.button("📧 WYŚLIJ RAPORT", type="primary", use_container_width=True):
            pdf = create_pdf(df_active, s_og, s_got, s_wyd); csv = df_active.to_csv(index=False).encode('utf-8')
            if send_email_with_reports(pdf, csv): st.success("Wysłano!")

        # Usuwanie zaznaczonych
        selected_ids = df_active.iloc[::-1][res["Wybierz"] == True]["id"].tolist()
        if selected_ids:
            if st.button(f"🗑️ USUŃ ({len(selected_ids)})", type="primary", use_container_width=True):
                if st.session_state.get('conf_row') != True: st.session_state.conf_row = True; st.rerun()
            if st.session_state.get('conf_row'):
                st.warning("Usunąć?")
                if st.button("TAK"): archive_entries_supabase(selected_ids); st.session_state.conf_row = False; st.rerun()
                if st.button("NIE"): st.session_state.conf_row = False; st.rerun()

        st.divider()
        if 'del_c' not in st.session_state: st.session_state.del_c = 0
        if st.session_state.del_c == 0:
            if st.button("🗑️ USUŃ WSZYSTKO", use_container_width=True): st.session_state.del_c = 1; st.rerun()
        elif st.session_state.del_c == 1:
            st.warning("Na pewno?")
            if st.button("TAK"):
                pdf = create_pdf(df_active, s_og, s_got, s_wyd); csv = df_active.to_csv(index=False).encode('utf-8')
                if send_email_with_reports(pdf, csv, True): st.session_state.del_c = 2; st.rerun()
        elif st.session_state.del_c == 2:
            st.error("DANE ZOSTANĄ USUNIĘTE!")
            if st.button("POTWIERDZAM"): archive_entries_supabase(df_active["id"].tolist()); st.session_state.del_c = 0; st.rerun()
            if st.button("COFNIJ"): st.session_state.del_c = 0; st.rerun()
