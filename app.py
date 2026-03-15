import streamlit as st
import pandas as pd
from datetime import datetime

# Konfiguracja strony pod telefon
st.set_page_config(page_title="Licznik Finansowy", layout="centered")

st.title("📊 Moje Finanse")

# Inicjalizacja bazy danych w pamięci (w prawdziwej aplikacji byłaby to baza SQL)
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis'])

# --- LOGIKA OBLICZEŃ ---
df = st.session_state.data
przychody_ogolne = df[df['Typ'].isin(['Gotówka', 'Konto'])]['Kwota'].sum()
koszty_ogolne = df[df['Typ'] == 'Koszt']['Kwota'].sum()
wplaty_gotowka = df[df['Typ'] == 'Gotówka']['Kwota'].sum()
stan_gotowki = wplaty_gotowka - koszty_ogolne

# --- WIDOK NA TELEFONIE (LICZNIKI) ---
col1, col2 = st.columns(2)
col1.metric("PRZYCHÓD OGÓLNY", f"{przychody_ogolne:.2f} zł")
col2.metric("SUMA KOSZTÓW", f"{koszty_ogolne:.2f} zł")

st.info(f"💰 **STAN GOTÓWKI (W KASIE): {stan_gotowki:.2f} zł**")

st.divider()

# --- FORMULARZ WPISYWANIA ---
st.subheader("Dodaj nowy wpis")
kwota = st.number_input("Kwota (zł)", min_value=0.0, step=0.01)
typ = st.selectbox("Rodzaj", ["Gotówka", "Konto", "Koszt"])
opis = st.text_input("Opis (np. klient, paliwo, towar)")

if st.button("Zapisz wpis", use_container_width=True):
    nowy_wpis = {
        'Data': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'Typ': typ,
        'Kwota': kwota,
        'Opis': opis
    }
    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([nowy_wpis])], ignore_index=True)
    st.success("Dodano do archiwum!")
    st.rerun()

# --- ARCHIWUM ---
st.divider()
st.subheader("📂 Archiwum wpisów")
if not df.empty:
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)
else:
    st.write("Brak wpisów w archiwum.")
