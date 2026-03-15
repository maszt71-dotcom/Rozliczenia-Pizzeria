import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF

# --- KONFIGURACJA ---
st.set_page_config(page_title="Pizzeria - Rozliczenia", layout="centered", page_icon="🍕")

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

# Funkcja PDF (czyste nazwy bez nawiasów)
def create_pdf(dataframe, s_ogolny, s_gotowka, s_wydatki):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "RAPORT FINANSOWY PIZZERIA", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(190, 10, "PODSUMOWANIE:", ln=True, align="L", fill=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(95, 10, "PRZYCHOD OGOLNY:", 1); pdf.cell(95, 10, f"{s_ogolny:.2f} zl", 1, ln=True)
    pdf.cell(95, 10, "GOTOWKA:", 1); pdf.cell(95, 10, f"{s_gotowka:.2f} zl", 1, ln=True)
    pdf.cell(95, 10, "WYDATKI:", 1); pdf.cell(95, 10, f"{s_wydatki:.2f} zl", 1, ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(35, 10, "Data", 1); pdf.cell(40, 10, "Typ", 1); pdf.cell(35, 10, "Kwota", 1); pdf.cell(80, 10, "Opis", 1)
    pdf.ln()
    pdf.set_font("Arial", "", 9)
    for i, row in dataframe.iloc[::-1].iterrows():
        t = str(row['Typ']).replace('ó','o').replace('ś','s').replace('ą','a').replace('ę','e').replace('ł','l')
        o = str(row['Opis']).replace('ó','o').replace('ś','s').replace('ą','a').replace('ę','e').replace('ł','l')
        pdf.cell(35, 10, str(row['Data']), 1)
        pdf.cell(40, 10, t, 1)
        pdf.cell(35, 10, f"{row['Kwota']:.2f} zl", 1)
        pdf.cell(80, 10, str(o)[:45], 1)
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
    s_ogolny = df[df['Typ'] == 'Przychód ogólny']['Kwota'].sum()
    s_wydatki = df[df['Typ'] == 'Wydatki']['Kwota'].sum()
    w_gotowka = df[df['Typ'] == 'Gotówka']['Kwota'].sum()
    s_gotowka = w_gotowka - s_wydatki

    st.title("🍕 Panel Rozliczeń")

    # Kafelki
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

    # Formularz
    if "f" in st.session_state:
        typ = st.session_state.f
        with st.form("form_wpisu", clear_on_submit=True):
            kwota_raw = st.text_input(f"Wpisz kwotę ({typ})", placeholder="Wpisz...", key="k")
            opis = st.text_input("Jaki wydatek?", key="o") if typ == "Wydatki" else ""
            if st.form_submit_button("ZAPISZ", use_container_width=True):
                try:
                    k = float(kwota_raw.replace(',', '.'))
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': typ, 'Kwota': k, 'Opis': opis}
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([n])], ignore_index=True)
                    save_data(st.session_state.data)
                    del st.session_state.f
                    st.rerun()
                except: st.error("Błąd kwoty!")
            if st.form_submit_button("ANULUJ", use_container_width=True):
                del st.session_state.f
                st.rerun()

    st.subheader("📂 Historia (kliknij wiersz, aby wybrać)")
    
    # Interaktywna tabela z wybieraniem wierszy
    # dataframe.iloc[::-1] pokazuje najnowsze na górze, ale zachowujemy oryginalne ID do usuwania
    event = st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=False, 
        on_select="rerun", 
        selection_mode="single-row"
    )

    wybrane_wiersze = event.selection.rows

    with st.sidebar:
        st.header("⚙️ Opcje")
        
        # Przycisk usuwania - aktywny tylko gdy coś zaznaczono
        if wybrane_wiersze:
            index_do_usuniecia = wybrane_wiersze[0]
            if st.button("🗑️ USUŃ WPIS", type="primary", use_container_width=True):
                st.session_state.data = st.session_state.data.drop(index_do_usuniecia).reset_index(drop=True)
                save_data(st.session_state.data)
                st.rerun()
        else:
            st.info("Zaznacz wiersz w tabeli, aby go usunąć.")

        if not df.empty:
            pdf_data = create_pdf(df, s_ogolny, s_gotowka, s_wydatki)
            st.download_button("📄 Pobierz PDF", pdf_data, "raport.pdf", "application/pdf", use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Pobierz CSV", csv, "dane.csv", "text/csv", use_container_width=True)
