import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_cookies_manager import CookieManager

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Rozliczenie Pizzerii", layout="wide", page_icon="🍕")

cookies = CookieManager()
if not cookies.ready():
    st.stop()

# --- USTAWIENIA ---
MOJE_HASLO = "dup@"
DB_FILE = 'finanse_data.csv'

# --- LOGIKA DOSTĘPU ---
if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    wpisane = st.text_input("Hasło", type="password")
    if st.button("Zaloguj się"):
        if wpisane == MOJE_HASLO:
            cookies["is_logged"] = "true"
            cookies.save()
            st.rerun()
    st.stop()

# --- OBSŁUGA DANYCH ---
def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# Załaduj dane
data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

# Obliczenia do kafelków
s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

# --- STYLIZACJA TABELI ---
def apply_row_styles(row):
    color = ''
    if row['Typ'] == 'Przychód ogólny':
        color = 'background-color: #d4edda; color: #155724'
    elif row['Typ'] == 'Wydatki gotówkowe':
        color = 'background-color: #f8d7da; color: #721c24'
    elif 'Gotówka' in row['Typ']:
        color = 'background-color: #fff3cd; color: #856404'
    return [color] * len(row)

# --- WIDOK GŁÓWNY (KAFELKI) ---
st.title("🍕 Rozliczenie Pizzerii")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:18px;">{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ Dodaj Przychód", use_container_width=True):
        @st.dialog("Dodaj Przychód")
        def add_p():
            kw = st.number_input("Kwota", min_value=0.0, format="%.2f")
            da = st.date_input("Z dnia", datetime.now())
            if st.button("ZAPISZ"):
                nowy = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                save_data(pd.concat([load_data(), pd.DataFrame([nowy])], ignore_index=True))
                st.rerun()
        add_p()

with c2:
    bg_got = "#fff3cd" if s_got >= 0 else "#f8d7da"
    brd_got = "#ffc107" if s_got >= 0 else "#dc3545"
    st.markdown(f'<div style="background-color:{bg_got}; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid {brd_got}; height: 100px;"><span style="color:#856404; font-size:11px; font-weight:bold;">GOTÓWKA (SUMA)</span><br><b style="color:#856404; font-size:18px;">{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ Rozlicz Gotówkę", use_container_width=True):
        @st.dialog("Rozlicz Gotówkę")
        def add_g():
            osoba = st.selectbox("Kto?", ["Bufet", "Kierowca 1", "Kierowca 2", "Kierowca 3", "Kierowca 4"])
            kw = st.number_input("Kwota", min_value=0.0, format="%.2f")
            da = st.date_input("Z dnia", datetime.now())
            if st.button("ZAPISZ"):
                nowy = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': f"Gotówka - {osoba}", 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                save_data(pd.concat([load_data(), pd.DataFrame([nowy])], ignore_index=True))
                st.rerun()
        add_g()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI GOTÓWKOWE</span><br><b style="color:#721c24; font-size:18px;">{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➖ Dodaj Wydatek", use_container_width=True):
        @st.dialog("Dodaj Wydatek")
        def add_w():
            kw = st.number_input("Kwota", min_value=0.0, format="%.2f")
            da = st.date_input("Z dnia", datetime.now())
            op = st.text_input("Opis")
            if st.button("ZAPISZ"):
                nowy = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%d.%m")}
                save_data(pd.concat([load_data(), pd.DataFrame([nowy])], ignore_index=True))
                st.rerun()
        add_w()

# --- TABELA HISTORII ---
st.divider()
st.subheader("📂 Historia zdarzeń")

df_h = df_active[['Data', 'Typ', 'Kwota', 'Data zdarzenia', 'Opis']].iloc[::-1]
sel = st.dataframe(
    df_h.style.apply(apply_row_styles, axis=1), 
    use_container_width=True, 
    on_select="rerun", 
    selection_mode="multi-row",
    column_config={
        "Kwota": st.column_config.NumberColumn(format="%.2f zł"),
        "Opis": st.column_config.TextColumn(width="large")
    }
)

# --- SIDEBAR (MENU BOCZNE) ---
with st.sidebar:
    st.header("⚙️ Opcje")
    if sel.selection.rows:
        if st.button("🗑️ USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            current_all = load_data()
            indices_to_delete = df_h.index[sel.selection.rows]
            current_all.loc[indices_to_delete, 'Status'] = 'Usunięty'
            save_data(current_all)
            st.rerun()
    
    st.divider()
    if st.button("🔄 ODŚWIEŻ", use_container_width=True):
        st.rerun()
