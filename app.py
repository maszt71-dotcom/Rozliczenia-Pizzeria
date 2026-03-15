import streamlit as st
import pandas as pd
import os
import random
from datetime import datetime
from fpdf import FPDF
from streamlit_cookies_manager import CookieManager

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Rozliczenie Pizzerii", 
    layout="centered", 
    page_icon="🍕" 
)

# Manager ciasteczek
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

# --- GENERATOR PDF ---
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
        pdf.cell(70, 10, str(row['Opis'])[:45] if str(row['Opis']) != "nan" else "", 1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

if check_password():
    DB_FILE = 'finanse_data.csv'
    
    def load_data():
        if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
        return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])
    
    def save_data(df): df.to_csv(DB_FILE, index=False)

    if 'data' not in st.session_state: st.session_state.data = load_data()
    df_all = st.session_state.data
    
    if 'Status' not in df_all.columns: df_all['Status'] = 'Aktywny'
    if 'Data zdarzenia' not in df_all.columns: df_all['Data zdarzenia'] = df_all['Data']
    
    df_active = df_all[df_all['Status'] == 'Aktywny'].copy()
    df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

    # Obliczenia
    s_ogolny = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
    s_wydatki = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
    s_gotowka = df_active[df_active['Typ'] == 'Gotówka']['Kwota'].sum() - s_wydatki

    st.title("🍕 Rozliczenie Pizzerii")

    # Kolory kafli gotówki
    bg_got, brd_got, txt_got = ("#fff3cd", "#ffc107", "#856404") if s_gotowka >= 0 else ("#ff0000", "#8b0000", "#ffffff")

    @st.dialog("Dodaj nowy wpis")
    def add_entry_dialog(typ):
        st.write(f"Kategoria: **{typ}**")
        kwota = st.number_input("Podaj kwotę (zł)", min_value=0.0, step=1.0, format="%.2f", key="nowa_kwota_input", value=None)
        etykieta_daty = "Data wydatku" if typ == "Wydatki gotówkowe" else "Data przychodu"
        data_wybrana = st.date_input(etykieta_daty, datetime.now())
        opis = st.text_input("Opis wydatku")
        
        if st.button("ZAPISZ WPIS", type="primary", use_container_width=True):
            if kwota is not None and kwota > 0:
                data_systemowa = datetime.now().strftime("%d.%m %H:%M")
                data_zdarzenia = data_wybrana.strftime("%d.%m")
                n = {'Data': data_systemowa, 'Typ': typ, 'Kwota': float(kwota), 'Opis': opis, 'Status': 'Aktywny', 'Data zdarzenia': data_zdarzenia}
                st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([n])], ignore_index=True)
                save_data(st.session_state.data)
                st.rerun()
            else:
                st.error("Wpisz kwotę!")

    # Kafelki
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:16px;">{s_ogolny:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b1", use_container_width=True): add_entry_dialog("Przychód ogólny")
    with c3:
        st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI GOTÓWKOWE</span><br><b style="color:#721c24; font-size:16px;">{s_wydatki:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➖ Dodaj", key="b3", use_container_width=True): add_entry_dialog("Wydatki gotówkowe")
    with c2:
        st.markdown(f'<div style="background-color:{bg_got}; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid {brd_got}; height: 100px;"><span style="color:{txt_got}; font-size:11px; font-weight:bold;">GOTÓWKA</span><br><b style="color:{txt_got}; font-size:16px;">{s_gotowka:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b2", use_container_width=True): add_entry_dialog("Gotówka")

    st.divider()
    st.subheader("📂 Historia")

    # --- TABELA HTML (SZEROKOŚCI I ZAWJANIE) ---
    df_h = df_active[['Data', 'Typ', 'Kwota', 'Data zdarzenia', 'Opis']].iloc[::-1].copy()
    
    table_style = """
    <style>
        .pizzeria-table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px; }
        .pizzeria-table th { background-color: #f0f2f6; padding: 8px; border: 1px solid #ddd; text-align: left; }
        .pizzeria-table td { padding: 8px; border: 1px solid #ddd; word-wrap: break-word; vertical-align: top; }
        .col-data { width: 90px; }
        .col-typ { width: 125px; }
        .col-kwota { width: 100px; }
        .col-zdnia { width: 75px; }
        .row-przychod { background-color: #d4edda; }
        .row-wydatek { background-color: #f8d7da; }
        .row-gotowka { background-color: #fff3cd; }
    </style>
    """

    html_table = f'{table_style}<table class="pizzeria-table"><tr>'
    html_table += '<th class="col-data">Data wpisu</th><th class="col-typ">Typ</th><th class="col-kwota">Kwota</th><th class="col-zdnia">Z dnia</th><th>Opis</th></tr>'

    for _, row in df_h.iterrows():
        r_c = "row-przychod" if row['Typ'] == "Przychód ogólny" else "row-wydatek" if row['Typ'] == "Wydatki gotówkowe" else "row-gotowka"
        html_table += f'<tr class="{r_c}"><td>{row["Data"]}</td><td>{row["Typ"]}</td><td>{row["Kwota"]:,.2f} zł</td><td>{row["Data zdarzenia"]}</td><td>{row["Opis"] if str(row["Opis"]) != "nan" else ""}</td></tr>'
    
    html_table += "</table>"
    st.markdown(html_table, unsafe_allow_html=True)

    if not df_active.empty:
        st.write("")
        if st.button("🗑️ USUŃ OSTATNI WPIS", use_container_width=True):
            st.session_state.data.at[df_active.index[-1], 'Status'] = 'Usunięty'
            save_data(st.session_state.data)
            st.rerun()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Opcje")
        if st.button("WYLOGUJ", use_container_width=True):
            cookies["is_logged"] = "false"
            cookies.save()
            st.rerun()
        if not df_active.empty:
            pdf_now = create_pdf(df_active, s_ogolny, s_gotowka, s_wydatki)
            st.download_button("📄 POBIERZ RAPORT PDF", pdf_now, f"Raport_{datetime.now().strftime('%d_%m')}.pdf", "application/pdf", use_container_width=True)
            st.divider()
            if st.button("💾 PRZYGOTUJ RESET DNIA", use_container_width=True): st.session_state.reset_check = True
            if st.session_state.get('reset_check'):
                if st.button("🔥 POTWIERDZAM: ZERUJ", type="primary", use_container_width=True):
                    st.session_state.data = pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])
                    save_data(st.session_state.data)
                    st.session_state.reset_check = False
                    st.rerun()
