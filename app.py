import streamlit as st
import pandas as pd
from datetime import datetime

# Konfiguracja strony
st.set_page_config(page_title="System Rozliczeń Pizzeria", layout="wide", initial_sidebar_state="expanded")

# --- STYLE CSS (Przywrócenie wyglądu i naprawa zer) ---
st.markdown("""
    <style>
    /* Główna czcionka i tło */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }

    /* Stylizacja paska bocznego */
    [data-testid="stSidebar"] {
        background-color: #2c3e50 !important;
        color: white;
    }

    /* Kafelki w menu */
    .menu-card {
        background: #34495e;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 5px solid #e67e22;
        transition: 0.3s;
        cursor: pointer;
    }
    .menu-card:hover {
        background: #3e5871;
        transform: translateX(5px);
    }
    .menu-header {
        color: #e67e22;
        font-weight: bold;
        margin-bottom: 5px;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    /* Naprawa pól liczbowych - usuwanie strzałek i formatowanie */
    input[type=number] {
        -moz-appearance: textfield;
    }
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none;
        margin: 0; 
    }
    
    /* Ukrycie dekoracji Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
""", unsafe_allow_html=True)

# --- LOGIKA SESJI (Baza danych w pamięci) ---
if 'history' not in st.session_state:
    st.session_state.history = []

# --- PASEK BOCZNY ---
with st.sidebar:
    st.markdown('<h1 style="color: #e67e22; text-align: center;">PIZZA SYSTEM</h1>', unsafe_allow_html=True)
    st.markdown('<hr style="border-color: #465a6d;">', unsafe_allow_html=True)

    # PRZYWRÓCONE KAFELKI MENU
    st.markdown('<div class="menu-header"><i class="fas fa-database"></i> OPERACJE</div>', unsafe_allow_html=True)
    
    if st.button("📥 Pobierz i Zapisz", use_container_width=True):
        if st.session_state.history:
            st.toast("Dane zarchiwizowane pomyślnie!")
        else:
            st.warning("Brak danych do zapisu.")

    if st.button("💾 Pobierz dane", use_container_width=True):
        st.toast("Generowanie raportu Excel/CSV...")

    st.markdown('<div style="margin-top: 20px;" class="menu-header"><i class="fas fa-tools"></i> SYSTEM</div>', unsafe_allow_html=True)
    
    if st.button("🔄 Odśwież system", use_container_width=True):
        st.rerun()

    if st.button("⚙️ Ustawienia pizzerii", use_container_width=True):
        st.sidebar.info("Moduł ustawień w budowie.")

# --- GŁÓWNY PANEL ---
col_main, col_hist = st.columns([0.6, 0.4])

with col_main:
    st.markdown("## 🍕 Nowe Rozliczenie")
    
    with st.container():
        # NAPRAWA ZER: value=None sprawia, że pole jest puste na starcie
        kwota_brutto = st.number_input(
            "Kwota całkowita z raportu (zł)", 
            min_value=0.0, 
            value=None, 
            step=0.01, 
            format="%.2f",
            placeholder="Wpisz kwotę..."
        )
        
        wydatki_gotowkowe = st.number_input(
            "Wydatki gotówkowe (zakupy/paliwo)", 
            min_value=0.0, 
            value=None, 
            step=0.01, 
            format="%.2f",
            placeholder="0.00"
        )
        
        pracownik = st.text_input("Osoba rozliczająca", placeholder="Imię i nazwisko")

        if st.button("✅ ZATWIERDŹ I OBLICZ", use_container_width=True, type="primary"):
            if kwota_brutto is not None:
                do_oddania = kwota_brutto - (wydatki_gotowkowe if wydatki_gotowkowe else 0)
                
                # Dodanie do historii
                nowy_wpis = {
                    "Data": datetime.now().strftime("%H:%M:%S"),
                    "Pracownik": pracownik if pracownik else "Brak danych",
                    "Brutto": kwota_brutto,
                    "Wydatki": wydatki_gotowkowe if wydatki_gotowkowe else 0,
                    "Netto": do_oddania
                }
                st.session_state.history.insert(0, nowy_wpis)
                
                st.balloons()
                st.success(f"### DO ODDANIA: {do_oddania:.2f} zł")
            else:
                st.error("BŁĄD: Musisz podać kwotę brutto!")

# --- SEKCJA HISTORII (Prawa strona) ---
with col_hist:
    st.markdown("### 📂 Ostatnie wpisy")
    if st.session_state.history:
        for entry in st.session_state.history[:5]:  # Pokaż 5 ostatnich
            with st.expander(f"🕒 {entry['Data']} - {entry['Pracownik']}"):
                st.write(f"**Brutto:** {entry['Brutto']:.2f} zł")
                st.write(f"**Wydatki:** {entry['Wydatki']:.2f} zł")
                st.write(f"---")
                st.write(f"**Suma:** {entry['Netto']:.2f} zł")
    else:
        st.info("Historia jest obecnie pusta.")

# --- STOPKA ---
st.markdown("---")
st.caption(f"Zalogowano jako: Administrator | Data: {datetime.now().strftime('%Y-%m-%d')}")
