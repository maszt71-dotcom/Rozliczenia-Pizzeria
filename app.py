import streamlit as st
import pandas as pd
import os
import random
from datetime import datetime
from fpdf import FPDF
from streamlit_cookies_manager import CookieManager

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Rozliczenie Pizzerii", layout="centered", page_icon="🍕")

cookies = CookieManager()
if not cookies.ready():
    st.stop()

MOJE_HASLO = "dup@"

def check_password():
    if cookies.get("is_logged") == "true": return True
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
    pdf.cell(190, 10, "PODSUMOWANIE:", ln=True, align="L")
    pdf.set_fill_color(212, 237, 218); pdf.cell(95, 10, "PRZYCHOD OGOLNY:", 1, 0, 'L', True); pdf.cell(95, 10, f"{s_ogolny:.2f} zl", 1, 1, 'R', True)
    pdf.set_fill_color(248, 215, 218); pdf.cell(95, 10, "WYDATKI GOTOWKOWE:", 1, 0, 'L', True); pdf.cell(95, 10, f"{s_wydatki:.2f} zl", 1, 1, 'R', True)
    pdf.set_fill_color(255, 243, 205); pdf.cell(95, 10, "GOTOWKA (W KASIE):", 1, 0, 'L', True); pdf.cell(95, 10, f"{s_gotowka:.2f} zl", 1, 1, 'R', True)
    pdf.ln(10)
    pdf.set_font("Arial", "B", 9); pdf.set_fill_color(240, 240, 240)
    headers = ["Data wpisu", "Typ", "Kwota", "Z dnia", "Opis"]
    cols = [30, 40, 30, 25, 65]
    for i, h in enumerate(headers): pdf.cell(cols[i], 10, h, 1, 0, 'C', True)
    pdf.ln()
    pdf.set_font("Arial", "", 8)
    for _, row in dataframe.iterrows():
        pdf.cell(30, 10, str(row['Data']), 1)
        pdf.cell(40, 10, str(row['Typ']), 1)
        pdf.cell(30, 10, f"{row['Kwota']:.2f} zl", 1)
        pdf.cell(25, 10, str(row['Data zdarzenia']), 1)
        pdf.cell(65, 10, str(row['Opis']), 1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- STYLE KOLORÓW ---
def apply_row_styles(row):
    color = ''
    if row['Typ'] == 'Przychód ogólny': color = 'background-color: #d4edda'
    elif row['Typ'] == 'Wydatki gotówkowe': color = 'background-color: #f8d7da'
    elif row['Typ'] == 'Gotówka': color = 'background-color: #fff3cd'
    return [color] * len(row)

if check_password():
    DB_FILE = 'finanse_data.csv'
    def load_data():
        if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
        return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])
    def save_data(df): df.to_csv(DB_FILE, index=False)

    if 'data' not in st.session_state: st.session_state.data = load_data()
    
    df_active = st.session_state.data[st.session_state.data['Status'] == 'Aktywny'].copy()
    df_active['Data zdarzenia'] = df_active['Data zdarzenia'].astype(str).str[:5]
    df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

    s_ogolny = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
    s_wydatki = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
    s_gotowka = df_active[df_active['Typ'] == 'Gotówka']['Kwota'].sum() - s_wydatki

    st.title("🍕 Rozliczenie Pizzerii")
    bg_got, brd_got, txt_got = ("#fff3cd", "#ffc107", "#856404") if s_gotowka >= 0 else ("#ff0000", "#8b0000", "#ffffff")

    @st.dialog("Dodaj nowy wpis")
    def add_entry_dialog(typ):
        st.write(f"Kategoria: **{typ}**")
        kwota = st.number_input("Podaj kwotę (zł)", min_value=0.0, step=1.0, format="%.2f", key="nowa_kwota_input", value=None)
        data_wybrana = st.date_input("Dzień zdarzenia", datetime.now())
        
        # OGRANICZENIE ZNAKÓW DO 40 DLA ESTETYKI
        opis = st.text_input("Opis (max 40 znaków)", max_chars=40)
        
        if st.button("ZAPISZ WPIS", type="primary", use_container_width=True):
            if kwota is not None and kwota > 0:
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': typ, 'Kwota': float(kwota), 'Opis': opis, 'Status': 'Aktywny', 'Data zdarzenia': data_wybrana.strftime("%d.%m")}
                st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([n])], ignore_index=True)
                save_data(st.session_state.data); st.rerun()

    @st.dialog("Potwierdzenie usunięcia")
    def confirm_delete_dialog(rows_to_del):
        st.warning(f"Czy usunąć {len(rows_to_del)} zaznaczone wpisy?")
        if st.button("TAK, USUŃ", type="primary", use_container_width=True):
            st.session_state.data.loc[rows_to_del, 'Status'] = 'Usunięty'
            save_data(st.session_state.data)
            st.session_state.table_id = random.randint(0, 999)
            st.rerun()

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

    st.divider(); st.subheader("📂 Historia")
    df_history = df_active[['Data', 'Typ', 'Kwota', 'Data zdarzenia', 'Opis']].iloc[::-1]
    
    if "table_id" not in st.session_state: st.session_state.table_id = 1

    # TABELA ROZCIĄGNIĘTA NA PEŁNĄ SZEROKOŚĆ KONTENERÓW
    selection = st.dataframe(
        df_history.style.apply(apply_row_styles, axis=1),
        use_container_width=True,
        on_select="rerun",
        selection_mode="multi-row",
        key=f"historia_table_{st.session_state.table_id}",
        column_config={
            "Data": st.column_config.TextColumn("Data wpisu", width="medium"),
            "Typ": st.column_config.TextColumn("Typ", width="medium"),
            "Kwota": st.column_config.NumberColumn("Kwota", format="%.2f zł", width="medium"),
            "Data zdarzenia": st.column_config.TextColumn("Z dnia", width="small"),
            "Opis": st.column_config.TextColumn("Opis", width="large")
        }
    )

    with st.sidebar:
        st.header("⚙️ Opcje")
        if selection.selection.rows:
            if st.button("🗑️ USUŃ ZAZNACZONE", type="primary", use_container_width=True):
                confirm_delete_dialog(df_history.index[selection.selection.rows])
        
        st.divider()
        if st.button("WYLOGUJ", use_container_width=True):
            cookies["is_logged"] = "false"; cookies.save(); st.rerun()
            
        if not df_active.empty:
            st.subheader("🏁 Zamknięcie dnia")
            pdf_raw = create_pdf(df_active, s_ogolny, s_gotowka, s_wydatki)
            
            if st.download_button("📄 1. POBIERZ RAPORT PDF", pdf_raw, f"Raport_{datetime.now().strftime('%d_%m')}.pdf", use_container_width=True):
                st.session_state.pdf_pobrany = True

            if not st.session_state.get('pdf_pobrany', False):
                st.info("Pobierz raport, aby odblokować reset.")
                st.button("💾 2. RESETUJ TABELĘ (Zablokowane)", disabled=True, use_container_width=True)
            else:
                if st.button("🔥 2. POTWIERDZAM RESET DNIA", type="primary", use_container_width=True):
                    st.session_state.data = pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])
                    save_data(st.session_state.data)
                    st.session_state.pdf_pobrany = False
                    st.rerun()
