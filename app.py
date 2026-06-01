import streamlit as st
import pandas as pd
import smtplib
import base64
import hashlib
import hmac
import json
import time
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

def get_secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default

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

def parse_event_date(value):
    txt = str(value).strip()
    if not txt or txt.lower() in ("none", "nan", "nat"):
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            pass
    return None

def short_pdf_text(value, max_len=58):
    text = pdf_safe(value).replace("\n", " ").strip()
    return text if len(text) <= max_len else text[: max_len - 3] + "..."

def make_auth_token(ttl_seconds=60 * 60 * 12):
    secret = str(get_secret("AUTH_COOKIE_SECRET") or get_secret("APP_PASSWORD") or "")
    if not secret:
        return ""
    payload = {"logged": True, "exp": int(time.time()) + ttl_seconds}
    payload_raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_raw).decode("ascii")
    signature = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"

def is_valid_auth_token(token):
    secret = str(get_secret("AUTH_COOKIE_SECRET") or get_secret("APP_PASSWORD") or "")
    if not token or not secret or "." not in str(token):
        return False
    payload_b64, signature = str(token).rsplit(".", 1)
    expected = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("ascii")))
    except Exception:
        return False
    return bool(payload.get("logged")) and int(payload.get("exp", 0)) > int(time.time())

def check_secret_password(value, secret_name):
    expected = str(get_secret(secret_name) or "")
    return bool(expected) and hmac.compare_digest(str(value or ""), expected)

def insert_report_with_ids(date_from, date_to, total_income, entry_ids):
    payload = {
        "data_wygenerowania": get_now().isoformat(),
        "okres_od": date_from.strftime("%d.%m.%Y"),
        "okres_do": date_to.strftime("%d.%m.%Y"),
        "suma_przychodow": float(total_income),
        "entry_ids": [int(x) for x in entry_ids],
    }
    try:
        return supabase.table("raporty").insert(payload).execute()
    except Exception:
        payload.pop("entry_ids", None)
        st.warning("Tabela raporty nie ma kolumny entry_ids. Raport zapisano, ale archiwum będzie odtwarzane po datach.")
        return supabase.table("raporty").insert(payload).execute()

def update_finance_status(ids, status):
    ids = [int(x) for x in ids]
    if ids:
        return supabase.table("finanse").update({"status": status}).in_("id", ids).execute()
    return None

def load_report_rows(report_row):
    entry_ids = report_row.get("entry_ids", None)
    if isinstance(entry_ids, str):
        try:
            entry_ids = json.loads(entry_ids)
        except Exception:
            entry_ids = None

    if isinstance(entry_ids, list) and entry_ids:
        res = supabase.table("finanse").select("*").in_("id", [int(x) for x in entry_ids]).execute()
        return sort_df_by_data_zdarzenia(pd.DataFrame(res.data)) if res.data else pd.DataFrame()

    d_from_parsed = datetime.strptime(report_row["okres_od"], "%d.%m.%Y").date()
    d_to_parsed = datetime.strptime(report_row["okres_do"], "%d.%m.%Y").date()
    return sort_df_by_data_zdarzenia(filter_data_by_date_range(load_data(), d_from_parsed, d_to_parsed))

# --- FUNKCJA WYSYŁKI E-MAIL ---
def send_email_with_reports(pdf_data, csv_data):
    receiver_email = get_secret("REPORT_RECEIVER_EMAIL")
    sender_email = get_secret("REPORT_SENDER_EMAIL")
    password = get_secret("REPORT_EMAIL_PASSWORD")

    if not receiver_email or not sender_email or not password:
        st.error("Brakuje konfiguracji e-mail w st.secrets.")
        return False

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
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
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

if not is_valid_auth_token(cookies.get("auth_token")):
    st.title("🍕 Logowanie")
    if not get_secret("APP_PASSWORD"):
        st.error("Brakuje APP_PASSWORD w st.secrets.")
        st.stop()

    haslo = st.text_input("Hasło", type="password", autofocus=True)
    if st.button("Zaloguj"):
        if check_secret_password(haslo, "APP_PASSWORD"):
            cookies["auth_token"] = make_auth_token()
            cookies.save()
            st.rerun()
        else:
            st.error("Nieprawidłowe hasło.")
    st.stop()

# --- 2. DANE Z SUPABASE ---
def load_data():
    res = supabase.table("finanse").select("*").order("id").execute()
    if res.data:
        return pd.DataFrame(res.data)
    return pd.DataFrame(columns=["id", "data", "typ", "kwota", "opis", "status", "data_zdarzenia"])

def load_archived_reports():
    res = supabase.table("raporty").select("*").order("id", desc=True).execute()
    expected_cols = ["id", "data_wygenerowania", "okres_od", "okres_do", "suma_przychodow", "entry_ids"]
    
    if res.data:
        df = pd.DataFrame(res.data)
        for col in expected_cols:
            if col not in df.columns:
                if col == "suma_przychodow":
                    df[col] = 0.0
                elif col == "entry_ids":
                    df[col] = None
                else:
                    df[col] = "Brak daty"
        return df
        
    return pd.DataFrame(columns=expected_cols)

def filter_data_by_date_range(df, date_from, date_to):
    if df.empty:
        return df.copy()

    temp = df.copy()
    temp["date_str"] = temp["data_zdarzenia"].astype(str).str.strip()

    parsed_dates = []
    for val in temp["date_str"]:
        parsed_dates.append(parse_event_date(val))

    temp["parsed_date"] = parsed_dates
    
    filtered = temp[
        (temp["parsed_date"].notna()) &
        (temp["parsed_date"] >= date_from) &
        (temp["parsed_date"] <= date_to)
    ].copy()

    return filtered.drop(columns=["parsed_date", "date_str"], errors="ignore")

def calculate_range_sums(df):
    if df.empty:
        return 0.0, 0.0, 0.0

    temp = df.copy()
    temp["kwota"] = pd.to_numeric(temp["kwota"], errors="coerce").fillna(0)

    przychod = temp[temp["typ"] == "Przychód ogólny"]["kwota"].sum()
    wydatki = temp[temp["typ"] == "Wydatki gotówkowe"]["kwota"].sum()
    gotowka = temp[temp["typ"].astype(str).str.contains("Gotówka", na=False)]["kwota"].sum() - wydatki

    return przychod, gotowka, wydatki

# --- POMOCNICZA FUNKCJA DO SORTOWANIA PO DACIE ZDARZENIA ---
def sort_df_by_data_zdarzenia(df):
    if df.empty:
        return df
    temp = df.copy()
    parsed = []
    for val in temp["data_zdarzenia"].astype(str).str.strip():
        parsed.append(parse_event_date(val) or datetime.min.date())
    temp["_sort_date"] = parsed
    temp = temp.sort_values(by=["_sort_date", "id"], ascending=[True, True])
    return temp.drop(columns=["_sort_date"], errors="ignore")


# --- PASEK BOCZNY ---
with st.sidebar:
    st.header("⚙️ Menu")
    pokaz_rozliczone = st.checkbox("📂 Pokaż rozliczone wpisy (Archiwum)", value=False)
    st.divider()

# Ładowanie danych z bazy
data = load_data()

# Filtrowanie na podstawie wybranego trybu widoku
if pokaz_rozliczone:
    df_active_calc = data.copy()
else:
    df_active_calc = data[data["status"] == "Aktywny"].copy()

# Przeliczanie głównych kafelków finansowych
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
    pdf.cell(0, 10, pdf_safe(f"RAPORT SZCZEGOLOWY - {get_now().strftime('%d.%m.%Y')}"), ln=True, align="C")
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
    pdf.cell(28, 8, "Data", border=1, fill=True, align="C")
    pdf.cell(52, 8, "Typ", border=1, fill=True, align="C")
    pdf.cell(30, 8, "Kwota", border=1, fill=True, align="C")
    pdf.cell(80, 8, "Opis", border=1, ln=1, fill=True, align="C")

    pdf.set_font("Helvetica", size=9)
    fill = False

    df_to_print = df.copy()
    if "kwota" in df_to_print.columns:
        df_to_print["kwota"] = pd.to_numeric(df_to_print["kwota"], errors="coerce").fillna(0)

    for _, row in df_to_print.iterrows():
        if fill:
            pdf.set_fill_color(245, 245, 245)
        else:
            pdf.set_fill_color(255, 255, 255)

        data_txt = str(row.get("data_zdarzenia", ""))
        typ_txt = str(row.get("typ", ""))
        kwota_txt = f"{float(row.get('kwota', 0)):.2f} zl"
        opis_txt = short_pdf_text(row.get("opis", ""))

        pdf.cell(28, 8, pdf_safe(data_txt), border=1, fill=True, align="C")
        pdf.cell(52, 8, pdf_safe(typ_txt), border=1, fill=True)
        pdf.cell(30, 8, pdf_safe(kwota_txt), border=1, fill=True, align="R")
        pdf.cell(80, 8, opis_txt, border=1, ln=1, fill=True)

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
if "show_report_picker" not in st.session_state:
    st.session_state.show_report_picker = False
if "show_send_picker" not in st.session_state:
    st.session_state.show_send_picker = False
if "show_archive_picker" not in st.session_state:
    st.session_state.show_archive_picker = False

if "lock_confirm_1" not in st.session_state:
    st.session_state.lock_confirm_1 = False
if "lock_confirm_2" not in st.session_state:
    st.session_state.lock_confirm_2 = False

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
                        "data_zdarzenia": d_p.strftime("%d.%m.%Y")
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
                                    "data_zdarzenia": d_g.strftime("%d.%m.%Y")
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
                        "data_zdarzenia": d_w.strftime("%d.%m.%Y")
                    }).execute()
                    st.session_state.s = ""
                    st.rerun()

# --- 6. PASEK BOCZNY (AKCJE) ---
with st.sidebar:
    if st.button("📧 WYŚLIJ RAPORT", use_container_width=True, type="primary", key="open_send_picker"):
        st.session_state.show_send_picker = not st.session_state.show_send_picker
        if st.session_state.show_send_picker:
            st.session_state.show_report_picker = False
            st.session_state.show_archive_picker = False
        st.rerun()

    if st.session_state.show_send_picker:
        with st.container(border=True):
            send_date_from = st.date_input("Data od", value=get_now().date(), key="send_date_from")
            send_date_to = st.date_input("Data do", value=get_now().date(), key="send_date_to")

            if send_date_from > send_date_to:
                st.error("Data od nie może być większa niż data do")
            else:
                df_send_range = filter_data_by_date_range(df_active_calc, send_date_from, send_date_to).copy()
                df_send_range = sort_df_by_data_zdarzenia(df_send_range)
                send_p, send_g, send_w = calculate_range_sums(df_send_range)

                if st.button("📧 Wyślij PDF + CSV", use_container_width=True, type="primary", key="send_range_btn"):
                    pdf_f = create_pdf(df_send_range, send_p, send_g, send_w)
                    csv_f = df_send_range.to_csv(index=False).encode("utf-8")
                    if send_email_with_reports(pdf_f, csv_f):
                        st.success("✅ Wysłano raport!")

                if st.button("↩️ Powrót", use_container_width=True, key="send_back_btn"):
                    st.session_state.show_send_picker = False
                    st.rerun()

    st.divider()

    if st.button("🔒 ZAMKNIJ I ROZLICZ OKRES", type="primary", use_container_width=True):
        st.session_state.lock_step = 1
        st.session_state.lock_confirm_1 = False
        st.session_state.lock_confirm_2 = False
        st.rerun()

    if st.session_state.get("lock_step", 0) >= 1:
        with st.container(border=True):
            lock_date_from = st.date_input("Rozlicz od:", value=get_now().date(), key="lock_date_from_sidebar")
            lock_date_to = st.date_input("Rozlicz do:", value=get_now().date(), key="lock_date_to_sidebar")
            
            h = st.text_input("Hasło Szefa:", type="password", key="boss_pass_sidebar")
            
            if check_secret_password(h, "BOSS_PASSWORD"):
                if not st.session_state.lock_confirm_1:
                    if st.button("❓ Jesteś pewien?", use_container_width=True, type="primary", key="confirm_1_sidebar"):
                        st.session_state.lock_confirm_1 = True
                        st.rerun()
                
                elif st.session_state.lock_confirm_1 and not st.session_state.lock_confirm_2:
                    st.warning("⚠️ Tej czynności nie można cofnąć!")
                    if st.button("💥 POTWIERDZAM I ROZLICZAM", use_container_width=True, type="primary", key="confirm_2_sidebar"):
                        df_all_raw_data = load_data()
                        df_lock_range = filter_data_by_date_range(df_all_raw_data[df_all_raw_data["status"] == "Aktywny"], lock_date_from, lock_date_to).copy()
                        df_lock_range = sort_df_by_data_zdarzenia(df_lock_range)

                        if not df_lock_range.empty:
                            lock_p, lock_g, lock_w = calculate_range_sums(df_lock_range)
                            p_r = create_pdf(df_lock_range, lock_p, lock_g, lock_w)
                            c_r = df_lock_range.to_csv(index=False).encode("utf-8")
                            send_email_with_reports(p_r, c_r)

                            lock_ids = df_lock_range["id"].tolist()
                            insert_report_with_ids(lock_date_from, lock_date_to, lock_p, lock_ids)
                            update_finance_status(lock_ids, "Rozliczono")

                        st.session_state.lock_step = 0
                        st.session_state.lock_confirm_1 = False
                        st.session_state.lock_confirm_2 = False
                        st.rerun()

            if st.button("Anuluj", use_container_width=True, key="cancel_close_sidebar"):
                st.session_state.lock_step = 0
                st.session_state.lock_confirm_1 = False
                st.session_state.lock_confirm_2 = False
                st.rerun()

    st.divider()

    if len(st.session_state.selected_ids) > 0:
        if st.button(f"🗑️ USUŃ LINIĘ ({len(st.session_state.selected_ids)})", use_container_width=True, type="primary", key="delete_sidebar_btn"):
            st.session_state.show_delete_confirm = True

        if st.session_state.get("show_delete_confirm", False):
            st.warning("Czy na pewno chcesz usunąć zaznaczoną linię / linie?")
            if st.button("✅ POTWIERDŹ USUNIĘCIE", use_container_width=True, type="primary", key="delete_sidebar_confirm"):
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

    if st.button("📥 Pobierz raport", use_container_width=True, key="open_report_picker"):
        st.session_state.show_report_picker = not st.session_state.show_report_picker
        if st.session_state.show_report_picker:
            st.session_state.show_send_picker = False
            st.session_state.show_archive_picker = False
        st.rerun()

    if st.session_state.show_report_picker:
        with st.container(border=True):
            report_date_from = st.date_input("Data od", value=get_now().date(), key="report_date_from_picker")
            report_date_to = st.date_input("Data do", value=get_now().date(), key="report_date_to_picker")

            if report_date_from > report_date_to:
                st.error("Data od nie może być większa niż data do")
            else:
                df_all_database = load_data() 
                df_report_range = filter_data_by_date_range(df_all_database, report_date_from, report_date_to).copy()
                df_report_range = sort_df_by_data_zdarzenia(df_report_range)
                
                report_p, report_g, report_w = calculate_range_sums(df_report_range)

                _ = st.download_button(
                    "📥 Pobierz PDF (Szczegółowy)",
                    data=create_pdf(df_report_range, report_p, report_g, report_w),
                    file_name=f"raport_{report_date_from}_{report_date_to}.pdf",
                    use_container_width=True,
                    key="download_pdf_range"
                )

                _ = st.download_button(
                    "📥 Pobierz CSV (Szczegółowy)",
                    data=df_report_range.to_csv(index=False).encode("utf-8"),
                    file_name=f"raport_{report_date_from}_{report_date_to}.csv",
                    use_container_width=True,
                    key="download_csv_range"
                )

                if st.button("↩️ Powrót", use_container_width=True, key="report_back_btn"):
                    st.session_state.show_report_picker = False
                    st.rerun()

    st.divider()

    if st.button("📜 Archiwum raportów", use_container_width=True, key="open_archive_picker"):
        st.session_state.show_archive_picker = not st.session_state.show_archive_picker
        if st.session_state.show_archive_picker:
            st.session_state.show_send_picker = False
            st.session_state.show_report_picker = False
        st.rerun()

    if st.session_state.show_archive_picker:
        with st.container(border=True):
            st.markdown("**Zapisane zamknięcia z bazy:**")
            df_arch = load_archived_reports()
            
            if df_arch.empty:
                st.info("Brak zapisanych raportów w bazie.")
            else:
                for _, r_row in df_arch.iterrows():
                    lbl = f"📅 {r_row['okres_od']} - {r_row['okres_do']}"
                    with st.expander(lbl):
                        st.write(f"**Wygenerowano:** {r_row.get('data_wygenerowania', r_row.get('data', ''))}")
                        st.write(f"💰 Suma Przychodów: {r_row['suma_przychodow']:.2f} zł")
                        
                        try:
                            if r_row['okres_od'] == "Brak daty" or r_row['okres_do'] == "Brak daty":
                                st.warning("Ten wpis jest zbyt stary, aby odtworzyć pełne dane źródłowe.")
                            else:
                                df_filtered_arch = load_report_rows(r_row)
                                
                                st.download_button(
                                    "📥 Pobierz CSV (Dane)",
                                    data=df_filtered_arch.to_csv(index=False).encode("utf-8"),
                                    file_name=f"archiwum_{r_row['okres_od']}_{r_row['okres_do']}.csv",
                                    key=f"dl_arch_{r_row['id']}",
                                    use_container_width=True
                                )
                        except Exception:
                            st.error("Nie udało się odtworzyć pełnych danych.")

                if st.button("↩️ Powrót", use_container_width=True, key="archive_back_btn"):
                    st.session_state.show_archive_picker = False
                    st.rerun()

    st.divider()

    if st.button("🔓 Wyloguj", use_container_width=True):
        cookies["auth_token"] = ""
        cookies.save()
        st.rerun()

# --- 7. HISTORIA WPISÓW ---
st.divider()

if pokaz_rozliczone:
    st.subheader("Historia wpisów (Wszystkie dane - Archiwum)")
else:
    st.subheader("Historia wpisów (Bieżący okres)")

if not df_active_calc.empty:
    df_editor_input = sort_df_by_data_zdarzenia(df_active_calc)
    df_editor_input = df_editor_input[["id", "data", "data_zdarzenia", "typ", "kwota", "opis", "status"]]
    df_editor_input.insert(0, "Wybierz", False)

    res = st.data_editor(
        df_editor_input,
        column_config={
            "Wybierz": st.column_config.CheckboxColumn("Wybierz", width="small"),
            "id": None,
            "kwota": st.column_config.NumberColumn("Kwota", format="%.2f zł"),
            "status": st.column_config.TextColumn("Status"),
        },
        disabled=["id", "data", "data_zdarzenia", "typ", "kwota", "opis", "status"],
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


# --- 7.5 PANEL HURTOWEGO ODZYSKIWANIA CAŁEGO RAPORTU (AKTYWNY W TRYBIE ARCHIWUM) ---
if pokaz_rozliczone:
    df_raporty_baza = load_archived_reports()
    
    if not df_raporty_baza.empty:
        with st.container(border=True):
            st.markdown("### ↩️ Hurtowe Przywracanie Całego Okresu")
            st.info("Wybierz zamknięty raport z listy. Kliknięcie przycisku przywróci WSZYSTKIE wpisy z tamtego okresu z powrotem do bieżących rozliczeń.")
            
            df_raporty_baza["raport_label"] = (
                "📅 Okres: " + df_raporty_baza["okres_od"].astype(str) + 
                " do " + df_raporty_baza["okres_do"].astype(str) + 
                " | Przychód: " + df_raporty_baza["suma_przychodow"].astype(str) + " zł"
            )
            
            raporty_dict = df_raporty_baza.set_index("id").to_dict(orient="index")
            
            wybrany_raport_id = st.selectbox(
                "Wybierz raport, który chcesz anulować i przywrócić:",
                options=df_raporty_baza["id"].tolist(),
                format_func=lambda x: raporty_dict[x]["raport_label"],
                index=None,
                placeholder="Wybierz raport z listy..."
            )
            
            if wybrany_raport_id is not None:
                rap_dane = raporty_dict[wybrany_raport_id]
                
                if st.button("↩️ OTWÓRZ OKRES NA NOWO (Przywróć wszystkie wpisy)", type="primary", use_container_width=True):
                    try:
                        if rap_dane['okres_od'] == "Brak daty" or rap_dane['okres_do'] == "Brak daty":
                             st.error("Ten stary wpis nie zawiera dat. Otwarcie masowe jest niedostępne dla tego rekordu.")
                        else:
                            df_do_odblokowania = load_report_rows(rap_dane)
                            if not df_do_odblokowania.empty and "status" in df_do_odblokowania.columns:
                                df_do_odblokowania = df_do_odblokowania[df_do_odblokowania["status"] == "Rozliczono"]
                            
                            if not df_do_odblokowania.empty:
                                update_finance_status(df_do_odblokowania["id"].tolist(), "Aktywny")
                                
                                supabase.table("raporty").delete().eq("id", int(wybrany_raport_id)).execute()
                                
                                st.success(f"✅ Okres {rap_dane['okres_od']} - {rap_dane['okres_do']} został pomyślnie otwarty! Wszystkie wpisy wrócą na ekran główny.")
                                st.rerun()
                            else:
                                st.warning("Nie znaleziono rozliczonych wpisów in tym przedziale dat.")
                    except Exception as e:
                        st.error(f"Błąd podczas przywracania okresu: {e}")
    else:
        with st.container(border=True):
            st.info("Brak zamkniętych raportów w bazie danych.")


# --- 8. AKCJE MOBILNE ---
st.divider()
st.subheader("⚡ Szybkie akcje")

m1, m2, m3 = st.columns(3)

with m1:
    if st.button("📧 Raport", use_container_width=True, key="mobile_report"):
        df_sorted_mobile = sort_df_by_data_zdarzenia(df_active_calc)
        pdf_f = create_pdf(df_sorted_mobile, s_og, s_got, s_wyd)
        csv_f = df_sorted_mobile.to_csv(index=False).encode("utf-8")
        if send_email_with_reports(pdf_f, csv_f):
            st.success("✅ Wysłano raport!")

with m2:
    if st.button("🔒 Zamknij", use_container_width=True, key="mobile_lock"):
        st.session_state.lock_step = 1
        st.session_state.lock_confirm_1 = False
        st.session_state.lock_confirm_2 = False
        st.rerun()

with m3:
    if len(st.session_state.selected_ids) > 0:
        if st.button(f"🗑️ Usuń ({len(st.session_state.selected_ids)})", use_container_width=True, key="mobile_delete"):
            st.session_state.show_delete_confirm = True
            st.rerun()

if st.session_state.get("lock_step", 0) >= 1:
    with st.container(border=True):
        st.markdown("**Zamknij i rozlicz okres**")
        lock_date_from_m = st.date_input("Rozlicz od:", value=get_now().date(), key="lock_date_from_mobile")
        lock_date_to_m = st.date_input("Rozlicz do:", value=get_now().date(), key="lock_date_to_mobile")
        
        h_mobile = st.text_input("Hasło Szefa:", type="password", key="boss_pass_mobile")
        if check_secret_password(h_mobile, "BOSS_PASSWORD"):
            if not st.session_state.lock_confirm_1:
                if st.button("❓ Jesteś pewien?", use_container_width=True, type="primary", key="confirm_1_mobile"):
                    st.session_state.lock_confirm_1 = True
                    st.rerun()
            
            elif st.session_state.lock_confirm_1 and not st.session_state.lock_confirm_2:
                st.warning("⚠️ Tej czynności nie można cofnąć!")
                c_a, c_b = st.columns(2)
                with c_a:
                    if st.button("✅ Potwierdzam", use_container_width=True, key="confirm_2_mobile", type="primary"):
                        df_all_raw_data_m = load_data()
                        df_lock_range_m = filter_data_by_date_range(df_all_raw_data_m[df_all_raw_data_m["status"] == "Aktywny"], lock_date_from_m, lock_date_to_m).copy()
                        df_lock_range_m = sort_df_by_data_zdarzenia(df_lock_range_m)
                        
                        if not df_lock_range_m.empty:
                            lock_p, lock_g, lock_w = calculate_range_sums(df_lock_range_m)
                            p_r = create_pdf(df_lock_range_m, lock_p, lock_g, lock_w)
                            c_r = df_lock_range_m.to_csv(index=False).encode("utf-8")
                            send_email_with_reports(p_r, c_r)

                            lock_ids = df_lock_range_m["id"].tolist()
                            insert_report_with_ids(lock_date_from_m, lock_date_to_m, lock_p, lock_ids)
                            update_finance_status(lock_ids, "Rozliczono")

                        st.session_state.lock_step = 0
                        st.session_state.lock_confirm_1 = False
                        st.session_state.lock_confirm_2 = False
                        st.rerun()
                with c_b:
                    if st.button("Anuluj", use_container_width=True, key="cancel_close_mobile_inner"):
                        st.session_state.lock_step = 0
                        st.session_state.lock_confirm_1 = False
                        st.session_state.lock_confirm_2 = False
                        st.rerun()

        if not st.session_state.lock_confirm_1:
            if st.button("Anuluj", use_container_width=True, key="cancel_close_mobile"):
                st.session_state.lock_step = 0
                st.session_state.lock_confirm_1 = False
                st.session_state.lock_confirm_2 = False
                st.rerun()
