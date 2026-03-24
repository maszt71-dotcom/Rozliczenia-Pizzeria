import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from streamlit_cookies_manager import CookieManager
from fpdf import FPDF

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Rozliczenie Pizzerii", layout="wide", page_icon="🍕")

cookies = CookieManager()
if not cookies.ready():
    st.stop()

# --- 2. DANE DO MAILA (TWOJA NOWA KONFIGURACJA) ---
EMAIL_ADRES = "mange929598@gmail.com"
EMAIL_HASLO = "pxonwcimblzuwaou" # Twoje nowe hasło bez spacji
EMAIL_ODBIORCA = "mange929598@gmail.com"

# --- 3. USTAWIENIA SYSTEMOWE ---
MOJE_HASLO = "dup@"
DB_FILE = 'finanse_data.csv'

# --- 4. FUNKCJA WYSYŁKI RAPORTU ---
def send_email_report(pdf_content, filename):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADRES
        msg['To'] = EMAIL_ODBIORCA
        msg['Subject'] = f"🍕 RAPORT PIZZERIA - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        body = "W zalaczniku przesylam pelny raport finansowy wygenerowany przed wyzerowaniem danych."
        msg.attach(MIMEText(body, 'plain'))

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_content)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filename}")
        msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADRES, EMAIL_HASLO)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"❌ Blad poczty: {e}")
        return False

# --- 5. OBSŁUGA DANYCH (ZAPIS NA DYSK) ---
def load_data():
    if os.path.exists(DB_FILE): 
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

def clean_text(text):
    if not isinstance(text, str): return str(text)
    return text.encode('ascii', 'ignore').decode('ascii').strip()

def create_pdf(df_to_pdf, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 15, txt="RAPORT FINANSOWY PIZZERIA", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    # Kolory w PDF (Święte!)
    pdf.set_fill_color(212, 237, 218); pdf.set_text_color(21, 87, 36)
    pdf.cell(190, 10, txt=f" PRZYCHOD OGOLNY: {s_og:.2f} zl", ln=True, fill=True)
    pdf.set_fill_color(255, 243, 205); pdf.set_text_color(133, 100, 4)
    pdf.cell(190, 10, txt=f" GOTOWKA (SUMA): {s_got:.2f} zl", ln=True, fill=True)
    pdf.set_fill_color(248, 215, 218); pdf.set_text_color(114, 28, 36)
    pdf.cell(190, 10, txt=f" WYDATKI GOTOWKOWE: {s_wyd:.2f} zl", ln=True, fill=True)
    pdf.ln(10); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 8, "Data zapisu", 1); pdf.cell(25, 8, "Kwota", 1); pdf.cell(35, 8, "Data zdarz.", 1); pdf.cell(90, 8, "Typ / Opis", 1); pdf.ln()
    pdf.set_font("Arial", size=9)
    for _, row in df_to_pdf.iterrows():
        pdf.cell(40, 8, clean_text(row['Data']), 1)
        pdf.cell(25, 8, f"{row['Kwota']:.2f}", 1, 0, 'R')
        pdf.cell(35, 8, clean_text(row['Data zdarzenia']), 1, 0, 'C')
        info = f"{clean_text(row['Typ'])} {clean_text(row['Opis']) if pd.notna(row['Opis']) else ''}"
        pdf.cell(90, 8, info[:50], 1); pdf.ln()
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 6. LOGOWANIE ---
if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    wpisane = st.text_input("Podaj haslo", type="password")
    if st.button("Zaloguj"):
        if wpisane == MOJE_HASLO:
            cookies["is_logged"] = "true"; cookies.save(); st.rerun()
    st.stop()

# --- 7. OBLICZENIA ---
data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)
s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

def apply_row_styles(row):
    color = ''
    typ = str(row['Typ'])
    if typ == 'Przychód ogólny': color = 'background-color: #d4edda; color: #155724'
    elif typ == 'Wydatki gotówkowe': color = 'background-color: #f8d7da; color: #721c24'
    elif 'Gotówka' in typ: color = 'background-color: #fff3cd; color: #856404'
    return [color] * len(row)

# --- 8. WIDOK GLOWNY ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><b>PRZYCHÓD OGÓLNY</b><br><b style="font-size:20px;">{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ Dodaj Przychod", use_container_width=True):
        @st.dialog("Dodaj Przychod")
        def add_p():
            kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None)
            da = st.date_input("Data zdarzenia", datetime.now())
            if st.button("ZAPISZ"):
                if kw:
                    n = pd.DataFrame([{'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%Y-%m-%d")}])
                    save_data(pd.concat([load_data(), n], ignore_index=True)); st.rerun()
        add_p()

with c2:
    bg_got = "#fff3cd" if s_got >= 0 else "#f8d7da"; brd_got = "#ffc107" if s_got >= 0 else "#dc3545"
    st.markdown(f'<div style="background-color:{bg_got}; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid {brd_got}; height: 100px;"><b>GOTÓWKA (SUMA)</b><br><b style="font-size:20px;">{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ Dodaj Gotowke", use_container_width=True):
        if "os_v_27" not in st.session_state: st.session_state.os_v_27 = None
        @st.dialog("Dodaj Gotowke")
        def add_g():
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            for o in osoby:
                if st.button(o, use_container_width=True): st.session_state.os_v_27 = o
                if st.session_state.os_v_27 == o:
                    kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None, key=f"k_{o}")
                    da = st.date_input("Data zdarzenia", datetime.now(), key=f"d_{o}")
                    if st.button("ZAPISZ", type="primary", use_container_width=True):
                        if kw:
                            n = pd.DataFrame([{'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Typ': f"Gotówka - {o}", 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%Y-%m-%d")}])
                            save_data(pd.concat([load_data(), n], ignore_index=True))
                            st.session_state.os_v_27 = None; st.rerun()
        add_g()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><b>WYDATKI GOTÓWKOWE</b><br><b style="font-size:20px;">{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➖ Dodaj Wydatek", use_container_width=True):
        @st.dialog("Dodaj Wydatek")
        def add_w():
            kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None)
            da = st.date_input("Data zdarzenia", datetime.now())
            op = st.text_input("Opis")
            if st.button("ZAPISZ"):
                if kw:
                    n = pd.DataFrame([{'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%Y-%m-%d")}])
                    save_data(pd.concat([load_data(), n], ignore_index=True)); st.rerun()
        add_w()

st.divider()
df_h = df_active[['Data', 'Kwota', 'Data zdarzenia', 'Opis', 'Typ']].iloc[::-1]
if "tk_27" not in st.session_state: st.session_state.tk_27 = 0
event = st.dataframe(df_h.style.apply(apply_row_styles, axis=1), use_container_width=True, on_select="rerun", selection_mode="multi-row", key=f"table_{st.session_state.tk_27}",
    column_config={"Data": st.column_config.TextColumn("Data zapisu"), "Kwota": st.column_config.NumberColumn("Kwota", format="%.2f zł"), "Data zdarzenia": st.column_config.TextColumn("Data zdarzenia"), "Typ": None})

# --- 9. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Opcje")
    pdf_bytes = create_pdf(df_h, s_og, s_got, s_wyd)
    st.download_button(label="📥 POBIERZ RAPORT PDF", data=pdf_bytes, file_name=f"raport_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
    st.divider()

    if "wipe_27" not in st.session_state: st.session_state.wipe_27 = 0
    if st.session_state.wipe_27 == 0:
        if st.button("🚀 WYSLIJ RAPORT I ZERUJ", type="primary", use_container_width=True):
            st.session_state.wipe_27 = 1; st.rerun()
    elif st.session_state.wipe_27 == 1:
        st.warning("Czy wyslac raport i wyzerowac system?")
        if st.button("TAK, WYSLIJ I CZYSC", type="primary", use_container_width=True):
            with st.spinner("Trwa wysylanie poczty..."):
                if send_email_report(pdf_bytes, f"raport_{datetime.now().strftime('%Y%m%d')}.pdf"):
                    f = load_data(); f.loc[f['Status'] == 'Aktywny', 'Status'] = f"Arch_{datetime.now().strftime('%Y%m%d')}"
                    save_data(f); st.success("Wysłano i wyzerowano!"); st.session_state.wipe_27 = 0; st.rerun()
        if st.button("ANULUJ", use_container_width=True): st.session_state.wipe_27 = 0; st.rerun()

    st.divider()
    sel = event.selection.rows
    if sel:
        if "del_27" not in st.session_state: st.session_state.del_27 = 0
        if st.session_state.del_27 == 0:
            if st.button("🗑️ USUN ZAZNACZONE", use_container_width=True): st.session_state.del_27 = 1; st.rerun()
        elif st.session_state.del_27 == 1:
            st.error("Na pewno usunac?"); c_t, c_n = st.columns(2)
            if c_t.button("TAK"):
                ff = load_data(); ff.loc[df_h.index[sel], 'Status'] = 'Usunięty'; save_data(ff)
                st.session_state.del_27 = 0; st.session_state.tk_27 += 1; st.rerun()
            if c_n.button("NIE"): st.session_state.del_27 = 0; st.session_state.tk_27 += 1; st.rerun()
    st.divider()
    if st.button("🔄 ODSWIEŻ", use_container_width=True): st.rerun()
