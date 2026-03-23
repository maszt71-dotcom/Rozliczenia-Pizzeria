import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_cookies_manager import CookieManager
from fpdf import FPDF

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
            cookies["is_logged"] = "true"; cookies.save(); st.rerun()
    st.stop()

# --- OBSŁUGA DANYCH ---
def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# Funkcja generująca PDF
def create_pdf(df_to_pdf, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('Arial', '', 'https://github.com/reingart/pyfpdf/raw/master/font/arial.ttf', uni=True) # Obsługa polskich znaków
    pdf.set_font("Arial", size=12)
    
    # Nagłówek
    pdf.cell(200, 10, txt="RAPORT FINANSOWY PIZZERIA", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Data wygenerowania: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
    # Podsumowanie
    pdf.cell(200, 10, txt=f"PRZYCHÓD OGÓLNY: {s_og:.2f} zł", ln=True)
    pdf.cell(200, 10, txt=f"GOTÓWKA (SUMA): {s_got:.2f} zł", ln=True)
    pdf.cell(200, 10, txt=f"WYDATKI GOTÓWKOWE: {s_wyd:.2f} zł", ln=True)
    pdf.ln(10)
    
    # Tabela
    pdf.set_font("Arial", size=10)
    pdf.cell(40, 10, "Data zapisu", 1)
    pdf.cell(30, 10, "Kwota", 1)
    pdf.cell(40, 10, "Data zdarz.", 1)
    pdf.cell(80, 10, "Typ / Opis", 1)
    pdf.ln()
    
    for i, row in df_to_pdf.iterrows():
        pdf.cell(40, 10, str(row['Data']), 1)
        pdf.cell(30, 10, f"{row['Kwota']:.2f} zł", 1)
        pdf.cell(40, 10, str(row['Data zdarzenia']), 1)
        pdf.cell(80, 10, f"{row['Typ']} {row['Opis'] if pd.notna(row['Opis']) else ''}", 1)
        pdf.ln()
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

# Sumy
s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd

def apply_row_styles(row):
    color = ''
    typ = str(row['Typ'])
    if typ == 'Przychód ogólny': color = 'background-color: #d4edda; color: #155724'
    elif typ == 'Wydatki gotówkowe': color = 'background-color: #f8d7da; color: #721c24'
    elif 'Gotówka' in typ: color = 'background-color: #fff3cd; color: #856404'
    return [color] * len(row)

# --- WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:18px;">{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ Dodaj Przychód", use_container_width=True):
        @st.dialog("Dodaj Przychód")
        def add_p():
            kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None, placeholder=" ")
            da = st.date_input("Data zdarzenia", datetime.now())
            if st.button("ZAPISZ"):
                if kw:
                    n = {'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Typ': 'Przychód ogólny', 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%Y-%m-%d")}
                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True)); st.rerun()
        add_p()

with c2:
    bg_got = "#fff3cd" if s_got >= 0 else "#f8d7da"; brd_got = "#ffc107" if s_got >= 0 else "#dc3545"
    st.markdown(f'<div style="background-color:{bg_got}; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid {brd_got}; height: 100px;"><span style="color:#856404; font-size:11px; font-weight:bold;">GOTÓWKA (SUMA)</span><br><b style="color:#856404; font-size:18px;">{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ Dodaj Gotówkę", use_container_width=True):
        if "os_v9" not in st.session_state: st.session_state.os_v9 = None
        @st.dialog("Dodaj Gotówkę")
        def add_g():
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            for o in osoby:
                st.button(o, use_container_width=True, key=f"b_{o}", on_click=lambda x=o: st.session_state.update({"os_v9": x}))
                if st.session_state.os_v9 == o:
                    with st.container(border=True):
                        kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None, placeholder=" ", key=f"k_{o}")
                        da = st.date_input("Data zdarzenia", datetime.now(), key=f"d_{o}")
                        if st.button("ZAPISZ", type="primary", use_container_width=True, key=f"s_{o}"):
                            if kw:
                                n = {'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Typ': f"Gotówka - {o}", 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%Y-%m-%d")}
                                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                                st.session_state.os_v9 = None; st.rerun()
                        if st.button("WYJDŹ", use_container_width=True, key=f"e_{o}"):
                            st.session_state.os_v9 = None; st.rerun()
        st.session_state.os_v9 = None
        add_g()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI GOTÓWKOWE</span><br><b style="color:#721c24; font-size:18px;">{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➖ Dodaj Wydatek", use_container_width=True):
        @st.dialog("Dodaj Wydatek")
        def add_w():
            kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None, placeholder=" ")
            da = st.date_input("Data zdarzenia", datetime.now())
            op = st.text_input("Opis", placeholder=" ")
            if st.button("ZAPISZ"):
                if kw:
                    n = {'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Typ': 'Wydatki gotówkowe', 'Kwota': float(kw), 'Opis': op, 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%Y-%m-%d")}
                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True)); st.rerun()
        add_w()

# --- TABELA ---
st.divider()
df_h = df_active[['Data', 'Kwota', 'Data zdarzenia', 'Opis', 'Typ']].iloc[::-1]
event = st.dataframe(df_h.style.apply(apply_row_styles, axis=1), use_container_width=True, on_select="rerun", selection_mode="multi-row",
    column_config={"Data": st.column_config.TextColumn("Data zapisu"), "Kwota": st.column_config.NumberColumn("Kwota", format="%.2f zł"), "Data zdarzenia": st.column_config.TextColumn("Data zdarzenia"), "Typ": None})

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Opcje")
    
    # Przycisk Raportu PDF
    pdf_data = create_pdf(df_h, s_og, s_got, s_wyd)
    st.download_button(label="📥 POBIERZ RAPORT PDF", data=pdf_data, file_name=f"raport_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
    
    st.divider()
    selected_rows = event.selection.rows
    if selected_rows:
        if "del_confirm" not in st.session_state: st.session_state.del_confirm = False
        if not st.session_state.del_confirm:
            if st.button("🗑️ USUŃ ZAZNACZONE", type="primary", use_container_width=True):
                st.session_state.del_confirm = True; st.rerun()
        else:
            st.error("Czy jesteś pewien?"); c_t, c_n = st.columns(2)
            if c_t.button("TAK", type="primary", use_container_width=True):
                full = load_data(); full.loc[df_h.index[selected_rows], 'Status'] = 'Usunięty'; save_data(full)
                st.session_state.del_confirm = False; st.rerun()
            if c_n.button("NIE", use_container_width=True):
                st.session_state.del_confirm = False; st.rerun()
    else: st.session_state.del_confirm = False
    
    st.divider()
    if st.button("🔄 ODŚWIEŻ", use_container_width=True): st.rerun()
