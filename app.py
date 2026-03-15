import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- KONFIGURACJA ---
st.set_page_config(page_title="Finanse Pizzeria", layout="centered")

# TUTAJ WPISZ SWOJE HASŁO (zamiast 1234)
MOJE_HASLO = "dup@"

def check_password():
    if "password_correct" not in st.session_state:
        st.subheader("Zaloguj się do systemu")
        wpisane_haslo = st.text_input("Hasło", type="password")
        if st.button("Wejdź"):
            if wpisane_haslo == MOJE_HASLO:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Błędne hasło")
        return False
    return True

if check_password():
    # --- PROGRAM GŁÓWNY ---
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

    # OBLICZENIA
    przychody_ogolne = df[df['Typ'].isin(['Gotówka', 'Konto'])]['Kwota'].sum()
    koszty_ogolne = df[df['Typ'] == 'Koszt']['Kwota'].sum()
    wplaty_gotowka = df[df['Typ'] == 'Gotówka']['Kwota'].sum()
    stan_gotowki = wplaty_gotowka - koszty_ogolne

    st.title("🍕 Rozliczenia Pizzeria")

    # LICZNIKI
    c1, c2 = st.columns(2)
    c1.metric("PRZYCHÓD OGÓLNY", f"{przychody_ogolne:,.2f} zł".replace(',', ' '))
    c2.metric("SUMA KOSZTÓW", f"{koszty_ogolne:,.2f} zł".replace(',', ' '))
    st.warning(f"💰 **STAN GOTÓWKI W KASIE: {stan_gotowki:,.2f} zł**".replace(',', ' '))

    st.divider()

    # FORMULARZ
    with st.form("nowy_wpis", clear_on_submit=True):
        st.subheader("Dodaj transakcję")
        kwota = st.number_input("Kwota (zł)", min_value=0.0, step=1.0, format="%.2f")
        typ = st.selectbox("Rodzaj", ["Gotówka", "Konto", "Koszt"])
        opis = st.text_input("Opis (np. Klient, Dostawca, Paliwo)")
        submit = st.form_submit_button("ZAPISZ I PRZELICZ", use_container_width=True)

    if submit:
        nowy = {'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Typ': typ, 'Kwota': kwota, 'Opis': opis}
        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([nowy])], ignore_index=True)
        save_data(st.session_state.data)
        st.success("Zapisano!")
        st.rerun()

    # ARCHIWUM
    st.divider()
    st.subheader("📂 Historia wpisów")
    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)

    # USUWANIE
    if st.checkbox("Opcje administratora"):
        if st.button("Usuń ostatni wpis"):
            if not st.session_state.data.empty:
                st.session_state.data = st.session_state.data.drop(st.session_state.data.index[-1])
                save_data(st.session_state.data)
                st.rerun()
