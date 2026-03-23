import streamlit as st
import pandas as pd
import os
import smtplib
import random
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

# --- TWOJE DANE POCZTOWE (JUŻ WPISANE) ---
EMAIL_WYSYLKOWY = "kontakt@coolpizza.pl" 
EMAIL_HASLO = "pizz@123" 
EMAIL_DOCELOWY = "mange929598@gmail.com" 

SMTP_SERVER = "mail.cyberfolks.pl" 
SMTP_PORT = 587
MOJE_HASLO = "dup@"

# --- FUNKCJA WYSYŁANIA MAILA ---
def wyslij_backup_na_mail(pdf_data, nazwa_pliku):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_WYSYLKOWY
        msg['To'] = EMAIL_DOCELOWY
        msg['Subject'] = f"🚀 RAPORT PIZZERIA - {datetime.now().strftime('%d.%m.%Y')}"
        
        body = f"W załączniku przesyłam raport finansowy wygenerowany: {datetime.now().strftime('%d.%m.%Y %H:%M')}."
        msg.attach(MIMEText(body, 'plain'))

        part = MIMEBase('application', "octet-stream")
        part.set_payload(pdf_data)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={nazwa_pliku}')
        msg.attach(part)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_WYSYLKOWY, EMAIL_HASLO)
        server.sendmail(EMAIL_WYSYLKOWY, EMAIL_DOCELOWY, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Problem z wysyłką przez Cyberfolks: {e}")
        return False

# --- LOGIKA DOSTĘPU ---
def check_password():
    if cookies.get("is_logged") == "true": return True
    if "password_correct" not in st.session_state:
        st.title("🍕 Rozliczenie Pizzerii")
        wpisane_haslo = st.text_input("Podaj hasło dostępu", type="password")
        if st.button("ZALOGUJ SIĘ", use_container_width=True):
            if wpisane_haslo == MOJE_HASLO:
                st.session_state["password_correct"] = True
                cookies["is_logged"] = "true"
                cookies.save()
                st.rerun()
            else:
                st.error("❌ Błędne hasło")
        return False
    return True

# --- GENERATOR PDF ---
def create_pdf(dataframe, s_ogolny, s_gotowka, s_wydatki):
    pdf = FPDF()
    pdf.add_page()
    def b_t(tekst):
        return str(tekst).replace('ą','a').replace('ć','c').replace('ę','e').replace('ł','l').replace('ń','n').replace('ó','o').replace('ś','s').replace('ź','z').replace('ż','z').replace('Ą','A').replace('Ć','C').replace('Ę','E').replace('Ł','L').replace('Ń','N').replace('Ó','O').replace('Ś','S').replace('Ź','Z').replace('Ż','Z')
    pdf.set_font("Courier", "B", 14)
    pdf.cell(190, 10, b_t(f"RAPORT FINANSOWY - {datetime.now().strftime('%d.%m.%Y %H:%M')}"), ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Courier", "B", 10)
    pdf.set_fill_color(212, 237, 218); pdf.cell(95, 10, b_t("PRZYCHOD OGOLNY:"), 1, 0, 'L', True); pdf.cell(95, 10, f"{s_ogolny:.2f} zl", 1, 1, 'R', True)
    pdf.set_fill_color(248, 215, 218); pdf.cell(95, 10, b_t("WYDATKI GOTOWKOWE:"), 1, 0, 'L', True); pdf.cell(95, 10, f"{s_wydatki:.2f} zl", 1, 1, 'R', True)
    pdf.set_fill_color(255, 243, 205); pdf.cell(95, 10, b_t("GOTOWKA (SUMA):"), 1, 0, 'L', True); pdf.cell(95, 10, f"{s_gotowka:.2f} zl", 1, 1, 'R', True)
    pdf.ln(10)
    headers = ["Data", "Typ", "Kwota", "Z dnia", "Opis"]
    cols = [25, 45, 25, 15, 80]
    pdf.set_fill_color(240, 240, 240)
    for i, h in enumerate(headers): pdf.cell(cols[i], 8, b_t(h), 1, 0, 'C', True)
    pdf.ln()
    pdf.set_font("Courier", "", 8)
    for _, row in dataframe.iterrows():
        pdf.cell(25, 8, b_t(row['Data']), 1)
        pdf.cell(45, 8, b_t(row['Typ']), 1)
        pdf.cell(25, 8, f"{row['Kwota']:.2f}", 1)
        pdf.cell(15, 8, b_t(row['Data zdarzenia']), 1)
        pdf.cell(80, 8, b_t(row['Opis'])[:45], 1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

def apply_row_styles(row):
    color = ''
    if row['Typ'] == 'Przychód ogólny': color = 'background-color: #d4edda; color: #155724'
    elif row['Typ'] == 'Wydatki gotówkowe': color = 'background-color: #f8d7da; color: #721c24'
    elif 'Gotówka' in row['Typ']: color = 'background-color: #fff3cd; color: #856404'
    return [color] * len(row)

if check_password():
    DB_FILE = 'finanse_data.csv'
    def load_data():
        if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
        return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])
    def save_data(df): df.to_csv(DB_FILE, index=False)

    st.session_state.data = load_data()
    df_active = st.session_state.data[st.session_state.data['Status'] == 'Aktywny'].copy()
    df_active['Data zdarzenia'] = df_active['Data zdarzenia'].astype(str).str[:5]
    df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

    s_ogolny = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
    s_wydatki = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
    s_gotowka = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wydatki

    st.title("🍕 Rozliczenie Pizzerii")
    
    # --- LOGIKA RESETU ---
    @st.dialog("Pobierz raport i resetuj dane")
    def final_reset_flow():
        if st.session_state.get('reset_step', 0) == 0:
            pdf_raw = create_pdf(df_active, s_ogolny, s_gotowka, s_wydatki)
            st.write("Krok 1: Pobierz plik raportu.")
            if st.download_button("📄 POBIERZ RAPORT PDF", pdf_raw, f"Raport_{datetime.now().strftime('%d_%m')}.pdf", use_container_width=True, type="primary"):
                st.session_state.reset_step = 1
                st.session_state.show_reset_dialog = True
                st.rerun()
        elif st.session_state.reset_step == 1:
            st.success("✅ Raport pobrany.")
            if st.button("🔥 RESETUJ DANE", use_container_width=True, type="primary"):
                st.session_state.reset_step = 2
                st.rerun()
            if st.button("❌ PRZERWIJ OPERACJĘ", use_container_width=True):
                st.session_state.reset_step = 0; st.session_state.show_reset_dialog = False; st.rerun()
        elif st.session_state.reset_step == 2:
            st.error("❗ JESTEŚ PEWIEN? Raport zostanie wysłany na Gmail: mange929598@gmail.com")
            if st.button("✅ TAK, JESTEM PEWIEN", use_container_width=True, type="primary"):
                pdf_to_mail = create_pdf(df_active, s_ogolny, s_gotowka, s_wydatki)
                wyslij_backup_na_mail(pdf_to_mail, f"Raport_{datetime.now().strftime('%d_%m')}.pdf")
                
                empty_df = pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])
                save_data(empty_df)
                st.session_state.data = empty_df
                st.session_state.reset_step = 0; st.session_state.show_reset_dialog = False; st.rerun()
            if st.button("❌ PRZERWIJ", use_container_width=True):
                st.session_state.reset_step = 0; st.session_state.show_reset_dialog = False; st.rerun()

    if st.session_state.get('show_reset_dialog', False):
        final_reset_flow()

    # --- KAFELKI ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:16px;">{s_ogolny:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b1", use_container_width=True):
            @st.dialog("Dodaj Przychód")
            def d1():
                kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None)
                da = st.date_input("Z dnia", datetime.now())
                if st.button("ZAPISZ", type="primary", use_container_width=True):
                    if kw:
                        n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                        current_data = load_data()
                        new_data = pd.concat([current_data, pd.DataFrame([n])], ignore_index=True)
                        save_data(new_data); st.rerun()
            d1()
    with c3:
        st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI GOTÓWKOWE</span><br><b style="color:#721c24; font-size:16px;">{s_wydatki:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➖ Dodaj", key="b3", use_container_width=True):
            @st.dialog("Dodaj Wydatek")
            def d3():
                kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None)
                da = st.date_input("Z dnia", datetime.now())
                op = st.text_input("Opis")
                if st.button("ZAPISZ", type="primary", use_container_width=True):
                    if kw:
                        n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                        current_data = load_data()
                        new_data = pd.concat([current_data, pd.DataFrame([n])], ignore_index=True)
                        save_data(new_data); st.rerun()
            d3()
    with c2:
        bg_got, brd_got, txt_got = ("#fff3cd", "#ffc107", "#856404") if s_gotowka >= 0 else ("#ff0000", "#8b0000", "#ffffff")
        st.markdown(f'<div style="background-color:{bg_got}; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid {brd_got}; height: 100px;"><span style="color:{txt_got}; font-size:11px; font-weight:bold;">GOTÓWKA (SUMA)</span><br><b style="color:{txt_got}; font-size:16px;">{s_gotowka:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj   ", key="b2", use_container_width=True):
            @st.dialog("Rozlicz Gotówkę")
            def d_got():
                opcje = [("🏠 Bufet", "Bufet"), ("🚗 Kierowca 1", "Kierowca 1"), ("🚗 Kierowca 2", "Kierowca 2"), ("🚗 Kierowca 3", "Kierowca 3"), ("🚗 Kierowca 4", "Kierowca 4")]
                for label, nazwa in opcje:
                    with st.expander(label):
                        kw_v = st.number_input(f"Kwota ({nazwa})", min_value=0.0, format="%.2f", value=None, key=f"k_{nazwa}")
                        da_v = st.date_input("Z dnia", datetime.now(), key=f"d_{nazwa}")
                        if st.button(f"ZAPISZ {nazwa.upper()}", type="primary", use_container_width=True, key=f"s_{nazwa}"):
                            if kw_v:
                                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {nazwa}", 'Kwota': float(kw_v), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da_v.strftime("%d.%m")}
                                current_data = load_data()
                                new_data = pd.concat([current_data, pd.DataFrame([n])], ignore_index=True)
                                save_data(new_data); st.rerun()
            d_got()

    # --- HISTORIA ---
    st.divider(); st.subheader("📂 Historia")
    df_h = df_active[['Data', 'Typ', 'Kwota', 'Data zdarzenia', 'Opis']].iloc[::-1]
    
    selection = st.dataframe(
        df_h.style.apply(apply_row_styles, axis=1), 
        use_container_width=True,
        on_select="rerun",
        selection_mode="multi-row",
        key=f"table_{random.randint(0,9999)}",
        column_config={
            "Kwota": st.column_config.NumberColumn(format="%.2f zł"),
            "Opis": st.column_config.TextColumn(width="large"),
        }
    )

    with st.sidebar:
        st.header("⚙️ Opcje")
        if selection.selection.rows:
            if st.button("🗑️ USUŃ ZAZNACZONE", type="primary", use_container_width=True):
                @st.dialog("Potwierdź usunięcie")
                def confirm_delete():
                    st.warning("Usunąć zaznaczone wpisy?"); 
                    if st.button("TAK", type="primary", use_container_width=True):
                        indices = df_h.index[selection.selection.rows]
                        current_data = load_data(); current_data.loc[indices, 'Status'] = 'Usunięty'; save_data(current_data); st.rerun()
                confirm_delete()
        if not df_active.empty:
            pdf_copy = create_pdf(df_active, s_ogolny, s_gotowka, s_wydatki)
            st.download_button("📄 POBIERZ RAPORT (KOPIA)", pdf_copy, f"Kopia_Raport_{datetime.now().strftime('%d_%m')}.pdf", use_container_width=True)
        if st.button("🔄 ODŚWIEŻ DANE", use_container_width=True): st.rerun()
        if not df_active.empty:
            if st.button("💾 POBIERZ RAPORT I RESETUJ DANE", use_container_width=True, type="primary"):
                st.session_state.reset_step = 0; st.session_state.show_reset_dialog = True; st.rerun()
