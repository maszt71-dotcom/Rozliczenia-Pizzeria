import streamlit as st
import pandas as pd

# Konfiguracja
st.set_page_config(page_title="Rozliczenia Pizzeria", layout="wide")

# --- STYLE CSS (Naprawa wyglądu i zer) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background-color: #2c3e50;
        color: white;
    }
    /* Stylizacja trzech kontenerów na górze */
    .stats-container {
        display: flex;
        gap: 20px;
        margin-bottom: 25px;
    }
    .stat-card {
        flex: 1;
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    }
    .card-1 { background-color: #2ecc71; } /* Zielony */
    .card-2 { background-color: #e74c3c; } /* Czerwony */
    .card-3 { background-color: #3498db; } /* Niebieski */
    
    .stat-value { font-size: 24px; font-weight: bold; }
    .stat-label { font-size: 14px; opacity: 0.9; }

    /* Naprawa pól liczbowych */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none; margin: 0; 
    }
    </style>
""", unsafe_allow_html=True)

# --- INICJALIZACJA DANYCH ---
if 'obrot' not in st.session_state: st.session_state.obrot = 0.0
if 'wydatki' not in st.session_state: st.session_state.wydatki = 0.0

# --- PASEK BOCZNY (MENU) ---
with st.sidebar:
    st.title("🍕 Menu")
    if st.button("📥 Pobierz i Zapisz", use_container_width=True):
        st.success("Zapisano!")
    if st.button("💾 Pobierz", use_container_width=True):
        st.info("Pobieranie...")
    st.markdown("---")
    if st.button("⚙️ Ustawienia", use_container_width=True):
        pass

# --- TRZY KONTENERY NA GÓRZE ---
bilans = st.session_state.obrot - st.session_state.wydatki

st.markdown(f"""
    <div class="stats-container">
        <div class="stat-card card-1">
            <div class="stat-label">OBRÓT CAŁKOWITY</div>
            <div class="stat-value">{st.session_state.obrot:.2f} zł</div>
        </div>
        <div class="stat-card card-2">
            <div class="stat-label">WYDATKI GOTÓWKOWE</div>
            <div class="stat-value">{st.session_state.wydatki:.2f} zł</div>
        </div>
        <div class="stat-card card-3">
            <div class="stat-label">DO ROZLICZENIA</div>
            <div class="stat-value">{bilans:.2f} zł</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- FORMULARZ WPISYWANIA ---
st.subheader("Nowy wpis")
col1, col2 = st.columns(2)

with col1:
    nowa_kwota = st.number_input("Wpisz kwotę zamówienia:", min_value=0.0, value=None, step=0.01, placeholder="0.00")
with col2:
    nowe_wydatki = st.number_input("Wpisz wydatki:", min_value=0.0, value=None, step=0.01, placeholder="0.00")

if st.button("Aktualizuj liczniki", type="primary"):
    if nowa_kwota: st.session_state.obrot += nowa_kwota
    if nowe_wydatki: st.session_state.wydatki += nowe_wydatki
    st.rerun()

# --- HISTORIA ---
st.markdown("---")
st.markdown("### 📁 Historia")
# Tutaj możesz dodać tabelę z historią
