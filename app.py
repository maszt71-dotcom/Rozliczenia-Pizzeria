import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Konfiguracja pod telefon
st.set_page_config(page_title="Finanse Czechowice", layout="centered")

# Nazwa pliku bazy danych
DB_FILE = 'finanse_data.csv'

# --- FUNKCJE BAZY DANYCH ---
def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# Inicjalizacja danych
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- LOGIKA OBLICZEŃ ---
df = st.session_state.data
# Zamiana kwot na liczby (na wypadek błędów w CSV)
df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)

przychody_ogolne = df[df['Typ'].isin(['Gotówka', 'Konto'])]['Kwota'].sum()
koszty_ogolne = df[df['Typ'] == 'Koszt']['Kwota'].sum()
wplaty_gotowka = df[df['Typ'] == 'Gotówka']['Kwota'].sum()
stan_gotowki = wplaty_gotowka - koszty_ogolne

# --- INTERFEJS ---
st.title("📊 System Finansowy")

# Liczniki na górze
c1, c2 = st.columns(2)
c1.metric("PRZYCHÓD OGÓLNY", f"{przychody_ogolne:,.2f} zł".replace(',', ' '))
c2.metric("SUMA KOSZTÓW", f"{koszty_ogolne:,.2f} zł".replace(',', ' '))

st.warning(f"💰 **STAN GOTÓWKI W KASIE: {stan_gotowki:,.2f} zł**".replace(',', ' '))

st.divider()

# Formularz
with st.form("nowy_wpis", clear_on_submit=True):
    st.subheader("Dodaj transakcję")
    kwota = st.number_input("Kwota (zł)", min_value=0.0, step=1.0, format="%.2f")
    typ = st.selectbox("Rodzaj płatności / Typ", ["Gotówka", "Konto", "Koszt"])
    opis = st.text_input("Opis (np. Klient, Paliwo, Narzędzia)")
    
    submit = st.form_submit_button("ZAPISZ I PRZELICZ", use_container_width=True)

if submit:
    nowy_wpis = {
        'Data': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'Typ': typ,
        'Kwota': kwota,
        'Opis': opis
    }
    # Dodanie do danych i zapis do pliku
    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([nowy_wpis])], ignore_index=True)
    save_data(st.session_state.data)
    st.success("Zapisano pomyślnie!")
    st.rerun()

# --- ARCHIWUM ---
st.divider()
st.subheader("📂 Historia wpisów")
if not df.empty:
    # Wyświetlamy od najnowszych
    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)
else:
    st.info("Archiwum jest puste.")

# Przycisk bezpieczeństwa (opcjonalnie)
if st.checkbox("Pokaż opcje usuwania"):
    if st.button("Usuń ostatni wpis"):
        if not st.session_state.data.empty:
            st.session_state.data = st.session_state.data.drop(st.session_state.data.index[-1])
            save_data(st.session_state.data)
            st.rerun()
