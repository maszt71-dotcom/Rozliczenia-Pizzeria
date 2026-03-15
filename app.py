import streamlit as st
import pandas as pd
import os
from datetime import datetime

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
        st.markdown(f"""<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745;">
        <span style="color:#155724; font-size:14px;">PRZYCHÓD OGÓLNY</span><br>
        <b style="color:#155724; font-size:18px;">{suma_przychodu_ogolnego:,.2f} zł</b></div>""", unsafe_allow_html=True)
        if st.button("➕ Dodaj Ogólny", use_container_width=True):
            st.session_state.pokaz_formularz = "Przychód ogólny"

    with col2:
        st.markdown(f"""<div style="background-color:#fff3cd; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #ffc107;">
        <span style="color:#856404; font-size:14px;">STAN KASY</span><br>
        <b style="color:#856404; font-size:18px;">{stan_gotowki:,.2f} zł</b></div>""", unsafe_allow_html=True)
        if st.button("➕ Dodaj Gotówkę", use_container_width=True):
            st.session_state.pokaz_formularz = "Gotówka"

    with col3:
        st.markdown(f"""<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545;">
        <span style="color:#721c24; font-size:14px;">WYDATKI</span><br>
        <b style="color:#721c24; font-size:18px;">{suma_wydatkow:,.2f} zł</b></div>""", unsafe_allow_html=True)
        if st.button("➖ Dodaj Wydatek", use_container_width=True):
            st.session_state.pokaz_formularz = "Wydatki"

    st.divider()

    # --- OKNO EDYCJI (FORMULARZ PO KLIKNIĘCIU) ---
    if "pokaz_formularz" in st.session_state:
        typ_wpisu = st.session_state.pokaz_formularz
        st.info(f"Edytujesz: **{typ_wpisu}**")
        
        with st.form("nowy_wpis", clear_on_submit=True):
            kwota = st.number_input("Podaj kwotę (zł)", min_value=0.0, step=1.0, format="%.2f")
            
            # Dynamiczne pytanie o opis
            if typ_wpisu == "Wydatki":
                opis = st.text_input("Jaki wydatek? (np. towar, paliwo, wypłata)")
            else:
                opis = st.text_input("Opis (opcjonalnie)")

            col_a, col_b = st.columns(2)
            with col_a:
                if st.form_submit_button("ZAPISZ", use_container_width=True):
                    nowy = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': typ_wpisu, 'Kwota': kwota, 'Opis': opis}
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([nowy])], ignore_index=True)
                    save_data(st.session_state.data)
                    del st.session_state.pokaz_formularz
                    st.rerun()
            with col_b:
                if st.form_submit_button("ANULUJ", use_container_width=True):
                    del st.session_state.pokaz_formularz
                    st.rerun()

    # --- ARCHIWUM ---
    st.subheader("📂 Historia wpisów")
    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)

    with st.sidebar:
        st.header("⚙️ Opcje")
        if st.button("Usuń ostatni wpis"):
            if not st.session_state.data.empty:
                st.session_state.data = st.session_state.data.drop(st.session_state.data.index[-1])
                save_data(st.session_state.data)
                st.rerun()
