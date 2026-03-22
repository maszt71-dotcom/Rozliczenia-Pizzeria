import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="System Rozliczeń Pizzeria",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. MECHANIZM AUTO-WYŚWIETLANIA (DATABASE) ---
DB_FILE = "baza_pizza.csv"

def wczytaj_dane_na_start():
    # Ta funkcja uruchamia się sama przy każdym wejściu na stronę
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE)
        except:
            return pd.DataFrame(columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
    return pd.DataFrame(columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])

def zapisz_dane(df):
    df.to_csv(DB_FILE, index=False)

# Automatyczne wczytanie przy starcie/odświeżeniu
if 'data_log' not in st.session_state:
    st.session_state.data_log = wczytaj_dane_na_start()

# --- 3. STYLE CSS (Przywrócenie wyglądu i naprawa zer) ---
st.markdown("""
    <style>
    /* Ukrycie elementów Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    [data-testid="stSidebar"] {
        background-color: #2c3e50 !important;
        color: white;
    }
    
    /* Trzy kontenery na górze */
    .top-container {
        display: flex;
        justify-content: space-between;
        gap: 15px;
        margin-bottom: 25px;
    }
    
    .card {
        flex: 1;
        padding: 25px;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .card-income { background: linear-gradient(135deg, #27ae60, #2ecc71); }
    .card-expenses { background: linear-gradient(135deg, #c0392b, #e74c3c); }
    .card-total { background: linear-gradient(135deg, #2980b9, #3498db); }
    
    .card-val { font-size: 28px; font-weight: bold; margin-top: 5px; }
    .card-lab { font-size: 13px; text-transform: uppercase; font-weight: bold; }

    /* Naprawa pól wprowadzania - brak zer */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none; margin: 0; 
    }
    </style>
""", unsafe_allow_html=True)

# --- 4. OBLICZENIA (Zawsze aktualne) ---
df_current = st.session_state.data_log
df_current['Kwota'] = pd.to_numeric(df_current['Kwota'], errors='coerce').fillna(0)

suma_obrot = df_current[df_current['Typ'].str.contains("Obrót", na=False)]['Kwota'].sum()
suma_wydatki = df_current[df_current['Typ'].str.contains("Wydatek", na=False)]['Kwota'].sum()
bilans = suma_obrot - suma_wydatki

# --- 5. PASEK BOCZNY (MENU) ---
with st.sidebar:
    st.markdown('<h2 style="text-align:center;">PANEL PIZZERIA</h2>', unsafe_allow_html=True)
    st.markdown("---")
    
    # PRZYWRÓCONE KAFELKI
    if st.button("📥 Zapisz Kopię", use_container_width=True):
        zapisz_dane(st.session_state.data_log)
        st.success("Dane zapisane!")

    csv_file = st.session_state.data_log.to_csv(index=False).encode('utf-8')
    st.download_button("💾 Pobierz Plik CSV", data=csv_file, file_name="rozliczenie.csv", use_container_width=True)

    st.markdown("---")
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO", use_container_width=True, type="secondary"):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        st.session_state.data_log = pd.DataFrame(columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
        st.rerun()

# --- 6. WIDOK GŁÓWNY (Trzy kontenery - zawsze widoczne) ---
st.markdown(f"""
    <div class="top-container">
        <div class="card card-income">
            <div class="card-lab">Łączny Obrót</div>
            <div class="card-val">{suma_obrot:.2f} zł</div>
        </div>
        <div class="card card-expenses">
            <div class="card-lab">Wydatki</div>
            <div class="card-val">{suma_wydatki:.2f} zł</div>
        </div>
        <div class="card card-total">
            <div class="card-lab">Do Oddania</div>
            <div class="card-val">{bilans:.2f} zł</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 7. FORMULARZ DODAWANIA ---
st.subheader("➕ Nowy wpis")
with st.container():
    c1, c2, c3 = st.columns([2, 2, 4])
    with c1:
        kwota_in = st.number_input("Kwota (zł)", min_value=0.0, value=None, step=0.01, placeholder="0.00")
    with c2:
        typ_in = st.selectbox("Rodzaj", ["Przychód (Obrót)", "Wydatek (Zakupy/Paliwo)"])
    with c3:
        opis_in = st.text_input("Notatka", placeholder="np. Raport wieczorny")

    if st.button("ZATWIERDŹ WPIS", type="primary", use_container_width=True):
        if kwota_in is not None:
            now = datetime.now()
            nowy_wiersz = pd.DataFrame([[
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
                typ_in, kwota_in, opis_in
            ]], columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
            
            # Dodaj i zapisz do pliku natychmiast
            st.session_state.data_log = pd.concat([nowy_wiersz, st.session_state.data_log], ignore_index=True)
            zapisz_dane(st.session_state.data_log)
            st.rerun()

# --- 8. HISTORIA (Poniżej, zawsze widoczna) ---
st.markdown("---")
st.markdown("### 📂 Historia wpisów")
if not st.session_state.data_log.empty:
    st.dataframe(st.session_state.data_log, use_container_width=True, hide_index=True)
else:
    st.info("Brak danych. Wpisz pierwszą kwotę powyżej.")

st.caption(f"System automatycznie wczytuje dane z pliku {DB_FILE}")
