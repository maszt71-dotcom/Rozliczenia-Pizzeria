import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF

# --- KONFIGURACJA ---
st.set_page_config(page_title="Pizzeria - Rozliczenia", layout="centered", page_icon="🍕")

# Hasło dostępu
MOJE_HASLO = "1234"

def check_password():
    if "password_correct" not in st.session_state:
        st.title("🍕 System Pizzerii")
        wpisane_haslo = st.text_input("Podaj hasło dostępu", type="password")
        if st.button("ZALOGUJ SIĘ", use_container_width=True):
            if wpisane_haslo == MOJE_HASLO:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Błędne hasło")
        return False
    return True

# Funkcja tworząca PDF (z polskimi znakami zamienionymi na standardowe dla bezpieczeństwa)
def create_pdf(dataframe):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Raport Finansowy Pizzeria", ln=True, align="C")
    pdf.ln(10)
    
    # Nagłówki
    pdf.set_font("Arial", "B", 10)
    pdf.cell(35, 10, "Data", 1)
    pdf.cell(40, 10, "Typ", 1)
    pdf.cell(35, 10, "Kwota", 1)
    pdf.cell(80, 10, "Opis", 1)
    pdf.ln()
    
    # Wiersze danych
    pdf.set_font("Arial", "", 10)
    for i, row in dataframe.iloc[::-1].iterrows():
        # Usuwamy polskie znaki w PDF, aby uniknąć błędów czcionki
        txt_typ = str(row['Typ']).replace('ó','o').replace('ś','s').replace('ą','a').replace('ę','e')
        txt_opis = str(row['Opis']).replace('ó','o').replace('ś','s').replace('ą','a').replace('ę','e')
        
        pdf.cell(35, 10, str(row['Data']), 1)
        pdf.cell(40, 10, txt_typ, 1)
        pdf.cell(35, 10, f"{row['Kwota']:.2f} zl", 1)
        pdf.cell(80, 10, txt_opis[:40], 1)
        pdf.ln()
    
    return pdf.output(dest='S').encode('latin-1')

if check_password():
    DB_FILE = 'finanse_data.csv'
    def load_data():
        if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
        return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis'])
    def save_data(df): df.to_csv(DB_FILE, index=False)

    if 'data' not in st.session_state: st.session_state.data = load_data()
    df = st.session_state.data
    df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)

    # Obliczenia
    suma_ogolny = df[df['Typ'] == 'Przychód ogólny']['Kwota'].sum()
    suma_wydatkow = df[df['Typ'] == 'Wydatki']['Kwota'].sum()
    wplaty_gotowka = df[df['Typ'] == 'Gotówka']['Kwota'].sum()
    stan_gotowki = wplaty_gotowka - suma_wydatkow

    st.title("🍕 Panel Rozliczeń")

    # Kafelki
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:16px;">{suma_ogolny:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b1", use_container_width=True): st.session_state.f = "Przychód ogólny"
    with c2:
        st.markdown(f'<div style="background-color:#fff3cd; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #ffc107; height: 100px;"><span style="color:#856404; font-size:11px; font-weight:bold;">GOTÓWKA</span><br><b style="color:#856404; font-size:16px;">{stan_gotowki:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b2", use_container_width=True): st.session_state.f = "Gotówka"
    with c3:
        st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI</span><br><b style="color:#721c24; font-size:16px;">{suma_wydatkow:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➖ Dodaj", key="b3", use_container_width=True): st.session_state.f = "Wydatki"

    st.divider()

    # Formularz
    if "f" in st.session_state:
        typ = st.session_state.f
        with st.form("form_wpisu", clear_on_submit=True):
            kwota_raw = st.text_input(f"Wpisz kwotę ({typ})", placeholder="0.00", key="k")
            opis = st.text_input("Jaki wydatek?", key="o") if typ == "Wydatki" else ""
            c_s, c_c = st.columns(2)
            with c_s:
                if st.form_submit_button("ZAPISZ", use_container_width=True):
                    try:
                        k = float(kwota_raw.replace(',', '.'))
                        n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': typ, 'Kwota': k, 'Opis': opis}
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([n])], ignore_index=True)
                        save_data(st.session_state.data)
                        del st.session_state.f
                        st.rerun()
                    except: st.error("Błędna kwota!")
            with c_c:
                if st.form_submit_button("ANULUJ", use_container_width=True):
                    del st.session_state.f
                    st.rerun()

    st.subheader("📂 Historia")
    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)

    with st.sidebar:
        st.header("⚙️ Opcje")
        if st.button("Cofnij ostatni wpis"):
            if not st.session_state.data.empty:
                st.session_state.data = st.session_state.data.drop(st.session_state.data.index[-1])
                save_data(st.session_state.data)
                st.rerun()
        
        if not df.empty:
            pdf_data = create_pdf(df)
            st.download_button("📄 Pobierz Raport PDF", pdf_data, "raport_pizzeria.pdf", "application/pdf", use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Pobierz Plik CSV", csv, "dane.csv", "text/csv", use_container_width=True)
