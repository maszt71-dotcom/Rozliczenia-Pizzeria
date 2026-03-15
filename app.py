import streamlit as st
import pandas as pd
import os
import random
from datetime import datetime
from fpdf import FPDF
from streamlit_cookies_manager import CookieManager

# --- KONFIGURACJA ---
st.set_page_config(page_title="Rozliczenie Pizzerii", layout="centered", page_icon="🍕")

cookies = CookieManager()
if not cookies.ready():
    st.stop()

MOJE_HASLO = "dup@"

def check_password():
    if cookies.get("is_logged") == "true":
        return True
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

# --- GENERATOR PDF (Z POPRAWIONĄ KOLEJNOŚCIĄ) ---
def create_pdf(dataframe, s_ogolny, s_gotowka, s_wydatki):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, f"RAPORT FINANSOWY - {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(190, 10, "PODSUMOWANIE:", ln=True, align="L", fill=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(95, 10, "PRZYCHOD OGOLNY:", 1); pdf.cell(95, 10, f"{s_ogolny:.2f} zl", 1, ln=True)
    pdf.cell(95, 10, "WYDATKI GOTOWKOWE:", 1); pdf.cell(95, 10, f"{s_wydatki:.2f} zl", 1, ln=True)
    pdf.cell(95, 10, "GOTOWKA (W KASIE):", 1); pdf.cell(95, 10, f"{s_gotowka:.2f} zl", 1, ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", "B", 9)
    cols = [30, 35, 30, 25, 70]
    headers = ["Data wpisu", "Typ", "Kwota", "Z dnia", "Opis"]
    for i, h in enumerate(headers): pdf.cell(cols[i], 10, h, 1)
    pdf.ln()
    pdf.set_font("Arial", "", 8)
    for _, row in dataframe.iterrows():
        pdf.cell(30, 10, str(row['Data']), 1)
        pdf.cell(35, 10, str(row['Typ'])[:20], 1)
        pdf.cell(30, 10, f"{row['Kwota']:.2f} zl", 1)
        pdf.cell(25, 10, str(row['Data zdarzenia']), 1)
        pdf.cell(70, 10, str(row['Opis'])[:45], 1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

if check_password():
    DB_FILE = 'finanse_data.csv'
    if 'data' not in st.session_state:
        st.session_state.data = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])
    
    df_active = st.session_state.data[st.session_state.data['Status'] == 'Aktywny'].copy()
    df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

    s_ogolny = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
    s_wydatki = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
    s_gotowka = df_active[df_active['Typ'] == 'Gotówka']['Kwota'].sum() - s_wydatki

    st.title("🍕 Rozliczenie Pizzerii")

    # Sekcja dodawania (Kafelki)
    c1, c2, c3 = st.columns(3)
    # ... (Tutaj Twoja istniejąca logika kafelków i @st.dialog add_entry_dialog) ...

    st.divider()
    st.subheader("📂 Historia")

    # --- TWORZENIE TABELI HTML DLA IDEALNYCH SZEROKOŚCI ---
    df_h = df_active[['Data', 'Typ', 'Kwota', 'Data zdarzenia', 'Opis']].iloc[::-1].copy()
    
    # Styl CSS dla tabeli
    table_style = """
    <style>
        .pizzeria-table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; }
        .pizzeria-table th { background-color: #f0f2f6; padding: 10px; border: 1px solid #ddd; text-align: left; }
        .pizzeria-table td { padding: 10px; border: 1px solid #ddd; word-wrap: break-word; }
        .col-data { width: 100px; }
        .col-typ { width: 140px; }
        .col-kwota { width: 110px; }
        .col-zdnia { width: 80px; }
        .row-przychod { background-color: #d4edda; }
        .row-wydatek { background-color: #f8d7da; }
        .row-gotowka { background-color: #fff3cd; }
    </style>
    """

    html_table = f'{table_style}<table class="pizzeria-table"><tr>'
    html_table += '<th class="col-data">Data wpisu</th><th class="col-typ">Typ</th><th class="col-kwota">Kwota</th><th class="col-zdnia">Z dnia</th><th>Opis</th></tr>'

    for _, row in df_h.iterrows():
        row_class = "row-przychod" if row['Typ'] == "Przychód ogólny" else "row-wydatek" if row['Typ'] == "Wydatki gotówkowe" else "row-gotowka"
        html_table += f'<tr class="{row_class}">'
        html_table += f'<td>{row["Data"]}</td><td>{row["Typ"]}</td><td>{row["Kwota"]:,.2f} zł</td><td>{row["Data zdarzenia"]}</td><td>{row["Opis"] if str(row["Opis"]) != "nan" else ""}</td></tr>'
    
    html_table += "</table>"
    st.markdown(html_table, unsafe_allow_html=True)

    # Przycisk usuwania ostatniego wpisu
    if not df_active.empty:
        st.write("")
        if st.button("🗑️ USUŃ OSTATNI WPIS", use_container_width=True):
            st.session_state.data.at[df_active.index[-1], 'Status'] = 'Usunięty'
            st.session_state.data.to_csv(DB_FILE, index=False)
            st.rerun()
