import streamlit as st
import pandas as pd
import os
import uuid
from datetime import datetime, date

# =========================
# USTAWIENIA STRONY
# =========================
st.set_page_config(
    page_title="Pizzeria",
    page_icon="🍕",
    layout="wide"
)

# =========================
# CSS
# =========================
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
}
div[data-testid="stMetric"] {
    background: #111827;
    border-radius: 12px;
    padding: 10px;
}
.stButton > button {
    border-radius: 10px;
    font-weight: 600;
}
.stTextInput input, .stSelectbox div, .stDateInput input {
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# PLIKI
# =========================
HISTORIA_FILE = "historia.csv"
RAPORTY_FILE = "raporty.csv"

# =========================
# FUNKCJE POMOCNICZE
# =========================
def parse_kwota(txt):
    if txt is None:
        return None
    txt = str(txt).strip().replace("zł", "").replace(" ", "").replace(",", ".")
    if txt == "":
        return None
    try:
        return round(float(txt), 2)
    except:
        return None

def format_kwota(x):
    try:
        return f"{float(x):,.2f} zł".replace(",", " ")
    except:
        return "0.00 zł"

def load_historia():
    if os.path.exists(HISTORIA_FILE):
        df = pd.read_csv(HISTORIA_FILE)
        expected_cols = ["id", "data", "osoba", "typ", "opis", "kwota"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        return df[expected_cols]
    return pd.DataFrame(columns=["id", "data", "osoba", "typ", "opis", "kwota"])

def save_historia(df):
    df.to_csv(HISTORIA_FILE, index=False)

def load_raporty():
    if os.path.exists(RAPORTY_FILE):
        df = pd.read_csv(RAPORTY_FILE)
        expected_cols = ["Data wykonania", "Data od", "Data do", "Zakres dat", "Przychód", "Gotówka", "Wydatki"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        return df[expected_cols]
    return pd.DataFrame(columns=[
        "Data wykonania",
        "Data od",
        "Data do",
        "Zakres dat",
        "Przychód",
        "Gotówka",
        "Wydatki"
    ])

def save_raporty(df):
    df.to_csv(RAPORTY_FILE, index=False)

def licz_podsumowanie(df):
    if df.empty:
        return 0.0, 0.0, 0.0

    rob = df.copy()
    rob["kwota"] = pd.to_numeric(rob["kwota"], errors="coerce").fillna(0)

    przychod = rob.loc[rob["typ"] == "Przychód", "kwota"].sum()
    gotowka = rob.loc[rob["typ"] == "Gotówka", "kwota"].sum()
    wydatki = rob.loc[rob["typ"] == "Wydatek", "kwota"].sum()

    return round(przychod, 2), round(gotowka, 2), round(wydatki, 2)

def filtruj_po_datach(df, data_od, data_do):
    if df.empty:
        return df.copy()

    rob = df.copy()
    rob["data_dt"] = pd.to_datetime(rob["data"], errors="coerce").dt.date
    wynik = rob[(rob["data_dt"] >= data_od) & (rob["data_dt"] <= data_do)].copy()
    return wynik.drop(columns=["data_dt"], errors="ignore")

# =========================
# SESSION STATE
# =========================
if "historia_df" not in st.session_state:
    st.session_state.historia_df = load_historia()

if "raporty_df" not in st.session_state:
    st.session_state.raporty_df = load_raporty()

if "delete_target_id" not in st.session_state:
    st.session_state.delete_target_id = None

if "delete_confirm_1" not in st.session_state:
    st.session_state.delete_confirm_1 = False

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("Menu")

    st.markdown("### Usuń linię")

    historia_sidebar = st.session_state.historia_df.copy()

    if not historia_sidebar.empty:
        historia_sidebar["kwota"] = pd.to_numeric(historia_sidebar["kwota"], errors="coerce").fillna(0)

        options = historia_sidebar["id"].tolist()

        def format_opcji(x):
            row = historia_sidebar[historia_sidebar["id"] == x].iloc[0]
            return f"{row['data']} | {row['osoba']} | {row['typ']} | {format_kwota(row['kwota'])}"

        zaznaczona_id = st.selectbox(
            "Wybierz linię",
            options=options,
            format_func=format_opcji,
            index=None,
            placeholder="Wybierz wpis do usunięcia"
        )

        if zaznaczona_id:
            st.session_state.delete_target_id = zaznaczona_id
            st.session_state.delete_confirm_1 = False
            if st.button("Usuń linię", use_container_width=True):
                st.session_state.delete_confirm_1 = True

        if st.session_state.delete_confirm_1 and st.session_state.delete_target_id:
            st.warning("Drugie zabezpieczenie: potwierdź usunięcie")
            if st.button("Potwierdzam usunięcie", use_container_width=True):
                st.session_state.historia_df = st.session_state.historia_df[
                    st.session_state.historia_df["id"] != st.session_state.delete_target_id
                ].reset_index(drop=True)

                save_historia(st.session_state.historia_df)
                st.session_state.delete_target_id = None
                st.session_state.delete_confirm_1 = False
                st.success("Linia usunięta")
                st.rerun()
    else:
        st.info("Brak wpisów do usunięcia")

# =========================
# NAGŁÓWEK
# =========================
st.title("🍕 Pizzeria")
st.caption("Historia wpisów + raporty")

# =========================
# DODAWANIE WPISU
# =========================
st.subheader("Dodaj wpis")

col1, col2, col3 = st.columns(3)

with col1:
    data_wpisu = st.date_input("Data", value=date.today())
    osoba = st.selectbox("Osoba", ["Bar", "Kuchnia", "Sala", "Dostawca", "Inne"])

with col2:
    typ = st.selectbox("Typ", ["Przychód", "Gotówka", "Wydatek"])
    opis = st.text_input("Opis", value="")

with col3:
    kwota_txt = st.text_input("Kwota", value="", placeholder="np. 1250,50")

if st.button("Dodaj wpis", use_container_width=True):
    kwota = parse_kwota(kwota_txt)

    if kwota is None:
        st.error("Wpisz poprawną kwotę")
    else:
        nowy_wpis = pd.DataFrame([{
            "id": str(uuid.uuid4()),
            "data": data_wpisu.strftime("%Y-%m-%d"),
            "osoba": osoba,
            "typ": typ,
            "opis": opis.strip(),
            "kwota": kwota
        }])

        st.session_state.historia_df = pd.concat(
            [st.session_state.historia_df, nowy_wpis],
            ignore_index=True
        )

        save_historia(st.session_state.historia_df)
        st.success("Wpis dodany")
        st.rerun()

# =========================
# PODSUMOWANIE
# =========================
przychod_sum, gotowka_sum, wydatki_sum = licz_podsumowanie(st.session_state.historia_df)

st.subheader("Podsumowanie")
m1, m2, m3 = st.columns(3)
m1.metric("Przychód", format_kwota(przychod_sum))
m2.metric("Gotówka", format_kwota(gotowka_sum))
m3.metric("Wydatki", format_kwota(wydatki_sum))

# =========================
# HISTORIA
# =========================
st.subheader("Historia")

if not st.session_state.historia_df.empty:
    df_show = st.session_state.historia_df.copy()

    df_show["kwota"] = pd.to_numeric(df_show["kwota"], errors="coerce").fillna(0)
    df_show = df_show.sort_values(by="data", ascending=False)

    # ukrywamy id
    df_show = df_show[["data", "osoba", "typ", "opis", "kwota"]].copy()
    df_show.columns = ["Data", "Osoba", "Typ", "Opis", "Kwota"]
    df_show["Kwota"] = df_show["Kwota"].apply(format_kwota)

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Brak wpisów w historii")

# =========================
# RAPORTY
# =========================
st.subheader("Raporty z apki")

r1, r2 = st.columns(2)
with r1:
    raport_data_od = st.date_input("Raport od", value=date.today(), key="raport_od")
with r2:
    raport_data_do = st.date_input("Raport do", value=date.today(), key="raport_do")

if raport_data_od > raport_data_do:
    st.error("Data 'od' nie może być większa niż data 'do'")
else:
    raport_df = filtruj_po_datach(st.session_state.historia_df, raport_data_od, raport_data_do)
    raport_przychod, raport_gotowka, raport_wydatki = licz_podsumowanie(raport_df)

    c1, c2, c3 = st.columns(3)
    c1.metric("Przychód w zakresie", format_kwota(raport_przychod))
    c2.metric("Gotówka w zakresie", format_kwota(raport_gotowka))
    c3.metric("Wydatki w zakresie", format_kwota(raport_wydatki))

    if st.button("Zapisz raport", use_container_width=True):
        zakres_dat = f"{raport_data_od.strftime('%d-%m-%Y')} do {raport_data_do.strftime('%d-%m-%Y')}"

        nowy_raport = pd.DataFrame([{
            "Data wykonania": datetime.now().strftime("%d-%m-%Y %H:%M"),
            "Data od": str(raport_data_od),
            "Data do": str(raport_data_do),
            "Zakres dat": zakres_dat,
            "Przychód": round(raport_przychod, 2),
            "Gotówka": round(raport_gotowka, 2),
            "Wydatki": round(raport_wydatki, 2)
        }])

        st.session_state.raporty_df = pd.concat(
            [st.session_state.raporty_df, nowy_raport],
            ignore_index=True
        )

        save_raporty(st.session_state.raporty_df)
        st.success("Raport zapisany")
        st.rerun()

# =========================
# TABELA RAPORTÓW
# =========================
if not st.session_state.raporty_df.empty:
    raporty_show = st.session_state.raporty_df.copy()

    raporty_show = raporty_show[[
        "Data wykonania",
        "Zakres dat",
        "Przychód",
        "Gotówka",
        "Wydatki"
    ]]

    for col in ["Przychód", "Gotówka", "Wydatki"]:
        raporty_show[col] = pd.to_numeric(raporty_show[col], errors="coerce").fillna(0).apply(format_kwota)

    st.dataframe(
        raporty_show,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Brak zapisanych raportów")
