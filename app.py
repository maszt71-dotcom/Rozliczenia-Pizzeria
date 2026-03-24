import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Ustawienia strony
st.set_page_config(page_title="Finanse Pizzeria", layout="centered")

DB_FILE = 'finanse_data.csv'

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Dzień'])

# Inicjalizacja stanu menu (żeby pamiętał, co kliknęliśmy)
if 'menu' not in st.session_state:
    st.session_state.menu = 'start'

df = load_data()

# --- NAGŁÓWEK I STATYSTYKI ---
st.title("🍕 System Pizzeria")

# Proste liczenie sum
df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)
s_og = df[df['Typ'] == 'Przychód']['Kwota'].sum()
s_wyd = df[df['Typ'] == 'Wydatek']['Kwota'].sum()
s_got = df[df['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

c1, c2, c3 = st.columns(3)
c1.metric("PRZYCHÓD", f"{s_og} zł")
c2.metric("GOTÓWKA", f"{s_got} zł")
c3.metric("WYDATKI", f"{s_wyd} zł")

st.divider()

# --- LOGIKA MENU ---

# 1. EKRAN GŁÓWNY (3 GŁÓWNE PRZYCISKI)
if st.session_state.menu == 'start':
    col1, col2, col3 = st.columns(3)
    
    if col1.button("➕ PRZYCHÓD", use_container_width=True):
        st.session_state.menu = 'przychód'
        st.rerun()
        
    if col2.button("💰 GOTÓWKA", use_container_width=True):
        st.session_state.menu = 'gotówka_wybór'
        st.rerun()
        
    if col3.button("💸 WYDATEK", use_container_width=True):
        st.session_state.menu = 'wydatek'
        st.rerun()

# 2. EKRAN WYBORU OSOBY (PO KLIKNIĘCIU GOTÓWKA)
elif st.session_state.menu == 'gotówka_wybór':
    st.subheader("Kto wpłaca gotówkę?")
    osoba = st.selectbox("Wybierz osobę:", ["Bufet", "Kierowca 1", "Kierowca 2", "Kierowca 3", "Kierowca 4"])
    
    kwota = st.number_input("Kwota wpłaty (zł):", min_value=0.0, step=1.0)
    dzien = st.date_input("Z jakiego dnia?", datetime.now())
    
    col_a, col_b = st.columns(2)
    if col_a.button("✅ ZAPISZ", use_container_width=True):
        nowy = pd.DataFrame([{'Data': datetime.now().strftime("%H:%M"), 'Typ': f"Gotówka - {osoba}", 'Kwota': kwota, 'Opis': '', 'Dzień': dzien}])
        pd.concat([df, nowy]).to_csv(DB_FILE, index=False)
        st.success("Zapisano!")
        st.session_state.menu = 'start'
        st.rerun()
        
    if col_b.button("⬅️ POWRÓT", use_container_width=True):
        st.session_state.menu = 'start'
        st.rerun()

# 3. EKRAN PRZYCHODU / WYDATKU
elif st.session_state.menu in ['przychód', 'wydatek']:
    tryb = "Przychód" if st.session_state.menu == 'przychód' else "Wydatek"
    st.subheader(f"Dodaj {tryb}")
    
    kwota = st.number_input("Kwota (zł):", min_value=0.0, step=1.0)
    opis = ""
    if tryb == "Wydatek":
        opis = st.text_input("Na co? (Opis)")
    
    dzien = st.date_input("Z jakiego dnia?", datetime.now())
    
    col_a, col_b = st.columns(2)
    if col_a.button("✅ ZAPISZ", use_container_width=True):
        nowy = pd.DataFrame([{'Data': datetime.now().strftime("%H:%M"), 'Typ': tryb, 'Kwota': kwota, 'Opis': opis, 'Dzień': dzien}])
        pd.concat([df, nowy]).to_csv(DB_FILE, index=False)
        st.success("Zapisano!")
        st.session_state.menu = 'start'
        st.rerun()
        
    if col_b.button("⬅️ POWRÓT", use_container_width=True):
        st.session_state.menu = 'start'
        st.rerun()

# Historia na dole (opcjonalnie)
if st.checkbox("Pokaż ostatnie wpisy"):
    st.dataframe(df.tail(5), use_container_width=True)
