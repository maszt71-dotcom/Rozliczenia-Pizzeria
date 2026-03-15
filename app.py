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

# --- GENERATOR PDF (NAPRAWIONE POLSKIE ZNAKI + KOLORY) ---
def create_pdf(dataframe, s_ogolny, s_gotowka, s_wydatki):
    # Używamy wbudowanej czcionki Courier
    pdf = FPDF()
    pdf.add_page()
    
    # Funkcja do usuwania polskich znaków (aby uniknąć błędu)
    def bezpieczny_tekst(tekst):
        return str(tekst).replace('ą','a').replace('ć','c').replace('ę','e').replace('ł','l').replace('ń','n').replace('ó','o').replace('ś','s').replace('ź','z').replace('ż','z').replace('Ą','A').replace('Ć','C').replace('Ę','E').replace('Ł','L').replace('Ń','N').replace('Ó','O').replace('Ś','S').replace('Ź','Z').replace('Ż','Z')

    # Tytuł
    pdf.set_font("Courier", "B", 14)
    pdf.cell(190, 10, bezpieczny_tekst(f"RAPORT FINANSOWY - {datetime.now().strftime('%d.%m.%Y %H:%M')}"), ln=True, align="C")
    pdf.ln(10)
    
    # --- KOLOROWE PODSUMOWANIE ---
    pdf.set_font("Courier", "B", 10)
    
    # Przychód (Zielony jak kontener)
    pdf.set_fill_color(212, 237, 218) # Tło
    pdf.set_text_color(21, 87, 36)    # Ciemnozielony tekst
    pdf.cell(95, 10, "PRZYCHÓD OGÓLNY:", 1, 0, 'L', True)
    pdf.cell(95, 10, f"{s_ogolny:.2f} zł", 1, 1, 'R', True)
    
    # Wydatki (Czerwony jak kontener)
    pdf.set_fill_color(248, 215, 218) # Tło
    pdf.set_text_color(114, 28, 36)   # Ciemnoczerwony tekst
    pdf.cell(95, 10, "WYDATKI GOTÓWKOWE:", 1, 0, 'L', True)
    pdf.cell(95, 10, f"{s_wydatki:.2f} zł", 1, 1, 'R', True)
    
    # Gotówka (Żółty jak kontener)
    pdf.set_fill_color(255, 243, 205) # Tło
    pdf.set_text_color(133, 100, 4)   # Ciemnożółty tekst
    pdf.cell(95, 10, "GOTÓWKA (W KASIE):", 1, 0, 'L', True)
    pdf.cell(95, 10, f"{s_gotowka:.2f} zł", 1, 1, 'R', True)
    
    # Reset koloru tekstu dla głównej tabeli
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)
    
    # Nagłówki tabeli
    headers = ["Data", "Typ", "Kwota", "Z dnia", "Opis"]
    cols = [25, 45, 25, 15, 80]
    # Szare tło dla nagłówków
    pdf.set_fill_color(240, 240, 240)
    for i, h in enumerate(headers): pdf.cell(cols[i], 8, bezpieczny_tekst(h), 1, 0, 'C', True)
    pdf.ln()
    
    # Dane tabeli (BEZ kolorów wierszy, tylko tło ogólne)
    pdf.set_font("Courier", "", 8)
    for _, row in dataframe.iterrows():
        # Kolor wiersza zależy od typu wpisu (jasne odcienie jak w kontenerach)
        if row['Typ'] == 'Przychód ogólny': pdf.set_fill_color(230, 255, 235)
        elif row['Typ'] == 'Wydatki gotówkowe': pdf.set_fill_color(255, 235, 240)
        else: pdf.set_fill_color(255, 250, 220) # Gotówka i inne
        
        pdf.cell(25, 8, bezpieczny_tekst(row['Data']), 1, 0, 'L', True)
        pdf.cell(45, 8, bezpieczny_tekst(row['Typ']), 1, 0, 'L', True)
        pdf.cell(25, 8, f"{row['Kwota']:.2f}", 1, 0, 'R', True)
        pdf.cell(15, 8, bezpieczny_tekst(row['Data zdarzenia']), 1, 0, 'C', True)
        pdf.cell(80, 8, bezpieczny_tekst(row['Opis'])[:45], 1, 0, 'L', True)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- STYLE KOLORÓW DLA TABELI ---
def apply_row_styles(row):
    color = ''
    if row['Typ'] == 'Przychód ogólny': color = 'background-color: #d4edda; color: #155724'
    elif row['Typ'] == 'Wydatki gotówkowe': color = 'background-color: #f8d7da; color: #721c24'
    elif row['Typ'] == 'Gotówka': color = 'background-color: #fff3cd; color: #856404'
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
    
    # --- LOGIKA DIALOGU RESETU ---
    @st.dialog("Pobierz raport i wyczyść")
    def final_reset_dialog():
        pdf_raw = create_pdf(df_active, s_ogolny, s_gotowka, s_wydatki)
        st.write("Krok 1: Pobierz raport PDF.")
        if st.download_button("📄 1. POBIERZ RAPORT PDF", pdf_raw, f"Raport_{datetime.now().strftime('%d_%m')}.pdf", use_container_width=True):
            st.session_state.pdf_pobrany_final = True
        st.divider()
        if st.session_state.get('pdf_pobrany_final', False):
            if st.button("🔥 2. ZERUJ HISTORIĘ I KONTENERY", type="primary", use_container_width=True):
                st.session_state.pokaz_pytanie = True
        else:
            st.button("2. ZERUJ HISTORIĘ (Pobierz raport)", disabled=True, use_container_width=True)
        if st.session_state.get('pokaz_pytanie', False):
            st.error("❗ JESTEŚ PEWIEN? Danych nie da się odzyskać!")
            if st.button("✅ TAK, JESTEM PEWIEN - CZYŚĆ WSZYSTKO", type="primary", use_container_width=True):
                st.session_state.data = pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])
                save_data(st.session_state.data)
                st.session_state.pdf_pobrany_final = False
                st.session_state.pokaz_pytanie = False
                st.rerun()
            if st.button("❌ ANULUJ"):
                st.session_state.pokaz_pytanie = False
                st.rerun()

    # --- KONTENERY ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:16px;">{s_ogolny:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b1", use_container_width=True):
            @st.dialog("Dodaj Przychód")
            def d1():
                kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None, placeholder="Wpisz kwotę...")
                da = st.date_input("Z dnia", datetime.now())
                if st.button("Zapisz"):
                    if kw:
                        n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([n])], ignore_index=True)
                        save_data(st.session_state.data); st.rerun()
            d1()
    with c3:
        st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI GOTÓWKOWE</span><br><b style="color:#721c24; font-size:16px;">{s_wydatki:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➖ Dodaj", key="b3", use_container_width=True):
            @st.dialog("Dodaj Wydatek")
            def d3():
                kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None, placeholder="Wpisz kwotę...")
                da = st.date_input("Z dnia", datetime.now())
                op = st.text_input("Opis (max 35)", max_chars=35)
                if st.button("Zapisz"):
                    if kw:
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
                kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None, placeholder="Wpisz kwotę...")
                da = st.date_input("Z dnia", datetime.now())
                if st.button("Zapisz"):
                    if kw:
                        n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Gotówka', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([n])], ignore_index=True)
                        save_data(st.session_state.data); st.rerun()
            d2()

    st.divider(); st.subheader("📂 Historia")
    df_h = df_active[['Data', 'Typ', 'Kwota', 'Data zdarzenia', 'Opis']].iloc[::-1]
    if "table_id" not in st.session_state: st.session_state.table_id = 1
    
    # Wyświetlanie tabeli historii Z KOLORAMI WIERSZY
    sel = st.dataframe(
        df_h.style.apply(apply_row_styles, axis=1), 
        use_container_width=True, 
        on_select="rerun", 
        selection_mode="multi-row", 
        key=f"t_{st.session_state.table_id}", 
        column_config={
            "Data": st.column_config.TextColumn("Data wpisu", width="small"), 
            "Typ": st.column_config.TextColumn("Typ", width="medium"), 
            "Kwota": st.column_config.NumberColumn("Kwota", format="%.2f zł", width="small"), 
            "Data zdarzenia": st.column_config.TextColumn("Z dnia", width="small"), 
            "Opis": st.column_config.TextColumn("Opis", width="medium")
        }
    )

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
                st.session_state.pokaz_pytanie = False
                final_reset_dialog()
