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

# --- 2. DANE DO MAILA ---
EMAIL_ADRES = "mange929598@gmail.com"
EMAIL_HASLO = "pxonwcimblzuwaou" 
EMAIL_ODBIORCA = "mange929598@gmail.com"

# --- 3. USTAWIENIA SYSTEMOWE ---
MOJE_HASLO = "dup@"
DB_FILE = 'finanse_data.csv'

# --- 4. FUNKCJA WYSYŁKI ---
def send_email_with_backup(pdf_content, csv_content, date_str):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADRES
        msg['To'] = EMAIL_ODBIORCA
        msg['Subject'] = f"🍕 RAPORT I KOPIA - {date_str}"
        body = "W zalaczniku raport PDF oraz surowy plik CSV (kopia ratunkowa)."
        msg.attach(MIMEText(body, 'plain'))
        part1 = MIMEBase('application', 'octet-stream'); part1.set_payload(pdf_content); encoders.encode_base64(part1)
        part1.add_header('Content-Disposition', f"attachment; filename= raport_{date_str}.pdf"); msg.attach(part1)
        part2 = MIMEBase('application', 'octet-stream'); part2.set_payload(csv_content.encode('utf-8')); encoders.encode_base64(part2)
        part2.add_header('Content-Disposition', f"attachment; filename= KOPIA_RATUNKOWA_{date_str}.csv"); msg.attach(part2)
        server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(EMAIL_ADRES, EMAIL_HASLO)
        server.send_message(msg); server.quit()
        return True
    except Exception as e:
        st.error(f"❌ Blad poczty: {e}"); return False

# --- 5. OBSŁUGA DANYCH ---
def load_data():
    if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

def clean_text(text):
    if not isinstance(text, str): return str(text)
    return text.encode('ascii', 'ignore').decode('ascii').strip()

def create_pdf(df_to_pdf, s_og, s_got, s_wyd):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 15, txt="RAPORT FINANSOWY PIZZERIA", ln=True, align='C'); pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(212, 237, 218); pdf.set_text_color(21, 87, 36); pdf.cell(190, 10, txt=f" PRZYCHOD OGOLNY: {s_og:.2f} zl", ln=True, fill=True)
    pdf.set_fill_color(255, 243, 205); pdf.set_text_color(133, 100, 4); pdf.cell(190, 10, txt=f" GOTOWKA (SUMA): {s_got:.2f} zl", ln=True, fill=True)
    pdf.set_fill_color(248, 215, 218); pdf.set_text_color(114, 28, 36); pdf.cell(190, 10, txt=f" WYDATKI GOTOWKOWE: {s_wyd:.2f} zl", ln=True, fill=True)
    pdf.ln(10); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 8, "Data zapisu", 1); pdf.cell(25, 8, "Kwota", 1); pdf.cell(35, 8, "Data zdarz.", 1); pdf.cell(90, 8, "Typ / Opis", 1); pdf.ln()
    pdf.set_font("Arial", size=9)
    for _, row in df_to_pdf.iterrows():
        pdf.cell(40, 8, clean_text(row['Data']), 1); pdf.cell(25, 8, f"{row['Kwota']:.2f}", 1, 0, 'R')
        pdf.cell(35, 8, clean_text(row['Data zdarzenia']), 1, 0, 'C')
        info = f"{clean_text(row['Typ'])} {clean_text(row['Opis']) if pd.notna(row['Opis']) else ''}"
        pdf.cell(90, 8, info[:50], 1); pdf.ln()
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 6. LOGOWANIE ---
if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    wpisane = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        if wpisane == MOJE_HASLO: cookies["is_logged"] = "true"; cookies.save(); st.rerun()
    st.stop()

# --- 7. DANE ---
data = load_data(); df_active = data[data['Status'] == 'Aktywny'].copy()
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

# --- 8. WIDOK ---
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
        if "os_v" not in st.session_state: st.session_state.os_v = None
        @st.dialog("Dodaj Gotowke")
        def add_g():
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            
            # Pętla wyświetlająca osoby (oryginalny schemat)
            for o in osoby:
                if st.button(o, use_container_width=True, key=f"btn_{o}"):
                    st.session_state.os_v = o
                
                # Jeśli osoba jest kliknięta, pokaż formularz pod nią
                if st.session_state.get("os_v") == o:
                    with st.container(border=True):
                        kw = st.number_input(f"Kwota dla: {o}", min_value=0.0, format="%.2f", value=None, key=f"k_{o}")
                        da = st.date_input("Data zdarzenia", datetime.now(), key=f"d_{o}")
                        
                        col1, col2 = st.columns(2)
                        if col1.button("ZAPISZ", type="primary", use_container_width=True, key=f"s_{o}"):
                            if kw:
                                n = pd.DataFrame([{'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Typ': f"Gotówka - {o}", 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%Y-%m-%d")}])
                                save_data(pd.concat([load_data(), n], ignore_index=True))
                                st.session_state.os_v = None
                                st.rerun()
                        
                        # NOWY PRZYCISK COFNIJ
                        if col2.button("⬅️ COFNIJ", use_container_width=True, key=f"c_{o}"):
                            st.session_state.os_v = None
                            st.rerun()
        add_g()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><b>WYDATKI GOTÓWKOWE</b><br><b style="font-size:20px;">{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➖ Dodaj Wydatek", use_container_width=True):
        @st.dialog("Dodaj Wydatek")
        def add_w():
            kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None)
            da = st.date_input("Data zdarzenia", datetime.now()); op = st.text_input("Opis")
            if st.button("ZAPISZ"):
                if kw:
                    n = pd.DataFrame([{'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%Y-%m-%d")}])
                    save_data(pd.concat([load_data(), n], ignore_index=True)); st.rerun()
        add_w()

st.divider()
df_h = df_active[['Data', 'Kwota', 'Data zdarzenia', 'Opis', 'Typ']].iloc[::-1]
if "tk_v30" not in st.session_state: st.session_state.tk_v30 = 0
event = st.dataframe(df_h.style.apply(apply_row_styles, axis=1), use_container_width=True, on_select="rerun", selection_mode="multi-row", key=f"table_{st.session_state.tk_v30}",
    column_config={"Data": st.column_config.TextColumn("Data zapisu"), "Kwota": st.column_config.NumberColumn("Kwota", format="%.2f zł"), "Data zdarzenia": st.column_config.TextColumn("Data zdarzenia"), "Typ": None})

# --- 9. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Opcje")
    pdf_bytes = create_pdf(df_h, s_og, s_got, s_wyd)
    st.download_button(label="📥 POBIERZ RAPORT PDF", data=pdf_bytes, file_name=f"raport_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
    st.divider()
    if "step" not in st.session_state: st.session_state.step = 0
    if st.session_state.step == 0:
        if st.button("🚀 POBIERZ RAPORT I WYŚLIJ", type="primary", use_container_width=True):
            with st.spinner("Wysyłam raport..."):
                d_full = load_data(); csv_str = d_full.to_csv(index=False); date_str = datetime.now().strftime('%Y%m%d_%H%M')
                if send_email_with_backup(pdf_bytes, csv_str, date_str): st.toast("Wysłano!", icon="📧"); st.session_state.step = 1; st.rerun()
    elif st.session_state.step == 1:
        st.success("✅ Wysłano!")
        if st.button("🗑️ USUŃ DANE Z SYSTEMU", type="primary", use_container_width=True): st.session_state.step = 2; st.rerun()
        if st.button("ANULUJ", use_container_width=True): st.session_state.step = 0; st.rerun()
    elif st.session_state.step == 2:
        st.error("JESTEŚ PEWIEN? Tej czynności nie można cofnąć!")
        if st.button("POTWIERDZAM - USUŃ WSZYSTKO", type="primary", use_container_width=True):
            d_full = load_data(); date_str = datetime.now().strftime('%Y%m%d_%H%M')
            d_full.loc[d_full['Status'] == 'Aktywny', 'Status'] = f"Arch_{date_str}"; save_data(d_full)
            st.success("System wyzerowany."); st.session_state.step = 0; st.rerun()
        if st.button("POWRÓT", use_container_width=True): st.session_state.step = 1; st.rerun()
    st.divider()
    sel = event.selection.rows
    if sel:
        if "del_s" not in st.session_state: st.session_state.del_s = 0
        if st.session_state.del_s == 0:
            if st.button("🗑️ USUŃ ZAZNACZONE", use_container_width=True): st.session_state.del_s = 1; st.rerun()
        elif st.session_state.del_s == 1:
            st.error("Na pewno?"); c_t, c_n = st.columns(2)
            if c_t.button("TAK"):
                ff = load_data(); ff.loc[df_h.index[sel], 'Status'] = 'Usunięty'; save_data(ff)
                st.session_state.del_s = 0; st.session_state.tk_v30 += 1; st.rerun()
            if c_n.button("NIE"): st.session_state.del_s = 0; st.session_state.tk_v30 += 1; st.rerun()
    st.divider(); 
    if st.button("🔄 ODSWIEŻ", use_container_width=True): st.rerun()
