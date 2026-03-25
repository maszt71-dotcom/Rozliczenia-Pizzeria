import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime
from streamlit_cookies_manager import CookieManager

# --- FUNKCJA NAPRAWCZA DLA PDF ---
def pdf_safe(txt):
    if not txt: return ""
    rep = {"ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ź":"z","ż":"z",
           "Ą":"A","Ć":"C","Ę":"E","Ł":"L","Ń":"N","Ó":"O","Ś":"S","Ź":"Z","Ż":"Z"}
    t = str(txt)
    for k, v in rep.items(): t = t.replace(k, v)
    return t.encode('ascii', 'ignore').decode('ascii')

# --- 1. KONFIGURACJA I LOGOWANIE ---
st.set_page_config(page_title="Pizzeria", layout="wide")

cookies = CookieManager()
if not cookies.ready():
    st.stop()

if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    haslo = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        if haslo == "dup@":
            cookies["is_logged"] = "true"
            cookies.save()
            st.rerun()
    st.stop()

# --- 2. DANE ---
DB_FILE = 'finanse_data.csv'

def load_data():
    if os.path.exists(DB_FILE): 
        df = pd.read_csv(DB_FILE)
    else: 
        df = pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])
    return df

def save_data(df):
    df.to_csv(DB_FILE, index=False)

data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].astype(str).str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- 3. GENERATOR PDF ---
def create_pdf(df, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, pdf_safe(f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m.%Y %H:%M')}"), ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, pdf_safe(f"Przychod: {s_og:.2f} zl | Gotowka: {s_got:.2f} zl | Wydatki: {s_wyd:.2f} zl"), ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", size=10)
    for _, row in df.iterrows():
        linia = f"{row['Data zdarzenia']} | {row['Typ']} | {row['Kwota']:.2f} zl | {row['Opis']}"
        pdf.cell(0, 10, pdf_safe(linia), ln=True, border=1)
    return bytes(pdf.output())

# --- 4. WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:15px; border-radius:10px; text-align:center;">Przychód: <b>{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="p"):
        st.session_state.s = "P" if getattr(st.session_state, "s", "") != "P" else ""
        st.rerun()
    
    if getattr(st.session_state, "s", "") == "P":
        with st.container(border=True):
            d_p = st.date_input("Data zdarzenia", datetime.now(), key="date_p")
            kw_p = st.number_input("Kwota", min_value=0.0, step=1.0, key="val_p")
            if st.button("ZAPISZ", key="save_p"):
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw_p), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_p.strftime("%d.%m")}
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                st.session_state.s = ""; st.rerun()

with c2:
    st.markdown(f'<div style="background-color:#fff3cd; padding:15px; border-radius:10px; text-align:center;">Gotówka: <b>{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="g"):
        st.session_state.s = "G" if getattr(st.session_state, "s", "") != "G" else ""
        st.session_state.os = None
        st.rerun()
    
    if getattr(st.session_state, "s", "") == "G":
        with st.container(border=True):
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            if not getattr(st.session_state, "os", None):
                for o in osoby:
                    if st.button(o, key=f"os_{o}"): 
                        st.session_state.os = o
                        st.rerun()
            else:
                st.write(f"Wybrano: **{st.session_state.os}**")
                d_g = st.date_input("Data zdarzenia", datetime.now(), key="date_g")
                kw_g = st.number_input(f"Kwota", min_value=0.0, step=1.0, key="val_g")
                c_save, c_back = st.columns(2)
                with c_save:
                    if st.button("ZAPISZ G", use_container_width=True):
                        n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {st.session_state.os}", 'Kwota': float(kw_g), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': d_g.strftime("%d.%m")}
                        save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                        st.session_state.s = ""; st.session_state.os = None; st.rerun()
                with c_back:
                    if st.button("COFNIJ", use_container_width=True): 
                        st.session_state.os = None
                        st.rerun()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:15px; border-radius:10px; text-align:center;">Wydatki: <b>{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ DODAJ", key="w"):
        st.session_state.s = "W" if getattr(st.session_state, "s", "") != "W" else ""
        st.rerun()
    
    if getattr(st.session_state, "s", "") == "W":
        with st.container(border=True):
            d_w = st.date_input("Data zdarzenia", datetime.now(), key="date_w")
            kw_w = st.number_input("Kwota", min_value=0.0, step=1.0, key="val_w")
            op_w = st.text_input("Opis", key="desc_w")
            if st.button("ZAPISZ W", key="save_w"):
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw_w), 'Opis': op_w, 'Status': 'Aktywny', 'Data zdarzenia': d_w.strftime("%d.%m")}
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                st.session_state.s = ""; st.rerun()

# --- 5. PASEK BOCZNY ---
with st.sidebar:
    st.header("⚙️ Menu")
    st.download_button("📥 Pobierz CSV", data=df_active.to_csv(index=False).encode('utf-8'), file_name="raport.csv", use_container_width=True)
    st.download_button("📥 Pobierz PDF", data=create_pdf(df_active, s_og, s_got, s_wyd), file_name="raport.pdf", use_container_width=True)
    
    if st.button("🗑️ USUŃ HISTORIĘ", type="primary", use_container_width=True):
        full = load_data()
        full.loc[full["Status"] == "Aktywny", "Status"] = "Archiwum"
        save_data(full)
        st.rerun()

st.divider()
if not df_active.empty:
    show_df = df_active[['Data zdarzenia', 'Typ', 'Kwota', 'Opis']].iloc[::-1].copy()
    show_df['Kwota'] = show_df['Kwota'].map(lambda x: f"{x:,.2f} zł")
    st.dataframe(show_df, use_container_width=True, hide_index=True)
else:
    st.info("Brak aktywnych danych.")
