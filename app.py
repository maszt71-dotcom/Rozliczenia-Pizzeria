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

# --- FUNKCJA BEZPIECZEŃSTWA DLA PDF ---
def pdf_safe(txt):
    if not txt: return ""
    rep = {"ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ź":"z","ż":"z",
           "Ą":"A","Ć":"C","Ę":"E","Ł":"L","N":"N","Ó":"O","Ś":"S","Ź":"Z","Ż":"Z"}
    t = str(txt)
    for k, v in rep.items(): t = t.replace(k, v)
    return t.encode('ascii', 'ignore').decode('ascii')

# --- FUNKCJA WYSYŁKI E-MAIL ---
def send_email_with_reports(pdf_data, csv_data):
    receiver_email = "mange929598@gmail.com"
    sender_email = "mange929598@gmail.com"
    password = "hlqivtidxgchoqdi" 

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"Raport Pizzeria - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    msg.attach(MIMEText("W załączniku przesyłam aktualny raport finansowy.", 'plain'))

    part_pdf = MIMEBase('application', 'octet-stream')
    part_pdf.set_payload(pdf_data)
    encoders.encode_base64(part_pdf)
    part_pdf.add_header('Content-Disposition', f"attachment; filename=raport_{datetime.now().strftime('%d_%m')}.pdf")
    msg.attach(part_pdf)

    part_csv = MIMEBase('application', 'octet-stream')
    part_csv.set_payload(csv_data)
    encoders.encode_base64(part_csv)
    part_csv.add_header('Content-Disposition', f"attachment; filename=raport_{datetime.now().strftime('%d_%m')}.csv")
    msg.attach(part_csv)

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

def save_data(df): df.to_csv(DB_FILE, index=False)

data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].astype(str).str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- 3. GENERATOR PDF (TABELA JAK W HISTORII) ---
def create_pdf(df, s_og, s_got, s_wyd):
    pdf = FPDF(orientation='L', unit='mm', format='A4') # Orientacja pozioma dla lepszego dopasowania
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, pdf_safe(f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m.%Y')}"), ln=True, align='C')
    pdf.ln(10)
    
    # Podsumowanie
    pdf.set_font("Helvetica", 'B', 11)
    pdf.set_fill_color(212, 237, 218)
    pdf.cell(92, 10, pdf_safe(f"Przychod: {s_og:.2f} zl"), border=1, fill=True, align='C')
    
    if s_got < 0:
        pdf.set_fill_color(255, 0, 0); pdf.set_text_color(255, 255, 255)
    else:
        pdf.set_fill_color(255, 243, 205); pdf.set_text_color(0, 0, 0)
    pdf.cell(93, 10, pdf_safe(f"Gotowka: {s_got:.2f} zl"), border=1, fill=True, align='C')
    
    pdf.set_fill_color(248, 215, 218); pdf.set_text_color(0, 0, 0)
    pdf.cell(92, 10, pdf_safe(f"Wydatki: {s_wyd:.2f} zl"), border=1, ln=1, fill=True, align='C')
    
    pdf.ln(10)
    
    # NAGŁÓWEK TABELI (Identyczny jak w aplikacji)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(35, 8, pdf_safe("Data wpisu"), border=1, fill=True, align='C')
    pdf.cell(20, 8, pdf_safe("Dzien"), border=1, fill=True, align='C')
    pdf.cell(50, 8, pdf_safe("Typ"), border=1, fill=True, align='C')
    pdf.cell(30, 8, pdf_safe("Kwota"), border=1, fill=True, align='C')
    pdf.cell(142, 8, pdf_safe("Opis"), border=1, ln=1, fill=True, align='C')
    
    # WIERSZE TABELI (Identyczny układ jak w aplikacji)
    pdf.set_font("Helvetica", size=8)
    # Sortujemy od najnowszego (tak jak w data_editor iloc[::-1])
    for _, row in df.iloc[::-1].iterrows():
        pdf.cell(35, 7, pdf_safe(row['Data']), border=1, align='C')
        pdf.cell(20, 7, pdf_safe(row['Data zdarzenia']), border=1, align='C')
        pdf.cell(50, 7, pdf_safe(row['Typ']), border=1)
        pdf.cell(30, 7, pdf_safe(f"{row['Kwota']:.2f} zl"), border=1, align='R')
        pdf.cell(142, 7, pdf_safe(row['Opis']), border=1, ln=1)
        
    return pdf.output(dest="S").encode("latin-1")

# --- 4. WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

if 's' not in st.session_state: st.session_state.s = ""
if 'os' not in st.session_state: st.session_state.os = None

with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:15px; border-radius:10px; text-align:center; color: black;">Przychód: <b>{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="p"): st.session_state.s = "P" if st.session_state.s != "P" else ""; st.rerun()
    if st.session_state.s == "P":
        with st.container(border=True):
            d_p = st.date_input("z dnia", datetime.now(), key="date_p")
            kw_p = st.number_input("Kwota", value=None, step=1.0, key="p_v")
            if st.button("DODAJ", key="save_p", use_container_width=True, type="primary"):
                if kw_p:
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw_p), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_p.strftime("%d.%m")}
                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True)); st.session_state.s = ""; st.rerun()
            if st.button("⬅️ POWRÓT", key="back_p", use_container_width=True): st.session_state.s = ""; st.rerun()

with c2:
    bg_got = "#ff0000" if s_got < 0 else "#fff3cd"
    txt_got = "white" if s_got < 0 else "black"
    st.markdown(f'<div style="background-color:{bg_got}; padding:15px; border-radius:10px; text-align:center; color: {txt_got};">Gotówka: <b>{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="g"): st.session_state.s = "G" if st.session_state.s != "G" else ""; st.session_state.os = None; st.rerun()
    if st.session_state.s == "G":
        with st.container(border=True):
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            for o in osoby:
                if st.button(o, key=f"os_{o}", use_container_width=True): st.session_state.os = o if st.session_state.os != o else None; st.rerun()
                if st.session_state.os == o:
                    with st.container(border=True):
                        st.markdown(f"Dla: **{o}**")
                        d_g = st.date_input("z dnia", datetime.now(), key=f"date_g_{o}")
                        kw_g = st.number_input("Kwota", value=None, step=1.0, key=f"g_v_{o}")
                        cs, cb = st.columns(2)
                        if cs.button("DODAJ", key=f"save_g_{o}", use_container_width=True, type="primary"):
                            if kw_g:
                                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {o}", 'Kwota': float(kw_g), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_g.strftime("%d.%m")}
                                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True)); st.session_state.s = ""; st.session_state.os = None; st.rerun()
                        if cb.button("COFNIJ", key=f"back_g_{o}", use_container_width=True): st.session_state.os = None; st.rerun()
            st.divider()
            if st.button("⬅️ POWRÓT", key="back_g_main", use_container_width=True): st.session_state.s = ""; st.session_state.os = None; st.rerun()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:15px; border-radius:10px; text-align:center; color: black;">Wydatki: <b>{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="w"): st.session_state.s = "W" if st.session_state.s != "W" else ""; st.rerun()
    if st.session_state.s == "W":
        with st.container(border=True):
            d_w = st.date_input("z dnia", datetime.now(), key="date_w")
            kw_w = st.number_input("Kwota", value=None, step=1.0, key="w_v")
            op_w = st.text_input("Opis", key="desc_w")
            if st.button("DODAJ", key="save_w", use_container_width=True, type="primary"):
                if kw_w:
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw_w), 'Opis': op_w, 'Status': 'Aktywny', 'Data zdarzenia': d_w.strftime("%d.%m")}
                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True)); st.session_state.s = ""; st.rerun()
            if st.button("⬅️ POWRÓT", key="back_w", use_container_width=True): st.session_state.s = ""; st.rerun()

st.divider()

# --- 5. HISTORIA I MENU ---
st.subheader("Historia wpisów")
if not df_active.empty:
    df_editor = df_active.copy()
    cols_to_show = ["Data", "Data zdarzenia", "Typ", "Kwota", "Opis"]
    df_editor = df_editor[cols_to_show]
    df_editor.insert(0, "Wybierz", False)
    
    res = st.data_editor(
        df_editor.iloc[::-1],
        column_config={
            "Wybierz": st.column_config.CheckboxColumn("Wybierz", width="small", default=False),
            "Data": st.column_config.TextColumn("Data wpisu", width="medium"),
            "Data zdarzenia": st.column_config.TextColumn("Dzień", width="small"),
            "Typ": st.column_config.TextColumn("Typ", width="medium"),
            "Kwota": st.column_config.NumberColumn("Kwota", width="small", format="%.2f zł"),
            "Opis": st.column_config.TextColumn("Opis", width="large")
        },
        disabled=["Data", "Data zdarzenia", "Typ", "Kwota", "Opis"],
        hide_index=True,
        use_container_width=True,
        key="pizza_editor"
    )

    with st.sidebar:
        st.header("⚙️ Menu")
        if st.button("📧 WYŚLIJ RAPORT", use_container_width=True, type="primary"):
            pdf_file = create_pdf(df_active, s_og, s_got, s_wyd)
            csv_file = df_active.to_csv(index=False).encode('utf-8')
            with st.spinner("Wysyłanie..."):
                if send_email_with_reports(pdf_file, csv_file): st.success("✅ Wysłano!")

        st.divider()
        
        selected_rows = res[res["Wybierz"] == True].index.tolist()
        if len(selected_rows) > 0:
            if st.button(f"🗑️ USUŃ ZAZNACZONE ({len(selected_rows)})", use_container_width=True, type="primary"):
                full = load_data()
                full.loc[selected_rows, 'Status'] = 'Archiwum'
                save_data(full)
                st.rerun()

        st.divider()
        st.download_button("📥 Pobierz CSV", data=df_active.to_csv(index=False).encode('utf-8'), file_name="raport.csv", use_container_width=True)
        st.download_button("📥 Pobierz PDF", data=create_pdf(df_active, s_og, s_got, s_wyd), file_name="raport.pdf", use_container_width=True)
        
        st.divider()
        if 'delete_confirm' not in st.session_state: st.session_state.delete_confirm = 0
        
        if st.session_state.delete_confirm == 0:
            if st.button("🗑️ USUŃ CAŁĄ HISTORIĘ", use_container_width=True):
                st.session_state.delete_confirm = 1; st.rerun()
        
        if st.session_state.delete_confirm == 1:
            st.warning("Czy na pewno chcesz usunąć wszystko?")
            col_y, col_n = st.columns(2)
            if col_y.button("TAK", use_container_width=True):
                st.session_state.delete_confirm = 2; st.rerun()
            if col_n.button("ANULUJ", use_container_width=True):
                st.session_state.delete_confirm = 0; st.rerun()

        if st.session_state.delete_confirm == 2:
            st.error("DANE ZOSTANĄ USUNIETE! OSTATECZNE POTWIERDZENIE?")
            if st.button("🔥 POTWIERDZAM USUNIĘCIE", use_container_width=True, type="primary"):
                full = load_data(); full.loc[df_active.index, 'Status'] = 'Archiwum'; save_data(full)
                st.session_state.delete_confirm = 0; st.rerun()
            if st.button("⬅️ COFNIJ", use_container_width=True):
                st.session_state.delete_confirm = 0; st.rerun()
else:
    st.info("Brak aktywnych wpisów.")
    with st.sidebar:
        st.header("⚙️ Menu")
        st.write("Dodaj wpisy, aby zobaczyć menu.")
