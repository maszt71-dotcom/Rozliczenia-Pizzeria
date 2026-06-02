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
from datetime import datetime, timedelta
import pytz
from streamlit_cookies_manager import CookieManager
from supabase import create_client, Client

# --- 0. POŁĄCZENIE Z SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

DEFAULT_SECRETS = {
    "APP_PASSWORD": "dup@",
    "AUTH_COOKIE_SECRET": "dup@_sekret_cookie_2026",
    "REPORT_RECEIVER_EMAIL": "maszt71@gmail.com",
    "REPORT_SENDER_EMAIL": "mange929598@gmail.com",
    "REPORT_EMAIL_PASSWORD": "kwoaohaszcshiggg",
}

def get_secret(name, default=None):
    try:
        return st.secrets.get(name, DEFAULT_SECRETS.get(name, default))
    except Exception:
        return DEFAULT_SECRETS.get(name, default)

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
    generated_iso = get_now().isoformat()
    generated_label = get_now().strftime("%d.%m.%Y %H:%M")
    period_from = date_from.strftime("%d.%m.%Y")
    period_to = date_to.strftime("%d.%m.%Y")
    ids = [int(x) for x in entry_ids]

    payloads = [
        {
            "data_wygenerowania": generated_iso,
            "okres_od": period_from,
            "okres_do": period_to,
            "suma_przychodow": float(total_income),
            "entry_ids": ids,
        },
        {
            "data_wygenerowania": generated_iso,
            "okres_od": period_from,
            "okres_do": period_to,
            "suma_przychodow": float(total_income),
        },
        {
            "data": generated_label,
            "okres_od": period_from,
            "okres_do": period_to,
            "suma_przychodow": float(total_income),
            "entry_ids": ids,
        },
        {
            "data": generated_label,
            "okres_od": period_from,
            "okres_do": period_to,
            "suma_przychodow": float(total_income),
        },
    ]

    for payload in payloads:
        try:
            result = supabase.table("raporty").insert(payload).execute()
            if "entry_ids" not in payload:
                st.warning("Raport zapisano w archiwum po datach. Wpisy finansowe pozostały aktywne.")
            return result
        except Exception:
            pass

    st.warning(
        "Raport wysłano e-mailem, a wpisy finansowe pozostały aktywne, "
        "ale nie udało się zapisać pozycji w Archiwum raportów. "
        "Sprawdź w Supabase, czy tabela raporty ma kolumny: okres_od, okres_do i suma_przychodow."
    )
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
def clean_app_password(value):
    return str(value or "").replace(" ", "").strip()

def get_email_configs():
    try:
        secrets_receiver = st.secrets.get("REPORT_RECEIVER_EMAIL")
        secrets_password = st.secrets.get("REPORT_EMAIL_PASSWORD")
        if secrets_receiver and secrets_password:
            return [{
                "receiver": str(secrets_receiver).strip(),
                "sender": DEFAULT_SECRETS["REPORT_SENDER_EMAIL"],
                "password": clean_app_password(secrets_password),
                "source": "Streamlit secrets",
            }]
    except Exception:
        pass

    return [{
        "receiver": DEFAULT_SECRETS["REPORT_RECEIVER_EMAIL"],
        "sender": DEFAULT_SECRETS["REPORT_SENDER_EMAIL"],
        "password": clean_app_password(DEFAULT_SECRETS["REPORT_EMAIL_PASSWORD"]),
        "source": "kod aplikacji",
    }]

def has_email_config():
    return bool(get_email_configs())

def build_email_message(sender_email, receiver_email, pdf_data, csv_data):
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
    return msg

def send_email_with_reports(pdf_data, csv_data):
    configs = get_email_configs()
    if not configs:
        st.error("Brakuje konfiguracji e-mail.")
        return False

    for cfg in configs:
        sender = cfg["sender"]
        receiver = cfg["receiver"]
        password = cfg["password"]

        if not sender or not receiver or not password:
            st.error("Brakuje adresu nadawcy, odbiorcy albo hasła aplikacji Gmail.")
            return False

        for mode in ("SSL 465", "STARTTLS 587"):
            try:
                msg = build_email_message(sender, receiver, pdf_data, csv_data)
                if mode == "SSL 465":
                    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
                        server.login(sender, password)
                        server.send_message(msg)
                else:
                    with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
                        server.ehlo()
                        server.starttls()
                        server.ehlo()
                        server.login(sender, password)
                        server.send_message(msg)
                return True
            except smtplib.SMTPAuthenticationError:
                st.error(
                    "Gmail odrzucił hasło aplikacji dla konta nadawcy "
                    f"{sender}. Utwórz nowe hasło aplikacji dokładnie dla tego konta."
                )
                return False
            except Exception as e:
                last_error = str(e)

        st.error(
            "Nie udało się wysłać maila przez Gmail. "
            f"Nadawca: {sender}. Ostatni błąd: {last_error}"
        )
        return False

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

    with st.container(border=True):
        haslo = st.text_input("Hasło", type="password")
        if st.button("Zaloguj", type="primary", use_container_width=True):
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
        df = pd.DataFrame(res.data)
    else:
        df = pd.DataFrame()

    expected_cols = ["id", "data", "typ", "kwota", "opis", "status", "data_zdarzenia"]
    defaults = {
        "id": None,
        "data": "",
        "typ": "",
        "kwota": 0.0,
        "opis": "",
        "status": "Aktywny",
        "data_zdarzenia": "",
    }
    for col in expected_cols:
        if col not in df.columns:
            df[col] = defaults[col]
            
    if not df.empty and "status" in df.columns:
        df["status"] = df["status"].fillna("Aktywny")
    return df

def load_archived_reports():
    res = supabase.table("raporty").select("*").order("id", desc=True).execute()
    expected_cols = ["id", "data_wygenerowania", "okres_od", "okres_do", "suma_przychodow", "entry_ids"]
    
    if res.data:
        df = pd.DataFrame(res.data)
        if "data_wygenerowania" not in df.columns and "data" in df.columns:
            df["data_wygenerowania"] = df["data"]
        for col in expected_cols:
            if col not in df.columns:
                if col == "suma_przychodow":
                    df[col] = 0.0
                elif col == "entry_ids":
                    df[col] = None
                else:
                    df[col] = "Brak daty"
        df["suma_przychodow"] = pd.to_numeric(df["suma_przychodow"], errors="coerce").fillna(0.0)
        return df

    return pd.DataFrame(columns=expected_cols)

def get_next_date_after_latest_closed_report():
    df_reports = load_archived_reports()
    closed_to_dates = []
    if not df_reports.empty and "okres_do" in df_reports.columns:
        for val in df_reports["okres_do"].astype(str).str.strip():
            parsed = parse_event_date(val)
            if parsed:
                closed_to_dates.append(parsed)

    if not closed_to_dates:
        return None

    return max(closed_to_dates) + timedelta(days=1)

def parse_entry_ids(value):
    if isinstance(value, list):
        return [int(x) for x in value if str(x).strip()]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [int(x) for x in parsed if str(x).strip()]
        except Exception:
            return []
    return []

def filter_data_by_date_range(df, date_from, date_to):
    if df.empty:
        return df.copy()

    temp = df.copy()
    if "data_zdarzenia" not in temp.columns:
        temp["data_zdarzenia"] = ""
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

CARRYOVER_TYPE = "Gotówka z przeniesienia"

def public_csv_data(df):
    export_df = df.copy()
    export_df = export_df.drop(columns=["status"], errors="ignore")
    return export_df.to_csv(index=False).encode("utf-8")

def calculate_range_sums(df):
    if df.empty:
        return 0.0, 0.0, 0.0, 0.0

    temp = df.copy()
    if "kwota" not in temp.columns:
        temp["kwota"] = 0.0
    if "typ" not in temp.columns:
        temp["typ"] = ""
    temp["kwota"] = pd.to_numeric(temp["kwota"], errors="coerce").fillna(0)

    przychod = temp[temp["typ"] == "Przychód ogólny"]["kwota"].sum()
    wydatki = temp[temp["typ"] == "Wydatki gotówkowe"]["kwota"].sum()
    przeniesienie = temp[temp["typ"] == CARRYOVER_TYPE]["kwota"].sum()
    gotowka = temp[temp["typ"].astype(str).str.contains("Gotówka", na=False)]["kwota"].sum() - wydatki

    return przychod, gotowka, wydatki, przeniesienie

# --- POMOCNICZA FUNKCJA DO SORTOWANIA PO DACIE ZDARZENIA ---
def sort_df_by_data_zdarzenia(df):
    if df.empty:
        return df
    temp = df.copy()
    if "data_zdarzenia" not in temp.columns:
        temp["data_zdarzenia"] = ""
    if "id" not in temp.columns:
        temp["id"] = 0
    parsed = []
    for val in temp["data_zdarzenia"].astype(str).str.strip():
        parsed.append(parse_event_date(val) or datetime.min.date())
    temp["_sort_date"] = parsed
    temp = temp.sort_values(by=["_sort_date", "id"], ascending=[False, False])
    return temp.drop(columns=["_sort_date"], errors="ignore")


# Ładowanie pełnych danych z bazy
data = load_data()

def get_default_date_range(df):
    dates = []
    if not df.empty and "data_zdarzenia" in df.columns:
        for val in df["data_zdarzenia"].astype(str).str.strip():
            parsed = parse_event_date(val)
            if parsed:
                dates.append(parsed)
    if dates:
        latest = max(dates)
        return latest.replace(day=1), latest
    today = get_now().date()
    return today.replace(day=1), today

def get_latest_event_date(df):
    dates = []
    if not df.empty and "data_zdarzenia" in df.columns:
        for val in df["data_zdarzenia"].astype(str).str.strip():
            parsed = parse_event_date(val)
            if parsed:
                dates.append(parsed)
    return max(dates) if dates else get_now().date()


default_date_from, default_date_to = get_default_date_range(data)

df_current_all = data.copy()
latest_reset_date = get_next_date_after_latest_closed_report()
next_cumulative_date_from = st.session_state.pop("next_cumulative_date_from", None)
if next_cumulative_date_from is not None:
    st.session_state.cumulative_date_widget_version = st.session_state.get("cumulative_date_widget_version", 0) + 1

current_month_start = next_cumulative_date_from or latest_reset_date or get_now().date().replace(day=1)

# --- PASEK BOCZNY ---
with st.sidebar:
    st.header("⚙️ Menu")
    pokaz_rozliczone = False
    st.markdown("**Kwoty narastająco:**")
    cumulative_date_key = f"cumulative_date_from_{st.session_state.get('cumulative_date_widget_version', 0)}"
    cumulative_date_from = st.date_input("Pokaż od", value=current_month_start, key=cumulative_date_key)
    st.divider()

latest_data_date = get_latest_event_date(df_current_all)
cumulative_date_to = max(latest_data_date, cumulative_date_from)
if cumulative_date_from > latest_data_date:
    df_current = pd.DataFrame(columns=data.columns)
else:
    df_current = filter_data_by_date_range(df_current_all, cumulative_date_from, latest_data_date).copy()

df_active_calc = df_current.copy()
df_history = df_current.copy()

# Przeliczanie głównych kafelków finansowych
if not df_active_calc.empty:
    df_active_calc["kwota"] = pd.to_numeric(df_active_calc["kwota"], errors="coerce").fillna(0)
    st.session_state.all_finance_data = df_active_calc
    s_og = df_active_calc[df_active_calc["typ"] == "Przychód ogólny"]["kwota"].sum()
    s_wyd = df_active_calc[df_active_calc["typ"] == "Wydatki gotówkowe"]["kwota"].sum()
    s_przeniesienie = df_active_calc[df_active_calc["typ"] == CARRYOVER_TYPE]["kwota"].sum()
    s_got = df_active_calc[df_active_calc["typ"].astype(str).str.contains("Gotówka", na=False)]["kwota"].sum() - s_wyd
else:
    s_og, s_wyd, s_got, s_przeniesienie = 0.0, 0.0, 0.0, 0.0

# --- 3. GENERATOR PDF ---
def infer_report_range(df):
    dates = []
    if not df.empty and "data_zdarzenia" in df.columns:
        for val in df["data_zdarzenia"].astype(str).str.strip():
            parsed = parse_event_date(val)
            if parsed:
                dates.append(parsed)
    if dates:
        return min(dates), max(dates)
    today = get_now().date()
    return today, today

def create_pdf(df, p, g, w, przeniesienie=0.0, date_from=None, date_to=None):
    if date_from is None or date_to is None:
        inferred_from, inferred_to = infer_report_range(df)
        date_from = date_from or inferred_from
        date_to = date_to or inferred_to

    generated_at = get_now()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, pdf_safe("RAPORT SZCZEGOLOWY"), ln=True, align="C")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 7, pdf_safe(f"Zakres raportu: {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}"), ln=True, align="C")
    pdf.cell(0, 7, pdf_safe(f"Wygenerowano: {generated_at.strftime('%d.%m.%Y %H:%M')}"), ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(219, 234, 254)
    pdf.cell(190, 10, pdf_safe(f"Gotowka z przeniesienia: {przeniesienie:,.2f} zl"), border=1, ln=1, fill=True, align="C")

    pdf.set_fill_color(212, 237, 218)
    pdf.cell(63, 10, pdf_safe(f"Przychod: {p:,.2f} zl"), border=1, fill=True, align="C")

    if g < 0:
        pdf.set_fill_color(255, 0, 0)
        pdf.set_text_color(255, 255, 255)
    else:
        pdf.set_fill_color(255, 243, 205)
        pdf.set_text_color(0, 0, 0)

    pdf.cell(64, 10, pdf_safe(f"Gotowka: {g:,.2f} zl"), border=1, fill=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(248, 215, 218)
    pdf.cell(63, 10, pdf_safe(f"Wydatki: {w:,.2f} zl"), border=1, ln=1, fill=True, align="C")
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(28, 8, "Data", border=1, fill=True, align="C")
    pdf.cell(52, 8, "Typ", border=1, fill=True, align="C")
    pdf.cell(30, 8, "Kwota", border=1, fill=True, align="C")
    pdf.cell(80, 8, "Opis", border=1, ln=1, fill=True, align="C")

    pdf.set_font("Helvetica", size=9)
    df_to_print = df.copy()
    if "kwota" in df_to_print.columns:
        df_to_print["kwota"] = pd.to_numeric(df_to_print["kwota"], errors="coerce").fillna(0)

    for _, row in df_to_print.iterrows():
        data_txt = str(row.get("data_zdarzenia", ""))
        typ_txt = str(row.get("typ", ""))
        kwota_txt = f"{float(row.get('kwota', 0)):,.2f} zl"
        opis_txt = short_pdf_text(row.get("opis", ""))
        bg_color, text_color = get_pdf_row_colors(typ_txt)
        pdf.set_fill_color(*bg_color)
        pdf.set_text_color(*text_color)

        pdf.cell(28, 8, pdf_safe(data_txt), border=1, fill=True, align="C")
        pdf.cell(52, 8, pdf_safe(typ_txt), border=1, fill=True)
        pdf.cell(30, 8, pdf_safe(kwota_txt), border=1, fill=True, align="R")
        pdf.cell(80, 8, opis_txt, border=1, ln=1, fill=True)
        pdf.set_text_color(0, 0, 0)

    pdf_output = pdf.output(dest="S")
    if isinstance(pdf_output, (bytes, bytearray)):
        return bytes(pdf_output)
    return pdf_output.encode("latin-1")

def get_pdf_row_colors(typ):
    typ = str(typ)
    if typ == CARRYOVER_TYPE:
        return (219, 234, 254), (0, 0, 0)
    if typ == "Przychód ogólny":
        return (212, 237, 218), (0, 0, 0)
    if typ == "Wydatki gotówkowe":
        return (248, 215, 218), (0, 0, 0)
    if "Gotówka" in typ:
        return (255, 243, 205), (0, 0, 0)
    return (255, 255, 255), (0, 0, 0)

# --- FUNKCJA STYLIZOWANIA KOLORÓW W HISTORII ---
def style_row_by_type(row):
    typ = str(row["typ"])
    if typ == CARRYOVER_TYPE:
        return ["background-color: #dbeafe; color: black;"] * len(row)
    elif typ == "Przychód ogólny":
        return ["background-color: #d4edda; color: black;"] * len(row)
    elif "Gotówka" in typ:
        return ["background-color: #fff3cd; color: black;"] * len(row)
    elif typ == "Wydatki gotówkowe":
        return ["background-color: #f8d7da; color: black;"] * len(row)
    return [""] * len(row)

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
st.caption(f"Kwoty narastająco od {cumulative_date_from.strftime('%d.%m.%Y')} do {cumulative_date_to.strftime('%d.%m.%Y')}")

st.markdown(
    f'<div style="background-color:#dbeafe; padding:15px; border-radius:10px; text-align:center; margin-bottom:12px;">Gotówka z przeniesienia: <b>{s_przeniesienie:,.2f} zł</b></div>',
    unsafe_allow_html=True
)
if st.button("➕ DODAJ", key="zp"):
    st.session_state.s = "ZP" if st.session_state.s != "ZP" else ""
    st.rerun()

if st.session_state.s == "ZP":
    with st.container(border=True):
        d_zp = st.date_input("Data zdarzenia", get_now().date(), key="date_zp")
        kw_zp = st.number_input("Kwota", value=None, step=1.0, key="zp_v", placeholder="Wpisz kwotę")
        op_zp = st.text_input("Opis", key="desc_zp", placeholder="Opcjonalnie")
        if st.button("DODAJ", key="save_zp", use_container_width=True, type="primary"):
            if kw_zp is not None and kw_zp > 0:
                supabase.table("finanse").insert({
                    "data": get_now().strftime("%d.%m %H:%M"),
                    "typ": CARRYOVER_TYPE,
                    "kwota": float(kw_zp),
                    "opis": op_zp,
                    "status": "Aktywny",
                    "data_zdarzenia": d_zp.strftime("%d.%m.%Y")
                }).execute()
                st.session_state.s = ""
                st.rerun()

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
                send_p, send_g, send_w, send_przeniesienie = calculate_range_sums(df_send_range)

                if st.button("📧 Wyślij PDF + CSV", use_container_width=True, type="primary", key="send_range_btn"):
                    pdf_f = create_pdf(df_send_range, send_p, send_g, send_w, send_przeniesienie, send_date_from, send_date_to)
                    csv_f = public_csv_data(df_send_range)
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
            
            if lock_date_from > lock_date_to:
                st.error("Data od nie może być większa niż data do")
            else:
                if not st.session_state.lock_confirm_1:
                    if st.button("❓ Jesteś pewien?", use_container_width=True, type="primary", key="confirm_1_sidebar"):
                        st.session_state.lock_confirm_1 = True
                        st.rerun()
                
                elif st.session_state.lock_confirm_1 and not st.session_state.lock_confirm_2:
                    st.warning("⚠️ Tej czynności nie można cofnąć!")
                    if st.button("🚀 WYKONAJ ZAMKNIĘCIE", use_container_width=True, type="primary", key="confirm_2_sidebar"):
                        df_all_raw_data = load_data()
                        df_lock_range = filter_data_by_date_range(df_all_raw_data, lock_date_from, lock_date_to).copy()
                        df_lock_range = sort_df_by_data_zdarzenia(df_lock_range)

                        if not df_lock_range.empty:
                            lock_p, lock_g, lock_w, lock_przeniesienie = calculate_range_sums(df_lock_range)
                            p_r = create_pdf(df_lock_range, lock_p, lock_g, lock_w, lock_przeniesienie, lock_date_from, lock_date_to)
                            c_r = public_csv_data(df_lock_range)
                            if not has_email_config():
                                st.error("Brakuje konfiguracji e-mail w st.secrets. Okres nie został rozliczony.")
                                st.stop()

                            if not send_email_with_reports(p_r, c_r):
                                st.error("Nie rozliczono okresu, bo nie udało się wysłać raportu e-mailem.")
                                st.stop()

                            lock_ids = df_lock_range["id"].tolist()
                            insert_report_with_ids(lock_date_from, lock_date_to, lock_p, lock_ids)
                            st.session_state.next_cumulative_date_from = lock_date_to + timedelta(days=1)
                            st.success("✅ Raport wysłany e-mailem i zapisany. Wpisy pozostają aktywne.")

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
            report_date_from = st.date_input("Data od", value=default_date_from, key="report_date_from_picker")
            report_date_to = st.date_input("Data do", value=default_date_to, key="report_date_to_picker")

            if report_date_from > report_date_to:
                st.error("Data od nie może być większa niż data do")
            else:
                st.info(f"Raport zostanie pobrany z wpisów: {report_date_from.strftime('%d.%m.%Y')} - {report_date_to.strftime('%d.%m.%Y')}.")
                df_report_range = filter_data_by_date_range(df_active_calc, report_date_from, report_date_to).copy()
                df_report_range = sort_df_by_data_zdarzenia(df_report_range)
                report_p, report_g, report_w, report_przeniesienie = calculate_range_sums(df_report_range)
                st.write(f"Gotówka z przeniesienia: **{report_przeniesienie:,.2f} zł**")
                st.write(f"Przychód: **{report_p:,.2f} zł**")
                st.write(f"Gotówka: **{report_g:,.2f} zł**")
                st.write(f"Wydatki: **{report_w:,.2f} zł**")

                _ = st.download_button(
                    "📥 Pobierz PDF (Szczegółowy)",
                    data=create_pdf(df_report_range, report_p, report_g, report_w, report_przeniesienie, report_date_from, report_date_to),
                    file_name=f"raport_{report_date_from}_{report_date_to}.pdf",
                    use_container_width=True,
                    key="download_pdf_range"
                )

                _ = st.download_button(
                    "📥 Pobierz CSV (Szczegółowy)",
                    data=public_csv_data(df_report_range),
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
                                    data=public_csv_data(df_filtered_arch),
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

# --- 7. HISTORIA WPISÓW Z KOLOROWANIEM ---
st.divider()
st.subheader("Historia wpisów")

if not df_history.empty:
    df_display = sort_df_by_data_zdarzenia(df_history)
    df_display = df_display[["id", "data", "data_zdarzenia", "typ", "kwota", "opis"]]
    
    # Formatowanie wyświetlania kwot w tabeli głównej (z separatorami tysięcznymi)
    df_display["kwota"] = df_display["kwota"].map(lambda x: f"{x:,.2f} zł")

    # Tworzenie selektora usuwania jako wielokrotnego wyboru
    options_dict = {row["id"]: f"📅 {row['data_zdarzenia']} | {row['typ']} | {row['kwota']} | {row['opis']}" for _, row in df_display.iterrows()}
    
    selected_ids = st.multiselect(
        "Zaznacz wpisy do usunięcia:", 
        options=list(options_dict.keys()), 
        format_func=lambda x: options_dict[x],
        key="delete_multiselect"
    )
    
    if st.session_state.selected_ids != selected_ids:
        st.session_state.selected_ids = selected_ids
        st.session_state.show_delete_confirm = False
        st.rerun()

    # Nakładanie stylów kolorystycznych na wiersze
    styled_df = df_display.style.apply(style_row_by_type, axis=1)

    st.dataframe(
        styled_df,
        hide_index=True,
        use_container_width=True
    )
else:
    st.info("Brak wpisów w historii dla wybranego okresu.")


# --- 8. AKCJE MOBILNE ---
st.divider()
st.subheader("⚡ Szybkie akcje")

m1, m2, m3 = st.columns(3)

with m1:
    if st.button("📧 Raport", use_container_width=True, key="mobile_report"):
        df_sorted_mobile = sort_df_by_data_zdarzenia(df_active_calc)
        mobile_p, mobile_g, mobile_w, mobile_przeniesienie = calculate_range_sums(df_sorted_mobile)
        pdf_f = create_pdf(df_sorted_mobile, mobile_p, mobile_g, mobile_w, mobile_przeniesienie)
        csv_f = public_csv_data(df_sorted_mobile)
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
        
        if lock_date_from_m > lock_date_to_m:
            st.error("Data od nie może być większa niż data do")
        else:
            if not st.session_state.lock_confirm_1:
                if st.button("❓ Jesteś pewien?", use_container_width=True, type="primary", key="confirm_1_mobile"):
                    st.session_state.lock_confirm_1 = True
                    st.rerun()
            
            elif st.session_state.lock_confirm_1 and not st.session_state.lock_confirm_2:
                st.warning("⚠️ Tej czynności nie można cofnąć!")
                c_a, c_b = st.columns(2)
                with c_a:
                    if st.button("🚀 WYKONAJ ZAMKNIĘCIE", use_container_width=True, key="confirm_2_mobile", type="primary"):
                        df_all_raw_data_m = load_data()
                        df_lock_range_m = filter_data_by_date_range(df_all_raw_data_m, lock_date_from_m, lock_date_to_m).copy()
                        df_lock_range_m = sort_df_by_data_zdarzenia(df_lock_range_m)
                        
                        if not df_lock_range_m.empty:
                            lock_p, lock_g, lock_w, lock_przeniesienie = calculate_range_sums(df_lock_range_m)
                            p_r = create_pdf(df_lock_range_m, lock_p, lock_g, lock_w, lock_przeniesienie, lock_date_from_m, lock_date_to_m)
                            c_r = public_csv_data(df_lock_range_m)
                            if not has_email_config():
                                st.error("Brakuje konfiguracji e-mail w st.secrets. Okres nie został rozliczony.")
                                st.stop()

                            if not send_email_with_reports(p_r, c_r):
                                st.error("Nie rozliczono okresu, bo nie udało się wysłać raportu e-mailem.")
                                st.stop()

                            lock_ids = df_lock_range_m["id"].tolist()
                            insert_report_with_ids(lock_date_from_m, lock_date_to_m, lock_p, lock_ids)
                            st.session_state.next_cumulative_date_from = lock_date_to_m + timedelta(days=1)
                            st.success("✅ Raport wysłany e-mailem i zapisany. Wpisy zostają aktywne.")

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
