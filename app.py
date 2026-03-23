import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, timedelta
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
    if os.path.exists(DB_FILE): 
        df = pd.read_csv(DB_FILE)
        df['Data_dt'] = pd.to_datetime(df['Data'], format="%Y-%m-%d %H:%M", errors='coerce')
        return df
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia', 'Data_dt'])

def save_data(df):
    if 'Data_dt' in df.columns: df = df.drop(columns=['Data_dt'])
    df.to_csv(DB_FILE, index=False)

def clean_text(text):
    if not isinstance(text, str): return str(text)
    return text.encode('ascii', 'ignore').decode('ascii').strip()

def create_pdf(df_to_pdf, s_og, s_got, s_wyd, tytul="RAPORT"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 15, txt=tytul, ln=True, align='C')
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

# --- AUTOMAT: RAPORT DOBOWY 2:00-2:00 ---
teraz = datetime.now()
dzis_str = teraz.strftime('%Y%m%d')
plik_nocny = f"{REPORT_DIR}/raport_{dzis_str}.pdf"

if teraz.hour >= 2 and not os.path.exists(plik_nocny):
    d_raw = load_data()
    g_dolna = (teraz - timedelta(days=1)).replace(hour=2, minute=0, second=0, microsecond=0)
    g_gorna = teraz.replace(hour=2, minute=0, second=0, microsecond=0)
    mask = (d_raw['Data_dt'] >= g_dolna) & (d_raw['Data_dt'] < g_gorna)
    d_noc = d_raw[mask].copy()
    d_noc['Kwota'] = pd.to_numeric(d_noc['Kwota'], errors='coerce').fillna(0)
    if not d_noc.empty:
        s1 = d_noc[d_noc['Typ'] == 'Przychód ogólny']['Kwota'].sum()
        s2 = d_noc[d_noc['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
        s3 = d_noc[d_noc['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s2
        pdf_b = create_pdf(d_noc.iloc[::-1], s1, s3, s2, tytul=f"RAPORT 2:00-2:00 ({dzis_str})")
        with open(plik_nocny, "wb") as f: f.write(pdf_b)

# --- DANE ---
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

# PANCERNA LOGIKA ZNIKAJĄCEGO PRZYCISKU
if "pobrany_dzisiaj" not in st.session_state:
    st.session_state.pobrany_dzisiaj = (cookies.get("pobrany_nocny") == dzis_str)

if os.path.exists(plik_nocny) and not st.session_state.pobrany_dzisiaj:
    with open(plik_nocny, "rb") as f:
        bytes_nocny = f.read()
    st.success(f"✅ Masz gotowy raport dobowy (2:00-2:00) z dnia {teraz.strftime('%d.%m')}!")
    if st.download_button("📥 POBIERZ RAPORT NOCNY", bytes_nocny, file_name=f"raport_nocny_{dzis_str}.pdf", use_container_width=True, key="btn_nocny_final"):
        cookies["pobrany_nocny"] = dzis_str
        cookies.save()
        st.session_state.pobrany_dzisiaj = True
        st.rerun()

# --- KAFELKI ---
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
        if "os_v_last" not in st.session_state: st.session_state.os_v_last = None
        @st.dialog("Dodaj Gotówkę")
        def add_g():
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            for o in osoby:
                if st.button(o, use_container_width=True, key=f"b_{o}"): st.session_state.os_v_last = o
                if st.session_state.get("os_v_last") == o:
                    with st.container(border=True):
                        kw = st.number_input("Kwota", min_value=0.0, format="%.2f", value=None, placeholder=" ", key=f"k_{o}")
                        da = st.date_input("Data zdarzenia", datetime.now(), key=f"d_{o}")
                        if st.button("ZAPISZ", type="primary", use_container_width=True, key=f"s_{o}"):
                            if kw:
                                n = {'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Typ': f"Gotówka - {o}", 'Kwota': float(kw), 'Opis': '', 'Status': 'Aktywny', 'Data zdarzenia': da.strftime("%Y-%m-%d")}
                                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                                st.session_state.os_v_last = None; st.rerun()
                        if st.button("WYJDŹ", use_container_width=True, key=f"e_{o}"):
                            st.session_state.os_v_last = None; st.rerun()
        st.session_state.os_v_last = None
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
if "tk" not in st.session_state: st.session_state.tk = 0
event = st.dataframe(df_h.style.apply(apply_row_styles, axis=1), use_container_width=True, on_select="rerun", selection_mode="multi-row", key=f"table_{st.session_state.tk}",
    column_config={"Data": st.column_config.TextColumn("Data zapisu"), "Kwota": st.column_config.NumberColumn("Kwota", format="%.2f zł"), "Data zdarzenia": st.column_config.TextColumn("Data zdarzenia"), "Typ": None})

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Opcje")
    st.download_button(label="📥 POBIERZ RAPORT PDF", data=create_pdf(df_h, s_og, s_got, s_wyd), file_name=f"raport_{dzis_str}.pdf", mime="application/pdf", use_container_width=True)
    st.divider()
    if "ws" not in st.session_state: st.session_state.ws = 0
    if st.session_state.ws == 0:
        if st.download_button(label="📥 POBIERZ RAPORT I WYZERUJ DANE", data=create_pdf(df_h, s_og, s_got, s_wyd), file_name=f"koniec_{dzis_str}.pdf", mime="application/pdf", use_container_width=True, type="primary"):
            st.session_state.ws = 1; st.rerun()
    elif st.session_state.ws == 1:
        st.warning("Czy na pewno WYZEROWAĆ?")
        if st.button("TAK, ZERUJ", type="primary", use_container_width=True): st.session_state.ws = 2; st.rerun()
        if st.button("ANULUJ", use_container_width=True): st.session_state.ws = 0; st.rerun()
    elif st.session_state.ws == 2:
        st.error("JESTEŚ PEWIEN?")
        if st.button("POTWIERDZAM", type="primary", use_container_width=True):
            f = load_data(); f.loc[f['Status'] == 'Aktywny', 'Status'] = f"Arch_{dzis_str}"; save_data(f); st.session_state.ws = 0; st.rerun()
        if st.button("WRÓĆ", use_container_width=True): st.session_state.ws = 0; st.rerun()
    st.divider()
    selected = event.selection.rows
    if selected:
        if "as_s" not in st.session_state: st.session_state.as_s = False
        if not st.session_state.as_s:
            if st.button("🗑️ USUŃ ZAZNACZONE", use_container_width=True): st.session_state.as_s = True; st.rerun()
        else:
            st.error("Usunąć?"); c_t, c_n = st.columns(2)
            if c_t.button("TAK"):
                ff = load_data(); ff.loc[df_h.index[selected], 'Status'] = 'Usunięty'; save_data(ff); st.session_state.as_s = False; st.session_state.tk += 1; st.rerun()
            if c_n.button("NIE"): st.session_state.as_s = False; st.session_state.tk += 1; st.rerun()
    st.divider()
    if st.button("🔄 ODŚWIEŻ", use_container_width=True): st.rerun()
