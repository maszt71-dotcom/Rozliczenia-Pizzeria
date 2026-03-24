import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Ustawienia strony - szeroki układ, żeby kafelki ładnie wyglądały
st.set_page_config(page_title="Pizzeria - System", layout="wide")

DB_FILE = 'finanse_data.csv'

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        for col in ['Data', 'Typ', 'Kwota', 'Opis', 'Dzień']:
            if col not in df.columns: df[col] = ""
        return df
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Dzień'])

# Inicjalizacja menu
if 'menu' not in st.session_state:
    st.session_state.menu = 'start'

df = load_data()
df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)

# --- STATYSTYKI NA GÓRZE ---
s_og = df[df['Typ'] == 'Przychód']['Kwota'].sum()
s_wyd = df[df['Typ'] == 'Wydatek']['Kwota'].sum()
s_got = df[df['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

st.title("🍕 System Pizzeria")

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("PRZYCHÓD", f"{s_og:.2f} zł")
col_m2.metric("W KASIE", f"{s_got:.2f} zł")
col_m3.metric("WYDATKI", f"{s_wyd:.2f} zł")

st.divider()

# --- WIDOK GŁÓWNY (TRZY PRZYCISKI) ---
if st.session_state.menu == 'start':
    c1, c2, c3 = st.columns(3)
    
    if c1.button("➕ PRZYCHÓD", use_container_width=True, type="primary"):
        st.session_state.menu = 'przychód'
        st.rerun()
        
    if c2.button("💰 GOTÓWKA", use_container_width=True, type="primary"):
        st.session_state.menu = 'gotówka_wybór'
        st.rerun()
        
    if c3.button("💸 WYDATEK", use_container_width=True, type="primary"):
        st.session_state.menu = 'wydatek'
        st.rerun()

    # --- RZECZ ŚWIĘTA (POD PRZYCISKAMI) ---
    st.markdown("### 😇 Rzecz Święta (Rozliczenie)")
    
    gotowka_df = df[df['Typ'].str.contains('Gotówka', na=False)].copy()
    if not gotowka_df.empty:
        summary = gotowka_df.groupby('Typ')['Kwota'].sum().reset_index()
        summary.columns = ['Kto/Skąd', 'Suma wpłat']
        st.dataframe(summary, use_container_width=True, hide_index=True)
    else:
        st.write("Brak wpłat do wyświetlenia.")

# --- PODMENU: GOTÓWKA ---
elif st.session_state.menu == 'gotówka_wybór':
    st.subheader("💰 Kto wpłaca gotówkę?")
    osoba = st.selectbox("Wybierz:", ["Bufet", "Kierowca 1", "Kierowca 2", "Kierowca 3", "Kierowca 4"])
    kwota = st.number_input("Kwota:", min_value=0.0, step=1.0)
    dzien = st.date_input("Dzień:", datetime.now())
    
    col_z, col_p = st.columns(2)
    if col_z.button("✅ ZAPISZ", use_container_width=True):
        nowy = pd.DataFrame([{'Data': datetime.now().strftime("%H:%M"), 'Typ': f"Gotówka - {osoba}", 'Kwota': kwota, 'Opis': '', 'Dzień': dzien}])
        pd.concat([df, nowy]).to_csv(DB_FILE, index=False)
        st.session_state.menu = 'start'
        st.rerun()
    if col_p.button("⬅️ POWRÓT", use_container_width=True):
        st.session_state.menu = 'start'
        st.rerun()

# --- PODMENU: PRZYCHÓD / WYDATEK ---
elif st.session_state.menu in ['przychód', 'wydatek']:
    tryb = "Przychód" if st.session_state.menu == 'przychód' else "Wydatek"
    st.subheader(f"Dodaj {tryb}")
    kwota = st.number_input("Kwota:", min_value=0.0, step=1.0)
    opis = st.text_input("Opis:") if tryb == "Wydatek" else ""
    dzien = st.date_input("Dzień:", datetime.now())
    
    col_z, col_p = st.columns(2)
    if col_z.button("✅ ZAPISZ", use_container_width=True):
        nowy = pd.DataFrame([{'Data': datetime.now().strftime("%H:%M"), 'Typ': tryb, 'Kwota': kwota, 'Opis': opis, 'Dzień': dzien}])
        pd.concat([df, nowy]).to_csv(DB_FILE, index=False)
        st.session_state.menu = 'start'
        st.rerun()
    if col_p.button("⬅️ POWRÓT", use_container_width=True):
        st.session_state.menu = 'start'
        st.rerun()
