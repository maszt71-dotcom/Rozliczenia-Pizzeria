import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="System Rozliczeń Pizzeria", layout="wide")

# --- TRWAŁY ZAPIS DANYCH (DATABASE) ---
DB_FILE = "baza_pizza.csv"

def wczytaj_dane():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])

def zapisz_dane(df):
    df.to_csv(DB_FILE, index=False)

# Inicjalizacja danych w sesji
if 'data_log' not in st.session_state:
    st.session_state.data_log = wczytaj_dane()

# --- STYLE CSS (Przywrócenie wyglądu i naprawa pól) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #2c3e50 !important; }
    .top-container { display: flex; justify-content: space-between; gap: 20px; margin-bottom: 30px; }
    .card {
        flex: 1; padding: 20px; border-radius: 12px; color: white; text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .card-income { background: linear-gradient(135deg, #27ae60, #2ecc71); }
    .card-expenses { background: linear-gradient(135deg, #c0392b, #e74c3c); }
    .card-total { background: linear-gradient(135deg, #2980b9, #3498db); }
    .card-val { font-size: 26px; font-weight: bold; }
    
    /* Naprawa pól liczbowych - brak zer na starcie */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    </style>
""", unsafe_allow_html=True)

# --- OBLICZENIA STATYSTYK ---
df = st.session_state.data_log
# Konwersja kwot na liczby na wypadek błędów w pliku
df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)

suma_in = df[df['Typ'].str.contains("Przychód", na=False)]['Kwota'].sum()
suma_out = df[df['Typ'].str.contains("Wydatek", na=False)]['Kwota'].sum()
bilans = suma_in - suma_out

# --- PASEK BOCZNY ---
with st.sidebar:
    st.markdown('<h2 style="color:white; text-align:center;">🍕 MENU</h2>', unsafe_allow_html=True)
    st.markdown("---")
    
    # PRZYWRÓCONE KAFELKI
    if st.button("📥 Pobierz i Zapisz (Plik)", use_container_width=True):
        zapisz_dane(st.session_state.data_log)
        st.toast("Wszystkie wpisy zostały trwale zapisane w pliku!")
        
    # Przycisk do pobrania kopii na komputer
    csv = st.session_state.data_log.to_csv(index=False).encode('utf-8')
    st.download_button("💾 Eksportuj do Excel (CSV)", data=csv, file_name=f"raport_{datetime.now().strftime('%Y-%m-%d')}.csv", use_container_width=True)
    
    st.markdown("---")
    if st.button("🗑️ Wyczyść wszystko", use_container_width=True):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.session_state.data_log = pd.DataFrame(columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
        st.rerun()

# --- PANEL GŁÓWNY (Trzy kontenery) ---
st.markdown(f"""
    <div class="top-container">
        <div class="card card-income">
            <div>ŁĄCZNY OBRÓT</div>
            <div class="card-val">{suma_in:.2f} zł</div>
        </div>
        <div class="card card-expenses">
            <div>WYDATKI</div>
            <div class="card-val">{suma_out:.2f} zł</div>
        </div>
        <div class="card card-total">
            <div>DO ODDANIA</div>
            <div class="card-val">{bilans:.2f} zł</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- FORMULARZ WPISYWANIA ---
st.markdown("### ➕ Dodaj rozliczenie")
with st.expander("Kliknij tutaj, aby wpisać dane", expanded=True):
    c1, c2, c3 = st.columns([2, 2, 3])
    with c1:
        kwota = st.number_input("Kwota (zł)", min_value=0.0, value=None, step=0.01, placeholder="Wpisz...")
    with c2:
        typ = st.selectbox("Rodzaj", ["Przychód (Obrót)", "Wydatek (Zakupy/Paliwo)"])
    with c3:
        opis = st.text_input("Opis (opcjonalnie)", placeholder="np. Raport wieczorny")

    if st.button("ZATWIERDŹ WPIS", type="primary", use_container_width=True):
        if kwota is not None:
            now = datetime.now()
            nowy_wpis = pd.DataFrame([[
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
                typ, kwota, opis
            ]], columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
            
            # Dodaj do sesji i od razu zapisz do pliku (żeby nie zginęło!)
            st.session_state.data_log = pd.concat([nowy_wpis, st.session_state.data_log], ignore_index=True)
            zapisz_dane(st.session_state.data_log)
            st.rerun()
        else:
            st.error("Wpisz kwotę!")

# --- TABELA HISTORII ---
st.markdown("### 📂 Historia wpisów (zapisana)")
st.dataframe(st.session_state.data_log, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption(f"Dane są automatycznie zapisywane w pliku: {DB_FILE}")
