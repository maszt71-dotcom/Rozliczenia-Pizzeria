import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Pizzeria - Zarządzanie Finansami",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DB_FILE = 'finanse_data.csv'

# --- FUNKCJE POMOCNICZE ---
def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            required_cols = ['Data_wpisu', 'Typ', 'Kwota', 'Opis', 'Data_zdarzenia', 'Kto']
            for col in required_cols:
                if col not in df.columns:
                    df[col] = ""
            return df
        except:
            return pd.DataFrame(columns=['Data_wpisu', 'Typ', 'Kwota', 'Opis', 'Data_zdarzenia', 'Kto'])
    return pd.DataFrame(columns=['Data_wpisu', 'Typ', 'Kwota', 'Opis', 'Data_zdarzenia', 'Kto'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# --- STYLIZACJA CSS ---
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stMetric {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricValue"] { color: #333; font-size: 32px; }
    .footer { text-align: center; color: #888; padding: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIKA DANYCH ---
df = load_data()
df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)

# Obliczenia
s_og = df[df['Typ'] == 'Przychód']['Kwota'].sum()
s_wyd = df[df['Typ'] == 'Wydatek']['Kwota'].sum()
s_got = df[df['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- INTERFEJS UŻYTKOWNIKA ---
st.title("🍕 System Zarządzania Pizzerią")
st.markdown(f"**Dzień operacyjny:** {datetime.now().strftime('%d.%m.%Y')}")

# KOLOROWE KONTENERY (GÓRA)
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown('<div style="background-color: #e8f5e9; border-left: 8px solid #2e7d32; padding: 5px; border-radius: 10px;">', unsafe_allow_html=True)
    st.metric("PRZYCHÓD OGÓLNY", f"{s_og:,.2f} zł")
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div style="background-color: #fffde7; border-left: 8px solid #fbc02d; padding: 5px; border-radius: 10px;">', unsafe_allow_html=True)
    st.metric("STAN GOTÓWKI (KASA)", f"{s_got:,.2f} zł")
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    st.markdown('<div style="background-color: #ffebee; border-left: 8px solid #c62828; padding: 5px; border-radius: 10px;">', unsafe_allow_html=True)
    st.metric("SUMA WYDATKÓW", f"{s_wyd:,.2f} zł")
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- FORMULARZ (ŚRODEK) ---
col_form, col_space = st.columns([2, 1])

with col_form:
    st.subheader("➕ Nowa Transakcja")
    with st.form("transakcja_form", clear_on_submit=True):
        kategoria = st.selectbox("Rodzaj operacji:", ["Przychód", "Gotówka (Wpłata)", "Wydatek"])
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            kwota = st.number_input("Kwota (zł):", min_value=0.0, step=0.01, format="%.2f")
        with col_f2:
            data_zd = st.date_input("Data zdarzenia:", datetime.now())
            
        osoba = ""
        if kategoria == "Gotówka (Wpłata)":
            osoba = st.selectbox("Osoba wpłacająca:", ["Bufet", "Kierowca 1", "Kierowca 2", "Kierowca 3", "Kierowca 4"])
            
        opis = ""
        if kategoria == "Wydatek":
            opis = st.text_input("Cel wydatku (Opis):")
            
        submit = st.form_submit_button("ZAPISZ I AKTUALIZUJ")
        
        if submit:
            typ_finalny = f"Gotówka - {osoba}" if osoba else kategoria
            nowy_wpis = {
                'Data_wpisu': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Typ': typ_finalny,
                'Kwota': kwota,
                'Opis': opis,
                'Data_zdarzenia': data_zd.strftime("%Y-%m-%d"),
                'Kto': osoba if osoba else "System"
            }
            df = pd.concat([df, pd.DataFrame([nowy_wpis])], ignore_index=True)
            save_data(df)
            st.success(f"Dodano: {typ_finalny} | {kwota} zł")
            st.rerun()

# --- RZECZ ŚWIĘTA (DÓŁ) ---
st.divider()
st.subheader("😇 Rzecz Święta - Rozliczenie Kierowców i Punktów")

tab1, tab2 = st.tabs(["📊 Sumy zbiorcze", "📜 Historia operacji"])

with tab1:
    got_df = df[df['Typ'].str.contains('Gotówka', na=False)].copy()
    if not got_df.empty:
        # Grupowanie i ładne formatowanie
        rozliczenie = got_df.groupby('Typ')['Kwota'].sum().reset_index()
        rozliczenie.columns = ['Podmiot', 'Suma wpłat (zł)']
        
        # Stylizacja tabeli
        st.dataframe(
            rozliczenie.style.format({'Suma wpłat (zł)': '{:.2f}'})
            .highlight_max(subset=['Suma wpłat (zł)'], color='#d4edda'),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Brak danych gotówkowych do wyświetlenia.")

with tab2:
    if not df.empty:
        st.dataframe(
            df.sort_values(by='Data_wpisu', ascending=False),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.write("Baza danych jest pusta.")

st.markdown('<div class="footer">System Pizzeria v2.0 | Kod Pizza Streamlit Edition</div>', unsafe_allow_html=True)
