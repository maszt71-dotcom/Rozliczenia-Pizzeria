import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="System Rozliczeń Pizzeria", layout="wide")

# --- 2. BAZA DANYCH (Zapis/Odczyt) ---
DB_FILE = "baza_pizza.csv"

def wczytaj_dane():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE)
        except:
            return pd.DataFrame(columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
    return pd.DataFrame(columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])

def zapisz_dane(df):
    df.to_csv(DB_FILE, index=False)

if 'data_log' not in st.session_state:
    st.session_state.data_log = wczytaj_dane()

# --- 3. STYLE CSS (Wygląd i naprawa pól) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #2c3e50 !important; color: white; }
    
    /* Główne kontenery */
    .card {
        padding: 20px;
        border-radius: 12px 12px 0 0;
        color: white;
        text-align: center;
        font-weight: bold;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .card-income { background: #27ae60; }
    .card-expenses { background: #c0392b; }
    .card-total { background: #2980b9; }
    
    .card-val { font-size: 28px; display: block; margin-top: 5px; }
    
    /* Stylizacja expanderów, aby pasowały do kontenerów */
    .stExpander { border: none !important; box-shadow: none !important; margin-top: -5px !important; }
    
    /* Naprawa pól liczbowych */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    </style>
""", unsafe_allow_html=True)

# --- 4. OBLICZENIA ---
df = st.session_state.data_log
df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)

suma_in = df[df['Typ'].str.contains("Obrót", na=False)]['Kwota'].sum()
suma_out = df[df['Typ'].str.contains("Wydatek", na=False)]['Kwota'].sum()
bilans = suma_in - suma_out

# --- 5. PASEK BOCZNY ---
with st.sidebar:
    st.markdown('<h2 style="text-align:center; color:#e67e22;">PIZZA SYSTEM</h2>', unsafe_allow_html=True)
    st.markdown("---")
    
    if st.button("📥 Zapisz wszystko", use_container_width=True):
        zapisz_dane(st.session_state.data_log)
        st.success("Zapisano!")

    # USUWANIE LINII
    st.markdown("### 🗑️ Usuń wpis")
    if not st.session_state.data_log.empty:
        lista_wpisow = st.session_state.data_log.apply(lambda x: f"{x['Godzina']} | {x['Kwota']} zł", axis=1).tolist()
        do_usuniecia = st.multiselect("Wybierz wpisy:", lista_wpisow)
        if st.button("USUŃ WYBRANE", use_container_width=True):
            idx = [lista_wpisow.index(w) for w in do_usuniecia]
            st.session_state.data_log = st.session_state.data_log.drop(st.session_state.data_log.index[idx]).reset_index(drop=True)
            zapisz_dane(st.session_state.data_log)
            st.rerun()

# --- 6. TRZY KONTENERY Z WYSUWANYMI TABELAMI ---
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f'<div class="card card-income">OBRÓT<span class="card-val">{suma_in:.2f} zł</span></div>', unsafe_allow_html=True)
    with st.expander("➕ Dopisz Obrót"):
        kwota_in = st.number_input("Kwota obrotu:", min_value=0.0, value=None, step=0.01, key="in_val", placeholder="0.00")
        opis_in = st.text_input("Notatka (obrót):", key="in_desc")
        if st.button("Dodaj Przychod", use_container_width=True):
            if kwota_in:
                now = datetime.now()
                nowy = pd.DataFrame([[now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), "Przychód (Obrót)", kwota_in, opis_in]], 
                                    columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
                st.session_state.data_log = pd.concat([nowy, st.session_state.data_log], ignore_index=True)
                zapisz_dane(st.session_state.data_log)
                st.rerun()

with col2:
    st.markdown(f'<div class="card card-expenses">WYDATKI<span class="card-val">{suma_out:.2f} zł</span></div>', unsafe_allow_html=True)
    with st.expander("➕ Dopisz Wydatek"):
        kwota_out = st.number_input("Kwota wydatku:", min_value=0.0, value=None, step=0.01, key="out_val", placeholder="0.00")
        opis_out = st.text_input("Na co wydano?", key="out_desc")
        if st.button("Dodaj Wydatek", use_container_width=True):
            if kwota_out:
                now = datetime.now()
                nowy = pd.DataFrame([[now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), "Wydatek (Zakupy)", kwota_out, opis_out]], 
                                    columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
                st.session_state.data_log = pd.concat([nowy, st.session_state.data_log], ignore_index=True)
                zapisz_dane(st.session_state.data_log)
                st.rerun()

with col3:
    st.markdown(f'<div class="card card-total">BILANS<span class="card-val">{bilans:.2f} zł</span></div>', unsafe_allow_html=True)
    with st.expander("📊 Szybki podgląd"):
        st.write(f"Dzisiejsza data: {datetime.now().strftime('%d.%m.%Y')}")
        st.write(f"Liczba wpisów: {len(st.session_state.data_log)}")

# --- 7. HISTORIA (Zawsze pod spodem) ---
st.markdown("---")
st.markdown("### 📂 Historia operacji")
st.dataframe(st.session_state.data_log, use_container_width=True, hide_index=True)
