import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Konfiguracja strony
st.set_page_config(page_title="Finanse Pizzeria", layout="wide")
DB_FILE = 'finanse_data.csv'

# Funkcja do ładowania danych
def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        # Sprawdzamy, czy są wszystkie potrzebne kolumny
        for col in ['Data_wpisu', 'Typ', 'Kwota', 'Opis', 'Data_zdarzenia']:
            if col not in df.columns: df[col] = ""
        return df
    return pd.DataFrame(columns=['Data_wpisu', 'Typ', 'Kwota', 'Opis', 'Data_zdarzenia'])

df = load_data()

# Nagłówek aplikacji
st.title("🍕 System Finansowy Pizzerii")

# --- LICZENIE SUM DO KAFELKÓW ---
df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)
s_og = df[df['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df[df['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
# Gotówka w kasie to wpłaty od osób minus wydatki
s_got = df[df['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- WYŚWIETLANIE KAFELKÓW (METRYKI) ---
col1, col2, col3 = st.columns(3)
col1.metric("PRZYCHÓD OGÓLNY", f"{s_og:.2f} zł")
col2.metric("GOTÓWKA (Stan)", f"{s_got:.2f} zł")
col3.metric("WYDATKI", f"{s_wyd:.2f} zł")

st.divider()

# --- FORMULARZ DODAWANIA WPISU ---
st.subheader("Dodaj nową operację")

# Wybór co robimy (to zmienia pola w formularzu)
kategoria = st.radio("Co chcesz dodać?", ["Przychód", "Gotówka (Wpłata)", "Wydatek"], horizontal=True)

with st.form("dodaj_wpis", clear_on_submit=True):
    typ_finalny = ""
    opis = ""
    
    if kategoria == "Przychód":
        typ_finalny = "Przychód ogólny"
        
    elif kategoria == "Gotówka (Wpłata)":
        # Tu pojawił się wybór osoby
        kto = st.selectbox("Kto wpłaca?", ["Bufet", "Kierowca 1", "Kierowca 2", "Kierowca 3", "Kierowca 4"])
        typ_finalny = f"Gotówka - {kto}"
        
    elif kategoria == "Wydatek":
        typ_finalny = "Wydatki gotówkowe"
        opis = st.text_input("Na co wydano? (Opis)")

    kwota = st.number_input("Kwota (zł)", min_value=0.0, step=0.01)
    data_zd = st.date_input("Z jakiego dnia?", datetime.now())
    
    submit = st.form_submit_button("ZAPISZ DANE")

    if submit:
        nowy_wpis = {
            'Data_wpisu': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'Typ': typ_finalny,
            'Kwota': kwota,
            'Opis': opis,
            'Data_zdarzenia': data_zd.strftime("%Y-%m-%d")
        }
        # Łączymy stare dane z nowymi i zapisujemy do CSV
        df = pd.concat([df, pd.DataFrame([nowy_wpis])], ignore_index=True)
        df.to_csv(DB_FILE, index=False)
        st.success(f"Zapisano: {typ_finalny} - {kwota} zł")
        st.rerun() # Odśwież stronę, żeby kafelki na górze się zmieniły

# Opcjonalny podgląd tabeli
if st.checkbox("Pokaż historię wpisów"):
    st.dataframe(df.tail(10), use_container_width=True)
