import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime
from streamlit_cookies_manager import CookieManager

# --- TA FUNKCJA TYLKO PODMIENIA LITERY DLA PDF, ŻEBY NIE BYŁO BŁĘDU ---
def pdf_safe(txt):
    if not txt:
        return ""
    rep = {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z",
        "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N", "Ó": "O", "Ś": "S", "Ź": "Z", "Ż": "Z"
    }
    t = str(txt)
    for k, v in rep.items():
        t = t.replace(k, v)
    return t.encode("ascii", "ignore").decode("ascii")


# --- 1. KONFIGURACJA I LOGOWANIE ---
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
        else:
            st.error("Nieprawidłowe hasło")
    st.stop()


# --- 2. DANE ---
DB_FILE = "finanse_data.csv"


def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
    else:
        df = pd.DataFrame(columns=["Data", "Typ", "Kwota", "Opis", "Status", "Data zdarzenia"])

    required_cols = ["Data", "Typ", "Kwota", "Opis", "Status", "Data zdarzenia"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

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


# --- 3. GENERATOR PDF ---
def create_pdf(df, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(
        0,
        10,
        pdf_safe(f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m.%Y')}"),
        ln=True,
        align="C"
    )
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(
        0,
        8,
        pdf_safe(f"Przychod: {s_og:.2f} zl | Gotowka: {s_got:.2f} zl | Wydatki: {s_wyd:.2f} zl")
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", size=10)

    if df.empty:
        pdf.cell(0, 8, pdf_safe("Brak aktywnych danych."), ln=True)
    else:
        for _, row in df.iterrows():
            data_zdarzenia = row.get("Data zdarzenia", "")
            typ = row.get("Typ", "")
            kwota = pd.to_numeric(row.get("Kwota", 0), errors="coerce")
            if pd.isna(kwota):
                kwota = 0.0
            opis = row.get("Opis", "")

            linia = f"{data_zdarzenia} | {typ} | {kwota:.2f} zl | {opis}"
            pdf.multi_cell(0, 8, pdf_safe(linia), border=1)

    return pdf.output(dest="S").encode("latin-1")


# --- 4. WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(
        f"""
        <div style="background-color:#d4edda; padding:15px; border-radius:10px; text-align:center;">
            Przychód: <b>{s_og:,.2f} zł</b>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button("➕ DODAJ", key="p"):
        st.session_state.s = "P"
        st.rerun()

    if st.session_state.get("s", "") == "P":
        kw = st.number_input("Kwota", min_value=0.0, step=1.0, key="p_v")
        if st.button("ZAPISZ", key="save_p"):
            n = {
                "Data": datetime.now().strftime("%d.%m %H:%M"),
                "Typ": "Przychód ogólny",
                "Kwota": float(kw),
                "Opis": "",
                "Status": "Aktywny",
                "Data zdarzenia": datetime.now().strftime("%d.%m")
            }
            save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
            st.session_state.s = ""
            st.rerun()

with c2:
    st.markdown(
        f"""
        <div style="background-color:#fff3cd; padding:15px; border-radius:10px; text-align:center;">
            Gotówka: <b>{s_got:,.2f} zł</b>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button("➕ DODAJ", key="g"):
        st.session_state.s = "G"
        st.session_state.os = None
        st.rerun()

    if st.session_state.get("s", "") == "G":
        osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]

        if not st.session_state.get("os", None):
            for o in osoby:
                if st.button(o, key=f"os_{o}"):
                    st.session_state.os = o
                    st.rerun()
        else:
            kw = st.number_input(
                f"Kwota ({st.session_state.os})",
                min_value=0.0,
                step=1.0,
                key="g_v"
            )
            if st.button("ZAPISZ G", key="save_g"):
                n = {
                    "Data": datetime.now().strftime("%d.%m %H:%M"),
                    "Typ": f"Gotówka - {st.session_state.os}",
                    "Kwota": float(kw),
                    "Opis": "",
                    "Status": "Aktywny",
                    "Data zdarzenia": datetime.now().strftime("%d.%m")
                }
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                st.session_state.s = ""
                st.session_state.os = None
                st.rerun()

with c3:
    st.markdown(
        f"""
        <div style="background-color:#f8d7da; padding:15px; border-radius:10px; text-align:center;">
            Wydatki: <b>{s_wyd:,.2f} zł</b>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button("➕ DODAJ", key="w"):
        st.session_state.s = "W"
        st.rerun()

    if st.session_state.get("s", "") == "W":
        kw = st.number_input("Kwota", min_value=0.0, step=1.0, key="w_v")
        op = st.text_input("Opis", key="w_d")
        if st.button("ZAPISZ W", key="save_w"):
            n = {
                "Data": datetime.now().strftime("%d.%m %H:%M"),
                "Typ": "Wydatki gotówkowe",
                "Kwota": float(kw),
                "Opis": op,
                "Status": "Aktywny",
                "Data zdarzenia": datetime.now().strftime("%d.%m")
            }
            save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
            st.session_state.s = ""
            st.rerun()


# --- 5. PASEK BOCZNY ---
with st.sidebar:
    st.header("⚙️ Menu")

    st.download_button(
        "📥 Pobierz CSV",
        data=df_active.to_csv(index=False).encode("utf-8"),
        file_name="raport.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.download_button(
        "📥 Pobierz PDF",
        data=create_pdf(df_active, s_og, s_got, s_wyd),
        file_name="raport.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    if st.button("🗑️ USUŃ HISTORIĘ", type="primary", use_container_width=True):
        full = load_data()
        full["Status"] = full["Status"].fillna("Aktywny")
        active_mask = full["Status"] == "Aktywny"
        full.loc[active_mask, "Status"] = "Archiwum"
        save_data(full)
        st.rerun()


# --- 6. TABELA ---
st.divider()

if not df_active.empty:
    show_df = df_active[["Data zdarzenia", "Typ", "Kwota", "Opis"]].iloc[::-1].copy()
    show_df["Kwota"] = pd.to_numeric(show_df["Kwota"], errors="coerce").fillna(0)
    show_df["Kwota"] = show_df["Kwota"].map(lambda x: f"{x:,.2f} zł")
    st.dataframe(show_df, use_container_width=True, hide_index=True)
else:
    st.info("Brak aktywnych danych.")
