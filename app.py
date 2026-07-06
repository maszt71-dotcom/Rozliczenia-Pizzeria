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

# =============================================================================
# 0. POŁĄCZENIE Z SUPABASE
# Wszystkie dane wrażliwe WYŁĄCZNIE z st.secrets — nigdy w kodzie źródłowym!
# Wymagane klucze w secrets.toml:
#   SUPABASE_URL, SUPABASE_KEY,
#   APP_PASSWORD, AUTH_COOKIE_SECRET,
#   REPORT_RECEIVER_EMAIL, REPORT_SENDER_EMAIL, REPORT_EMAIL_PASSWORD
# =============================================================================

DEFAULT_SECRETS = {
    "APP_PASSWORD":           "dup@",
    "AUTH_COOKIE_SECRET":     "dup@_sekret_cookie_2026",
    "REPORT_RECEIVER_EMAIL":  "maszt71@gmail.com",
    "REPORT_SENDER_EMAIL":    "mange929598@gmail.com",
    "REPORT_EMAIL_PASSWORD":  "kwoaohaszcshiggg",
    "SUPABASE_URL":           "https://vtylqbykjispxoejmzxv.supabase.co",
    "SUPABASE_KEY":           "sb_secret_QO5nULOP-hDw0a4cuA6YiA_5FkzDU3x",
}

def get_secret(name: str, default=None):
    """Pobiera sekret z st.secrets, z fallbackiem do DEFAULT_SECRETS."""
    try:
        val = st.secrets.get(name)
        if val is not None:
            return val
    except Exception:
        pass
    return DEFAULT_SECRETS.get(name, default)


@st.cache_resource
def get_supabase_client() -> Client:
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Brak SUPABASE_URL lub SUPABASE_KEY")
    return create_client(url, key)

try:
    supabase = get_supabase_client()
except Exception as _e:
    st.error(f"❌ Błąd połączenia z bazą danych: {_e}")
    st.stop()



# =============================================================================
# 1. NARZĘDZIA POMOCNICZE
# =============================================================================

def get_now() -> datetime:
    """Zwraca aktualny czas w strefie czasowej Polski."""
    return datetime.now(pytz.timezone("Europe/Warsaw"))


def pdf_safe(txt: str) -> str:
    """Zamienia polskie znaki na ASCII-bezpieczne odpowiedniki dla biblioteki FPDF."""
    if not txt:
        return ""
    replacements = {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
        "ó": "o", "ś": "s", "ź": "z", "ż": "z",
        "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N",
        "Ó": "O", "Ś": "S", "Ź": "Z", "Ż": "Z",
    }
    result = str(txt)
    for k, v in replacements.items():
        result = result.replace(k, v)
    return result.encode("ascii", "ignore").decode("ascii")


def parse_event_date(value):
    """Parsuje datę z formatu DD.MM.YYYY lub YYYY-MM-DD. Zwraca date lub None."""
    txt = str(value).strip()
    if not txt or txt.lower() in ("none", "nan", "nat", ""):
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            pass
    return None


def short_pdf_text(value, max_len: int = 58) -> str:
    """Skraca tekst do max_len znaków (limit szerokości kolumny PDF ~80px)."""
    text = pdf_safe(str(value)).replace("\n", " ").strip()
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def money_text(value) -> str:
    return f"{float(value):,.2f} zł"


def parse_entry_ids(value):
    """Parsuje entry_ids z JSON-stringa lub listy."""
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


# =============================================================================
# 2. AUTENTYKACJA — TOKEN HMAC Z TTL
# =============================================================================

def make_auth_token(ttl_seconds: int = 60 * 60 * 12) -> str:
    secret = str(get_secret("AUTH_COOKIE_SECRET") or "")
    if not secret:
        return ""
    payload = {"logged": True, "exp": int(time.time()) + ttl_seconds}
    payload_raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_raw).decode("ascii")
    signature = hmac.new(
        secret.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def is_valid_auth_token(token) -> bool:
    secret = str(get_secret("AUTH_COOKIE_SECRET") or "")
    if not token or not secret or "." not in str(token):
        return False
    payload_b64, signature = str(token).rsplit(".", 1)
    expected = hmac.new(
        secret.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("ascii")))
    except Exception:
        return False
    return bool(payload.get("logged")) and int(payload.get("exp", 0)) > int(time.time())


def check_secret_password(value: str, secret_name: str) -> bool:
    expected = str(get_secret(secret_name) or "")
    return bool(expected) and hmac.compare_digest(str(value or ""), expected)


# =============================================================================
# 3. DANE Z SUPABASE
# =============================================================================

CARRYOVER_TYPE = "Gotówka z przeniesienia"

EXPECTED_FINANCE_COLS = ["id", "data", "typ", "kwota", "opis", "status", "data_zdarzenia"]
FINANCE_DEFAULTS = {
    "id": None,
    "data": "",
    "typ": "",
    "kwota": 0.0,
    "opis": "",
    "status": "Aktywny",
    "data_zdarzenia": "",
}


def load_data() -> pd.DataFrame:
    # Ładuje WSZYSTKIE wpisy bez filtrowania po statusie
    res = supabase.table("finanse").select("*").order("id").execute()
    df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    for col in EXPECTED_FINANCE_COLS:
        if col not in df.columns:
            df[col] = FINANCE_DEFAULTS[col]
    if not df.empty and "status" in df.columns:
        df["status"] = df["status"].fillna("Aktywny")
    return df


def load_archived_reports() -> pd.DataFrame:
    res = supabase.table("raporty").select("*").order("id", desc=True).execute()
    expected_cols = ["id", "data_wygenerowania", "okres_od", "okres_do", "suma_przychodow", "entry_ids"]
    if res.data:
        df = pd.DataFrame(res.data)
        # obsługa starszego schematu z kolumną "data" zamiast "data_wygenerowania"
        if "data_wygenerowania" not in df.columns and "data" in df.columns:
            df["data_wygenerowania"] = df["data"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0.0 if col == "suma_przychodow" else (None if col == "entry_ids" else "Brak daty")
        df["suma_przychodow"] = pd.to_numeric(df["suma_przychodow"], errors="coerce").fillna(0.0)
        return df
    return pd.DataFrame(columns=expected_cols)


def sort_df_by_data_zdarzenia(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    temp = df.copy()
    if "data_zdarzenia" not in temp.columns:
        temp["data_zdarzenia"] = ""
    if "id" not in temp.columns:
        temp["id"] = 0
    temp["_sort_date"] = [
        parse_event_date(v) or datetime.min.date()
        for v in temp["data_zdarzenia"].astype(str).str.strip()
    ]
    temp = temp.sort_values(by=["_sort_date", "id"], ascending=[False, False])
    return temp.drop(columns=["_sort_date"], errors="ignore")


def filter_data_by_date_range(df: pd.DataFrame, date_from, date_to) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    temp = df.copy()
    if "data_zdarzenia" not in temp.columns:
        temp["data_zdarzenia"] = ""
    temp["_parsed"] = [parse_event_date(v) for v in temp["data_zdarzenia"].astype(str).str.strip()]
    filtered = temp[
        temp["_parsed"].notna()
        & (temp["_parsed"] >= date_from)
        & (temp["_parsed"] <= date_to)
    ].copy()
    return filtered.drop(columns=["_parsed"], errors="ignore")


def calculate_range_sums(df: pd.DataFrame):
    """Zwraca (przychod, gotowka, wydatki, przeniesienie).
    gotowka = Gotowka z przeniesienia + suma Gotowka (bufet/kierowcy) - Wydatki gotowkowe
    """
    if df.empty:
        return 0.0, 0.0, 0.0, 0.0
    temp = df.copy()
    temp["kwota"] = pd.to_numeric(temp.get("kwota", 0), errors="coerce").fillna(0)
    przychod      = temp[temp["typ"] == "Przychód ogólny"]["kwota"].sum()
    wydatki       = temp[temp["typ"] == "Wydatki gotówkowe"]["kwota"].sum()
    przeniesienie = temp[temp["typ"] == CARRYOVER_TYPE]["kwota"].sum()
    # Gotówka kierowcy/bufet — tylko "Gotówka - *", bez przeniesienia (żeby nie liczyć dwa razy)
    gotowka_kb    = temp[temp["typ"].astype(str).str.startswith("Gotówka -", na=False)]["kwota"].sum()
    gotowka       = przeniesienie + gotowka_kb - wydatki
    return przychod, gotowka, wydatki, przeniesienie


def public_csv_data(df: pd.DataFrame) -> bytes:
    export_df = df.drop(columns=["status"], errors="ignore")
    return export_df.to_csv(index=False).encode("utf-8")


def get_default_date_range(df: pd.DataFrame):
    dates = [
        parse_event_date(v)
        for v in df.get("data_zdarzenia", pd.Series(dtype=str)).astype(str).str.strip()
        if parse_event_date(v)
    ] if not df.empty else []
    if dates:
        latest = max(dates)
        return latest.replace(day=1), latest
    today = get_now().date()
    return today.replace(day=1), today


def get_latest_event_date(df: pd.DataFrame):
    dates = [
        parse_event_date(v)
        for v in df.get("data_zdarzenia", pd.Series(dtype=str)).astype(str).str.strip()
        if parse_event_date(v)
    ] if not df.empty else []
    return max(dates) if dates else get_now().date()


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


def load_report_rows(report_row) -> pd.DataFrame:
    entry_ids = parse_entry_ids(report_row.get("entry_ids"))
    if entry_ids:
        res = supabase.table("finanse").select("*").in_("id", entry_ids).execute()
        return sort_df_by_data_zdarzenia(pd.DataFrame(res.data)) if res.data else pd.DataFrame()
    # fallback: filtruj po zakresie dat
    d_from = datetime.strptime(report_row["okres_od"], "%d.%m.%Y").date()
    d_to   = datetime.strptime(report_row["okres_do"], "%d.%m.%Y").date()
    return sort_df_by_data_zdarzenia(filter_data_by_date_range(load_data(), d_from, d_to))


# =============================================================================
# 4. ZAPIS RAPORTU DO BAZY (jednolity schemat)
# =============================================================================

def insert_report_with_ids(date_from, date_to, total_income, entry_ids):
    """
    Zapisuje zamknięcie okresu do tabeli 'raporty'.
    Oczekiwany schemat: data_wygenerowania, okres_od, okres_do, suma_przychodow, entry_ids
    """
    payload = {
        "data_wygenerowania": get_now().strftime("%d.%m.%Y %H:%M"),
        "okres_od":           date_from.strftime("%d.%m.%Y"),
        "okres_do":           date_to.strftime("%d.%m.%Y"),
        "suma_przychodow":    float(total_income),
        "entry_ids":          [int(x) for x in entry_ids],
    }
    try:
        result = supabase.table("raporty").insert(payload).execute()
        return result
    except Exception as e:
        st.warning(
            f"Raport wysłano e-mailem, ale nie udało się zapisać go w archiwum. "
            f"Sprawdź schemat tabeli 'raporty' w Supabase. Błąd: {e}"
        )
        return None


# =============================================================================
# 5. E-MAIL
# =============================================================================

def clean_app_password(value: str) -> str:
    return str(value or "").replace(" ", "").strip()


def build_email_message(sender_email: str, receiver_email: str, pdf_data: bytes, csv_data: bytes):
    msg = MIMEMultipart()
    msg["From"]    = sender_email
    msg["To"]      = receiver_email
    msg["Subject"] = f"Raport Pizzeria - {get_now().strftime('%d.%m.%Y %H:%M')}"
    msg.attach(MIMEText("Automatyczny raport z systemu.", "plain"))
    for content, ext in [(pdf_data, "pdf"), (csv_data, "csv")]:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(content)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename=raport.{ext}")
        msg.attach(part)
    return msg


def send_email_with_reports(pdf_data: bytes, csv_data: bytes) -> bool:
    sender   = str(get_secret("REPORT_SENDER_EMAIL") or "").strip()
    receiver = str(get_secret("REPORT_RECEIVER_EMAIL") or "").strip()
    password = clean_app_password(get_secret("REPORT_EMAIL_PASSWORD") or "")

    if not sender or not receiver or not password:
        st.error(
            "Brakuje konfiguracji e-mail. Dodaj REPORT_SENDER_EMAIL, "
            "REPORT_RECEIVER_EMAIL i REPORT_EMAIL_PASSWORD do st.secrets."
        )
        return False

    last_error = ""
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
                f"Gmail odrzucił hasło aplikacji dla konta {sender}. "
                "Utwórz nowe hasło aplikacji w ustawieniach konta Google."
            )
            return False
        except Exception as e:
            last_error = str(e)

    st.error(f"Nie udało się wysłać maila. Nadawca: {sender}. Błąd: {last_error}")
    return False


# =============================================================================
# 6. GENEROWANIE PDF
# =============================================================================

def get_pdf_row_colors(typ: str):
    if typ == CARRYOVER_TYPE:
        return (219, 234, 254), (0, 0, 0)
    if typ == "Przychód ogólny":
        return (212, 237, 218), (0, 0, 0)
    if typ == "Wydatki gotówkowe":
        return (248, 215, 218), (0, 0, 0)
    if "Gotówka" in typ:
        return (255, 243, 205), (0, 0, 0)
    return (255, 255, 255), (0, 0, 0)


def infer_report_range(df: pd.DataFrame):
    dates = [
        parse_event_date(v)
        for v in df.get("data_zdarzenia", pd.Series(dtype=str)).astype(str).str.strip()
        if parse_event_date(v)
    ] if not df.empty else []
    if dates:
        return min(dates), max(dates)
    today = get_now().date()
    return today, today


def create_pdf(df, p, g, w, przeniesienie=0.0, date_from=None, date_to=None) -> bytes:
    if date_from is None or date_to is None:
        inferred_from, inferred_to = infer_report_range(df)
        date_from = date_from or inferred_from
        date_to   = date_to   or inferred_to

    pdf = FPDF()
    pdf.add_page()

    # --- Nagłówek ---
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, pdf_safe("RAPORT SZCZEGOLOWY"), ln=True, align="C")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 7, pdf_safe(f"Zakres raportu: {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}"), ln=True, align="C")
    pdf.cell(0, 7, pdf_safe(f"Wygenerowano: {get_now().strftime('%d.%m.%Y %H:%M')}"), ln=True, align="C")
    pdf.ln(5)

    # --- Kafelki sumy ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(219, 234, 254)
    pdf.cell(190, 10, pdf_safe(f"Gotowka z przeniesienia: {przeniesienie:,.2f} zl"), border=1, ln=1, fill=True, align="C")

    pdf.set_fill_color(212, 237, 218)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(63, 10, pdf_safe(f"Przychod: {p:,.2f} zl"), border=1, fill=True, align="C")

    if g < 0:
        pdf.set_fill_color(220, 38, 38)
        pdf.set_text_color(255, 255, 255)
    else:
        pdf.set_fill_color(255, 243, 205)
        pdf.set_text_color(0, 0, 0)
    pdf.cell(64, 10, pdf_safe(f"Gotowka: {g:,.2f} zl"), border=1, fill=True, align="C")

    pdf.set_fill_color(248, 215, 218)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(63, 10, pdf_safe(f"Wydatki: {w:,.2f} zl"), border=1, ln=1, fill=True, align="C")
    pdf.ln(10)

    # --- Nagłówek tabeli ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(200, 200, 200)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(28, 8, "Data",  border=1, fill=True, align="C")
    pdf.cell(52, 8, "Typ",   border=1, fill=True, align="C")
    pdf.cell(30, 8, "Kwota", border=1, fill=True, align="C")
    pdf.cell(80, 8, "Opis",  border=1, ln=1, fill=True, align="C")

    # --- Wiersze danych ---
    pdf.set_font("Helvetica", size=9)
    df_to_print = df.copy()
    df_to_print["kwota"] = pd.to_numeric(df_to_print.get("kwota", 0), errors="coerce").fillna(0)

    for _, row in df_to_print.iterrows():
        typ_txt   = str(row.get("typ", ""))
        bg_color, text_color = get_pdf_row_colors(typ_txt)
        pdf.set_fill_color(*bg_color)
        pdf.set_text_color(*text_color)
        pdf.cell(28, 8, pdf_safe(str(row.get("data_zdarzenia", ""))),          border=1, fill=True, align="C")
        pdf.cell(52, 8, pdf_safe(typ_txt),                                      border=1, fill=True)
        pdf.cell(30, 8, pdf_safe(f"{float(row.get('kwota', 0)):,.2f} zl"),      border=1, fill=True, align="R")
        pdf.cell(80, 8, short_pdf_text(row.get("opis", "")),                    border=1, ln=1, fill=True)

    pdf.set_text_color(0, 0, 0)
    pdf_output = pdf.output(dest="S")
    return bytes(pdf_output) if isinstance(pdf_output, (bytes, bytearray)) else pdf_output.encode("latin-1")


# =============================================================================
# 7. ZAMKNIĘCIE OKRESU — wspólna logika (używana przez sidebar i widok mobilny)
# =============================================================================

def execute_period_close(date_from, date_to):
    """
    Wysyła raport e-mailem i zapisuje w archiwum.
    Zwraca True przy sukcesie, False przy błędzie.
    """
    df_all = load_data()
    df_range = sort_df_by_data_zdarzenia(filter_data_by_date_range(df_all, date_from, date_to))

    if df_range.empty:
        st.warning("Brak wpisów w wybranym zakresie dat.")
        return False

    lock_p, lock_g, lock_w, lock_przeniesienie = calculate_range_sums(df_range)
    pdf_data = create_pdf(df_range, lock_p, lock_g, lock_w, lock_przeniesienie, date_from, date_to)
    csv_data = public_csv_data(df_range)

    if not send_email_with_reports(pdf_data, csv_data):
        st.error("Nie rozliczono okresu — błąd wysyłki e-mail.")
        return False

    lock_ids = df_range["id"].dropna().astype(int).tolist()
    insert_report_with_ids(date_from, date_to, lock_p, lock_ids)
    st.session_state.next_cumulative_date_from = date_to + timedelta(days=1)
    st.success("✅ Raport wysłany e-mailem i zapisany w archiwum. Wpisy pozostają aktywne.")
    return True


def reset_lock_state():
    st.session_state.lock_step      = 0
    st.session_state.lock_confirm_1 = False
    st.session_state.lock_confirm_2 = False


# =============================================================================
# 8. STYLIZOWANIE WIERSZY TABELI
# =============================================================================

def style_row_by_type(row):
    typ = str(row["typ"])
    if typ == CARRYOVER_TYPE:
        color = "background-color: #dbeafe; color: black;"
    elif typ == "Przychód ogólny":
        color = "background-color: #d4edda; color: black;"
    elif "Gotówka" in typ:
        color = "background-color: #fff3cd; color: black;"
    elif typ == "Wydatki gotówkowe":
        color = "background-color: #f8d7da; color: black;"
    else:
        color = ""
    return [color] * len(row)


# =============================================================================
# 9. UI — KONFIGURACJA STRONY I CSS
# =============================================================================

st.set_page_config(
    page_title="Pizzeria",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');

        :root {
            --bg:        #0a0a0f;
            --bg2:       #0f0f16;
            --bg3:       #16161e;
            --surface:   #1c1c26;
            --surface2:  #24242f;
            --border:    rgba(255,255,255,0.07);
            --border2:   rgba(255,255,255,0.11);
            --text:      #eeeef8;
            --text2:     #8888a8;
            --text3:     #4a4a62;
            --accent:    #7c6eff;
            --accent2:   #a594ff;
            --green:     #22c55e;
            --green-bg:  rgba(34,197,94,0.10);
            --green-bd:  rgba(34,197,94,0.22);
            --yellow:    #f59e0b;
            --yellow-bg: rgba(245,158,11,0.10);
            --yellow-bd: rgba(245,158,11,0.22);
            --red:       #ef4444;
            --red-bg:    rgba(239,68,68,0.10);
            --red-bd:    rgba(239,68,68,0.25);
            --blue:      #60a5fa;
            --blue-bg:   rgba(96,165,250,0.10);
            --blue-bd:   rgba(96,165,250,0.22);
            --r:         12px;
            --r2:        18px;
            --shadow:    0 12px 40px rgba(0,0,0,0.5);
            --shadow2:   0 3px 14px rgba(0,0,0,0.35);
        }

        *, *::before, *::after { box-sizing: border-box; }
        #MainMenu, footer, header { display: none !important; }

        .stApp {
            background: var(--bg) !important;
            color: var(--text) !important;
            font-family: 'DM Sans', sans-serif !important;
        }
        .stApp::before {
            content: '';
            position: fixed;
            top: -25vh; left: -15vw;
            width: 55vw; height: 55vh;
            background: radial-gradient(ellipse, rgba(124,110,255,0.08) 0%, transparent 70%);
            pointer-events: none; z-index: 0;
        }
        .stApp::after {
            content: '';
            position: fixed;
            bottom: -20vh; right: -10vw;
            width: 45vw; height: 45vh;
            background: radial-gradient(ellipse, rgba(34,197,94,0.05) 0%, transparent 70%);
            pointer-events: none; z-index: 0;
        }

        .block-container {
            max-width: 1120px !important;
            padding: 2rem 1.5rem 7rem !important;
            position: relative; z-index: 1;
        }

        /* SIDEBAR */
        section[data-testid="stSidebar"] {
            background: var(--bg2) !important;
            border-right: 1px solid var(--border) !important;
            box-shadow: 4px 0 40px rgba(0,0,0,0.4) !important;
        }
        [data-testid="stSidebarNav"] { display: none !important; }

        /* Przycisk otwierania sidebara — zawsze widoczny i ładny */
        button[data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            background: var(--surface) !important;
            border: 1px solid var(--border2) !important;
            border-radius: 0 10px 10px 0 !important;
            color: var(--text) !important;
            box-shadow: 4px 0 16px rgba(0,0,0,0.3) !important;
            width: 2.2rem !important;
            height: 2.8rem !important;
            position: fixed !important;
            top: 50% !important;
            left: 0 !important;
            transform: translateY(-50%) !important;
            z-index: 999 !important;
            cursor: pointer !important;
        }
        button[data-testid="collapsedControl"]:hover,
        [data-testid="stSidebarCollapsedControl"]:hover {
            background: var(--surface2) !important;
            border-color: var(--accent) !important;
        }
        button[data-testid="collapsedControl"] svg,
        [data-testid="stSidebarCollapsedControl"] svg {
            fill: var(--accent2) !important;
        }
        [data-testid="stSidebar"] .block-container { padding-top: 1.5rem !important; }
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 { color: var(--text) !important; }
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label { color: var(--text2) !important; }

        /* TYPOGRAPHY */
        h1, h2, h3 {
            font-family: 'Syne', sans-serif !important;
            color: var(--text) !important;
            letter-spacing: -0.025em;
        }
        p, span { color: var(--text2) !important; }

        /* APP HEADER */
        .app-header { margin-bottom: 2rem; }
        .app-eyebrow {
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--accent2) !important;
            display: flex; align-items: center; gap: 7px;
            margin-bottom: 0.45rem;
        }
        .app-eyebrow::before {
            content: '';
            width: 7px; height: 7px;
            border-radius: 50%;
            background: var(--accent);
            box-shadow: 0 0 10px rgba(124,110,255,0.7);
            flex-shrink: 0;
        }
        .app-title {
            font-family: 'Syne', sans-serif !important;
            font-size: 2.6rem;
            font-weight: 800;
            color: var(--text) !important;
            line-height: 1.03;
            margin: 0;
            letter-spacing: -0.035em;
        }
        .app-subtitle {
            font-size: 0.82rem;
            color: var(--text3) !important;
            margin-top: 0.45rem;
        }

        /* METRIC CARDS */
        .metric-card {
            border-radius: var(--r2);
            padding: 1.4rem 1.5rem 1.3rem;
            margin-bottom: 1rem;
            position: relative;
            overflow: hidden;
            transition: transform 0.2s cubic-bezier(.4,0,.2,1), box-shadow 0.2s ease;
            backdrop-filter: blur(4px);
        }
        .metric-card::before {
            content: '';
            position: absolute;
            inset: 0;
            border-radius: var(--r2);
            border: 1px solid var(--border2);
            pointer-events: none;
        }
        .metric-card::after {
            content: '';
            position: absolute;
            top: -40%; right: -20%;
            width: 160px; height: 160px;
            border-radius: 50%;
            opacity: 0.06;
            pointer-events: none;
        }
        .metric-card:hover { transform: translateY(-3px); box-shadow: var(--shadow); }
        .metric-card .label {
            font-size: 0.68rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.13em;
            margin-bottom: 0.7rem;
        }
        .metric-card .value {
            font-family: 'Syne', sans-serif;
            font-size: 1.85rem;
            font-weight: 800;
            letter-spacing: -0.025em;
            line-height: 1;
        }

        .metric-card.blue   { background: linear-gradient(145deg, rgba(96,165,250,0.12) 0%, rgba(96,165,250,0.03) 100%); }
        .metric-card.blue .label { color: var(--blue) !important; }
        .metric-card.blue .value { color: var(--blue) !important; }
        .metric-card.blue::after { background: var(--blue); }

        .metric-card.green  { background: linear-gradient(145deg, rgba(34,197,94,0.12) 0%, rgba(34,197,94,0.03) 100%); }
        .metric-card.green .label { color: var(--green) !important; }
        .metric-card.green .value { color: var(--green) !important; }
        .metric-card.green::after { background: var(--green); }

        .metric-card.yellow { background: linear-gradient(145deg, rgba(245,158,11,0.12) 0%, rgba(245,158,11,0.03) 100%); }
        .metric-card.yellow .label { color: var(--yellow) !important; }
        .metric-card.yellow .value { color: var(--yellow) !important; }
        .metric-card.yellow::after { background: var(--yellow); }

        .metric-card.red    { background: linear-gradient(145deg, rgba(239,68,68,0.12) 0%, rgba(239,68,68,0.03) 100%); }
        .metric-card.red .label { color: var(--red) !important; }
        .metric-card.red .value { color: var(--red) !important; }
        .metric-card.red::after { background: var(--red); }

        .metric-card.negative {
            background: linear-gradient(145deg, rgba(239,68,68,0.20) 0%, rgba(239,68,68,0.07) 100%);
        }
        .metric-card.negative::before { border-color: var(--red-bd) !important; }
        .metric-card.negative .label { color: #fca5a5 !important; }
        .metric-card.negative .value { color: #ffffff !important; }
        .metric-card.negative::after { background: var(--red); }

        /* BUTTONS */
        div.stButton > button {
            background: var(--surface) !important;
            color: var(--text) !important;
            border: 1px solid var(--border2) !important;
            border-radius: var(--r) !important;
            min-height: 2.65rem !important;
            font-family: 'DM Sans', sans-serif !important;
            font-weight: 600 !important;
            font-size: 0.87rem !important;
            letter-spacing: 0.01em;
            transition: all 0.18s cubic-bezier(.4,0,.2,1) !important;
            box-shadow: none !important;
        }
        div.stButton > button:hover {
            background: var(--surface2) !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.3) !important;
        }
        div.stButton > button:active { transform: translateY(0) !important; }
        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, var(--accent) 0%, #5e50d8 100%) !important;
            border-color: transparent !important;
            color: #fff !important;
            box-shadow: 0 4px 22px rgba(124,110,255,0.38) !important;
        }
        div.stButton > button[kind="primary"]:hover {
            box-shadow: 0 6px 30px rgba(124,110,255,0.55) !important;
            transform: translateY(-2px);
        }

        /* INPUTS */
        .stTextInput input, .stNumberInput input {
            background: var(--surface) !important;
            border: 1px solid var(--border2) !important;
            border-radius: var(--r) !important;
            color: var(--text) !important;
            font-family: 'DM Sans', sans-serif !important;
            font-size: 0.92rem !important;
        }
        .stTextInput input:focus, .stNumberInput input:focus {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 3px rgba(124,110,255,0.14) !important;
            outline: none !important;
        }
        input[type="date"] {
            background: var(--surface) !important;
            border: 1px solid var(--border2) !important;
            border-radius: var(--r) !important;
            color: var(--text) !important;
            font-family: 'DM Sans', sans-serif !important;
        }
        .stTextInput label, .stNumberInput label,
        .stDateInput label, .stMultiSelect label {
            color: var(--text2) !important;
            font-size: 0.74rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.09em;
        }

        /* MULTISELECT */
        .stMultiSelect > div > div {
            background: var(--surface) !important;
            border: 1px solid var(--border2) !important;
            border-radius: var(--r) !important;
        }
        .stMultiSelect span[data-baseweb="tag"] {
            background: rgba(124,110,255,0.18) !important;
            border: 1px solid rgba(124,110,255,0.28) !important;
            color: var(--accent2) !important;
            border-radius: 6px !important;
            font-size: 0.78rem !important;
        }

        /* CONTAINERS */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--r2) !important;
            box-shadow: var(--shadow2) !important;
        }

        /* DATAFRAME */
        div[data-testid="stDataFrame"] {
            border-radius: var(--r2) !important;
            overflow: hidden;
            border: 1px solid var(--border) !important;
        }

        /* ALERTS */
        div[data-testid="stAlert"] {
            border-radius: var(--r) !important;
            background: var(--surface) !important;
            border: 1px solid var(--border2) !important;
        }
        div[data-testid="stAlert"] p { color: var(--text) !important; }

        /* DIVIDER */
        hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

        /* EXPANDER */
        details {
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--r) !important;
            margin-bottom: 0.4rem;
        }
        details summary { color: var(--text) !important; font-weight: 600; }
        details > div { background: var(--surface) !important; }

        /* SCROLLBAR */
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: var(--bg2); }
        ::-webkit-scrollbar-thumb { background: var(--surface2); border-radius: 3px; }

        /* SIDEBAR HEADER PILL */
        .sidebar-menu-label {
            font-size: 0.65rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            color: var(--text3) !important;
            margin: 0.2rem 0 0.7rem;
        }

        /* LOGIN */
        /* LOGIN PAGE */
        .login-page {
            position: fixed;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 999;
        }
        .login-wrap {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            width: 100%;
            max-width: 380px;
            padding: 2.5rem 2rem;
            background: var(--surface);
            border: 1px solid var(--border2);
            border-radius: 24px;
            box-shadow: 0 24px 80px rgba(0,0,0,0.6);
        }
        .login-icon {
            font-size: 3.5rem;
            margin-bottom: 0.5rem;
            filter: drop-shadow(0 0 24px rgba(124,110,255,0.45));
        }
        .login-title {
            font-family: 'Syne', sans-serif;
            font-size: 1.6rem;
            font-weight: 800;
            color: var(--text) !important;
            margin-bottom: 0.2rem;
            letter-spacing: -0.02em;
        }
        .login-sub {
            font-size: 0.82rem;
            color: var(--text3) !important;
            margin-bottom: 0;
        }
        /* wyśrodkuj kontener Streamlit na stronie logowania */
        .login-container .block-container {
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            min-height: 100vh !important;
            padding-top: 0 !important;
        }
        .login-container div[data-testid="stVerticalBlockBorderWrapper"] {
            width: 100% !important;
            max-width: 380px !important;
        }

        /* MOBILE */
        @media (max-width: 768px) {
            .block-container { padding: 1.1rem 0.9rem 8rem !important; }
            .app-title { font-size: 2rem; }
            .metric-card { padding: 1.1rem 1.2rem; margin-bottom: 0.75rem; }
            .metric-card .value { font-size: 1.5rem; }
            section[data-testid="stSidebar"] { display: none !important; }
        }

        /* Ukryj ikonkę Streamlit która zasłania przyciski */
        [data-testid="stActionButtonIcon"],
        .viewerBadge_container__r5tak,
        #stDecoration,
        a[href="https://streamlit.io"],
        .css-1dp5vir,
        iframe[title="streamlit_overlay"] {
            display: none !important;
        }

        /* BOTTOM NAV BAR — tylko mobile */
        .bottom-nav {
            display: none;
        }
        @media (max-width: 768px) {
            .bottom-nav {
                display: flex;
                position: fixed;
                bottom: 0; left: 0; right: 0;
                height: 4.8rem;
                padding-bottom: env(safe-area-inset-bottom);
                background: rgba(15,15,22,0.97);
                backdrop-filter: blur(20px);
                border-top: 1px solid rgba(255,255,255,0.08);
                z-index: 99999;
                align-items: center;
                justify-content: space-around;
                padding-left: 0.5rem;
                padding-right: 0.5rem;
                box-shadow: 0 -8px 32px rgba(0,0,0,0.5);
            }
            .bottom-nav a {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 3px;
                color: #4a4a62;
                text-decoration: none;
                font-size: 0.58rem;
                font-weight: 700;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                padding: 0.4rem 0.8rem;
                border-radius: 10px;
                transition: all 0.18s ease;
                -webkit-tap-highlight-color: transparent;
                min-width: 4rem;
                text-align: center;
            }
            .bottom-nav a:active { background: rgba(124,110,255,0.15); }
            .bottom-nav a .icon {
                font-size: 1.4rem;
                line-height: 1;
            }
            .bottom-nav a.accent { color: #7c6eff; }
            .bottom-nav a.danger { color: #ef4444; }
            .bottom-nav a.green  { color: #22c55e; }

            /* padding żeby ostatni element nie był pod paskiem */
            .block-container { padding-bottom: 9rem !important; }
        }
    </style>
""",
    unsafe_allow_html=True,
)


# =============================================================================
# 10. KAFELEK METRYKI
# =============================================================================

def metric_card(label: str, value, color_class: str):
    st.markdown(
        f"""
        <div class="metric-card {color_class}">
            <div class="label">{label}</div>
            <div class="value">{money_text(value)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# 11. LOGOWANIE
# =============================================================================

cookies = CookieManager()
if not cookies.ready():
    st.stop()

if not is_valid_auth_token(cookies.get("auth_token")):
    # Login — nagłówek na pełną szerokość, formularz wyśrodkowany pod nim
    st.markdown(
        """
        <style>
        /* na stronie logowania wyśrodkuj całą zawartość */
        .login-page-wrap .block-container {
            padding-top: 0 !important;
        }
        </style>
        <div style="
            width: 100%;
            text-align: center;
            padding: 3.5rem 1rem 2rem;
        ">
            <div style="font-size:3.2rem; margin-bottom:0.4rem; filter:drop-shadow(0 0 20px rgba(124,110,255,0.5))">🍕</div>
            <div style="
                font-family: 'Syne', sans-serif;
                font-size: 2rem;
                font-weight: 800;
                color: #eeeef8;
                letter-spacing: -0.03em;
                margin-bottom: 0.3rem;
            ">Pizzeria Finance</div>
            <div style="font-size:0.82rem; color:#4a4a62;">Zaloguj się, aby kontynuować</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not get_secret("APP_PASSWORD"):
        st.warning("⚠️ Brakuje APP_PASSWORD w st.secrets.")

    # pole i przycisk na pełną szerokość kontenera
    st.markdown("""
        <style>
        div[data-testid="stTextInput"],
        div[data-testid="stTextInput"] input,
        div[data-testid="stButton"],
        div[data-testid="stButton"] > button {
            width: 100% !important;
            max-width: 100% !important;
            box-sizing: border-box !important;
        }
        </style>
    """, unsafe_allow_html=True)

    haslo = st.text_input("Hasło dostępu", type="password", placeholder="••••••••")
    if st.button("Zaloguj →", type="primary", use_container_width=True):
        if not get_secret("APP_PASSWORD"):
            st.error("Brak APP_PASSWORD w konfiguracji.")
        elif check_secret_password(haslo, "APP_PASSWORD"):
            cookies["auth_token"] = make_auth_token()
            cookies.save()
            st.rerun()
        else:
            st.error("Nieprawidłowe hasło.")
    st.stop()


# =============================================================================
# 12. INICJALIZACJA STANU SESJI
# =============================================================================

for key, default in {
    "s":                    "",
    "os":                   None,
    "selected_ids":         [],
    "lock_step":            0,
    "lock_confirm_1":       False,
    "lock_confirm_2":       False,
    "show_delete_confirm":  False,
    "show_report_picker":   False,
    "show_send_picker":     False,
    "show_archive_picker":  False,
    "page":                 "home",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# =============================================================================
# 13. ŁADOWANIE DANYCH I ZAKRESY
# =============================================================================

data = load_data()
default_date_from, default_date_to = get_default_date_range(data)

next_cumulative_date_from = st.session_state.pop("next_cumulative_date_from", None)
if next_cumulative_date_from is not None:
    st.session_state.cumulative_date_widget_version = (
        st.session_state.get("cumulative_date_widget_version", 0) + 1
    )

latest_reset_date   = get_next_date_after_latest_closed_report()
# Domyślnie: pierwszy dzień miesiąca najpóźniejszego wpisu w bazie
_, _latest_date = get_default_date_range(data)
_default_month_start = _latest_date.replace(day=1)
current_month_start = next_cumulative_date_from or latest_reset_date or _default_month_start

# --- Pasek boczny: wybór zakresu narastającego ---
with st.sidebar:
    st.header("⚙️ Menu")
    st.markdown("**Kwoty narastająco:**")
    cumulative_date_key  = f"cumulative_date_from_{st.session_state.get('cumulative_date_widget_version', 0)}"
    cumulative_date_from = st.date_input("Pokaż od", value=current_month_start, key=cumulative_date_key)
    st.divider()

latest_data_date  = get_latest_event_date(data)
cumulative_date_to = max(latest_data_date, cumulative_date_from)

if cumulative_date_from > latest_data_date:
    df_current = pd.DataFrame(columns=data.columns)
else:
    df_current = filter_data_by_date_range(data, cumulative_date_from, latest_data_date).copy()

df_active_calc = df_current.copy()
df_history     = df_current.copy()

# Sumy do kafelków
if not df_active_calc.empty:
    df_active_calc["kwota"] = pd.to_numeric(df_active_calc["kwota"], errors="coerce").fillna(0)
    s_og, s_got, s_wyd, s_przeniesienie = calculate_range_sums(df_active_calc)
else:
    s_og = s_got = s_wyd = s_przeniesienie = 0.0


# =============================================================================
# 14. STRONA MENU (mobilna) lub WIDOK GŁÓWNY
# =============================================================================

if st.session_state.page == "menu":
    st.markdown(
        f"""
        <div class="app-header">
            <div class="app-eyebrow">System Finansowy</div>
            <div class="app-title">Menu</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**Kwoty narastająco od:**")
    cumulative_date_key2 = f"menu_date_{st.session_state.get('cumulative_date_widget_version', 0)}"
    new_date = st.date_input("Pokaż od", value=cumulative_date_from, key=cumulative_date_key2)
    if new_date != cumulative_date_from:
        st.session_state.cumulative_date_widget_version = st.session_state.get('cumulative_date_widget_version', 0) + 1
        st.rerun()

    st.divider()

    if st.button("📧 WYŚLIJ RAPORT", use_container_width=True, type="primary", key="menu_send_open"):
        st.session_state.show_send_picker = not st.session_state.show_send_picker
        st.rerun()
    if st.session_state.show_send_picker:
        with st.container(border=True):
            sd_from = st.date_input("Data od", value=get_now().date(), key="menu_send_from")
            sd_to   = st.date_input("Data do", value=get_now().date(), key="menu_send_to")
            if sd_from <= sd_to:
                df_s = sort_df_by_data_zdarzenia(filter_data_by_date_range(load_data(), sd_from, sd_to))
                sp, sg, sw, spr = calculate_range_sums(df_s)
                if st.button("📧 Wyślij PDF + CSV", use_container_width=True, type="primary", key="menu_send_btn"):
                    if send_email_with_reports(create_pdf(df_s, sp, sg, sw, spr, sd_from, sd_to), public_csv_data(df_s)):
                        st.success("✅ Wysłano!")
            if st.button("↩️ Zamknij", use_container_width=True, key="menu_send_close"):
                st.session_state.show_send_picker = False
                st.rerun()

    st.divider()

    if st.button("🔒 ZAMKNIJ I ROZLICZ OKRES", use_container_width=True, type="primary", key="menu_lock_open"):
        st.session_state.lock_step = 1
        st.session_state.lock_confirm_1 = False
        st.rerun()
    if st.session_state.lock_step >= 1:
        with st.container(border=True):
            ld_from = st.date_input("Rozlicz od:", value=get_now().date(), key="menu_lock_from")
            ld_to   = st.date_input("Rozlicz do:", value=get_now().date(), key="menu_lock_to")
            if ld_from <= ld_to:
                if not st.session_state.lock_confirm_1:
                    if st.button("❓ Jesteś pewien?", use_container_width=True, type="primary", key="menu_confirm1"):
                        st.session_state.lock_confirm_1 = True
                        st.rerun()
                else:
                    st.warning("⚠️ Tej czynności nie można cofnąć!")
                    if st.button("🚀 WYKONAJ ZAMKNIĘCIE", use_container_width=True, type="primary", key="menu_confirm2"):
                        execute_period_close(ld_from, ld_to)
                        reset_lock_state()
                        st.rerun()
            if st.button("Anuluj", use_container_width=True, key="menu_lock_cancel"):
                reset_lock_state()
                st.rerun()

    st.divider()

    if st.button("📥 POBIERZ RAPORT", use_container_width=True, key="menu_report_open"):
        st.session_state.show_report_picker = not st.session_state.show_report_picker
        st.rerun()
    if st.session_state.show_report_picker:
        with st.container(border=True):
            rd_from = st.date_input("Data od", value=default_date_from, key="menu_rep_from")
            rd_to   = st.date_input("Data do", value=default_date_to,   key="menu_rep_to")
            if rd_from <= rd_to:
                df_r = sort_df_by_data_zdarzenia(filter_data_by_date_range(load_data(), rd_from, rd_to))
                rp, rg, rw, rpr = calculate_range_sums(df_r)
                st.write(f"Przychód: **{rp:,.2f} zł** | Gotówka: **{rg:,.2f} zł** | Wydatki: **{rw:,.2f} zł**")
                st.download_button("📥 Pobierz PDF", data=create_pdf(df_r, rp, rg, rw, rpr, rd_from, rd_to),
                    file_name=f"raport_{rd_from}_{rd_to}.pdf", use_container_width=True, key="menu_dl_pdf")
                st.download_button("📥 Pobierz CSV", data=public_csv_data(df_r),
                    file_name=f"raport_{rd_from}_{rd_to}.csv", use_container_width=True, key="menu_dl_csv")
            if st.button("↩️ Zamknij", use_container_width=True, key="menu_rep_close"):
                st.session_state.show_report_picker = False
                st.rerun()

    st.divider()

    if st.button("📜 ARCHIWUM RAPORTÓW", use_container_width=True, key="menu_arch_open"):
        st.session_state.show_archive_picker = not st.session_state.show_archive_picker
        st.rerun()
    if st.session_state.show_archive_picker:
        with st.container(border=True):
            df_arch = load_archived_reports()
            if df_arch.empty:
                st.info("Brak zapisanych raportów.")
            else:
                for _, r_row in df_arch.iterrows():
                    with st.expander(f"📅 {r_row['okres_od']} - {r_row['okres_od']}"):
                        st.write(f"Suma: {r_row['suma_przychodow']:.2f} zł")
                        try:
                            df_ar = load_report_rows(r_row)
                            st.download_button("📥 CSV", data=public_csv_data(df_ar),
                                file_name=f"arch_{r_row['okres_od']}.csv",
                                key=f"menu_arch_{r_row['id']}", use_container_width=True)
                        except Exception as e:
                            st.error(f"Błąd: {e}")
            if st.button("↩️ Zamknij", use_container_width=True, key="menu_arch_close"):
                st.session_state.show_archive_picker = False
                st.rerun()

    st.divider()

    if st.button("🔓 WYLOGUJ", use_container_width=True, key="menu_logout"):
        cookies["auth_token"] = ""
        cookies.save()
        st.rerun()

    # bottom nav na stronie menu też
    st.markdown("""<div class="bottom-nav">
        <div style="display:flex;flex-direction:column;align-items:center;gap:3px;color:#4a4a62;font-size:0.58rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;">
            <span style="font-size:1.4rem;">🏠</span><span>Główna</span>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;gap:3px;color:#7c6eff;font-size:0.58rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;">
            <span style="font-size:1.4rem;">⚙️</span><span>Menu</span>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;gap:3px;color:#4a4a62;font-size:0.58rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;">
            <span style="font-size:1.4rem;">📋</span><span>Historia</span>
        </div>
    </div>""", unsafe_allow_html=True)
    mn1, mn2, mn3 = st.columns(3)
    with mn1:
        if st.button("🏠", key="menu_nav_home", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()
    with mn2:
        st.button("⚙️", key="menu_nav_menu", use_container_width=True, disabled=True)
    with mn3:
        if st.button("📋", key="menu_nav_hist", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

else:
    # =========================================================================
    # WIDOK GŁÓWNY (home)
    # =========================================================================
    pass

if st.session_state.page == "home":
    st.markdown(
    f"""
    <div class="app-header">
        <div class="app-eyebrow">System Finansowy</div>
        <div class="app-title">Rozliczenie</div>
        <div class="app-subtitle">
            Narastająco {cumulative_date_from.strftime('%d.%m.%Y')} &mdash; {cumulative_date_to.strftime('%d.%m.%Y')}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Gotówka z przeniesienia ---
metric_card("Gotówka z przeniesienia", s_przeniesienie, "blue")
if st.button("➕ DODAJ", key="zp"):
    st.session_state.s = "ZP" if st.session_state.s != "ZP" else ""
    st.rerun()

if st.session_state.s == "ZP":
    with st.container(border=True):
        d_zp  = st.date_input("Data zdarzenia", get_now().date(), key="date_zp")
        kw_zp = st.number_input("Kwota", value=None, step=1.0, key="zp_v", placeholder="Wpisz kwotę")
        op_zp = st.text_input("Opis", key="desc_zp", placeholder="Opcjonalnie")
        if st.button("DODAJ", key="save_zp", use_container_width=True, type="primary"):
            if kw_zp is not None and kw_zp > 0:
                supabase.table("finanse").insert({
                    "data":           get_now().strftime("%d.%m %H:%M"),
                    "typ":            CARRYOVER_TYPE,
                    "kwota":          float(kw_zp),
                    "opis":           op_zp,
                    "status":         "Aktywny",
                    "data_zdarzenia": d_zp.strftime("%d.%m.%Y"),
                }).execute()
                st.session_state.s = ""
                st.rerun()

# --- Trzy kolumny: Przychód / Gotówka / Wydatki ---
c1, c2, c3 = st.columns(3)

with c1:
    metric_card("Przychód", s_og, "green")
    if st.button("➕ DODAJ", key="p"):
        st.session_state.s = "P" if st.session_state.s != "P" else ""
        st.rerun()
    if st.session_state.s == "P":
        with st.container(border=True):
            d_p  = st.date_input("Data zdarzenia", get_now().date(), key="date_p")
            kw_p = st.number_input("Kwota", value=None, step=1.0, key="p_v", placeholder="Wpisz kwotę")
            if st.button("DODAJ", key="save_p", use_container_width=True, type="primary"):
                if kw_p is not None and kw_p > 0:
                    supabase.table("finanse").insert({
                        "data":           get_now().strftime("%d.%m %H:%M"),
                        "typ":            "Przychód ogólny",
                        "kwota":          float(kw_p),
                        "opis":           "",
                        "status":         "Aktywny",
                        "data_zdarzenia": d_p.strftime("%d.%m.%Y"),
                    }).execute()
                    st.session_state.s = ""
                    st.rerun()

with c2:
    metric_card("Gotówka", s_got, "negative" if s_got < 0 else "yellow")
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
                        d_g  = st.date_input("Data", get_now().date(), key=f"date_g_{o}")
                        kw_g = st.number_input("Kwota", value=None, step=1.0, key=f"g_v_{o}", placeholder="Wpisz kwotę")
                        if st.button("DODAJ", key=f"save_g_{o}", use_container_width=True, type="primary"):
                            if kw_g is not None and kw_g > 0:
                                supabase.table("finanse").insert({
                                    "data":           get_now().strftime("%d.%m %H:%M"),
                                    "typ":            f"Gotówka - {o}",
                                    "kwota":          float(kw_g),
                                    "opis":           "",
                                    "status":         "Aktywny",
                                    "data_zdarzenia": d_g.strftime("%d.%m.%Y"),
                                }).execute()
                                st.session_state.s  = ""
                                st.session_state.os = None
                                st.rerun()

with c3:
    metric_card("Wydatki", s_wyd, "red")
    if st.button("➕ DODAJ", key="w"):
        st.session_state.s = "W" if st.session_state.s != "W" else ""
        st.rerun()
    if st.session_state.s == "W":
        with st.container(border=True):
            d_w  = st.date_input("Data zdarzenia", get_now().date(), key="date_w")
            kw_w = st.number_input("Kwota", value=None, step=1.0, key="w_v", placeholder="Wpisz kwotę")
            op_w = st.text_input("Opis", key="desc_w")
            if st.button("DODAJ", key="save_w", use_container_width=True, type="primary"):
                if kw_w is not None and kw_w > 0:
                    supabase.table("finanse").insert({
                        "data":           get_now().strftime("%d.%m %H:%M"),
                        "typ":            "Wydatki gotówkowe",
                        "kwota":          float(kw_w),
                        "opis":           op_w,
                        "status":         "Aktywny",
                        "data_zdarzenia": d_w.strftime("%d.%m.%Y"),
                    }).execute()
                    st.session_state.s = ""
                    st.rerun()


# =============================================================================
# 15. PASEK BOCZNY — AKCJE
# =============================================================================

with st.sidebar:

    # ---- Wyślij raport ----
    if st.button("📧 WYŚLIJ RAPORT", use_container_width=True, type="primary", key="open_send_picker"):
        st.session_state.show_send_picker   = not st.session_state.show_send_picker
        st.session_state.show_report_picker = False
        st.session_state.show_archive_picker = False
        st.rerun()

    if st.session_state.show_send_picker:
        with st.container(border=True):
            send_date_from = st.date_input("Data od", value=get_now().date(), key="send_date_from")
            send_date_to   = st.date_input("Data do", value=get_now().date(), key="send_date_to")
            if send_date_from > send_date_to:
                st.error("Data od nie może być większa niż data do.")
            else:
                # Ładuj WSZYSTKIE dane z bazy — ignoruj filtr "Pokaż od"
                df_send = sort_df_by_data_zdarzenia(
                    filter_data_by_date_range(load_data(), send_date_from, send_date_to)
                )
                sp, sg, sw, spr = calculate_range_sums(df_send)
                st.write(f"Wpisów w zakresie: **{len(df_send)}** | Przychód: **{sp:,.2f} zł** | Wydatki: **{sw:,.2f} zł**")
                if st.button("📧 Wyślij PDF + CSV", use_container_width=True, type="primary", key="send_range_btn"):
                    if send_email_with_reports(
                        create_pdf(df_send, sp, sg, sw, spr, send_date_from, send_date_to),
                        public_csv_data(df_send),
                    ):
                        st.success("✅ Wysłano raport!")
            if st.button("↩️ Powrót", use_container_width=True, key="send_back_btn"):
                st.session_state.show_send_picker = False
                st.rerun()

    st.divider()

    # ---- Zamknij i rozlicz okres ----
    if st.button("🔒 ZAMKNIJ I ROZLICZ OKRES", type="primary", use_container_width=True, key="lock_open_sidebar"):
        st.session_state.lock_step      = 1
        st.session_state.lock_confirm_1 = False
        st.session_state.lock_confirm_2 = False
        st.rerun()

    if st.session_state.lock_step >= 1:
        with st.container(border=True):
            lock_df = st.date_input("Rozlicz od:", value=get_now().date(), key="lock_date_from_sidebar")
            lock_dt = st.date_input("Rozlicz do:", value=get_now().date(), key="lock_date_to_sidebar")
            if lock_df > lock_dt:
                st.error("Data od nie może być większa niż data do.")
            else:
                if not st.session_state.lock_confirm_1:
                    if st.button("❓ Jesteś pewien?", use_container_width=True, type="primary", key="confirm_1_sidebar"):
                        st.session_state.lock_confirm_1 = True
                        st.rerun()
                elif not st.session_state.lock_confirm_2:
                    st.warning("⚠️ Tej czynności nie można cofnąć!")
                    if st.button("🚀 WYKONAJ ZAMKNIĘCIE", use_container_width=True, type="primary", key="confirm_2_sidebar"):
                        execute_period_close(lock_df, lock_dt)
                        reset_lock_state()
                        st.rerun()
            if st.button("Anuluj", use_container_width=True, key="cancel_close_sidebar"):
                reset_lock_state()
                st.rerun()

    st.divider()

    # ---- Usuń zaznaczone wpisy ----
    if st.session_state.selected_ids:
        if st.button(f"🗑️ USUŃ LINIĘ ({len(st.session_state.selected_ids)})", use_container_width=True, type="primary", key="delete_sidebar_btn"):
            st.session_state.show_delete_confirm = True

        if st.session_state.show_delete_confirm:
            st.warning("Czy na pewno chcesz usunąć zaznaczone wpisy?")
            if st.button("✅ POTWIERDŹ USUNIĘCIE", use_container_width=True, type="primary", key="delete_sidebar_confirm"):
                for rid in st.session_state.selected_ids:
                    result = supabase.table("finanse").delete().eq("id", int(rid)).execute()
                    if not result.data:
                        st.warning(f"Nie udało się usunąć wpisu ID={rid}.")
                st.session_state.selected_ids       = []
                st.session_state.show_delete_confirm = False
                st.rerun()
            if st.button("Anuluj", use_container_width=True, key="delete_sidebar_cancel"):
                st.session_state.show_delete_confirm = False
                st.rerun()
    else:
        st.session_state.show_delete_confirm = False

    st.divider()

    # ---- Pobierz raport ----
    if st.button("📥 Pobierz raport", use_container_width=True, key="open_report_picker"):
        st.session_state.show_report_picker  = not st.session_state.show_report_picker
        st.session_state.show_send_picker    = False
        st.session_state.show_archive_picker = False
        st.rerun()

    if st.session_state.show_report_picker:
        with st.container(border=True):
            report_df = st.date_input("Data od", value=default_date_from, key="report_date_from_picker")
            report_dt = st.date_input("Data do", value=default_date_to,   key="report_date_to_picker")
            if report_df > report_dt:
                st.error("Data od nie może być większa niż data do.")
            else:
                df_rep = sort_df_by_data_zdarzenia(filter_data_by_date_range(load_data(), report_df, report_dt))
                rp, rg, rw, rpr = calculate_range_sums(df_rep)
                st.write(f"Gotówka z przeniesienia: **{rpr:,.2f} zł**")
                st.write(f"Przychód: **{rp:,.2f} zł**")
                st.write(f"Gotówka: **{rg:,.2f} zł**")
                st.write(f"Wydatki: **{rw:,.2f} zł**")
                st.download_button(
                    "📥 Pobierz PDF",
                    data=create_pdf(df_rep, rp, rg, rw, rpr, report_df, report_dt),
                    file_name=f"raport_{report_df}_{report_dt}.pdf",
                    use_container_width=True,
                    key="download_pdf_range",
                )
                st.download_button(
                    "📥 Pobierz CSV",
                    data=public_csv_data(df_rep),
                    file_name=f"raport_{report_df}_{report_dt}.csv",
                    use_container_width=True,
                    key="download_csv_range",
                )
            if st.button("↩️ Powrót", use_container_width=True, key="report_back_btn"):
                st.session_state.show_report_picker = False
                st.rerun()

    st.divider()

    # ---- Archiwum raportów ----
    if st.button("📜 Archiwum raportów", use_container_width=True, key="open_archive_picker"):
        st.session_state.show_archive_picker = not st.session_state.show_archive_picker
        st.session_state.show_send_picker    = False
        st.session_state.show_report_picker  = False
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
                        gen_date = r_row.get("data_wygenerowania") or r_row.get("data", "")
                        st.write(f"**Wygenerowano:** {gen_date}")
                        st.write(f"💰 Suma Przychodów: {r_row['suma_przychodow']:.2f} zł")
                        try:
                            if "Brak daty" in (str(r_row["okres_od"]), str(r_row["okres_do"])):
                                st.warning("Zbyt stary wpis — brak pełnych danych źródłowych.")
                            else:
                                df_arch_rows = load_report_rows(r_row)
                                st.download_button(
                                    "📥 Pobierz CSV",
                                    data=public_csv_data(df_arch_rows),
                                    file_name=f"archiwum_{r_row['okres_od']}_{r_row['okres_do']}.csv",
                                    key=f"dl_arch_{r_row['id']}",
                                    use_container_width=True,
                                )
                        except Exception as e:
                            st.error(f"Nie udało się odtworzyć danych: {e}")
            if st.button("↩️ Powrót", use_container_width=True, key="archive_back_btn"):
                st.session_state.show_archive_picker = False
                st.rerun()

    st.divider()

    # ---- Wyloguj ----
    if st.button("🔓 Wyloguj", use_container_width=True, key="logout_btn"):
        cookies["auth_token"] = ""
        cookies.save()
        st.rerun()


# =============================================================================
# 16. HISTORIA WPISÓW
# =============================================================================

st.divider()
st.markdown("""
    <div style="
        margin: 2rem 0 1.5rem 0;
        border-top: 1px solid rgba(255,255,255,0.06);
        position: relative;
    ">
        <span style="
            position: absolute;
            top: -0.65rem;
            left: 0;
            background: #0a0a0f;
            padding-right: 1rem;
            font-family: 'Syne', sans-serif;
            font-size: 1.05rem;
            font-weight: 800;
            color: #eeeef8;
            letter-spacing: -0.01em;
        ">Historia wpisów</span>
    </div>
    <div style="height: 0.8rem;"></div>
""", unsafe_allow_html=True)

if not df_history.empty:
    df_display = sort_df_by_data_zdarzenia(df_history)[
        ["id", "data", "data_zdarzenia", "typ", "kwota", "opis"]
    ].copy()
    df_display["kwota"] = pd.to_numeric(df_display["kwota"], errors="coerce").fillna(0).map(
        lambda x: f"{x:,.2f} zł"
    )

    # --- Tabela HTML (kolory) + multiselect do zaznaczania ---
    import html as _html

    rows_data = []
    for _, row in df_display.iterrows():
        rid  = int(row["id"])
        typ  = str(row["typ"])
        opis = str(row.get("opis",""))
        if opis.lower() in ("empty","nan","none",""): opis = ""
        if typ == "Przychód ogólny":
            kolor="#22c55e"; bg="rgba(34,197,94,0.10)"; bd="rgba(34,197,94,0.20)"
        elif typ == "Wydatki gotówkowe":
            kolor="#ef4444"; bg="rgba(239,68,68,0.10)"; bd="rgba(239,68,68,0.20)"
        elif typ == CARRYOVER_TYPE:
            kolor="#60a5fa"; bg="rgba(96,165,250,0.10)"; bd="rgba(96,165,250,0.20)"
        elif "Gotówka" in typ:
            kolor="#f59e0b"; bg="rgba(245,158,11,0.10)"; bd="rgba(245,158,11,0.20)"
        else:
            kolor="#c8c8e0"; bg="rgba(255,255,255,0.03)"; bd="rgba(255,255,255,0.05)"
        rows_data.append((rid,typ,opis,str(row.get("data","")),str(row.get("data_zdarzenia","")),str(row["kwota"]),kolor,bg,bd))

    all_ids   = [r[0] for r in rows_data]
    id_labels = {r[0]: f"{r[4]} | {r[1]}{(' · '+r[2]) if r[2] else ''} | {r[5]}" for r in rows_data}

    # Multiselect do zaznaczania — kompaktowy
    selected_ids = st.multiselect(
        "Zaznacz do usunięcia:",
        options=all_ids,
        default=[i for i in st.session_state.selected_ids if i in all_ids],
        format_func=lambda x: id_labels.get(x, str(x)),
        key="hist_multisel",
    )

    if selected_ids != st.session_state.selected_ids:
        st.session_state.selected_ids = selected_ids
        st.session_state.show_delete_confirm = False
        st.rerun()

    # Tabela HTML z kolorami
    rows_html = ""
    for rid,typ,opis,data,zdarz,kwota,kolor,bg,bd in rows_data:
        t = _html.escape(typ)
        o = _html.escape(opis)
        d = _html.escape(data)
        z = _html.escape(zdarz)
        k = _html.escape(kwota)
        label = f"{t} &middot; {o}" if o else t
        is_sel = rid in selected_ids
        border = f"2px solid {kolor}" if is_sel else f"1px solid {bd}"
        ck = f'<span style="color:{kolor};font-weight:700;">✓</span>' if is_sel else ""
        rows_html += (
            f'<div style="display:grid;grid-template-columns:20px 78px 84px 1fr 98px;'
            f'gap:6px;align-items:center;padding:0.52rem 0.8rem;'
            f'background:{bg};border-bottom:{border};">'
            f'<div>{ck}</div>'
            f'<div style="font-size:0.74rem;color:{kolor};opacity:0.75;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{d}</div>'
            f'<div style="font-size:0.74rem;color:{kolor};font-weight:600;white-space:nowrap;">{z}</div>'
            f'<div style="font-size:0.76rem;color:{kolor};font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{label}</div>'
            f'<div style="font-size:0.82rem;color:{kolor};font-weight:700;text-align:right;white-space:nowrap;">{k}</div>'
            f'</div>'
        )

    st.markdown(f"""
        <style>
        .hw2 {{ overflow-y:auto; max-height:420px; border-radius:14px;
                border:1px solid rgba(255,255,255,0.07); background:#0f0f16; }}
        .hw2::-webkit-scrollbar {{ width:4px; }}
        .hw2::-webkit-scrollbar-thumb {{ background:#2a2a3a; border-radius:2px; }}
        .hw2-head {{ display:grid; grid-template-columns:20px 78px 84px 1fr 98px;
                     gap:6px; padding:0.45rem 0.8rem;
                     border-bottom:1px solid rgba(255,255,255,0.09);
                     position:sticky; top:0; background:#14141c; z-index:2; }}
        .hw2-head span {{ font-size:0.62rem; font-weight:700; text-transform:uppercase;
                          letter-spacing:0.1em; color:#3a3a52; }}
        .hw2-head span:last-child {{ text-align:right; }}
        @media(max-width:768px){{
            .hw2-head,.hw2 > div > div{{ font-size:0.65rem !important; }}
        }}
        </style>
        <div class="hw2">
            <div class="hw2-head">
                <span></span><span>Wpis</span><span>Zdarzenie</span>
                <span>Typ / Opis</span><span>Kwota</span>
            </div>
            {rows_html}
        </div>
    """, unsafe_allow_html=True)

    # Przycisk usuwania
    if st.session_state.selected_ids:
        if not st.session_state.get("show_delete_confirm"):
            if st.button(f"🗑️ Usuń zaznaczone ({len(st.session_state.selected_ids)})",
                         use_container_width=True, type="primary", key="delete_checked_btn"):
                st.session_state.show_delete_confirm = True
                st.rerun()
        else:
            ids_str = ", ".join(str(x) for x in st.session_state.selected_ids)
            st.warning(f"⚠️ Usunięcie **{len(st.session_state.selected_ids)}** wpis(ów): ID {ids_str}. Tej operacji nie można cofnąć!")
            confirm_text = st.text_input(
                'Wpisz "USUŃ" aby potwierdzić:',
                key="delete_confirm_text",
                placeholder="USUŃ",
            )
            cd1, cd2 = st.columns(2)
            with cd1:
                ok = confirm_text.strip().upper() == "USUŃ"
                if st.button("✅ Potwierdź usunięcie", use_container_width=True, type="primary",
                             key="delete_confirm_yes", disabled=not ok):
                    for rid in st.session_state.selected_ids:
                        supabase.table("finanse").delete().eq("id", int(rid)).execute()
                    st.session_state.selected_ids = []
                    st.session_state.show_delete_confirm = False
                    st.success("✅ Usunięto wpisy.")
                    st.rerun()
            with cd2:
                if st.button("Anuluj", use_container_width=True, key="delete_confirm_no"):
                    st.session_state.show_delete_confirm = False
                    st.rerun()


else:
    st.info("Brak wpisów w historii dla wybranego okresu.")


# Bottom nav — Streamlit przyciski ukryte, HTML pasek na wierzchu
st.markdown("""
    <style>
    /* Ukryj etykiety przycisków nav — zostawiamy tylko funkcjonalność */
    div[data-testid="stHorizontalBlock"]:has(#nav_home) button,
    div[data-testid="stHorizontalBlock"]:has(#nav_menu) button,
    div[data-testid="stHorizontalBlock"]:has(#nav_hist) button {
        opacity: 0 !important;
        position: absolute !important;
        height: 4.8rem !important;
        width: 100% !important;
        z-index: 100000 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""<div class="bottom-nav">
    <div style="display:flex;flex-direction:column;align-items:center;gap:3px;color:#7c6eff;font-size:0.58rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;">
        <span style="font-size:1.4rem;">🏠</span><span>Główna</span>
    </div>
    <div style="display:flex;flex-direction:column;align-items:center;gap:3px;color:#7c6eff;font-size:0.58rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;">
        <span style="font-size:1.4rem;">⚙️</span><span>Menu</span>
    </div>
    <div style="display:flex;flex-direction:column;align-items:center;gap:3px;color:#4a4a62;font-size:0.58rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;">
        <span style="font-size:1.4rem;">📋</span><span>Historia</span>
    </div>
</div>""", unsafe_allow_html=True)

nav1, nav2, nav3 = st.columns(3)
with nav1:
    if st.button("🏠", key="nav_home", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()
with nav2:
    if st.button("⚙️", key="nav_menu", use_container_width=True):
        st.session_state.page = "menu"
        st.rerun()
with nav3:
    if st.button("📋", key="nav_hist", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()

# =============================================================================
# 17. SZYBKIE AKCJE (MOBILNE)
# =============================================================================

st.divider()
st.markdown("""
<style>
/* Szybkie akcje — duże kafelki z ikonką */
div[data-testid="stHorizontalBlock"]:has(.quick-action-col) {
    gap: 0.75rem !important;
}
.quick-btn > div > button {
    height: 5.5rem !important;
    border-radius: 16px !important;
    flex-direction: column !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    gap: 0.4rem !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    line-height: 1 !important;
}
</style>
""", unsafe_allow_html=True)

st.subheader("⚡ Szybkie akcje")

m1, m2 = st.columns(2)

with m1:
    if st.button("📧\nRaport", use_container_width=True, key="mobile_report"):
        df_mob = sort_df_by_data_zdarzenia(load_data())
        mp, mg, mw, mpr = calculate_range_sums(df_mob)
        if send_email_with_reports(
            create_pdf(df_mob, mp, mg, mw, mpr),
            public_csv_data(df_mob),
        ):
            st.success("✅ Wysłano raport!")

with m2:
    if st.button("🔒\nZamknij", use_container_width=True, key="mobile_lock"):
        st.session_state.lock_step      = 1
        st.session_state.lock_confirm_1 = False
        st.session_state.lock_confirm_2 = False
        st.rerun()

# Formularz zamknięcia okresu (wspólny — pojawia się po kliknięciu z paska lub mobile)
if st.session_state.lock_step >= 1:
    with st.container(border=True):
        st.markdown("**Zamknij i rozlicz okres**")
        lock_df_m = st.date_input("Rozlicz od:", value=get_now().date(), key="lock_date_from_mobile")
        lock_dt_m = st.date_input("Rozlicz do:", value=get_now().date(), key="lock_date_to_mobile")

        if lock_df_m > lock_dt_m:
            st.error("Data od nie może być większa niż data do.")
        else:
            if not st.session_state.lock_confirm_1:
                if st.button("❓ Jesteś pewien?", use_container_width=True, type="primary", key="confirm_1_mobile"):
                    st.session_state.lock_confirm_1 = True
                    st.rerun()
            elif not st.session_state.lock_confirm_2:
                st.warning("⚠️ Tej czynności nie można cofnąć!")
                ca, cb = st.columns(2)
                with ca:
                    if st.button("🚀 WYKONAJ ZAMKNIĘCIE", use_container_width=True, type="primary", key="confirm_2_mobile"):
                        execute_period_close(lock_df_m, lock_dt_m)
                        reset_lock_state()
                        st.rerun()
                with cb:
                    if st.button("Anuluj", use_container_width=True, key="cancel_close_mobile_inner"):
                        reset_lock_state()
                        st.rerun()

        if not st.session_state.lock_confirm_1:
            if st.button("Anuluj", use_container_width=True, key="cancel_close_mobile"):
                reset_lock_state()
                st.rerun()    # --- st.dataframe z on_select + kolorowanie przez Styler ---
    import html as _html

    df_show = df_display[["id","data","data_zdarzenia","typ","kwota","opis"]].copy()
    df_show["kwota"] = pd.to_numeric(df_show["kwota"].astype(str).str.replace(" zł","").str.replace(",",""), errors="coerce").fillna(0)

    def style_history(row):
        typ = str(row["typ"])
        if typ == "Przychód ogólny":
            c = "background-color:rgba(34,197,94,0.12);color:#22c55e"
        elif typ == "Wydatki gotówkowe":
            c = "background-color:rgba(239,68,68,0.12);color:#ef4444"
        elif typ == CARRYOVER_TYPE:
            c = "background-color:rgba(96,165,250,0.12);color:#60a5fa"
        elif "Gotówka" in typ:
            c = "background-color:rgba(245,158,11,0.12);color:#f59e0b"
        else:
            c = "background-color:rgba(255,255,255,0.03);color:#c8c8e0"
        return [c] * len(row)

    styled = df_show.style.apply(style_history, axis=1)

    event = st.dataframe(
        styled,
        hide_index=True,
        use_container_width=True,
        height=440,
        key="hist_df",
        on_select="rerun",
        selection_mode="multi-row",
        column_config={
            "id":             st.column_config.NumberColumn("ID",        width="small"),
            "data":           st.column_config.TextColumn("Wpis",        width="small"),
            "data_zdarzenia": st.column_config.TextColumn("Zdarzenie",   width="small"),
            "typ":            st.column_config.TextColumn("Typ",         width="medium"),
            "kwota":          st.column_config.NumberColumn("Kwota",     width="small", format="%.2f zł"),
            "opis":           st.column_config.TextColumn("Opis",        width="large"),
        },
    )

    # Pobierz zaznaczone wiersze
    sel_rows = event.selection.rows if event.selection else []
    new_selected = [int(df_show.iloc[i]["id"]) for i in sel_rows]

    if new_selected != st.session_state.selected_ids:
        st.session_state.selected_ids = new_selected
        st.session_state.show_delete_confirm = False

    # Przycisk usuwania
    if st.session_state.selected_ids:
        if not st.session_state.get("show_delete_confirm"):
            if st.button(f"🗑️ Usuń zaznaczone ({len(st.session_state.selected_ids)})",
                         use_container_width=True, type="primary", key="delete_checked_btn"):
                st.session_state.show_delete_confirm = True
                st.rerun()
        else:
            ids_str = ", ".join(str(x) for x in st.session_state.selected_ids)
            st.warning(f"⚠️ Usunięcie **{len(st.session_state.selected_ids)}** wpis(ów): ID {ids_str}. Tej operacji nie można cofnąć!")
            confirm_text = st.text_input(
                'Wpisz "USUŃ" aby potwierdzić:',
                key="delete_confirm_text",
                placeholder="USUŃ",
            )
            cd1, cd2 = st.columns(2)
            with cd1:
                ok = confirm_text.strip().upper() == "USUŃ"
                if st.button("✅ Potwierdź usunięcie", use_container_width=True, type="primary",
                             key="delete_confirm_yes", disabled=not ok):
                    for rid in st.session_state.selected_ids:
                        supabase.table("finanse").delete().eq("id", int(rid)).execute()
                    st.session_state.selected_ids = []
                    st.session_state.show_delete_confirm = False
                    st.success("✅ Usunięto wpisy.")
                    st.rerun()
            with cd2:
                if st.button("Anuluj", use_container_width=True, key="delete_confirm_no"):
                    st.session_state.show_delete_confirm = False
                    st.rerun()


else:
    st.info("Brak wpisów w historii dla wybranego okresu.")


# Bottom nav — Streamlit przyciski ukryte, HTML pasek na wierzchu
st.markdown("""
    <style>
    /* Ukryj etykiety przycisków nav — zostawiamy tylko funkcjonalność */
    div[data-testid="stHorizontalBlock"]:has(#nav_home) button,
    div[data-testid="stHorizontalBlock"]:has(#nav_menu) button,
    div[data-testid="stHorizontalBlock"]:has(#nav_hist) button {
        opacity: 0 !important;
        position: absolute !important;
        height: 4.8rem !important;
        width: 100% !important;
        z-index: 100000 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""<div class="bottom-nav">
    <div style="display:flex;flex-direction:column;align-items:center;gap:3px;color:#7c6eff;font-size:0.58rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;">
        <span style="font-size:1.4rem;">🏠</span><span>Główna</span>
    </div>
    <div style="display:flex;flex-direction:column;align-items:center;gap:3px;color:#7c6eff;font-size:0.58rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;">
        <span style="font-size:1.4rem;">⚙️</span><span>Menu</span>
    </div>
    <div style="display:flex;flex-direction:column;align-items:center;gap:3px;color:#4a4a62;font-size:0.58rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;">
        <span style="font-size:1.4rem;">📋</span><span>Historia</span>
    </div>
</div>""", unsafe_allow_html=True)

nav1, nav2, nav3 = st.columns(3)
with nav1:
    if st.button("🏠", key="nav_home", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()
with nav2:
    if st.button("⚙️", key="nav_menu", use_container_width=True):
        st.session_state.page = "menu"
        st.rerun()
with nav3:
    if st.button("📋", key="nav_hist", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()

# =============================================================================
# 17. SZYBKIE AKCJE (MOBILNE)
# =============================================================================

st.divider()
st.markdown("""
<style>
/* Szybkie akcje — duże kafelki z ikonką */
div[data-testid="stHorizontalBlock"]:has(.quick-action-col) {
    gap: 0.75rem !important;
}
.quick-btn > div > button {
    height: 5.5rem !important;
    border-radius: 16px !important;
    flex-direction: column !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    gap: 0.4rem !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    line-height: 1 !important;
}
</style>
""", unsafe_allow_html=True)

st.subheader("⚡ Szybkie akcje")

m1, m2 = st.columns(2)

with m1:
    if st.button("📧\nRaport", use_container_width=True, key="mobile_report"):
        df_mob = sort_df_by_data_zdarzenia(load_data())
        mp, mg, mw, mpr = calculate_range_sums(df_mob)
        if send_email_with_reports(
            create_pdf(df_mob, mp, mg, mw, mpr),
            public_csv_data(df_mob),
        ):
            st.success("✅ Wysłano raport!")

with m2:
    if st.button("🔒\nZamknij", use_container_width=True, key="mobile_lock"):
        st.session_state.lock_step      = 1
        st.session_state.lock_confirm_1 = False
        st.session_state.lock_confirm_2 = False
        st.rerun()

# Formularz zamknięcia okresu (wspólny — pojawia się po kliknięciu z paska lub mobile)
if st.session_state.lock_step >= 1:
    with st.container(border=True):
        st.markdown("**Zamknij i rozlicz okres**")
        lock_df_m = st.date_input("Rozlicz od:", value=get_now().date(), key="lock_date_from_mobile")
        lock_dt_m = st.date_input("Rozlicz do:", value=get_now().date(), key="lock_date_to_mobile")

        if lock_df_m > lock_dt_m:
            st.error("Data od nie może być większa niż data do.")
        else:
            if not st.session_state.lock_confirm_1:
                if st.button("❓ Jesteś pewien?", use_container_width=True, type="primary", key="confirm_1_mobile"):
                    st.session_state.lock_confirm_1 = True
                    st.rerun()
            elif not st.session_state.lock_confirm_2:
                st.warning("⚠️ Tej czynności nie można cofnąć!")
                ca, cb = st.columns(2)
                with ca:
                    if st.button("🚀 WYKONAJ ZAMKNIĘCIE", use_container_width=True, type="primary", key="confirm_2_mobile"):
                        execute_period_close(lock_df_m, lock_dt_m)
                        reset_lock_state()
                        st.rerun()
                with cb:
                    if st.button("Anuluj", use_container_width=True, key="cancel_close_mobile_inner"):
                        reset_lock_state()
                        st.rerun()

        if not st.session_state.lock_confirm_1:
            if st.button("Anuluj", use_container_width=True, key="cancel_close_mobile"):
                reset_lock_state()
                st.rerun()
