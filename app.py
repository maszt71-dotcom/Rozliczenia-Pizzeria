import streamlit as st
import pandas as pd
import os
import uuid
from datetime import datetime, date

# =====================================================
# USTAWIENIA
# =====================================================
st.set_page_config(
    page_title="Pizzeria",
    page_icon="🍕",
    layout="wide"
)

# =====================================================
# STYLE
# =====================================================
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
}
[data-testid="stSidebar"] {
    min-width: 280px;
    max-width: 320px;
}
.stButton > button {
    width: 100%;
    border-radius: 10px;
    font-weight: 600;
}
div[data-testid="stMetric"] {
    background: #111827;
    border-radius: 12px;
    padding: 12px;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# PLIKI
# =====================================================
HISTORIA_FILE = "historia.csv"
RAPORTY_FILE = "raporty.csv"

# =====================================================
# FUNKCJE
# =====================================================
def format_kwota(x):
    try:
        return f"{float(x):,.2f} zł".replace(",", " ")
    except:
        return "0.00 zł"

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

def load_historia():
    if os.path.exists(HISTORIA_FILE):
        df = pd.read_csv(HISTORIA_FILE)
        expected = ["id", "data", "osoba", "typ", "opis", "kwota"]
        for c in expected:
            if c not in df.columns:
                df[c] = ""
        return df[expected]
    return pd.DataFrame(columns=["id", "data", "osoba", "typ", "opis", "kwota"])

def save_historia(df):
    df.to_csv(HISTORIA_FILE, index=False)

def load_raporty():
    if os.path.exists(RAPORTY_FILE):
        df = pd.read_csv(RAPORTY_FILE)
        expected = ["Data wykonania", "Data od", "Data do", "Zakres dat", "Przychód", "Gotówka", "Wydatki"]
        for c in expected:
            if c not in df.columns:
                df[c] = ""
        return df[expected]
    return pd.DataFrame(columns=[
        "Data wykonania", "Data od", "Data do",
        "Zakres dat", "Przychód", "Gotówka", "Wydatki"
    ])

def save_raporty(df):
    df.to_csv(RAPORTY_FILE, index=False)

def policz_podsumowanie(df):
    if df.empty:
        return 0.0, 0.0, 0.0

    rob = df.copy()
    rob["kwota"] = pd.to_numeric(rob["kwota"], errors="coerce").fillna(0)

    przychod = rob.loc[rob["typ"] == "Przychód", "kwota"].sum()
    gotowka = rob.loc[rob["typ"] == "Gotówka", "kwota"].sum()
    wydatki = rob.loc[rob["typ"] == "Wydatek", "kwota"].sum()

    return round(przychod, 2), round(gotowka, 2), round(wydatki, 2)

def filtruj_zakres(df, data_od, data_do):
    if df.empty:
        return df.copy()

    rob = df.copy()
    rob["data_dt"] = pd.to_datetime(rob["data"], errors="coerce").dt.date
    wynik = rob[(rob["data_dt"] >= data_od) & (rob["data_dt"] <= data_do)].copy()
    return wynik.drop(columns=["data_dt"], errors="ignore")

# =====================================================
# SESSION STATE
# =====================================================
if "historia_df" not in st.session_state:
    st.session_state.historia_df = load_historia()

if "raporty_df" not in st.session_state:
    st.session_state.raporty_df = load_raporty()

if "delete_target_id" not in st.session_state:
    st.session_state.delete_target_id = None

if "delete_step_1" not in st.session_state:
    st.session_state.delete_step_1 = False

# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:
    st.header("Menu")

    st.markdown("### Usuń linię")

    hist_df = st.session_state.historia_df.copy()

    if not hist_df.empty:
        hist_df["kwota"] = pd.to_numeric(hist_df["kwota"], errors="coerce").fillna(0)

        options = hist_df["id"].tolist()

        def format_option(x):
            row = hist_df[hist_df["id"] == x].iloc[0]
            return f"{row['data']} | {row['osoba']} | {row['typ']} | {format_kwota(row['kwota'])}"

        selected_id = st.selectbox(
            "Wybierz wpis",
            options=options,
            format_func=format_option,
            index=None,
            placeholder="Kliknij i wybierz linię"
        )

        if selected_id:
            st.session_state.delete_target_id = selected_id
            st.session_state.delete_step_1 = False

            if st.button("Usuń linię"):
                st.session_state.delete_step_1 = True

        if st.session_state.delete_step_1 and st.session_state.delete_target_id:
            st.warning("Potwierdź usunięcie tej linii")

            if st.button("Potwierdzam usunięcie"):
                st.session_state.historia_df = st.session_state.historia_df[
                    st.session_state.historia_df["id"] != st.session_state.delete_target_id
                ].reset_index(drop=True)

                save_historia(st.session_state.historia_df)
                st.session_state.delete_target_id = None
                st.session_state.delete_step_1 = False
                st.success("Linia usunięta")
                st.rerun()
    else:
        st.info("Brak wpisów")

# =====================================================
# NAGŁÓWEK
# =====================================================
st.title("🍕 Pizzeria")
st.caption("Base version + raporty")

# =====================================================
# FORMULARZ DODAWANIA
# =====================================================
st.subheader("Dodaj wpis")

c1, c2, c3 = st.columns(3)

with c1:
    data_wpisu = st.date_input("Data", value=date.today())
    osoba = st.selectbox("Osoba", ["Bar", "Kuchnia", "Sala", "Dostawca", "Inne"])

with c2:
    typ = st.selectbox("Typ", ["Przychód", "Gotówka", "Wydatek"])
    opis = st.text_input("Opis", value="")

with c3:
    kwota_txt = st.text_input("Kwota", value="", placeholder="np. 250,50")

if st.button("Dodaj wpis"):
    kwota = parse_kwota(kwota_txt)

    if kwota is None:
        st.error("Wpisz poprawną kwotę")
    else:
        nowy = pd.DataFrame([{
            "id": str(uuid.uuid4()),
            "data": data_wpisu.strftime("%Y-%m-%d"),
            "osoba": osoba,
            "typ": typ,
            "opis": opis.strip(),
            "kwota": kwota
        }])

        st.session_state.historia_df = pd.concat(
            [st.session_state.historia_df, nowy],
            ignore_index=True
        )

        save_historia(st.session_state.historia_df)
        st.success("Dodano wpis")
        st.rerun()

# =====================================================
# PODSUMOWANIE
# =====================================================
przychod_sum, gotowka_sum, wydatki_sum = policz_podsumowanie(st.session_state.historia_df)

st.subheader("Podsumowanie")
m1, m2, m3 = st.columns(3)
m1.metric("Przychód", format_kwota(przychod_sum))
m2.metric("Gotówka", format_kwota(gotowka_sum))
m3.metric("Wydatki", format_kwota(wydatki_sum))

# =====================================================
# HISTORIA
# =====================================================
st.subheader("Historia")

if not st.session_state.historia_df.empty:
    show_df = st.session_state.historia_df.copy()
    show_df["kwota"] = pd.to_numeric(show_df["kwota"], errors="coerce").fillna(0)
    show_df = show_df.sort_values(by="data", ascending=False)

    show_df = show_df[["data", "osoba", "typ", "opis", "kwota"]].copy()
    show_df.columns = ["Data", "Osoba", "Typ", "Opis", "Kwota"]
    show_df["Kwota"] = show_df["Kwota"].apply(format_kwota)

    st.dataframe(
        show_df,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Brak historii")

# =====================================================
# RAPORTY
# =====================================================
st.subheader("Raporty z apki")

r1, r2 = st.columns(2)
with r1:
    raport_od = st.date_input("Data od", value=date.today(), key="raport_od")
with r2:
    raport_do = st.date_input("Data do", value=date.today(), key="raport_do")

if raport_od > raport_do:
    st.error("Data od nie może być większa niż data do")
else:
    raport_df = filtruj_zakres(st.session_state.historia_df, raport_od, raport_do)
    raport_przychod, raport_gotowka, raport_wydatki = policz_podsumowanie(raport_df)

    rr1, rr2, rr3 = st.columns(3)
    rr1.metric("Przychód z zakresu", format_kwota(raport_przychod))
    rr2.metric("Gotówka z zakresu", format_kwota(raport_gotowka))
    rr3.metric("Wydatki z zakresu", format_kwota(raport_wydatki))

    if st.button("Zapisz raport"):
        zakres = f"{raport_od.strftime('%d-%m-%Y')} do {raport_do.strftime('%d-%m-%Y')}"

        nowy_raport = pd.DataFrame([{
            "Data wykonania": datetime.now().strftime("%d-%m-%Y %H:%M"),
            "Data od": str(raport_od),
            "Data do": str(raport_do),
            "Zakres dat": zakres,
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

# =====================================================
# TABELA RAPORTÓW
# =====================================================
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
        raporty_show[col] = pd.to_numeric(raporty_show[col], errors="coerce").fillna(0)
        raporty_show[col] = raporty_show[col].apply(format_kwota)

    st.dataframe(
        raporty_show,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Brak zapisanych raportów")
