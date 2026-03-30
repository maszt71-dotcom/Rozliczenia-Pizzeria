import streamlit as st
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF
from datetime import datetime
import pytz
from streamlit_cookies_manager import CookieManager
from supabase import create_client, Client

# --- 0. POŁĄCZENIE Z SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Funkcja czasu dla Polski
def get_now():
    return datetime.now(pytz.timezone("Europe/Warsaw"))

# --- FUNKCJA BEZPIECZEŃSTWA DLA PDF ---
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

# --- FUNKCJA WYSYŁKI E-MAIL ---
def send_email_with_reports(pdf_data, csv_data):
    receiver_email = "mange929598@gmail.com"
    sender_email = "mange929598@gmail.com"
    password = "hlqivtidxgchoqdi"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = f"Raport Pizzeria - {get_now().strftime('%d.%m.%Y %H:%M')}"
    msg.attach(MIMEText("Automatyczny raport z systemu.", "plain"))

    for content, ext in [(pdf_data, "pdf"), (csv_data, "csv")]:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(content)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename=raport.{ext}")
        msg.attach(part)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Błąd wysyłki maila: {e}")
        return False

# --- 1. KONFIGURACJA I LOGOWANIE ---
st.set_page_config(
    page_title="Pizzeria",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# --- 2. DANE Z SUPABASE ---
def load_data():
    res = supabase.table("finanse").select("*").order("id").execute()
    if res.data:
        return pd.DataFrame(res.data)
    return pd.DataFrame(columns=["id", "data", "typ", "kwota", "opis", "status", "data_zdarzenia"])

data = load_data()
df_active_calc = data[data["status"] == "Aktywny"].copy()

if not df_active_calc.empty:
    df_active_calc["kwota"] = pd.to_numeric(df_active_calc["kwota"], errors="coerce").fillna(0)
    s_og = df_active_calc[df_active_calc["typ"] == "Przychód ogólny"]["kwota"].sum()
    s_wyd = df_active_calc[df_active_calc["typ"] == "Wydatki gotówkowe"]["kwota"].sum()
    s_got = df_active_calc[df_active_calc["typ"].astype(str).str.contains("Gotówka", na=False)]["kwota"].sum() - s_wyd
else:
    s_og, s_wyd, s_got = 0.0, 0.0, 0.0

# --- 3. GENERATOR PDF ---
def create_pdf(df, p, g, w):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, pdf_safe(f"RAPORT ZAMKNIECIA - {get_now().strftime('%d.%m.%Y')}"), ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(212, 237, 218)
    pdf.cell(63, 10, pdf_safe(f"Przychod: {p:.2f} zl"), border=1, fill=True, align="C")

    if g < 0:
        pdf.set_fill_color(255, 0, 0)
        pdf.set_text_color(255, 255, 255)
    else:
        pdf.set_fill_color(255, 243, 205)
        pdf.set_text_color(0, 0, 0)

    pdf.cell(64, 10, pdf_safe(f"Gotowka: {g:.2f} zl"), border=1, fill=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(248, 215, 218)
    pdf.cell(63, 10, pdf_safe(f"Wydatki: {w:.2f} zl"), border=1, ln=1, fill=True, align="C")
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(20, 8, "Data", border=1, fill=True, align="C")
    pdf.cell(50, 8, "Typ", border=1, fill=True, align="C")
    pdf.cell(30, 8, "Kwota", border=1, fill=True, align="C")
    pdf.cell(90, 8, "Opis", border=1, ln=1, fill=True, align="C")

    pdf.set_font("Helvetica", size=9)
    fill = False
    for _, row in df[df["status"] == "Aktywny"].iterrows():
        if fill:
            pdf.set_fill_color(245, 245, 245)
        else:
            pdf.set_fill_color(255, 255, 255)

        pdf.cell(20, 8, pdf_safe(str(row["data_zdarzenia"])), border=1, fill=True, align="C")
        pdf.cell(50, 8, pdf_safe(str(row["typ"])), border=1, fill=True)
        pdf.cell(30, 8, pdf_safe(f"{float(row['kwota']):.2f} zl"), border=1, fill=True, align="R")
        pdf.cell(90, 8, pdf_safe(str(row["opis"])), border=1, ln=1, fill=True)
        fill = not fill

    return pdf.output(dest="S").encode("latin-1")

# --- 4. STANY SESJI ---
if "s" not in st.session_state:
    st.session_state.s = ""
if "os" not in st.session_state:
    st.session_state.os = None
if "selected_ids" not in st.session_state:
    st.session_state.selected_ids = []
if "lock_step" not in st.session_state:
    st.session_state.lock_step = 0
if "show_delete_confirm" not in st.session_state:
    st.session_state.show_delete_confirm = False

# --- 5. WIDOK GŁÓWNY ---
st.title("🍕 Rozliczenie Pizzerii")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(
        f'<div style="background-color:#d4edda; padding:15px; border-radius:10px; text-align:center;">Przychód: <b>{s_og:,.2f} zł</b></div>',
        unsafe_allow_html=True
    )
    if st.button("➕ DODAJ", key="p"):
        st.session_state.s = "P" if st.session_state.s != "P" else ""
        st.rerun()

    if st.session_state.s == "P":
        with st.container(border=True):
            d_p = st.date_input("Data zdarzenia", get_now().date(), key="date_p")
            kw_p = st.number_input("Kwota", value=None, step=1.0, key="p_v", placeholder="Wpisz kwotę")
            if st.button("DODAJ", key="save_p", use_container_width=True, type="primary"):
                if kw_p is not None and kw_p > 0:
                    supabase.table("finanse").insert({
                        "data": get_now().strftime("%d.%m %H:%M"),
                        "typ": "Przychód ogólny",
                        "kwota": float(kw_p),
                        "opis": "",
                        "status": "Aktywny",
                        "data_zdarzenia": d_p.strftime("%d.%m")
                    }).execute()
                    st.session_state.s = ""
                    st.rerun()

with c2:
    got_bg = "#FF0000" if s_got < 0 else "#fff3cd"
    got_txt = "white" if s_got < 0 else "black"
    st.markdown(
        f'<div style="background-color:{got_bg}; color:{got_txt}; padding:15px; border-radius:10px; text-align:center;">Gotówka: <b>{s_got:,.2f} zł</b></div>',
        unsafe_allow_html=True
    )
    if st.button("➕ DODAJ", key="g"):
        st.session_state.s = "G" if st.session_state.s != "G" else ""
        st.session_state.os = None
        st.rerun()

    if st.session_state.s == "G":
        with st.container(border=True):
            osoby = ["🏢 Bufet", "🚗 Kierowca 1", "🚗 Kierowca 2", "🚗 Kierowca 3", "🚗 Kierowca 4"]
            for o in osoby:
                if st.button(o, key=f"os_{o}", use_container_width=True):
                    st.session_state.os = o if st.session_state.os != o else None
                    st.rerun()

                if st.session_state.os == o:
                    with st.container(border=True):
                        st.markdown(f"Dla: **{o}**")
                        d_g = st.date_input("Data", get_now().date(), key=f"date_g_{o}")
                        kw_g = st.number_input("Kwota", value=None, step=1.0, key=f"g_v_{o}", placeholder="Wpisz kwotę")
                        if st.button("DODAJ", key=f"save_g_{o}", use_container_width=True, type="primary"):
                            if kw_g is not None and kw_g > 0:
                                supabase.table("finanse").insert({
                                    "data": get_now().strftime("%d.%m %H:%M"),
                                    "typ": f"Gotówka - {o}",
                                    "kwota": float(kw_g),
                                    "opis": "",
                                    "status": "Aktywny",
                                    "data_zdarzenia": d_g.strftime("%d.%m")
                                }).execute()
                                st.session_state.s = ""
                                st.session_state.os = None
                                st.rerun()

with c3:
    st.markdown(
        f'<div style="background-color:#f8d7da; padding:15px; border-radius:10px; text-align:center;">Wydatki: <b>{s_wyd:,.2f} zł</b></div>',
        unsafe_allow_html=True
    )
    if st.button("➕ DODAJ", key="w"):
        st.session_state.s = "W" if st.session_state.s != "W" else ""
        st.rerun()

    if st.session_state.s == "W":
        with st.container(border=True):
            d_w = st.date_input("Data zdarzenia", get_now().date(), key="date_w")
            kw_w = st.number_input("Kwota", value=None, step=1.0, key="w_v", placeholder="Wpisz kwotę")
            op_w = st.text_input("Opis", key="desc_w")
            if st.button("DODAJ", key="save_w", use_container_width=True, type="primary"):
                if kw_w is not None and kw_w > 0:
                    supabase.table("finanse").insert({
                        "data": get_now().strftime("%d.%m %H:%M"),
                        "typ": "Wydatki gotówkowe",
                        "kwota": float(kw_w),
                        "opis": op_w,
                        "status": "Aktywny",
                        "data_zdarzenia": d_w.strftime("%d.%m")
                    }).execute()
                    st.session_state.s = ""
                    st.rerun()

# --- 6. PASEK BOCZNY ---
with st.sidebar:
    st.header("⚙️ Menu")

    if st.button("📧 WYŚLIJ RAPORT", use_container_width=True, type="primary"):
        pdf_f = create_pdf(df_active_calc, s_og, s_got, s_wyd)
        csv_f = df_active_calc.to_csv(index=False).encode("utf-8")
        if send_email_with_reports(pdf_f, csv_f):
            st.success("✅ Wysłano raport!")

    st.divider()

    if st.button("🔒 ZAMKNIJ I ROZLICZ OKRES", type="primary", use_container_width=True):
        st.session_state.lock_step = 1

    if st.session_state.get("lock_step", 0) >= 1:
        with st.container(border=True):
            h = st.text_input("Hasło Szefa:", type="password", key="boss_pass_sidebar")
            if h == "szef123":
                if st.button("✅ POTWIERDZAM I ROZLICZAM", use_container_width=True, key="confirm_close_sidebar"):
                    if not df_active_calc.empty:
                        # --- ZAPIS RAPORTU DO BAZY ---
                        okres_od = df_active_calc["data_zdarzenia"].min()
                        okres_do = df_active_calc["data_zdarzenia"].max()
                        supabase.table("raporty").insert({
                            "okres_od": str(okres_od),
                            "okres_do": str(okres_do),
                            "suma_przychodow": float(s_og),
                            "suma_gotowki": float(s_got),
                            "suma_wydatkow": float(s_wyd)
                        }).execute()
                        
                        p_r = create_pdf(df_active_calc, s_og, s_got, s_wyd)
                        c_r = df_active_calc.to_csv(index=False).encode("utf-8")
                        send_email_with_reports(p_r, c_r)

                        for rid in df_active_calc["id"].tolist():
                            supabase.table("finanse").update({"status": "Rozliczono"}).eq("id", int(rid)).execute()

                        st.session_state.lock_step = 0
                        st.rerun()

            if st.button("Anuluj", use_container_width=True, key="cancel_close_sidebar"):
                st.session_state.lock_step = 0
                st.rerun()

    st.divider()

    if len(st.session_state.selected_ids) > 0:
        if st.button(
            f"🗑️ USUŃ LINIĘ ({len(st.session_state.selected_ids)})",
            use_container_width=True,
            type="primary",
            key="delete_sidebar_btn"
        ):
            st.session_state.show_delete_confirm = True

        if st.session_state.get("show_delete_confirm", False):
            st.warning("Czy na pewno chcesz usunąć zaznaczoną linię / linie?")

            if st.button(
                "✅ POTWIERDŹ USUNIĘCIE",
                use_container_width=True,
                type="primary",
                key="delete_sidebar_confirm"
            ):
                for rid in st.session_state.selected_ids:
                    supabase.table("finanse").delete().eq("id", int(rid)).execute()

                st.session_state.selected_ids = []
                st.session_state.show_delete_confirm = False
                st.rerun()

            if st.button("Anuluj", use_container_width=True, key="delete_sidebar_cancel"):
                st.session_state.show_delete_confirm = False
                st.rerun()
    else:
        st.session_state.show_delete_confirm = False

    st.divider()

    _ = st.download_button(
        "📥 Pobierz CSV",
        data=df_active_calc.to_csv(index=False).encode("utf-8"),
        file_name="raport.csv",
        use_container_width=True
    )

    _ = st.download_button(
        "📥 Pobierz PDF",
        data=create_pdf(df_active_calc, s_og, s_got, s_wyd),
        file_name="raport.pdf",
        use_container_width=True
    )

    st.divider()

    if st.button("🔓 Wyloguj", use_container_width=True):
        cookies["is_logged"] = "false"
        cookies.save()
        st.rerun()

# --- 7. HISTORIA ---
st.divider()
st.subheader("Historia wpisów (Bieżący okres)")

if not df_active_calc.empty:
    df_editor_input = df_active_calc.iloc[::-1].copy()
    df_editor_input = df_editor_input[["id", "data", "data_zdarzenia", "typ", "kwota", "opis"]]
    df_editor_input.insert(0, "Wybierz", False)

    res = st.data_editor(
        df_editor_input,
        column_config={
            "Wybierz": st.column_config.CheckboxColumn("Wybierz", width="small"),
            "id": None,
            "kwota": st.column_config.NumberColumn("Kwota", format="%.2f zł"),
        },
        disabled=["id", "data", "data_zdarzenia", "typ", "kwota", "opis"],
        hide_index=True,
        use_container_width=True,
        key="pizza_editor"
    )

    selected_ids = res[res["Wybierz"] == True]["id"].tolist()

    if st.session_state.selected_ids != selected_ids:
        st.session_state.selected_ids = selected_ids
        st.session_state.show_delete_confirm = False
        st.rerun()
else:
    st.info("Brak wpisów w obecnym okresie.")

# --- 8. ARCHIWUM RAPORTÓW (Z BAZY) ---
st.divider()
st.subheader("📋 Archiwum Zamkniętych Raportów")

def load_reports():
    res = supabase.table("raporty").select("*").order("id", desc=True).execute()
    if res.data:
        return pd.DataFrame(res.data)
    return pd.DataFrame()

df_rep_hist = load_reports()
if not df_rep_hist.empty:
    st.dataframe(
        df_rep_hist[["okres_od", "okres_do", "suma_przychodow", "suma_gotowki", "suma_wydatkow"]],
        column_config={
            "suma_przychodow": "Przychód",
            "suma_gotowki": "Gotówka",
            "suma_wydatkow": "Wydatki"
        },
        hide_index=True,
        use_container_width=True
    )
