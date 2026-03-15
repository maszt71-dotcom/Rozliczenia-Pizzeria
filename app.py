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

# Funkcja tworząca PDF z podsumowaniem na górze
def create_pdf(dataframe, s_ogolny, s_gotowka, s_wydatki):
    pdf = FPDF()
    pdf.add_page()
    
    # Nagłówek
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "RAPORT FINANSOWY PIZZERIA", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 7, f"Data wygenerowania: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)
    
    # SEKCJA PODSUMOWANIA NA GÓRZE PDF
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(190, 10, "PODSUMOWANIE STANU:", ln=True, align="L", fill=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(95, 10, f"PRZYCHOD OGOLNY (Terminal/Inne):", 1)
    pdf.cell(95, 10, f"{s_ogolny:.2f} zl", 1, ln=True)
    pdf.cell(95, 10, f"STAN GOTOWKI (W kasie):", 1)
    pdf.cell(95, 10, f"{s_gotowka:.2f} zl", 1, ln=True)
    pdf.cell(95, 10, f"SUMA WYDATKOW:", 1)
    pdf.cell(95, 10, f"{s_wydatki:.2f} zl", 1, ln=True)
    pdf.ln(10)
    
    # TABELA Z HISTORIĄ
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "HISTORIA WSZYSTKICH WPISOW:", ln=True, align="L")
    
    # Nagłówki tabeli
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(35, 10, "Data", 1, 0, 'C', True)
    pdf.cell(40, 10, "Typ", 1, 0, 'C', True)
    pdf.cell(35, 10, "Kwota", 1, 0, 'C', True)
    pdf.cell(80, 10, "Opis / Wydatek", 1, 0, 'C', True)
    pdf.ln()
    
    # Dane (bez polskich znaków dla PDF)
    pdf.set_font("Arial", "", 9)
    for i, row in dataframe.iloc[::-1].iterrows():
        t = str(row['Typ']).replace('ó','o').replace('ś','s').replace('ą','a').replace('ę','e').replace('ó','o').replace('ł','l')
        o = str(row['Opis']).replace('ó','o').replace('ś','s').replace('ą','a').replace('ę','e').replace('ó','o').replace('ł','l')
        if o == "nan" or o == "": o = "-"
        
        pdf.cell(35, 10, str(row['Data']), 1)
        pdf.cell(40, 10, t, 1)
        pdf.cell(35, 10, f"{row['Kwota']:.2f} zl", 1)
        pdf.cell(80, 10, o[:45], 1)
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

    # Obliczenia do kafelków i raportu
    s_ogolny = df[df['Typ'] == 'Przychód ogólny']['Kwota'].sum()
    s_wydatki = df[df['Typ'] == 'Wydatki']['Kwota'].sum()
    w_gotowka = df[df['Typ'] == 'Gotówka']['Kwota'].sum()
    s_gotowka = w_gotowka - s_wydatki

    st.title("🍕 Panel Rozliczeń")

    # Kafelki na górze aplikacji
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:16px;">{s_ogolny:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b1", use_container_width=True): st.session_state.f = "Przychód ogólny"
    with c2:
        st.markdown(f'<div style="background-color:#fff3cd; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #ffc107; height: 100px;"><span style="color:#856404; font-size:11px; font-weight:bold;">GOTÓWKA</span><br><b style="color:#856404; font-size:16px;">{s_gotowka:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b2", use_container_width=True): st.session_state.f = "Gotówka"
    with c3:
        st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI</span><br><b style="color:#721c24; font-size:16px;">{s_wydatki:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➖ Dodaj", key="b3", use_container_width=True): st.session_state.f = "Wydatki"

    st.divider()

    # Formularz wpisu
    if "f" in st.session_state:
        typ = st.session_state.f
        with st.form("form_wpisu", clear_on_submit=True):
            kwota_raw = st.text_input(f"Wpisz kwotę ({typ})", placeholder="Wpisz tutaj...", key="k")
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
                    except: st.error("Wpisz poprawną kwotę!")
            with c_c:
                if st.form_submit_button("ANULUJ", use_container_width=True):
                    del st.session_state.f
                    st.rerun()

    st.subheader("📂 Historia")
    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)

    with st.sidebar:
        st.header("⚙️ Opcje")
        if not df.empty:
            # Przycisk PDF z wyliczonymi sumami
            pdf_data = create_pdf(df, s_ogolny, s_gotowka, s_wydatki)
            st.download_button("📄 Pobierz Raport PDF", pdf_data, "raport_pizzeria.pdf", "application/pdf", use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Pobierz Plik CSV", csv, "dane.csv", "text/csv", use_container_width=True)
        
        if st.button("Cofnij ostatni wpis"):
            if not st.session_state.data.empty:
                st.session_state.data = st.session_state.data.drop(st.session_state.data.index[-1])
                save_data(st.session_state.data)
                st.rerun()
