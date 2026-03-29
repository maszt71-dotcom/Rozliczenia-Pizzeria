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

# --- KONFIGURACJA PLIKÓW ---
DB_FILE = 'finanse_data.csv'

# --- FUNKCJE POMOCNICZE ---

def pdf_safe(txt):
    """Usuwa polskie znaki dla PDF."""
    if not txt: return ""
    rep = {"ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ź":"z","ż":"z",
           "Ą":"A","Ć":"C","Ę":"E","Ł":"L","Ń":"N","Ó":"O","Ś":"S","Ź":"Z","Ż":"Z"}
    t = str(txt)
    for k, v in rep.items(): t = t.replace(k, v)
    return t.encode('ascii', 'ignore').decode('ascii')

def load_data():
    """Wczytuje dane z głównego pliku."""
    if os.path.exists(DB_FILE): 
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df):
    """Zapisuje dane oraz tworzy kopię zapasową (AUTOZAPIS)."""
    # 1. Zapis główny
    df.to_csv(DB_FILE, index=False)
    # 2. Kopia zapasowa z datą (ochrona przed awarią)
    backup_name = f"backup_{datetime.now().strftime('%Y_%m_%d')}.csv"
    df.to_csv(backup_name, index=False)

def send_email_with_reports(pdf_data, csv_data):
    """Wysyła raporty na e-mail."""
    receiver_email = "mange929598@gmail.com"
    sender_email = "mange929598@gmail.com"
    password = "hlqivtidxgchoqdi" 

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"Raport Pizzeria - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    msg.attach(MIMEText("W załączniku aktualny raport.", 'plain'))

    for data, name in [(pdf_data, f"raport_{datetime.now().strftime('%d_%m')}.pdf"),
                       (csv_data, f"raport_{datetime.now().strftime('%d_%m')}.csv")]:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(data)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename={name}")
        msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"Błąd wysyłki: {e}")
        return False

def create_pdf(df, s_og, s_got, s_wyd):
    """Tworzy raport PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, pdf_safe(f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m.%Y')}"), ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    
    pdf.set_fill_color(212, 237, 218)
    pdf.cell(60, 10, pdf_safe(f"Przychod: {s_og:.2f} zl"), border=1, fill=True, align='C')
    pdf.set_fill_color(255, 243, 205)
    pdf.cell(60, 10, pdf_safe(f"Gotowka: {s_got:.2f} zl"), border=1, fill=True, align='C')
    pdf.set_fill_color(248, 215, 218)
    pdf.cell(60, 10, pdf_safe(f"Wydatki: {s_wyd:.2f} zl"), border=1, ln=1, fill=True, align='C')
    
    pdf.ln(5)
    pdf.set_font("Helvetica", size=10)
    for _, row in df.iterrows():
        linia = f"{row['Data zdarzenia']} | {row['Typ']} | {row['Kwota']:.2f} zl | {row['Opis']}"
        pdf.cell(0, 10, pdf_safe(linia), ln=True, border=1)
    return pdf.output(dest="S").encode("latin-1")

# --- START APLIKACJI ---

st.set_page_config(page_title="Pizzeria", layout="wide")
cookies = CookieManager()
if not cookies.ready(): st.stop()

# Logowanie
if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    haslo = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        if haslo == "dup@":
            cookies["is_logged"] = "true"
            cookies.save()
            st.rerun()
    st.stop()

# Dane
data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].astype(str).str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# Widok
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

if 's' not in st.session_state: st.session_state.s = ""
if 'os' not in st.session_state: st.session_state.os = None

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
                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                    st.session_state.s = ""; st.rerun()

with c2:
    st.markdown(f'<div style="background-color:#fff3cd; padding:15px; border-radius:10px; text-align:center;">Gotówka: <b>{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="g"): st.session_state.s = "G" if st.session_state.s != "G" else ""; st.session_state.os = None; st.rerun()
    if st.session_state.s == "G":
        with st.container(border=True):
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            for o in osoby:
                if st.button(o, key=f"os_{o}", use_container_width=True): st.session_state.os = o if st.session_state.os != o else None; st.rerun()
                if st.session_state.os == o:
                    with st.container(border=True):
                        st.markdown(f"Dla: **{o}**")
                        d_g = st.date_input("Data", datetime.now(), key=f"date_g_{o}")
                        kw_g = st.number_input("Kwota", value=None, step=1.0, key=f"g_v_{o}")
                        if st.button("ZAPISZ", key=f"save_g_{o}", use_container_width=True, type="primary"):
                            if kw_g:
                                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {o}", 'Kwota': float(kw_g), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_g.strftime("%d.%m")}
                                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                                st.session_state.s = ""; st.session_state.os = None; st.rerun()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:15px; border-radius:10px; text-align:center;">Wydatki: <b>{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="w"): st.session_state.s = "W" if st.session_state.s != "W" else ""; st.rerun()
    if st.session_state.s == "W":
        with st.container(border=True):
            d_w = st.date_input("Data zdarzenia", datetime.now(), key="date_w")
            kw_w = st.number_input("Kwota", value=None, step=1.0, key="w_v")
            op_w = st.text_input("Opis", key="desc_w")
            if st.button("DODAJ", key="save_w", use_container_width=True, type="primary"):
                if kw_w:
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw_w), 'Opis': op_w, 'Status': 'Aktywny', 'Data zdarzenia': d_w.strftime("%d.%m")}
                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                    st.session_state.s = ""; st.rerun()

# Menu boczne
with st.sidebar:
    st.header("⚙️ Opcje")
    if st.button("📧 WYŚLIJ RAPORT", use_container_width=True, type="primary"):
        pdf = create_pdf(df_active, s_og, s_got, s_wyd)
        csv = df_active.to_csv(index=False).encode('utf-8')
        if send_email_with_reports(pdf, csv): st.success("Wysłano!")

    st.divider()
    if 'selected_indices' in st.session_state and len(st.session_state.selected_indices) > 0:
        if st.button(f"🗑️ USUŃ ZAZNACZONE ({len(st.session_state.selected_indices)})", use_container_width=True):
            full = load_data()
            full.loc[st.session_state.selected_indices, 'Status'] = 'Archiwum'
            save_data(full)
            st.session_state.selected_indices = []
            st.rerun()

    st.divider()
    if st.button("🔓 Wyloguj", use_container_width=True):
        cookies["is_logged"] = "false"
        cookies.save()
        st.rerun()

# Historia
st.divider()
st.subheader("Historia")
if not df_active.empty:
    df_editor = df_active.copy()
    df_editor.insert(0, "Wybierz", False)
    res = st.data_editor(
        df_editor.iloc[::-1][["Wybierz", "Data zdarzenia", "Typ", "Kwota", "Opis"]],
        hide_index=True, use_container_width=True, key="p_editor"
    )
    current_selected = res[res["Wybierz"] == True].index.tolist()
    if st.session_state.get('selected_indices') != current_selected:
        st.session_state.selected_indices = current_selected
        st.rerun()
