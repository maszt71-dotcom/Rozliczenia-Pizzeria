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

# --- GENERATOR PDF (BEZPIECZNE ZNAKI) ---
def create_pdf(dataframe, s_ogolny, s_gotowka, s_wydatki):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", "B", 14)
    def bezpieczny_tekst(tekst):
        return str(tekst).replace('ą','a').replace('ć','c').replace('ę','e').replace('ł','l').replace('ń','n').replace('ó','o').replace('ś','s').replace('ź','z').replace('ż','z').replace('Ą','A').replace('Ć','C').replace('Ę','E').replace('Ł','L').replace('Ń','N').replace('Ó','O').replace('Ś','S').replace('Ź','Z').replace('Ż','Z')
    pdf.cell(190, 10, bezpieczny_tekst(f"RAPORT FINANSOWY - {datetime.now().strftime('%d.%m.%Y %H:%M')}"), ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Courier", "B", 10)
    pdf.cell(95, 10, "PRZYCHOD OGOLNY:", 1); pdf.cell(95, 10, f"{s_ogolny:.2f} zl", 1, 1, 'R')
    pdf.cell(95, 10, "WYDATKI GOTOWKOWE:", 1); pdf.cell(95, 10, f"{s_wydatki:.2f} zl", 1, 1, 'R')
    pdf.cell(95, 10, "GOTOWKA (W KASIE):", 1); pdf.cell(95, 10, f"{s_gotowka:.2f} zl", 1, 1, 'R')
    pdf.ln(10)
    headers = ["Data", "Typ", "Kwota", "Z dnia", "Opis"]
    cols = [25, 45, 25, 15, 80]
    for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 1)
    pdf.ln()
    pdf.set_font("Courier", "", 8)
    for _, row in dataframe.iterrows():
        pdf.cell(25, 8, bezpieczny_tekst(row['Data']), 1)
        pdf.cell(45, 8, bezpieczny_tekst(row['Typ']), 1)
        pdf.cell(25, 8, f"{row['Kwota']:.2f}", 1)
        pdf.cell(15, 8, bezpieczny_tekst(row['Data zdarzenia']), 1)
        pdf.cell(80, 8, bezpieczny_tekst(row['Opis'])[:45], 1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

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
    
    # --- NOWA LOGIKA OKNA RESETU ---
    @st.dialog("Zamknięcie dnia")
    def final_reset_dialog():
        # ETAP 3: OSTATECZNE PYTANIE
        if st.session_state.get('confirm_step_3', False):
            st.error("❗ CZY NA PEWNO?")
            st.write("Wszystkie dane z kontenerów i historia zostaną usunięte!")
            if st.button("✅ TAK, JESTEM PEWIEN", type="primary", use_container_width=True):
                st.session_state.data = pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])
                save_data(st.session_state.data)
                # Resetujemy wszystkie flagi
                st.session_state.pdf_pobrany_final = False
                st.session_state.confirm_step_3 = False
                st.rerun()
            if st.button("❌ ANULUJ", use_container_width=True):
                st.session_state.confirm_step_3 = False
                st.rerun()

        # ETAP 1 & 2: POBIERANIE I PRZYCISK ZEROWANIA
        else:
            pdf_raw = create_pdf(df_active, s_ogolny, s_gotowka, s_wydatki)
            st.write("Krok 1: Pobierz raport PDF.")
            
            # Pobranie raportu ustawia flagę
            if st.download_button("📄 1. POBIERZ RAPORT PDF", pdf_raw, f"Raport_{datetime.now().strftime('%d_%m')}.pdf", use_container_width=True):
                st.session_state.pdf_pobrany_final = True
            
            st.divider()

            # Przycisk Zeruj uaktywnia się po pobraniu PDF
            if st.session_state.get('pdf_pobrany_final', False):
                if st.button("🔥 2. ZERUJ HISTORIĘ I KONTENERY", type="primary", use_container_width=True):
                    st.session_state.confirm_step_3 = True
                    st.rerun()
            else:
                st.button("2. ZERUJ HISTORIĘ (Pobierz raport)", disabled=True, use_container_width=True)

    # --- KONTENERY DODAWANIA ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:16px;">{s_ogolny:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b1", use_container_width=True):
            @st.dialog("Dodaj Przychód")
            def d1():
                kw = st.number_input("Kwota", min_value=0.0, format="%.2f")
                da = st.date_input("Dzień", datetime.now())
                if st.button("Zapisz"):
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([n])], ignore_index=True)
                    save_data(st.session_state.data); st.rerun()
            d1()
    with c3:
        st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI GOTÓWKOWE</span><br><b style="color:#721c24; font-size:16px;">{s_wydatki:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➖ Dodaj", key="b3", use_container_width=True):
            @st.dialog("Dodaj Wydatek")
            def d3():
                kw = st.number_input("Kwota", min_value=0.0, format="%.2f")
                da = st.date_input("Dzień", datetime.now())
                op = st.text_input("Opis (max 35)", max_chars=35)
                if st.button("Zapisz"):
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([n])], ignore_index=True)
                    save_data(st.session_state.data); st.rerun()
            d3()
    with c2:
        bg_got, brd_got, txt_got = ("#fff3cd", "#ffc107", "#856404") if s_gotowka >= 0 else ("#ff0000", "#8b0000", "#ffffff")
        st.markdown(f'<div style="background-color:{bg_got}; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid {brd_got}; height: 100px;"><span style="color:{txt_got}; font-size:11px; font-weight:bold;">GOTÓWKA</span><br><b style="color:{txt_got}; font-size:16px;">{s_gotowka:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b2", use_container_width=True):
            @st.dialog("Dodaj Gotówkę")
            def d2():
                kw = st.number_input("Kwota", min_value=0.0, format="%.2f")
                da = st.date_input("Dzień", datetime.now())
                if st.button("Zapisz"):
                    n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Gotówka', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([n])], ignore_index=True)
                    save_data(st.session_state.data); st.rerun()
            d2()

    st.divider(); st.subheader("📂 Historia")
    df_h = df_active[['Data', 'Typ', 'Kwota', 'Data zdarzenia', 'Opis']].iloc[::-1]
    if "table_id" not in st.session_state: st.session_state.table_id = 1
    sel = st.dataframe(df_h.style.apply(apply_row_styles, axis=1), use_container_width=True, on_select="rerun", selection_mode="multi-row", key=f"t_{st.session_state.table_id}", column_config={"Data": st.column_config.TextColumn("Data wpisu", width="small"), "Typ": st.column_config.TextColumn("Typ", width="medium"), "Kwota": st.column_config.NumberColumn("Kwota", format="%.2f zł", width="small"), "Data zdarzenia": st.column_config.TextColumn("Z dnia", width="small"), "Opis": st.column_config.TextColumn("Opis", width="medium")})

    with st.sidebar:
        st.header("⚙️ Opcje")
        if sel.selection.rows:
            if st.button("🗑️ USUŃ ZAZNACZONE", type="primary", use_container_width=True):
                st.session_state.data.loc[df_h.index[sel.selection.rows], 'Status'] = 'Usunięty'
                save_data(st.session_state.data); st.session_state.table_id += 1; st.rerun()
        st.divider()
        if st.button("WYLOGUJ", use_container_width=True):
            cookies["is_logged"] = "false"; cookies.save(); st.rerun()
        if not df_active.empty:
            pdf_s = create_pdf(df_active, s_ogolny, s_gotowka, s_wydatki)
            st.download_button("📄 POBIERZ RAPORT PDF", pdf_s, f"Raport_{datetime.now().strftime('%d_%m')}.pdf", use_container_width=True)
            st.divider()
            if st.button("💾 POBIERZ RAPORT I WYCZYŚĆ", use_container_width=True):
                st.session_state.pdf_pobrany_final = False
                st.session_state.confirm_step_3 = False
                final_reset_dialog()
