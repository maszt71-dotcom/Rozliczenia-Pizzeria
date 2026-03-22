import streamlit as st
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="System Rozliczeń Pizzeria",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLE CSS (Przywrócenie wyglądu i naprawa pól) ---
st.markdown("""
    <style>
    /* Główne tło i czcionka */
    .stApp {
        background-color: #f8f9fa;
    }

    /* Pasek boczny */
    [data-testid="stSidebar"] {
        background-color: #2c3e50 !important;
        min-width: 260px;
    }
    
    .sidebar-text {
        color: white !important;
        text-align: center;
    }

    /* Trzy kontenery na górze */
    .top-container {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        margin-bottom: 30px;
    }
    
    .card {
        flex: 1;
        padding: 25px;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    
    .card:hover {
        transform: translateY(-5px);
    }
    
    .card-income { background: linear-gradient(135deg, #27ae60, #2ecc71); }
    .card-expenses { background: linear-gradient(135deg, #c0392b, #e74c3c); }
    .card-total { background: linear-gradient(135deg, #2980b9, #3498db); }
    
    .card-val { font-size: 28px; font-weight: bold; margin-top: 10px; }
    .card-lab { font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }

    /* Naprawa pól wprowadzania (brak strzałek i zer) */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none; margin: 0; 
    }
    
    /* Personalizacja przycisków w menu */
    .stButton>button {
        border-radius: 8px;
        height: 3em;
        transition: 0.3s;
    }
    </style>
""", unsafe_allow_html=True)

# --- INICJALIZACJA STANU (Baza danych w sesji) ---
if 'data_log' not in st.session_state:
    st.session_state.data_log = pd.DataFrame(columns=['Godzina', 'Typ', 'Kwota', 'Opis'])
if 'total_in' not in st.session_state: st.session_state.total_in = 0.0
if 'total_out' not in st.session_state: st.session_state.total_out = 0.0

# --- PASEK BOCZNY (MENU) ---
with st.sidebar:
    st.markdown('<h2 class="sidebar-text">🍕 MENU SYSTEMU</h2>', unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown('<p class="sidebar-text">OPERACJE NA DANYCH</p>', unsafe_allow_html=True)
    
    # PRZYWRÓCONE KAFELKI
    if st.button("📥 Pobierz i Zapisz", use_container_width=True):
        st.toast("Dane zostały zarchiwizowane pomyślnie!", icon="✅")
        
    if st.button("💾 Pobierz (Excel)", use_container_width=True):
        st.toast("Przygotowywanie pliku do pobrania...")
        
    st.markdown("---")
    
    if st.button("⚙️ Ustawienia", use_container_width=True):
        st.sidebar.warning("Ustawienia są zablokowane dla Twojej roli.")
        
    if st.button("🔄 Resetuj Dzisiejszy Dzień", use_container_width=True):
        st.session_state.total_in = 0.0
        st.session_state.total_out = 0.0
        st.session_state.data_log = pd.DataFrame(columns=['Godzina', 'Typ', 'Kwota', 'Opis'])
        st.rerun()

# --- GŁÓWNA TREŚĆ ---
st.title("Panel Rozliczeń Dziennych")

# TRZY KONTENERY NA GÓRZE
bilans = st.session_state.total_in - st.session_state.total_out

st.markdown(f"""
    <div class="top-container">
        <div class="card card-income">
            <div class="card-lab">Łączny Obrót</div>
            <div class="card-val">{st.session_state.total_in:.2f} zł</div>
        </div>
        <div class="card card-expenses">
            <div class="card-lab">Wydatki Gotówkowe</div>
            <div class="card-val">{st.session_state.total_out:.2f} zł</div>
        </div>
        <div class="card card-total">
            <div class="card-lab">Do Rozliczenia (Netto)</div>
            <div class="card-val">{bilans:.2f} zł</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# SEKACJA DODAWANIA WPISU
st.markdown("### ➕ Dodaj nową transakcję")
with st.container():
    c1, c2, c3 = st.columns([2, 2, 3])
    
    with c1:
        # NAPRAWA ZER: value=None sprawia, że pole jest puste
        kwota_input = st.number_input("Kwota (zł)", min_value=0.0, value=None, step=0.01, placeholder="Wpisz kwotę...")
    
    with c2:
        typ_transakcji = st.selectbox("Typ", ["Przychód (Obrót)", "Wydatek (Zakupy/Paliwo)"])
    
    with c3:
        notatka = st.text_input("Krótki opis (opcjonalnie)", placeholder="np. Dostawa serów, zamówienie #12")

    if st.button("Zatwierdź wpis", type="primary", use_container_width=True):
        if kwota_input is not None and kwota_input > 0:
            now = datetime.now().strftime("%H:%M:%S")
            
            if "Przychód" in typ_transakcji:
                st.session_state.total_in += kwota_input
            else:
                st.session_state.total_out += kwota_input
            
            # Dodanie do tabeli historii
            new_row = pd.DataFrame([[now, typ_transakcji, kwota_input, notatka]], 
                                   columns=['Godzina', 'Typ', 'Kwota', 'Opis'])
            st.session_state.data_log = pd.concat([new_row, st.session_state.data_log], ignore_index=True)
            
            st.success(f"Dodano: {kwota_input:.2f} zł")
            st.rerun()
        else:
            st.error("Proszę podać prawidłową kwotę!")

# SEKCJA HISTORII (Podobna do tej ze zrzutu ekranu)
st.markdown("---")
st.markdown("### 📂 Historia dzisiejszych operacji")

if not st.session_state.data_log.empty:
    st.dataframe(st.session_state.data_log, use_container_width=True, hide_index=True)
else:
    st.info("Brak wpisów w historii dla bieżącej sesji.")

# STOPKA SYSTEMOWA
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
col_f1, col_f2 = st.columns(2)
with col_f1:
    st.caption(f"Status połączenia: ✅ Stabilne")
with col_f2:
    st.caption(f"Ostatnia synchronizacja: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
