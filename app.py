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

# Funkcja PDF
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
    pdf.cell(95, 10, "GOTOWKA (W KASIE):", 1); pdf.cell(95, 10, f"{s_gotowka:.2f} zl", 1, ln=True)
    pdf.cell(95, 10, "SUMA WYDATKOW:", 1); pdf.cell(95, 10, f"{s_wydatki:.2f} zl", 1, ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(35, 10, "Data", 1); pdf.cell(40, 10, "Typ", 1); pdf.cell(35, 10, "Kwota", 1); pdf.cell(80, 10, "Opis", 1)
    pdf.ln()
    pdf.set_font("Arial", "", 9)
    for i, row in dataframe.iterrows():
        t = str(row['Typ']).replace('ó','o').replace('ś','s').replace('ą','a').replace('ę','e').replace('ł','l')
        o = str(row['Opis']).replace('ó','o').replace('ś','s').replace('ą','a').replace('ę','e').replace('ł','l')
        if o == "nan": o = ""
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
        return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status'])
    def save_data(df): df.to_csv(DB_FILE, index=False)

    if 'data' not in st.session_state: st.session_state.data = load_data()
    df_all = st.session_state.data
    if 'Status' not in df_all.columns: df_all['Status'] = 'Aktywny'
    
    df_active = df_all[df_all['Status'] == 'Aktywny'].copy()
    df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

    s_ogolny = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
    s_wydatki = df_active[df_active['Typ'] == 'Wydatki']['Kwota'].sum()
    s_gotowka = df_active[df_active['Typ'] == 'Gotówka']['Kwota'].sum() - s_wydatki

    st.title("🍕 Panel Rozliczeń")

    # Kolory kafelków - Gotówka zmienia się na czerwoną przy minusie
    color_gotowka = "#fff3cd" if s_gotowka >= 0 else "#f8d7da"
    border_gotowka = "#ffc107" if s_gotowka >= 0 else "#dc3545"
    text_gotowka = "#856404" if s_gotowka >= 0 else "#721c24"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:16px;">{s_ogolny:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b1", use_container_width=True): st.session_state.f = "Przychód ogólny"
    with c2:
        st.markdown(f'<div style="background-color:{color_gotowka}; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid {border_gotowka}; height: 100px;"><span style="color:{text_gotowka}; font-size:11px; font-weight:bold;">GOTÓWKA</span><br><b style="color:{text_gotowka}; font-size:16px;">{s_gotowka:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b2", use_container_width=True): st.session_state.f = "Gotówka"
    with c3:
        st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI</span><br><b style="color:#721c24; font-size:16px;">{s_wydatki:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➖ Dodaj", key="b3", use_container_width=True): st.session_state.f = "Wydatki"

    st.divider()

    if "f" in st.session_state:
        typ = st.session_state.f
        with st.form("form_wpisu", clear_on_submit=True):
            kwota = st.number_input(f"Dodaj: {typ}", min_value=0.0, step=1.0, format="%.2f", value=None, placeholder="Wpisz kwotę...")
            opis = st.text_input("Na co wydano?", key="o") if typ == "Wydatki" else ""
            cz, ca = st.columns(2)
            with cz:
                if st.form_submit_button("ZAPISZ", use_container_width=True):
                    if kwota:
                        n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': typ, 'Kwota': float(kwota), 'Opis': opis, 'Status': 'Aktywny'}
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([n])], ignore_index=True)
                        save_data(st.session_state.data)
                        del st.session_state.f
                        st.rerun()
            with ca:
                if st.form_submit_button("ANULUJ", use_container_width=True):
                    del st.session_state.f
                    st.rerun()

    st.subheader("📂 Historia")
    df_display = df_active[['Data', 'Typ', 'Kwota', 'Opis']].iloc[::-1]
    event = st.dataframe(df_display, use_container_width=True, hide_index=False, on_select="rerun", selection_mode="single-row")
    wybrane = event.selection.rows

    with st.sidebar:
        st.header("⚙️ Opcje")
        if not df_all.empty:
            pdf_now = create_pdf(df_all, s_ogolny, s_gotowka, s_wydatki)
            st.download_button("📄 POBIERZ RAPORT PDF", pdf_now, f"Raport_{datetime.now().strftime('%H%M')}.pdf", "application/pdf", use_container_width=True)
        
        if wybrane:
            orig_idx = df_display.index[wybrane[0]]
            if st.button("🗑️ USUŃ WPIS", type="primary", use_container_width=True):
                st.session_state.data.at[orig_idx, 'Status'] = 'Usunięty'
                save_data(st.session_state.data)
                st.rerun()

        if not df_all.empty:
            st.divider()
            st.warning("ZAMKNIĘCIE (ZEROWANIE)")
            pdf_res = create_pdf(df_all, s_ogolny, s_gotowka, s_wydatki)
            if st.download_button("💾 POBIERZ I PRZYGOTUJ RESET", pdf_res, "ZAMKNIECIE.pdf", "application/pdf", use_container_width=True):
                st.session_state.reset_check = True
            
            if st.session_state.get('reset_check'):
                if st.button("🔥 POTWIERDZAM: ZERUJ", type="primary", use_container_width=True):
                    st.session_state.data = pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status'])
                    save_data(st.session_state.data)
                    st.session_state.reset_check = False
                    st.rerun()
                if st.button("🔙 ANULUJ", use_container_width=True):
                    st.session_state.reset_check = False
                    st.rerun()
