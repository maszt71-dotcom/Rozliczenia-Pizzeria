import streamlit as st
import pandas as pd
import os
import io
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
REPORT_DIR = 'nocne_raporty'
if not os.path.exists(REPORT_DIR): os.makedirs(REPORT_DIR)

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
    if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

def clean_text(text):
    if not isinstance(text, str): return str(text)
    return text.encode('ascii', 'ignore').decode('ascii').strip()

def create_pdf(df_to_pdf, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 15, txt="RAPORT FINANSOWY PIZZERIA", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(212, 237, 218); pdf.set_text_color(21, 87, 36)
    pdf.cell(190, 10, txt=f" PRZYCHOD OGOLNY: {s_og:.2f} zl", ln=True, fill=True)
    pdf.set_fill_color(255, 243, 205); pdf.set_text_color(133, 100, 4)
    pdf.cell(190, 10, txt=f" GOTOWKA (SUMA): {s_got:.2f} zl", ln=True, fill=True)
    pdf.set_fill_color(248, 215, 218); pdf.set_text_color(114, 28, 36)
    pdf.cell(190, 10, txt=f" WYDATKI GOTOWKOWE: {s_wyd:.2f} zl", ln=True, fill=True)
    pdf.ln(10); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 8, "Data zapisu", 1); pdf.cell(25, 8, "Kwota", 1); pdf.cell(35, 8, "Data zdarz.", 1); pdf.cell(90, 8, "Typ / Opis", 1); pdf.ln()
    pdf.set_font("Arial", size=9)
    for _, row in df_to_pdf.iterrows():
        pdf.cell(40, 8, clean_text(row['Data']), 1); pdf.cell(25, 8, f"{row['Kwota']:.2f}", 1, 0, 'R')
        pdf.cell(35, 8, clean_text(row['Data zdarzenia']), 1, 0, 'C')
        info = f"{clean_text(row['Typ'])} {clean_text(row['Opis']) if pd.notna(row['Opis']) else ''}"
        pdf.cell(90, 8, info[:50], 1); pdf.ln()
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- AUTOMATYCZNY RAPORT NOCNY (2:00) ---
teraz = datetime.now()
plik_nocny = f"{REPORT_DIR}/raport_{teraz.strftime('%Y%m%d')}.pdf"

if teraz.hour >= 2 and not os.path.exists(plik_nocny):
    d = load_data()
    da = d[d['Status'] == 'Aktywny'].copy()
    da['Kwota'] = pd.to_numeric(da['Kwota'], errors='coerce').fillna(0)
    s1 = da[da['Typ'] == 'Przychód ogólny']['Kwota'].sum()
    s2 = da[da['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
    s3 = da[da['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s2
    pdf_bytes = create_pdf(da.iloc[::-1], s1, s3, s2)
    with open(plik_nocny, "wb") as f:
        f.write(pdf_bytes)

# --- DANE DO WIDOKU ---
data = load_data()
df_active = data[data['Status'] == 'Aktywny'].copy()
df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

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

# NAPRAWIONY PRZYCISK RAPORTU NOCNEGO
if os.path.exists(plik_nocny):
    try:
        with open(plik_nocny, "rb") as f:
            pdf_data_night = f.read() # Wczytujemy do RAM, żeby przycisk działał od razu
        st.success("✅ Masz gotowy raport nocny z godziny 02:00!")
        st.download_button(
            label="📥 POBIERZ RAPORT NOCNY",
            data=pdf_data_night,
            file_name=os.path.basename(plik_nocny),
            mime="application/pdf",
            use_container_width=True,
            key="night_report_btn"
        )
    except:
        st.error("Błąd odczytu raportu nocnego.")

# --- KAFELKI SUM ---
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><b>PRZYCHÓD OGÓLNY</b><br><b style="font-size:20px;">{s_og:,.2f} zł</b></div>', unsafe_allow_html=True)
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
    st.markdown(f'<div style="background-color:{bg_got}; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid {brd_got}; height: 100px;"><b>GOTÓWKA (SUMA)</b><br><b style="font-size:20px;">{s_got:,.2f} zł</b></div>', unsafe_allow_html=True)
    if st.button("➕ Dodaj Gotówkę", use_container_width=True):
        if "os_v18" not in st.session_state: st.session_state.os_v18 = None
        @st.dialog("Dodaj Gotówkę")
        def add_g():
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            for o in osoby:
                if st.button(o, use_container_width=True, key=f"b_{o}"): st.session_state.os_v18 = o
                if st.session_state.get("os_v18") == o:
                    with st.container(border=True):
                        kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None, placeholder=" ", key=f"k_{o}")
                        da = st.date_input("Data zdarzenia", datetime.now(), key=f"d_{o}")
                        if st.button("ZAPISZ", type="primary", use_container_width=True, key=f"s_{o}"):
                            if kw:
                                n = {'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Typ': f"Gotówka - {o}", 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%Y-%m-%d")}
                                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                                st.session_state.os_v18 = None; st.rerun()
                        if st.button("WYJDŹ", use_container_width=True, key=f"e_{o}"):
                            st.session_state.os_v18 = None; st.rerun()
        st.session_state.os_v18 = None
        add_g()

with c3:
    st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><b>WYDATKI GOTÓWKOWE</b><br><b style="font-size:20px;">{s_wyd:,.2f} zł</b></div>', unsafe_allow_html=True)
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
if "t_key" not in st.session_state: st.session_state.t_key = 0
event = st.dataframe(df_h.style.apply(apply_row_styles, axis=1), use_container_width=True, on_select="rerun", selection_mode="multi-row", key=f"table_{st.session_state.t_key}",
    column_config={"Data": st.column_config.TextColumn("Data zapisu"), "Kwota": st.column_config.NumberColumn("Kwota", format="%.2f zł"), "Data zdarzenia": st.column_config.TextColumn("Data zdarzenia"), "Typ": None})

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Opcje")
    
    # 1. ZWYKŁY RAPORT
    pdf_normal = create_pdf(df_h, s_og, s_got, s_wyd)
    st.download_button(label="📥 POBIERZ RAPORT PDF", data=pdf_normal, file_name=f"raport_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
    
    st.divider()

    # 2. RAPORT I ZEROWANIE
    if "wipe_step" not in st.session_state: st.session_state.wipe_step = 0
    if st.session_state.wipe_step == 0:
        if st.download_button(label="📥 POBIERZ RAPORT I WYZERUJ DANE", data=pdf_normal, file_name=f"raport_koncowy_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True, type="primary"):
            st.session_state.wipe_step = 1; st.rerun()
    elif st.session_state.wipe_step == 1:
        st.warning("Czy na pewno WYZEROWAĆ dane?")
        if st.button("TAK, ZERUJ", type="primary", use_container_width=True): st.session_state.wipe_step = 2; st.rerun()
        if st.button("ANULUJ", use_container_width=True): st.session_state.wipe_step = 0; st.rerun()
    elif st.session_state.wipe_step == 2:
        st.error("JESTEŚ PEWIEN?")
        if st.button("POTWIERDZAM – CZYŚĆ", type="primary", use_container_width=True):
            full = load_data(); full.loc[full['Status'] == 'Aktywny', 'Status'] = f"Arch_{datetime.now().strftime('%Y%m%d')}"; save_data(full)
            st.session_state.wipe_step = 0; st.rerun()
        if st.button("NIE, WRÓĆ", use_container_width=True): st.session_state.wipe_step = 0; st.rerun()

    st.divider()
    # Usuwanie zaznaczonych
    selected = event.selection.rows
    if selected:
        if "ask_s" not in st.session_state: st.session_state.ask_s = False
        if not st.session_state.ask_s:
            if st.button("🗑️ USUŃ ZAZNACZONE", use_container_width=True): st.session_state.ask_s = True; st.rerun()
        else:
            st.error("Usunąć?"); u1, u2 = st.columns(2)
            if u1.button("TAK"):
                f = load_data(); f.loc[df_h.index[selected], 'Status'] = 'Usunięty'; save_data(f)
                st.session_state.ask_s = False; st.session_state.t_key += 1; st.rerun()
            if u2.button("NIE"): st.session_state.ask_s = False; st.session_state.t_key += 1; st.rerun()
    
    st.divider()
    if st.button("🔄 ODŚWIEŻ", use_container_width=True): st.rerun()
