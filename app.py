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
            return pd.DataFrame(columns=['ID', 'Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
    return pd.DataFrame(columns=['ID', 'Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])

def zapisz_dane(df):
    df.to_csv(DB_FILE, index=False)

# Inicjalizacja danych - DANE NIE ZNIKNĄ PO ODŚWIEŻENIU
if 'data_log' not in st.session_state:
    st.session_state.data_log = wczytaj_dane()

# --- 3. STYLE CSS (Wygląd i naprawa pól) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #2c3e50 !important; color: white; }
    .top-container { display: flex; justify-content: space-between; gap: 15px; margin-bottom: 30px; }
    .card {
        flex: 1; padding: 25px; border-radius: 12px; color: white; text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    .card-income { background: linear-gradient(135deg, #27ae60, #2ecc71); }
    .card-expenses { background: linear-gradient(135deg, #c0392b, #e74c3c); }
    .card-total { background: linear-gradient(135deg, #2980b9, #3498db); }
    .card-val { font-size: 30px; font-weight: bold; margin-top: 10px; }
    
    /* Naprawa pól liczbowych - brak zer */
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
    if st.button("📥 Pobierz i Zapisz", use_container_width=True):
        zapisz_dane(st.session_state.data_log)
        st.success("Zapisano!")
    
    csv_bytes = st.session_state.data_log.to_csv(index=False).encode('utf-8')
    st.download_button("💾 Eksportuj CSV", data=csv_bytes, file_name="raport.csv", use_container_width=True)

    st.markdown("---")
    # USUWANIE ZAZNACZONYCH LINII
    st.markdown("### 🗑️ Usuwanie wpisów")
    if not st.session_state.data_log.empty:
        opcje_do_usuniecia = st.session_state.data_log.apply(lambda x: f"{x['Godzina']} - {x['Kwota']} zł ({x['Opis'][:10]}...)", axis=1).tolist()
        wybrane = st.multiselect("Zaznacz linie do usunięcia:", opcje_do_usuniecia)
        
        if st.button("USUŃ ZAZNACZONE", type="secondary", use_container_width=True):
            indices_to_drop = [opcje_do_usuniecia.index(w) for w in wybrane]
            st.session_state.data_log = st.session_state.data_log.drop(st.session_state.data_log.index[indices_to_drop]).reset_index(drop=True)
            zapisz_dane(st.session_state.data_log)
            st.rerun()

# --- 6. TRZY KONTENERY NA GÓRZE ---
st.markdown(f"""
    <div class="top-container">
        <div class="card card-income"><div class="card-lab">OBRÓT</div><div class="card-val">{suma_in:.2f} zł</div></div>
        <div class="card card-expenses"><div class="card-lab">WYDATKI</div><div class="card-val">{suma_out:.2f} zł</div></div>
        <div class="card card-total"><div class="card-lab">BILANS</div><div class="card-val">{bilans:.2f} zł</div></div>
    </div>
""", unsafe_allow_html=True)

# --- 7. ROZWIJANY KONTENER DO WPISÓW ---
with st.expander("➕ KLIKNIJ TUTAJ, ABY DODAĆ NOWY WPIS", expanded=False):
    c1, c2, c3 = st.columns([2, 2, 4])
    with c1:
        kwota_in = st.number_input("Kwota (zł):", min_value=0.0, value=None, step=0.01, placeholder="0.00")
    with c2:
        typ_in = st.selectbox("Rodzaj:", ["Przychód (Obrót)", "Wydatek (Zakupy/Paliwo)"])
    with c3:
        opis_in = st.text_input("Notatka:", placeholder="np. Raport dzienny...")

    if st.button("ZATWIERDŹ I ZAPISZ WPIS", type="primary", use_container_width=True):
        if kwota_in is not None:
            teraz = datetime.now()
            nowy = pd.DataFrame([[teraz.strftime("%Y-%m-%d"), teraz.strftime("%H:%M:%S"), typ_in, kwota_in, opis_in]], 
                                columns=['Data', 'Godzina', 'Typ', 'Kwota', 'Opis'])
            st.session_state.data_log = pd.concat([nowy, st.session_state.data_log], ignore_index=True)
            zapisz_dane(st.session_state.data_log)
            st.rerun()

# --- 8. HISTORIA ---
st.markdown("### 📂 Historia rozliczeń")
st.dataframe(st.session_state.data_log, use_container_width=True, hide_index=True)
