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

# --- KONFIGURACJA ---
DB_FILE = 'finanse_data.csv'

# --- FUNKCJE POMOCNICZE ---

def load_data():
    """Wczytuje dane z pliku CSV lub tworzy nową tabelę, jeśli plik nie istnieje."""
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df):
    """Zapisuje tabelę do pliku CSV."""
    df.to_csv(DB_FILE, index=False)

def send_email_with_reports(pdf_data, csv_data):
    """Wysyła e-mail z raportami PDF i CSV."""
    # Używamy st.secrets dla bezpieczeństwa (skonfiguruj to w Streamlit Cloud lub .streamlit/secrets.toml)
    try:
        sender_email = st.secrets["email"]["user"]
        password = st.secrets["email"]["password"]
        receiver_email = st.secrets["email"]["receiver"]
    except KeyError:
        st.error("Błąd: Brak skonfigurowanych haseł w st.secrets!")
        return False

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"Raport Pizzeria - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    msg.attach(MIMEText("W załączniku przesyłam aktualny raport finansowy.", 'plain'))

    # Załącznik PDF
    part_pdf = MIMEBase('application', 'octet-stream')
    part_pdf.set_payload(pdf_data)
    encoders.encode_base64(part_pdf)
    part_pdf.add_header('Content-Disposition', f"attachment; filename=raport_{datetime.now().strftime('%d_%m')}.pdf")
    msg.attach(part_pdf)

    # Załącznik CSV
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

def create_pdf(df, s_og, s_got, s_wyd):
    """Generuje dokument PDF z wynikami."""
    pdf = FPDF()
    pdf.add_page()
    # Uwaga: Aby polskie znaki działały, musisz mieć plik czcionki .ttf w folderze projektu
    # Jeśli nie masz czcionki, użyjemy standardowej (bez polskich znaków, jak wcześniej)
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m.%Y')}", ln=True, align='C')
    
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    
    # Podsumowanie w kolorowych ramkach
    pdf.set_fill_color(212, 237, 218)
    pdf.cell(60, 10, f"Przychod: {s_og:.2f} zl", border=1, fill=True, align='C')
    pdf.set_fill_color(255, 243, 205)
    pdf.cell(60, 10, f"Gotowka: {s_got:.2f} zl", border=1, fill=True, align='C')
    pdf.set_fill_color(248, 215, 218)
    pdf.cell(60, 10, f"Wydatki: {s_wyd:.2f} zl", border=1, ln=1, fill=True, align='C')
    
    pdf.ln(5)
    pdf.set_font("Helvetica", size=10)
    for _, row in df.iterrows():
        linia = f"{row['Data zdarzenia']} | {row['Typ']} | {row['Kwota']:.2f} zl | {row['Opis']}"
        pdf.cell(0, 10, linia.encode('latin-1', 'ignore').decode('latin-1'), ln=True, border=1)
    return pdf.output(dest="S").encode("latin-1")

# --- APLIKACJA START ---

st.set_page_config(page_title="Pizzeria - Zarządzanie", layout="wide")
cookies = CookieManager()

if not cookies.ready():
    st.stop()

# Logowanie
if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    # Hasło również przeniesione do secrets dla bezpieczeństwa
    poprawne_haslo = st.secrets.get("auth", {}).get("password", "domyslne_haslo")
    haslo = st.text_input("Wprowadź hasło", type="password")
    if st.button("Zaloguj"):
        if haslo == poprawne_haslo:
            cookies["is_logged"] = "true"
            cookies.save()
            st.rerun()
        else:
            st.error("Błędne hasło!")
    st.stop()

# --- GŁÓWNA LOGIKA DANYCH ---

data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

# Obliczenia
s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- INTERFEJS ---

st.title("🍕 Rozliczenie Pizzerii")

col1, col2, col3 = st.columns(3)

# Inicjalizacja stanu sesji
if 'menu_state' not in st.session_state: st.session_state.menu_state = ""
if 'sub_menu' not in st.session_state: st.session_state.sub_menu = None

with col1:
    st.info(f"### Przychód\n**{s_og:,.2f} zł**")
    if st.button("➕ Dodaj Przychód", use_container_width=True):
        st.session_state.menu_state = "P"
    
    if st.session_state.menu_state == "P":
        with st.form("form_przychody"):
            d_p = st.date_input("Data", datetime.now())
            kw_p = st.number_input("Kwota (zł)", min_value=0.0, step=10.0)
            if st.form_submit_button("Zapisz", use_container_width=True):
                new_row = {
                    'Data': datetime.now().strftime("%d.%m %H:%M"),
                    'Typ': 'Przychód ogólny',
                    'Kwota': float(kw_p),
                    'Opis': '',
                    'Status': 'Aktywny',
                    'Data zdarzenia': d_p.strftime("%d.%m")
                }
                save_data(pd.concat([load_data(), pd.DataFrame([new_row])], ignore_index=True))
                st.session_state.menu_state = ""
                st.rerun()

with col2:
    st.warning(f"### Gotówka\n**{s_got:,.2f} zł**")
    if st.button("➕ Dodaj Gotówkę", use_container_width=True):
        st.session_state.menu_state = "G"

    if st.session_state.menu_state == "G":
        osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
        wybor = st.selectbox("Wybierz osobę/miejsce", osoby)
        with st.form("form_gotowka"):
            d_g = st.date_input("Data", datetime.now())
            kw_g = st.number_input("Kwota (zł)", min_value=0.0, step=10.0)
            if st.form_submit_button("Zapisz wpłatę", use_container_width=True):
                new_row = {
                    'Data': datetime.now().strftime("%d.%m %H:%M"),
                    'Typ': f"Gotówka - {wybor}",
                    'Kwota': float(kw_g),
                    'Opis': '',
                    'Status': 'Aktywny',
                    'Data zdarzenia': d_g.strftime("%d.%m")
                }
                save_data(pd.concat([load_data(), pd.DataFrame([new_row])], ignore_index=True))
                st.session_state.menu_state = ""
                st.rerun()

with col3:
    st.error(f"### Wydatki\n**{s_wyd:,.2f} zł**")
    if st.button("➕ Dodaj Wydatek", use_container_width=True):
        st.session_state.menu_state = "W"

    if st.session_state.menu_state == "W":
        with st.form("form_wydatki"):
            d_w = st.date_input("Data", datetime.now())
            kw_w = st.number_input("Kwota (zł)", min_value=0.0, step=1.0)
            op_w = st.text_input("Na co poszło?")
            if st.form_submit_button("Zapisz wydatek", use_container_width=True):
                new_row = {
                    'Data': datetime.now().strftime("%d.%m %H:%M"),
                    'Typ': 'Wydatki gotówkowe',
                    'Kwota': float(kw_w),
                    'Opis': op_w,
                    'Status': 'Aktywny',
                    'Data zdarzenia': d_w.strftime("%d.%m")
                }
                save_data(pd.concat([load_data(), pd.DataFrame([new_row])], ignore_index=True))
                st.session_state.menu_state = ""
                st.rerun()

# --- PASEK BOCZNY ---

with st.sidebar:
    st.header("⚙️ Opcje")
    if st.button("📧 Wyślij Raport E-mailem", type="primary", use_container_width=True):
        with st.spinner("Przygotowuję raport..."):
            pdf = create_pdf(df_active, s_og, s_got, s_wyd)
            csv = df_active.to_csv(index=False).encode('utf-8')
            if send_email_with_reports(pdf, csv):
                st.success("Wysłano pomyślnie!")

    st.divider()
    
    # Pobieranie plików
    st.download_button("📥 Pobierz raport CSV", df_active.to_csv(index=False).encode('utf-8'), "raport.csv", use_container_width=True)
    
    if st.button("🔓 Wyloguj", use_container_width=True):
        cookies["is_logged"] = "false"
        cookies.save()
        st.rerun()

# --- TABELA HISTORII ---

st.divider()
st.subheader("Ostatnie wpisy")

if not df_active.empty:
    # Wyświetlamy tabelę od najnowszych [iloc[::-1]]
    st.dataframe(
        df_active.iloc[::-1][["Data zdarzenia", "Typ", "Kwota", "Opis"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Brak wpisów do wyświetlenia.")
