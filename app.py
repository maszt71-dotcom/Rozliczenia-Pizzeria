import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Ustawienia strony na szeroką, żeby kontenery ładnie leżały obok siebie
st.set_page_config(page_title="Pizzeria - Finanse", layout="wide")

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

# --- OBLICZENIA ---
s_og = df[df['Typ'] == 'Przychód']['Kwota'].sum()
s_wyd = df[df['Typ'] == 'Wydatek']['Kwota'].sum()
s_got = df[df['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- TRZY KOLOROWE KONTENERY (TWOJE ULUBIONE) ---
st.markdown("""
    <style>
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    /* Stylizacja kolorów dla kontenerów */
    [data-testid="stMetricValue"] { font-size: 28px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<div style="background-color: #d4edda; padding: 20px; border-radius: 10px; border-left: 10px solid #28a745;">', unsafe_allow_html=True)
    st.metric("PRZYCHÓD OGÓLNY", f"{s_og:.2f} zł")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div style="background-color: #fff3cd; padding: 20px; border-radius: 10px; border-left: 10px solid #ffc107;">', unsafe_allow_html=True)
    st.metric("STAN GOTÓWKI", f"{s_got:.2f} zł")
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div style="background-color: #f8d7da; padding: 20px; border-radius: 10px; border-left: 10px solid #dc3545;">', unsafe_allow_html=True)
    st.metric("WYDATKI", f"{s_wyd:.2f} zł")
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- FORMULARZ WPISYWANIA ---
st.subheader("📝 Dodaj nowy wpis")
with st.form("formularz", clear_on_submit=True):
    typ_glowny = st.selectbox("Co dodajesz?", ["Przychód", "Gotówka (Wpłata)", "Wydatek"])
    
    osoba = ""
    if typ_glowny == "Gotówka (Wpłata)":
        osoba = st.selectbox("Kto wpłaca?", ["Bufet", "Kierowca 1", "Kierowca 2", "Kierowca 3", "Kierowca 4"])
    
    opis = ""
    if typ_glowny == "Wydatek":
        opis = st.text_input("Na co? (Opis)")
        
    kwota = st.number_input("Kwota (zł):", min_value=0.0, step=1.0)
    dzien = st.date_input("Data:", datetime.now())
    
    submit = st.form_submit_button("ZAPISZ DO BAZY")
    
    if submit:
        typ_finalny = f"Gotówka - {osoba}" if osoba else typ_glowny
        nowy_wpis = pd.DataFrame([{
            'Data': datetime.now().strftime("%H:%M"),
            'Typ': typ_finalny,
            'Kwota': kwota,
            'Opis': opis,
            'Dzień': dzien.strftime("%Y-%m-%d")
        }])
        pd.concat([df, nowy_wpis]).to_csv(DB_FILE, index=False)
        st.success("Zapisano pomyślnie!")
        st.rerun()

# --- RZECZ ŚWIĘTA NA DOLE ---
st.divider()
st.subheader("😇 Rzecz Święta (Rozliczenie Kierowców)")
gotowka_df = df[df['Typ'].str.contains('Gotówka', na=False)].copy()
if not gotowka_df.empty:
    summary = gotowka_df.groupby('Typ')['Kwota'].sum().reset_index()
    summary.columns = ['Osoba', 'Suma wpłat']
    st.table(summary)
