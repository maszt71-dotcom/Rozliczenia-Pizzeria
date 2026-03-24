import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Ustawienia strony - szeroki układ dla kafelków
st.set_page_config(page_title="Pizzeria Finanse", layout="wide")

DB_FILE = 'finanse_data.csv'

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        for col in ['Data', 'Typ', 'Kwota', 'Opis', 'Dzień']:
            if col not in df.columns: df[col] = ""
        return df
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Dzień'])

df = load_data()
df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)

# OBLICZENIA
s_og = df[df['Typ'] == 'Przychód']['Kwota'].sum()
s_wyd = df[df['Typ'] == 'Wydatek']['Kwota'].sum()
s_got = df[df['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

st.title("🍕 System Pizzeria")

# --- TWOJE ULUBIONE TRZY KOLOROWE KONTENERY ---
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
        <div style="background-color: #d4edda; padding: 20px; border-radius: 10px; border-left: 10px solid #28a745;">
            <p style="margin:0; color: #155724; font-weight: bold;">PRZYCHÓD OGÓLNY</p>
            <h2 style="margin:0; color: #155724;">{s_og:.2f} zł</h2>
        </div>
        """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div style="background-color: #fff3cd; padding: 20px; border-radius: 10px; border-left: 10px solid #ffc107;">
            <p style="margin:0; color: #856404; font-weight: bold;">STAN GOTÓWKI</p>
            <h2 style="margin:0; color: #856404;">{s_got:.2f} zł</h2>
        </div>
        """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
        <div style="background-color: #f8d7da; padding: 20px; border-radius: 10px; border-left: 10px solid #dc3545;">
            <p style="margin:0; color: #721c24; font-weight: bold;">WYDATKI</p>
            <h2 style="margin:0; color: #721c24;">{s_wyd:.2f} zł</h2>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# --- PROSTY FORMULARZ POD SPODEM ---
st.subheader("📝 Dodaj wpis")
with st.form("form_pizzeria", clear_on_submit=True):
    typ_glowny = st.selectbox("Typ:", ["Przychód", "Gotówka (Wpłata)", "Wydatek"])
    
    osoba = ""
    if typ_glowny == "Gotówka (Wpłata)":
        osoba = st.selectbox("Kto?", ["Bufet", "Kierowca 1", "Kierowca 2", "Kierowca 3", "Kierowca 4"])
    
    opis = ""
    if typ_glowny == "Wydatek":
        opis = st.text_input("Opis:")
        
    kwota = st.number_input("Kwota (zł):", min_value=0.0, step=1.0)
    dzien = st.date_input("Data:", datetime.now())
    
    if st.form_submit_button("ZAPISZ"):
        typ_finalny = f"Gotówka - {osoba}" if osoba else typ_glowny
        nowy = pd.DataFrame([{'Data': datetime.now().strftime("%H:%M"), 'Typ': typ_finalny, 'Kwota': kwota, 'Opis': opis, 'Dzień': dzien}])
        pd.concat([df, nowy]).to_csv(DB_FILE, index=False)
        st.rerun()

# --- TABELA NA SAMYM DOLE (RZECZ ŚWIĘTA) ---
st.divider()
st.subheader("😇 Rzecz Święta")
got_df = df[df['Typ'].str.contains('Gotówka', na=False)].copy()
if not got_df.empty:
    st.table(got_df.groupby('Typ')['Kwota'].sum().reset_index())
