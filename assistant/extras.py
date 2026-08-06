"""
Tool-ecosystem extras (all optional-dep / confirm-gated):
  • email     — SMTP send when cfg has smtp_host/user/password (confirm-gated)
  • pdf       — text extraction via pypdf when installed
  • downloads — watch ~/Downloads for fresh files (digital-twin feed)
"""

import os
import time


# ------------------------------------------------------------------ email
def send_email(to, subject, body, cfg, confirm_fn=None):
    from . import security

    ok, note = security.gate("ceo", security.NETWORK, confirm_fn,
                             detail=f"email to {to}")
    if not ok:
        return note
    host, user, pwd = (cfg.get("smtp_host"), cfg.get("smtp_user"),
                       cfg.get("smtp_password"))
    if not (host and user and pwd):
        return ("Email not configured — add smtp_host / smtp_user / "
                "smtp_password to config.")
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    with smtplib.SMTP(host, cfg.get("smtp_port", 587)) as s:
        s.starttls()
        s.login(user, pwd)
        s.send_message(msg)
    return f"Email sent to {to}."


# ------------------------------------------------------------------ pdf
def latest_pdf(folder=None):
    folder = folder or os.path.join(os.path.expanduser("~"), "Downloads")
    try:
        pdfs = [os.path.join(folder, f) for f in os.listdir(folder)
                if f.lower().endswith(".pdf")]
        return max(pdfs, key=os.path.getmtime) if pdfs else None
    except OSError:
        return None


def pdf_summary(path=None, pages=2):
    path = path or latest_pdf()
    if not path:
        return "No PDF found in Downloads."
    try:
        from pypdf import PdfReader
    except ImportError:
        return f"Found {os.path.basename(path)} — install pypdf to analyze it."
    try:
        r = PdfReader(path)
        text = "".join((p.extract_text() or "") for p in r.pages[:pages])
        return f"{os.path.basename(path)} ({len(r.pages)} pages): {text[:400].strip()}"
    except Exception as e:  # noqa: BLE001
        return f"PDF read failed: {e}"


# ------------------------------------------------------------------ downloads
def fresh_downloads(minutes=60):
    folder = os.path.join(os.path.expanduser("~"), "Downloads")
    out = []
    try:
        for f in os.listdir(folder):
            p = os.path.join(folder, f)
            if os.path.isfile(p) and time.time() - os.path.getmtime(p) < minutes * 60:
                out.append(f)
    except OSError:
        pass
    return sorted(out)
