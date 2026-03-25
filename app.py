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
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z",
        "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N", "Ó": "O", "Ś": "S", "Ź": "Z", "Ż": "Z"
    }
    t = str(txt)
    for k, v in rep.items():
        t = t.replace(k, v)
    return t.encode("ascii", "ignore").decode("ascii")

# --- 1. KONFIG ---
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

# --- 3. PDF ---
def create_pdf(df, s_og, s_got, s_wyd):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(
        0, 10,
        pdf_safe(f"RAPORT PIZZERIA - {datetime.now().strftime('%d.%m.%Y')}"),
        ln=True, align="C"
    )
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(
        0, 10,
        pdf_safe(f"Przychod: {s_og:.2f} zl | Gotowka: {s_got:.2f} zl | Wydatki: {s_wyd:.2f} zl"),
        ln=True
    )
    pdf.ln(5)

    pdf.set_font("Helvetica", size=10)

    if df.empty:
        pdf.cell(0, 8, pdf_safe("Brak danych"), ln=True)
    else:
        for _, row in df.iterrows():
            try:
                kw = float(row["Kwota"])
            except:
                kw = 0.0

            linia = f"{row['Data zdarzenia']} | {row['Typ']} | {kw:.2f} zl | {row['Opis']}"
            pdf.multi_cell(0, 8, pdf_safe(linia), border=1)

    return pdf.output(dest="S").encode("latin-1")

# --- SESSION ---
if "s" not in st.session_state:
    st.session_state.s = ""

if "cash_open" not in st.session_state:
    st.session_state.cash_open = False

if "cash_person" not in st.session_state:
    st.session_state.cash_person = None

# --- UI ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

# --- PRZYCHÓD ---
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
        st.session_state.s = "P" if st.session_state.s != "P" else ""
        st.rerun()

    if st.session_state.s == "P":
        with st.container(border=True):
            d_p = st.date_input("Data zdarzenia", datetime.now(), key="date_p")
            kw_p = st.number_input("Kwota", min_value=0.0, step=1.0, key="val_p")

            if st.button("ZAPISZ", key="save_p"):
                n = {
                    "Data": datetime.now().strftime("%d.%m %H:%M"),
                    "Typ": "Przychód ogólny",
                    "Kwota": float(kw_p),
                    "Opis": "",
                    "Status": "Aktywny",
                    "Data zdarzenia": d_p.strftime("%d.%m")
                }
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                st.session_state.s = ""
                st.rerun()

# --- GOTÓWKA ---
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

        for i in range(0, len(osoby), 2):
            cols = st.columns(2)

            for j in range(2):
                idx = i + j
                if idx >= len(osoby):
                    continue

                osoba = osoby[idx]

                with cols[j]:
                    if st.button(osoba, key=f"os_{idx}", use_container_width=True):
                        if st.session_state.cash_person == osoba:
                            st.session_state.cash_person = None
                        else:
                            st.session_state.cash_person = osoba
                        st.rerun()

                    # Formularz pokazuje się dokładnie pod klikniętą osobą
                    if st.session_state.cash_person == osoba:
                        with st.container(border=True):
                            st.markdown(f"**Wybrano:** {osoba}")

                            d_g = st.date_input(
                                "Data zdarzenia",
                                datetime.now(),
                                key=f"date_g_{idx}"
                            )

                            kw_g = st.number_input(
                                "Kwota",
                                min_value=0.0,
                                step=1.0,
                                key=f"val_g_{idx}"
                            )

                            col_btn1, col_btn2 = st.columns(2)

                            with col_btn1:
                                if st.button("ZAPISZ", key=f"save_g_{idx}", use_container_width=True):
                                    n = {
                                        "Data": datetime.now().strftime("%d.%m %H:%M"),
                                        "Typ": f"Gotówka - {osoba}",
                                        "Kwota": float(kw_g),
                                        "Opis": "",
                                        "Status": "Aktywny",
                                        "Data zdarzenia": d_g.strftime("%d.%m")
                                    }
                                    save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                                    st.session_state.cash_person = None
                                    st.session_state.cash_open = False
                                    st.rerun()

                            with col_btn2:
                                if st.button("ANULUJ", key=f"cancel_g_{idx}", use_container_width=True):
                                    st.session_state.cash_person = None
                                    st.rerun()

# --- WYDATKI ---
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
        st.session_state.s = "W" if st.session_state.s != "W" else ""
        st.rerun()

    if st.session_state.s == "W":
        with st.container(border=True):
            d_w = st.date_input("Data zdarzenia", datetime.now(), key="date_w")
            kw_w = st.number_input("Kwota", min_value=0.0, step=1.0, key="val_w")
            op_w = st.text_input("Opis", key="desc_w")

            if st.button("ZAPISZ W", key="save_w"):
                n = {
                    "Data": datetime.now().strftime("%d.%m %H:%M"),
                    "Typ": "Wydatki gotówkowe",
                    "Kwota": float(kw_w),
                    "Opis": op_w,
                    "Status": "Aktywny",
                    "Data zdarzenia": d_w.strftime("%d.%m")
                }
                save_data(pd.concat([load_data(), pd.DataFrame([n])], ignore_index=True))
                st.session_state.s = ""
                st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Menu")

    st.download_button(
        "📥 Pobierz CSV",
        data=df_active.to_csv(index=False).encode("utf-8"),
        file_name="raport.csv",
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
        full.loc[df_active.index, "Status"] = "Archiwum"
        save_data(full)
        st.rerun()

# --- TABELA ---
st.divider()

show_df = df_active[["Data zdarzenia", "Typ", "Kwota", "Opis"]].iloc[::-1].copy()
show_df["Kwota"] = pd.to_numeric(show_df["Kwota"], errors="coerce").fillna(0)
show_df["Kwota"] = show_df["Kwota"].map(lambda x: f"{x:,.2f} zł")

st.dataframe(
    show_df,
    use_container_width=True,
    hide_index=True
)
