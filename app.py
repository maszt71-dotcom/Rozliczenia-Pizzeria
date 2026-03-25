import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime
from streamlit_cookies_manager import CookieManager

# --- PDF SAFE ---
def pdf_safe(txt):
    if not txt:
        return ""
    rep = {
        "ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ź":"z","ż":"z",
        "Ą":"A","Ć":"C","Ę":"E","Ł":"L","Ń":"N","Ó":"O","Ś":"S","Ź":"Z","Ż":"Z"
    }
    t = str(txt)
    for k, v in rep.items():
        t = t.replace(k, v)
    return t.encode("ascii", "ignore").decode("ascii")

# --- KONFIG ---
st.set_page_config(page_title="Pizzeria", layout="wide")

cookies = CookieManager()
if not cookies.ready():
    st.stop()

if cookies.get("is_logged") != "true":
    st.title("🍕 Logowanie")
    haslo = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        if haslo == "dup@":
            cookies["is_logged"] = "true"
            cookies.save()
            st.rerun()
    st.stop()

# --- DANE ---
DB_FILE = "finanse_data.csv"

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
    else:
        df = pd.DataFrame(columns=["Data", "Typ", "Kwota", "Opis", "Status", "Data zdarzenia"])

    df["Status"] = df.get("Status", "Aktywny")
    df["Status"] = df["Status"].fillna("Aktywny")
    return df

def save_data(df):
    df.to_csv(DB_FILE, index=False)

data = load_data()
df_active = data[data["Status"] == "Aktywny"].copy()
df_active["Kwota"] = pd.to_numeric(df_active["Kwota"], errors="coerce").fillna(0)

s_og = df_active[df_active["Typ"] == "Przychód ogólny"]["Kwota"].sum()
s_wyd = df_active[df_active["Typ"] == "Wydatki gotówkowe"]["Kwota"].sum()
s_got = df_active[df_active["Typ"].astype(str).str.contains("Gotówka", na=False)]["Kwota"].sum() - s_wyd

# --- PDF ---
def create_pdf(df, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, pdf_safe(f"RAPORT - {datetime.now().strftime('%d.%m.%Y')}"), ln=True, align="C")

    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, pdf_safe(f"Przychod: {s_og:.2f} zl | Gotowka: {s_got:.2f} zl | Wydatki: {s_wyd:.2f} zl"), ln=True)

    pdf.ln(5)

    pdf.set_font("Helvetica", size=10)

    for _, row in df.iterrows():
        linia = f"{row['Data zdarzenia']} | {row['Typ']} | {row['Kwota']:.2f} zl | {row['Opis']}"
        pdf.multi_cell(0, 8, pdf_safe(linia), border=1)

    return pdf.output(dest="S").encode("latin-1")

# --- SESSION ---
if "cash_open" not in st.session_state:
    st.session_state.cash_open = False

if "cash_person" not in st.session_state:
    st.session_state.cash_person = None

# --- UI ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

# --- GOTÓWKA ---
with c2:
    st.markdown(
        f'<div style="background-color:#fff3cd; padding:15px; border-radius:10px; text-align:center;">Gotówka: <b>{s_got:,.2f} zł</b></div>',
        unsafe_allow_html=True
    )

    if st.button("➕ DODAJ", key="g"):
        st.session_state.cash_open = not st.session_state.cash_open
        if not st.session_state.cash_open:
            st.session_state.cash_person = None
        st.rerun()

    if st.session_state.cash_open:
        osoby = [
            "🏢 Bufet",
            "🚗 Kierowca 1",
            "🚗 Kierowca 2",
            "🚗 Kierowca 3",
            "🚗 Kierowca 4"
        ]

        for i, osoba in enumerate(osoby):

            # PRZYCISK OSOBY
            if st.button(osoba, key=f"os_{i}", use_container_width=True):
                if st.session_state.cash_person == osoba:
                    st.session_state.cash_person = None
                else:
                    st.session_state.cash_person = osoba
                st.rerun()

            # FORMULARZ POD NIĄ
            if st.session_state.cash_person == osoba:
                with st.container(border=True):

                    st.markdown(f"**Wybrano:** {osoba}")

                    d = st.date_input(
                        "Data zdarzenia",
                        datetime.now(),
                        key=f"date_{i}"
                    )

                    kw = st.number_input(
                        "Kwota",
                        min_value=0.0,
                        step=1.0,
                        key=f"val_{i}"
                    )

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button("ZAPISZ", key=f"save_{i}", use_container_width=True):
                            n = {
                                "Data": datetime.now().strftime("%d.%m %H:%M"),
                                "Typ": f"Gotówka - {osoba}",
                                "Kwota": float(kw),
                                "Opis": "",
                                "Status": "Aktywny",
                                "Data zdarzenia": d.strftime("%d.%m")
                            }
                            save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))

                            st.session_state.cash_person = None
                            st.session_state.cash_open = False
                            st.rerun()

                    with col2:
                        if st.button("ANULUJ", key=f"cancel_{i}", use_container_width=True):
                            st.session_state.cash_person = None
                            st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.download_button("📥 PDF", data=create_pdf(df_active, s_og, s_got, s_wyd), file_name="raport.pdf")

# --- TABELA ---
st.divider()
st.dataframe(df_active[['Data zdarzenia', 'Typ', 'Kwota', 'Opis']].iloc[::-1], use_container_width=True)
