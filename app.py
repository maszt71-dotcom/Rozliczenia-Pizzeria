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

# --- 2. AUTOMATYCZNA BAZA DANYCH (Zapis/Odczyt) ---
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

# Inicjalizacja danych przy starcie - DANE NIE ZNIKNĄ
if 'data_log' not in st.session_state:
    st.session_state.data_log = wczytaj_dane()

# --- 3. STYLE CSS (Przywrócenie wyglądu i naprawa zer) ---
st.markdown("""
    <style>
    /* Pasek boczny - ciemny styl */
    [data-testid="stSidebar"] {
        background-color: #2c3e50 !important;
        color: white;
    }
    
    /* Trzy kontenery na górze (Obrót, Wydatki, Do oddania) */
    .top-container {
        display: flex;
        justify-content: space-between;
        gap: 15px;
        margin-bottom: 30px;
    }
    
    .card {
        flex: 1;
        padding: 25px;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    
    .card-income { background: linear-gradient(135deg, #27ae60, #2ecc71); }
    .card-expenses { background: linear-gradient(135deg, #c0392b, #e74c3c); }
    .card-total { background: linear-gradient(135deg, #2980b9, #3498db); }
    
    .card-val { font-size: 30px; font-weight: bold; margin-top: 10px; }
    .card-lab { font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }

    /* Naprawa pól wprowadzania - brak zer na starcie */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none; margin: 0; 
    }
    
    /* Ukrycie dekoracji Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 4. OBLICZENIA DLA KONTENERÓW ---
df = st.session_state.data_log
# Upewnienie się, że Kwota to liczba
df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)

suma_in = df[df['Typ'].str.contains("Obrót", na=False)]['Kwota'].sum()
suma_out = df[df['Typ'].str.contains("Wydatek", na=False)]['Kwota'].sum()
bilans = suma_in - suma_out

# --- 5. PASEK BOCZNY (MENU) ---
with st.sidebar:
    st.markdown('<h2 style="text-align:center; color:#e67e22;">PIZZA SYSTEM</h2>', unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown("### 📋 OPERACJE")
    
    # PRZYWRÓCONE KAFELKI Z MENU
    if st.button("📥 Pobierz i Zapisz", use_container_width=True):
        zapisz_dane(st.session_state.data_log)
        st.success("Dane zarchiwizowane!")

    # Przycisk eksportu do CSV
    csv_bytes = st.session_state.data_log.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="💾 Pobierz Plik (Excel/CSV)",
        data=csv_bytes,
        file_name=f"raport_{datetime.now().strftime('%Y-%m-%d')}.csv",
        use_container_width=True
    )

    st.markdown("---")
    if st.button("🔄 Odśwież widok", use_container_width=True):
        st.rerun()

    if st.button("🗑️ WYCZYŚĆ BAZĘ", use_container_width=True):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        st.session_state.data_log = pd.DataFrame(columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
        st.rerun()

# --- 6. WIDOK GŁÓWNY (TRZY KONTENERY) ---
st.markdown(f"""
    <div class="top-container">
        <div class="card card-income">
            <div class="card-lab">Obrót Całkowity</div>
            <div class="card-val">{suma_in:.2f} zł</div>
        </div>
        <div class="card card-expenses">
            <div class="card-lab">Wydatki Gotówkowe</div>
            <div class="card-val">{suma_out:.2f} zł</div>
        </div>
        <div class="card card-total">
            <div class="card-lab">Do Rozliczenia</div>
            <div class="card-val">{bilans:.2f} zł</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 7. FORMULARZ WPISYWANIA ---
st.markdown("### ➕ Dodaj nowy wpis")
with st.container():
    c1, c2, c3 = st.columns([2, 2, 4])
    
    with c1:
        # NAPRAWA ZER: value=None sprawia, że pole jest puste
        kwota_in = st.number_input("Kwota (zł):", min_value=0.0, value=None, step=0.01, placeholder="0.00")
    
    with c2:
        typ_in = st.selectbox("Rodzaj:", ["Przychód (Obrót)", "Wydatek (Zakupy/Paliwo)"])
    
    with c3:
        opis_in = st.text_input("Notatka/Opis:", placeholder="np. Raport dzienny, zakup paliwa...")

    if st.button("ZATWIERDŹ I ZAPISZ", type="primary", use_container_width=True):
        if kwota_in is not None:
            teraz = datetime.now()
            nowy_row = pd.DataFrame([[
                teraz.strftime("%Y-%m-%d"),
                teraz.strftime("%H:%M:%S"),
                typ_in, kwota_in, opis_in
            ]], columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
            
            # Dodaj do tabeli i natychmiast zapisz na dysk
            st.session_state.data_log = pd.concat([nowy_row, st.session_state.data_log], ignore_index=True)
            zapisz_dane(st.session_state.data_log)
            st.rerun()
        else:
            st.warning("Proszę wpisać kwotę przed zatwierdzeniem!")

# --- 8. TABELA HISTORII ---
st.markdown("---")
st.markdown("### 📂 Historia wpisów (Zapisana)")

if not st.session_state.data_log.empty:
    st.dataframe(
        st.session_state.data_log, 
        use_container_width=True, 
        hide_index=True
    )
else:
    st.info("Baza danych jest pusta. Dodaj pierwszy wpis powyżej.")

# Stopka informacyjna
st.markdown("<br><hr>", unsafe_allow_html=True)
st.caption(f"Status: Dane wczytane automatycznie | Plik: {DB_FILE} | Dzisiaj: {datetime.now().strftime('%d.%m.%Y')}")
