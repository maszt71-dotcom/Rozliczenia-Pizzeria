import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF
from datetime import datetime
from streamlit_cookies_manager import CookieManager

# --- FUNKCJE POMOCNICZE ---
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
    msg['Subject'] = f"Raport Pizzeria - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    msg.attach(MIMEText("W załączniku przesyłam raport finansowy.", 'plain'))
    for data, name in [(pdf_data, f"raport_{datetime.now().strftime('%d_%m')}.pdf"), 
                       (csv_data, f"raport_{datetime.now().strftime('%d_%m')}.csv")]:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(data)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename={name}")
        msg.attach(part)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls()
        server.login(sender_email, password); server.send_message(msg); server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"Błąd wysyłki: {e}"); return False

# --- 1. LOGOWANIE ---
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

# --- 2. POŁĄCZENIE GOOGLE SHEETS (POPRAWIONE ttl=0) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Tutaj poprawiłem ttl=0 (jako liczba)
    return conn.read(ttl=0)

def save_data(df):
    conn.update(data=df)
    st.cache_data.clear()

data = load_data()
df_active_calc = data[data['Status'] == 'Aktywny'].copy()
df_active_calc['Kwota'] = pd.to_numeric(df_active_calc['Kwota'], errors='coerce').fillna(0)

s_og = df_active_calc[df_active_calc['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active_calc[df_active_calc['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active_calc[df_active_calc['Typ'].astype(str).str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- 3. GENERATOR PDF ---
def create_pdf(df, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page(); pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, pdf_safe(f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m.%Y')}"), ln=True, align='C')
    pdf.ln(10); pdf.set_font("Helvetica", 'B', 12)
    pdf.set_fill_color(212, 237, 218)
    pdf.cell(60, 10, pdf_safe(f"Przychod: {s_og:.2f} zl"), border=1, fill=True, align='C')
    if s_got < 0:
        pdf.set_fill_color(255, 0, 0); pdf.set_text_color(255, 255, 255)
    else:
        pdf.set_fill_color(255, 243, 205); pdf.set_text_color(0, 0, 0)
    pdf.cell(60, 10, pdf_safe(f"Gotowka: {s_got:.2f} zl"), border=1, fill=True, align='C')
    pdf.set_text_color(0, 0, 0); pdf.set_fill_color(248, 215, 218)
    pdf.cell(60, 10, pdf_safe(f"Wydatki: {s_wyd:.2f} zl"), border=1, ln=1, fill=True, align='C')
    pdf.ln(5); pdf.set_font("Helvetica", size=10)
    for _, row in df.iterrows():
        linia = f"{row['Data zdarzenia']} | {row['Typ']} | {row['Kwota']:.2f} zl | {row['Opis']}"
        pdf.cell(0, 10, pdf_safe(linia), ln=True, border=1)
    return pdf.output(dest="S").encode("latin-1")

# --- 4. INTERFEJS GŁÓWNY ---
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
            if st.button("DODAJ WPIS", key="save_p", use_container_width=True, type="primary"):
                if kw_p:
                    n = pd.DataFrame([{'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw_p), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_p.strftime("%d.%m")}])
                    save_data(pd.concat([data, n], ignore_index=True)); st.session_state.s = ""; st.rerun()

with c2:
    got_bg, got_txt = ("#FF0000", "white") if s_got < 0 else ("#fff3cd", "black")
    st.markdown(f'<div style="background-color:{got_bg}; color:{got_txt}; padding:15px; border-radius:10px; text-align:center;">Gotówka: <b>{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="g"): st.session_state.s = "G" if st.session_state.s != "G" else ""; st.session_state.os = None; st.rerun()
    if st.session_state.s == "G":
        osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
        for o in osoby:
            if st.button(o, key=f"os_{o}", use_container_width=True): st.session_state.os = o if st.session_state.os != o else None; st.rerun()
            if st.session_state.os == o:
                with st.container(border=True):
                    d_g = st.date_input("Data", datetime.now(), key=f"date_g_{o}")
                    kw_g = st.number_input("Kwota", value=None, step=1.0, key=f"g_v_{o}")
                    if st.button("ZAPISZ", key=f"save_g_{o}", use_container_width=True, type="primary"):
                        if kw_g:
                            n = pd.DataFrame([{'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {o}", 'Kwota': float(kw_g), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_g.strftime("%d.%m")}])
                            save_data(pd.concat([data, n], ignore_index=True)); st.session_state.s = ""; st.session_state.os = None; st.rerun()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:15px; border-radius:10px; text-align:center;">Wydatki: <b>{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="w"): st.session_state.s = "W" if st.session_state.s != "W" else ""; st.rerun()
    if st.session_state.s == "W":
        with st.container(border=True):
            d_w = st.date_input("Data zdarzenia", datetime.now(), key="date_w")
            kw_w = st.number_input("Kwota", value=None, step=1.0, key="w_v")
            op_w = st.text_input("Opis", key="desc_w")
            if st.button("DODAJ WYDATEK", key="save_w", use_container_width=True, type="primary"):
                if kw_w:
                    n = pd.DataFrame([{'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw_w), 'Opis': op_w, 'Status': 'Aktywny', 'Data zdarzenia': d_w.strftime("%d.%m")}])
                    save_data(pd.concat([data, n], ignore_index=True)); st.session_state.s = ""; st.rerun()

# --- 5. MENU BOCZNE ---
with st.sidebar:
    st.header("⚙️ Menu")
    if st.button("📧 WYŚLIJ RAPORT", type="primary", use_container_width=True):
        pdf = create_pdf(df_active_calc, s_og, s_got, s_wyd)
        csv = df_active_calc.to_csv(index=False).encode('utf-8')
        if send_email_with_reports(pdf, csv): st.success("✅ Wysłano!")
    st.divider()
    if 'sel' in st.session_state and len(st.session_state.sel) > 0:
        if st.button(f"🗑️ USUŃ LINIE ({len(st.session_state.sel)})", type="primary", use_container_width=True):
            data.loc[st.session_state.sel, 'Status'] = 'Archiwum'
            save_data(data); st.session_state.sel = []; st.rerun()
    st.divider()
    if st.button("🗑️ USUŃ CAŁĄ HISTORIĘ", use_container_width=True): st.session_state.del_step = 1
    if st.session_state.get('del_step', 0) >= 1:
        st.warning("Potwierdź usunięcie")
        if st.button("🔥 TAK, CZYŚĆ", type="primary", use_container_width=True):
            data['Status'] = 'Archiwum'; save_data(data); st.session_state.del_step = 0; st.rerun()
    st.divider()
    if st.button("🔓 Wyloguj", use_container_width=True):
        cookies["is_logged"] = "false"; cookies.save(); st.rerun()

# --- 6. HISTORIA (Z WYSZARZANIEM) ---
st.divider()
st.subheader("Historia wpisów")
if not data.empty:
    df_display = data.copy().iloc[::-1]
    df_display.insert(0, "Wybierz", False)
    res = st.data_editor(
        df_display[["Wybierz", "Data zdarzenia", "Typ", "Kwota", "Opis", "Status"]],
        column_config={
            "Wybierz": st.column_config.CheckboxColumn("Wybierz", width="small"),
            "Status": st.column_config.TextColumn("Status", disabled=True),
        },
        use_container_width=True, hide_index=True, key="main_table"
    )
    st.session_state.sel = res[(res["Wybierz"] == True) & (res["Status"] == "Aktywny")].index.tolist()
else:
    st.info("Brak danych.")
