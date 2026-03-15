import streamlit as st
import pandas as pd
import os
from datetime import datetime

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

if check_password():
    DB_FILE = 'finanse_data.csv'

    def load_data():
        if os.path.exists(DB_FILE):
            return pd.read_csv(DB_FILE)
        return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis'])

    def save_data(df):
        df.to_csv(DB_FILE, index=False)

    if 'data' not in st.session_state:
        st.session_state.data = load_data()

    df = st.session_state.data
    df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)

    # Logika obliczeń
    suma_przychodu_ogolnego = df[df['Typ'] == 'Przychód ogólny']['Kwota'].sum()
    suma_wydatkow = df[df['Typ'] == 'Wydatki']['Kwota'].sum()
    wplaty_gotowka = df[df['Typ'] == 'Gotówka']['Kwota'].sum()
    stan_gotowki = wplaty_gotowka - suma_wydatkow

    st.title("🍕 Panel Rozliczeń")

    # --- KAFELKI NA GÓRZE ---
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;">
        <span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br>
        <b style="color:#155724; font-size:16px;">{suma_przychodu_ogolnego:,.2f} zł</b></div>""", unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="btn_ogolny", use_container_width=True):
            st.session_state.pokaz_formularz = "Przychód ogólny"

    with col2:
        st.markdown(f"""<div style="background-color:#fff3cd; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #ffc107; height: 100px;">
        <span style="color:#856404; font-size:11px; font-weight:bold;">GOTÓWKA</span><br>
        <b style="color:#856404; font-size:16px;">{stan_gotowki:,.2f} zł</b></div>""", unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="btn_gotowka", use_container_width=True):
            st.session_state.pokaz_formularz = "Gotówka"

    with col3:
        st.markdown(f"""<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;">
        <span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI</span><br>
        <b style="color:#721c24; font-size:16px;">{suma_wydatkow:,.2f} zł</b></div>""", unsafe_allow_html=True)
        if st.button("➖ Dodaj", key="btn_wydatki", use_container_width=True):
            st.session_state.pokaz_formularz = "Wydatki"

    st.divider()

    # --- DYNAMICZNY FORMULARZ ---
    if "pokaz_formularz" in st.session_state:
        typ_wpisu = st.session_state.pokaz_formularz
        st.subheader(f"Wprowadź: {typ_wpisu}")
        
        with st.form("formularz_wpisu", clear_on_submit=True):
            # Text_input zamiast number_input, aby pole było puste przy kliknięciu
            kwota_raw = st.text_input("Podaj kwotę (zł)", placeholder="Wpisz kwotę...", key="input_kwota")
            
            opis_final = ""
            if typ_wpisu == "Wydatki":
                opis_final = st.text_input("Jaki wydatek?", key="input_opis")
            
            c_save, c_cancel = st.columns(2)
            with c_save:
                if st.form_submit_button("ZAPISZ", use_container_width=True):
                    try:
                        kwota_clean = float(kwota_raw.replace(',', '.'))
                        if kwota_clean > 0:
                            nowy = {
                                'Data': datetime.now().strftime("%d.%m %H:%M"), 
                                'Typ': typ_wpisu, 
                                'Kwota': kwota_clean, 
                                'Opis': opis_final
                            }
                            st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([nowy])], ignore_index=True)
                            save_data(st.session_state.data)
                            del st.session_state.pokaz_formularz
                            st.rerun()
                        else:
                            st.error("Wpisz kwotę większą od zera!")
                    except ValueError:
                        st.error("Błędna kwota! Użyj tylko cyfr.")
            with c_cancel:
                if st.form_submit_button("ANULUJ", use_container_width=True):
                    del st.session_state.pokaz_formularz
                    st.rerun()

    # --- HISTORIA ---
    st.subheader("📂 Historia wpisów")
    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)

    with st.sidebar:
        st.header("⚙️ Ustawienia")
        if st.button("Cofnij ostatni wpis"):
            if not st.session_state.data.empty:
                st.session_state.data = st.session_state.data.drop(st.session_state.data.index[-1])
                save_data(st.session_state.data)
                st.rerun()
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Pobierz plik bazy (CSV)", csv, "finanse_pizzeria.csv", "text/csv")
