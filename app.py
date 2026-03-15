import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF
from streamlit_cookies_manager import CookieManager

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Rozliczenie Pizzerii", layout="centered", page_icon="🍕")

cookies = CookieManager()
if not cookies.ready():
    st.stop()

MOJE_HASLO = "dup@"

def check_password():
    if cookies.get("is_logged") == "true": return True
    if "password_correct" not in st.session_state:
        st.title("🍕 Rozliczenie Pizzerii")
        wpisane_haslo = st.text_input("Podaj hasło dostępu", type="password")
        if st.button("ZALOGUJ SIĘ", use_container_width=True):
            if wpisane_haslo == MOJE_HASLO:
                st.session_state["password_correct"] = True
                cookies["is_logged"] = "true"
                cookies.save()
                st.rerun()
            else:
                st.error("❌ Błędne hasło")
        return False
    return True

# --- GENERATOR PDF (KOLOROWE PODSUMOWANIE) ---
def create_pdf(dataframe, s_ogolny, s_gotowka, s_wydatki):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, f"RAPORT FINANSOWY - {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "PODSUMOWANIE:", ln=True, align="L")
    pdf.set_fill_color(212, 237, 218); pdf.cell(95, 10, "PRZYCHOD OGOLNY:", 1, 0, 'L', True); pdf.cell(95, 10, f"{s_ogolny:.2f} zl", 1, 1, 'R', True)
    pdf.set_fill_color(248, 215, 218); pdf.cell(95, 10, "WYDATKI GOTOWKOWE:", 1, 0, 'L', True); pdf.cell(95, 10, f"{s_wydatki:.2f} zl", 1, 1, 'R', True)
    pdf.set_fill_color(255, 243, 205); pdf.cell(95, 10, "GOTOWKA (W KASIE):", 1, 0, 'L', True); pdf.cell(95, 10, f"{s_gotowka:.2f} zl", 1, 1, 'R', True)
    pdf.ln(10)
    pdf.set_font("Arial", "B", 9); pdf.set_fill_color(240, 240, 240)
    headers = ["ID", "Data wpisu", "Typ", "Kwota", "Z dnia", "Opis"]
    cols = [10, 30, 35, 25, 20, 70]
    for i, h in enumerate(headers): pdf.cell(cols[i], 10, h, 1, 0, 'C', True)
    pdf.ln()
    pdf.set_font("Arial", "", 8)
    for idx, row in dataframe.iterrows():
        pdf.cell(10, 10, str(idx), 1)
        pdf.cell(30, 10, str(row['Data']), 1)
        pdf.cell(35, 10, str(row['Typ']), 1)
        pdf.cell(25, 10, f"{row['Kwota']:.2f} zl", 1)
        pdf.cell(20, 10, str(row['Data zdarzenia']), 1)
        pdf.cell(70, 10, str(row['Opis'])[:45] if str(row['Opis']) != "nan" else "", 1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

if check_password():
    DB_FILE = 'finanse_data.csv'
    def load_data():
        if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
        return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])
    def save_data(df): df.to_csv(DB_FILE, index=False)

    if 'data' not in st.session_state: st.session_state.data = load_data()
    df_active = st.session_state.data[st.session_state.data['Status'] == 'Aktywny'].copy()
    
    # Wyświetlamy datę bez godziny w "Z dnia"
    df_active['Data zdarzenia'] = df_active['Data zdarzenia'].astype(str).str[:5]
    df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)

    s_ogolny = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
    s_wydatki = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
    s_gotowka = df_active[df_active['Typ'] == 'Gotówka']['Kwota'].sum() - s_wydatki

    st.title("🍕 Rozliczenie Pizzerii")
    bg_got, brd_got, txt_got = ("#fff3cd", "#ffc107", "#856404") if s_gotowka >= 0 else ("#ff0000", "#8b0000", "#ffffff")

    @st.dialog("Dodaj nowy wpis")
    def add_entry_dialog(typ):
        st.write(f"Kategoria: **{typ}**")
        kwota = st.number_input("Podaj kwotę (zł)", min_value=0.0, step=1.0, format="%.2f", key="nowa_kwota_input", value=None)
        data_wybrana = st.date_input("Dzień zdarzenia", datetime.now())
        opis = st.text_input("Opis")
        if st.button("ZAPISZ WPIS", type="primary", use_container_width=True):
            if kwota is not None and kwota > 0:
                n = {'Data': datetime.now().strftime("%d.%m %H:%M"), 'Typ': typ, 'Kwota': float(kwota), 'Opis': opis, 'Status': 'Aktywny', 'Data zdarzenia': data_wybrana.strftime("%d.%m")}
                st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([n])], ignore_index=True)
                save_data(st.session_state.data); st.rerun()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="background-color:#d4edda; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #28a745; height: 100px;"><span style="color:#155724; font-size:11px; font-weight:bold;">PRZYCHÓD OGÓLNY</span><br><b style="color:#155724; font-size:16px;">{s_ogolny:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b1", use_container_width=True): add_entry_dialog("Przychód ogólny")
    with c3:
        st.markdown(f'<div style="background-color:#f8d7da; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid #dc3545; height: 100px;"><span style="color:#721c24; font-size:11px; font-weight:bold;">WYDATKI GOTÓWKOWE</span><br><b style="color:#721c24; font-size:16px;">{s_wydatki:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➖ Dodaj", key="b3", use_container_width=True): add_entry_dialog("Wydatki gotówkowe")
    with c2:
        st.markdown(f'<div style="background-color:{bg_got}; padding:10px; border-radius:10px; text-align:center; border-bottom: 5px solid {brd_got}; height: 100px;"><span style="color:{txt_got}; font-size:11px; font-weight:bold;">GOTÓWKA</span><br><b style="color:{txt_got}; font-size:16px;">{s_gotowka:,.2f} zł</b></div>', unsafe_allow_html=True)
        if st.button("➕ Dodaj", key="b2", use_container_width=True): add_entry_dialog("Gotówka")

    st.divider(); st.subheader("📂 Historia")

    # --- TABELA HTML (IDEALNE ZAWJANIE I KOLORY) ---
    table_style = """
    <style>
        .hist-table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px; table-layout: fixed; }
        .hist-table th { background-color: #f0f2f6; padding: 10px; border: 1px solid #ddd; text-align: left; }
        .hist-table td { padding: 10px; border: 1px solid #ddd; word-wrap: break-word; vertical-align: top; }
        .row-p { background-color: #d4edda; } .row-w { background-color: #f8d7da; } .row-g { background-color: #fff3cd; }
    </style>
    """
    
    html_content = f"{table_style}<table class='hist-table'><tr><th style='width:30px'>ID</th><th style='width:80px'>Data wpisu</th><th style='width:110px'>Typ</th><th style='width:80px'>Kwota</th><th style='width:50px'>Z dnia</th><th>Opis</th></tr>"

    # Wyświetlamy historię od najnowszych
    df_h = df_active.iloc[::-1]
    for idx, row in df_h.iterrows():
        cls = "row-p" if row['Typ']=="Przychód ogólny" else "row-w" if row['Typ']=="Wydatki gotówkowe" else "row-g"
        desc = row['Opis'] if str(row['Opis']) != "nan" else ""
        html_content += f"<tr class='{cls}'><td>{idx}</td><td>{row['Data']}</td><td>{row['Typ']}</td><td>{row['Kwota']:.2f} zł</td><td>{row['Data zdarzenia']}</td><td>{desc}</td></tr>"
    
    html_content += "</table>"
    st.markdown(html_content, unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ Opcje")
        
        # USUWANIE PO ID (najbezpieczniejsza metoda dla tabeli HTML)
        st.subheader("🗑️ Usuwanie")
        id_to_del = st.number_input("Podaj ID do usunięcia", min_value=0, max_value=2000, step=1, value=None)
        if st.button("POTWIERDŹ USUNIĘCIE", type="primary", use_container_width=True):
            if id_to_del in df_active.index:
                st.session_state.data.at[id_to_del, 'Status'] = 'Usunięty'
                save_data(st.session_state.data)
                st.rerun()
            else:
                st.error("Nie ma wpisu o takim ID!")

        st.divider()
        if st.button("WYLOGUJ", use_container_width=True):
            cookies["is_logged"] = "false"; cookies.save(); st.rerun()
            
        if not df_active.empty:
            pdf_raw = create_pdf(df_active, s_ogolny, s_gotowka, s_wydatki)
            st.download_button("📄 POBIERZ RAPORT PDF", pdf_raw, f"Raport_{datetime.now().strftime('%d_%m')}.pdf", use_container_width=True)
            
            st.divider()
            @st.dialog("Pobierz i Resetuj")
            def reset_dialog():
                st.warning("Najpierw pobierz PDF, potem resetuj!")
                st.download_button("📥 POBIERZ RAPORT OSTATECZNY", pdf_raw, "Raport_Final.pdf", use_container_width=True)
                if st.button("🔥 POTWIERDZAM RESET DNIA", type="primary", use_container_width=True):
                    st.session_state.data = pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data zdarzenia'])
                    save_data(st.session_state.data); st.rerun()
            
            if st.button("💾 POBIERZ RAPORT I RESETUJ", use_container_width=True):
                reset_dialog()
