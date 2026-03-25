import streamlit as st
import pandas as pd
import os
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import datetime
from streamlit_cookies_manager import CookieManager

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Rozliczenie Pizzerii", layout="wide", page_icon="🍕")

cookies = CookieManager()
if not cookies.ready():
    st.stop()

# --- 2. DANE DO WYSYŁKI ---
MOJE_HASLO = "dup@"
DB_FILE = 'finanse_data.csv'
EMAIL_KONTO = "mange929598@gmail.com"  
HASLO_APP = "hlqivtidxgchoqdi" 

# --- 3. FUNKCJA WYSYŁANIA ---
def wyslij_raporty_final(df):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_KONTO
        msg['To'] = EMAIL_KONTO
        msg['Subject'] = f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m %H:%M')}"
        msg.attach(MIMEText("W załączniku przesyłam raporty PDF i CSV.", 'plain'))

        csv_data = df.to_csv(index=False).encode('utf-8')
        pdf_data = df.to_csv(index=False).encode('utf-8')

        for filename, data in [("raport.csv", csv_data), ("raport.pdf", pdf_data)]:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(data)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={filename}")
            msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_KONTO, HASLO_APP)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"Błąd: {e}")
        return False

# --- 4. STYLE ---
st.markdown("""
    <style>
    div[data-testid="stColumn"] .stButton { width: 100% !important; }
    div[data-testid="stColumn"] .stButton > button {
        width: 100% !important; border-radius: 10px !important;
        font-weight: bold !important; height: 45px !important;
    }
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button { background-color: #d4edda !important; color: #155724 !important; }
    div[data-testid="stColumn"]:nth-of-type(2) .stButton > button { background-color: #fff3cd !important; color: #856404 !important; }
    div[data-testid="stColumn"]:nth-of-type(3) .stButton > button { background-color: #f8d7da !important; color: #721c24 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 5. LOGIKA DANYCH ---
def load_data():
    if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- 6. LOGOWANIE ---
if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    wpisane = st.text_input("Hasło", type="password")
    if st.button("Zaloguj się"):
        if wpisane == MOJE_HASLO:
            cookies["is_logged"] = "true"; cookies.save(); st.rerun()
    st.stop()

# --- 7. WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

# PRZYCHÓD
with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; height: 100px;">Przychód: {s_og:,.2f} zł</div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="p"): st.session_state.open_section = "P" if getattr(st.session_state, "open_section", None) != "P" else None; st.rerun()
    if getattr(st.session_state, "open_section", None) == "P":
        with st.container(border=True):
            d_zd = st.date_input("Data zdarzenia", datetime.now(), key="p_date")
            kw = st.number_input("Kwota", value=None, key="p_kw")
            if st.button("ZAPISZ", type="primary"):
                if kw:
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_zd.strftime("%d.%m")}
                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                    st.session_state.open_section = None; st.rerun()

# GOTÓWKA
with c2:
    bg = "#fff3cd" if s_got >= 0 else "#ff0000"; txt = "#856404" if s_got >= 0 else "#ffffff"
    st.markdown(f'<div style="background-color:{bg}; color:{txt}; padding:10px; border-radius:10px; text-align:center; height: 100px;">Gotówka: {s_got:,.2f} zł</div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="g"): st.session_state.open_section = "G" if getattr(st.session_state, "open_section", None) != "G" else None; st.session_state.selected_person = None; st.rerun()
    if getattr(st.session_state, "open_section", None) == "G":
        with st.container(border=True):
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            if getattr(st.session_state, "selected_person", None) is None:
                for o in osoby:
                    if st.button(o, key=f"sel_{o}"): st.session_state.selected_person = o; st.rerun()
            else:
                st.markdown(f"**Osoba:** `{st.session_state.selected_person}`")
                d_zd = st.date_input("Data zdarzenia", datetime.now(), key="g_date")
                kw = st.number_input("Kwota", value=None, key="g_kw")
                if st.button("ZAPISZ", type="primary"):
                    if kw:
                        n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {st.session_state.selected_person}", 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_zd.strftime("%d.%m")}
                        save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                        st.session_state.open_section = None; st.session_state.selected_person = None; st.rerun()

# WYDATKI
with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; height: 100px;">Wydatki: {s_wyd:,.2f} zł</div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="w"): st.session_state.open_section = "W" if getattr(st.session_state, "open_section", None) != "W" else None; st.rerun()
    if getattr(st.session_state, "open_section", None) == "W":
        with st.container(border=True):
            d_zd = st.date_input("Data zdarzenia", datetime.now(), key="w_date")
            kw = st.number_input("Kwota", value=None, key="w_kw")
            op = st.text_input("Opis")
            if st.button("ZAPISZ", type="primary"):
                if kw:
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': d_zd.strftime("%d.%m")}
                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                    st.session_state.open_section = None; st.rerun()

# --- 8. PASEK BOCZNY ---
with st.sidebar:
    st.header("⚙️ Menu Raportów")
    
    # Dane do plików
    csv_data = df_active[['Data', 'Typ', 'Kwota', 'Data zdarzenia', 'Opis']].to_csv(index=False).encode('utf-8')

    # DWA ODDZIELNE PRZYCISKI POBIERANIA
    st.download_button("📥 Pobierz raport CSV", data=csv_data, file_name="raport.csv", use_container_width=True)
    st.download_button("📥 Pobierz raport PDF", data=csv_data, file_name="raport.pdf", use_container_width=True)

    st.divider()

    # WYŚLIJ
    if st.button("📧 Wyślij raport", use_container_width=True):
        if wyslij_raporty_final(df_active):
            st.success("✅ RAPORTY WYSŁANE!")

    st.divider()

    # USUŃ HISTORIĘ
    if "confirm_delete" not in st.session_state: st.session_state.confirm_delete = False
    if not st.session_state.confirm_delete:
        if st.button("🗑️ USUŃ HISTORIĘ", type="primary", use_container_width=True):
            st.session_state.confirm_delete = True; st.rerun()
    else:
        st.warning("⚠️ CZY JESTEŚ PEWIEN?")
        st.write("Na pewno tego nie można cofnąć!")
        c_yes, c_no = st.columns(2)
        if c_yes.button("TAK, USUŃ"):
            full = load_data(); full.loc[df_active.index, 'Status'] = 'Archiwum'; save_data(full)
            st.session_state.confirm_delete = False; st.rerun()
        if c_no.button("NIE"):
            st.session_state.confirm_delete = False; st.rerun()

    st.divider()
    if st.button("🔄 ODŚWIEŻ", use_container_width=True): st.rerun()

# --- 9. TABELA ---
st.divider()
st.dataframe(df_active[['Data', 'Typ', 'Kwota', 'Data zdarzenia', 'Opis']].iloc[::-1], use_container_width=True, hide_index=True)
