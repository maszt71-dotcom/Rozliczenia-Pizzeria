import streamlit as st
import pandas as pd
import os
import random
from datetime import datetime
from fpdf import FPDF

# --- KONFIGURACJA ---
st.set_page_config(
    page_title="Rozliczenie Pizzerii", 
    layout="centered", 
    page_icon="favicon.png" 
)

# Hasło dostępu
MOJE_HASLO = "dup@"

def check_password():
    if "password_correct" not in st.session_state:
        st.title("🍕 Rozliczenie Pizzerii")
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
    pdf.set_font("Arial", "B", 14)
    data_gen = datetime.now().strftime("%d.%m.%Y %H:%M")
    pdf.cell(190, 10, f"RAPORT FINANSOWY - {data_gen}", ln=True, align="C")
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

    st.title("🍕 Rozliczenie Pizzerii")

    if s_gotowka >= 0:
        bg_got, brd_got, txt_got = "#fff3cd", "#ffc107", "#856404"
    else:
        bg_got, brd_got, txt_got = "#ff0000", "#8b0000", "#ffffff"

    @st.dialog("Dodaj nowy wpis")
    def add_entry_dialog(typ):
        st.write(f"Kategoria: **{typ}**")
        kwota = st.number_input("Podaj kwotę (zł)", min_value=0.0, step=1.0, format="%.2f", value=None)
        opis = st.text_input("Opis wydatku") if typ == "Wydatki" else ""
        if st.button("ZAPISZ WPIS", type="primary", use_container_width=True):
            if kwota:
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': typ, 'Kwota': float(kwota), 'Opis': opis, 'Status': 'Aktywny'}
                st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([n])], ignore_index=True)
                save_data(st.session_state.data)
                st.rerun()

    @st.dialog("Usuń wpis")
    def delete_entry_dialog(row_idx):
        row = df_display.iloc[row_idx]
        st.warning(f"Czy usunąć: {row['Typ']} - {row['Kwota']:.2f} zł?")
        if st.button("🔥 POTWIERDZAM: USUŃ", type="primary", use_container_width=True):
            orig_idx = df_display.index[row_idx]
            st.session_state.data.at[orig_idx, 'Status'] = 'Usunięty'
            save_data(st.session_state.data)
            st.rerun()
        if st.button("🔙 NIE USUWAJ", use_container_width=True):
            st.rerun()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:16px;">{s_ogolny:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b1", use_container_width=True): add_entry_dialog("Przychód ogólny")
    with c2:
        st.markdown(f'<div style="background-color:{bg_got}; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid {brd_got}; height: 100px;"><span style="color:{txt_got}; font-size:11px; font-weight:bold;">GOTÓWKA</span><br><b style="color:{txt_got}; font-size:16px;">{s_gotowka:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b2", use_container_width=True): add_entry_dialog("Gotówka")
    with c3:
        st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI</span><br><b style="color:#721c24; font-size:16px;">{s_wydatki:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➖ Dodaj", key="b3", use_container_width=True): add_entry_dialog("Wydatki")

    st.divider()
    st.subheader("📂 Historia")
    df_display = df_active[['Data', 'Typ', 'Kwota', 'Opis']].iloc[::-1]
    
    if "table_id" not in st.session_state or st.session_state.get('reset_table', False):
        st.session_state.table_id = random.randint(0, 100000)
        st.session_state.reset_table = False

    event = st.dataframe(
        df_display, 
        use_container_width=True, 
        hide_index=False, 
        on_select="rerun", 
        selection_mode="single-row",
        key=f"tabela_{st.session_state.table_id}"
    )
    
    if event.selection.rows:
        st.session_state.reset_table = True
        delete_entry_dialog(event.selection.rows[0])

    with st.sidebar:
        st.header("⚙️ Opcje")
        if not df_all.empty:
            pdf_now = create_pdf(df_all, s_ogolny, s_gotowka, s_wydatki)
            st.download_button("📄 POBIERZ RAPORT PDF", pdf_now, f"Raport_{datetime.now().strftime('%d_%m')}.pdf", "application/pdf", use_container_width=True)
            st.divider()
            st.warning("ZAMKNIĘCIE DNIA")
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
