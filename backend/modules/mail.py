# ── Mail System (IMAP + SMTP + Gemini) ───────────────────────────────────────

import imaplib
import smtplib
import email as email_lib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
import base64

IMAP_HOST = "imap.strato.de"
IMAP_PORT = 993
SMTP_HOST = "smtp.strato.de"
SMTP_PORT = 465
GEMINI_KEY = ""  # Wird aus DB-Einstellungen gelesen

def get_mail_creds(db):
    u = db.execute("SELECT value FROM settings WHERE key='mail_user'").fetchone()
    p = db.execute("SELECT value FROM settings WHERE key='mail_pass'").fetchone()
    return (u["value"] if u else "admin@example.com",
            p["value"] if p else "05220677dD!")

def decode_str(s):
    if not s: return ""
    parts = decode_header(s)
    result = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            result += part.decode(enc or "utf-8", errors="replace")
        else:
            result += str(part)
    return result

def fetch_all_inbox() -> list:
    """Holt ALLE Mails aus dem Postfach (letzten 500)."""
    with get_db() as db:
        user, pwd = get_mail_creds(db)
    mails = []
    try:
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
            imap.login(user, pwd)
            imap.select("INBOX")
            # Echte UIDs verwenden (stabil, ändern sich nicht)
            _, uid_data = imap.uid("search", None, "ALL")
            uids = uid_data[0].split() if uid_data[0] else []
            # Letzte 300 Mails
            uids = uids[-300:]
            for uid_bytes in uids:
                try:
                    _, msg_data = imap.uid("fetch", uid_bytes, "(RFC822)")
                    if not msg_data or not msg_data[0]:
                        continue
                    raw = msg_data[0][1]
                    if not isinstance(raw, bytes):
                        continue
                    msg = email_lib.message_from_bytes(raw)
                    num = uid_bytes  # für Kompatibilität
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            ct = part.get_content_type()
                            cd = str(part.get("Content-Disposition",""))
                            if ct == "text/plain" and "attachment" not in cd:
                                try:
                                    body = part.get_payload(decode=True).decode("utf-8","replace")
                                except:
                                    body = str(part.get_payload())
                                break
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode("utf-8","replace")
                        except:
                            body = str(msg.get_payload())
                    # To und CC Header sammeln - möglichst viele Empfängerfelder
                    to_field   = decode_str(msg.get("To",""))
                    cc_field   = decode_str(msg.get("Cc",""))
                    delivered  = decode_str(msg.get("Delivered-To",""))
                    x_del      = decode_str(msg.get("X-Delivered-To",""))
                    x_orig     = decode_str(msg.get("X-Original-To",""))
                    envelope   = decode_str(msg.get("Envelope-To",""))
                    all_rcpt   = (to_field + " " + cc_field + " " + delivered + " " + x_del + " " + x_orig + " " + envelope).lower()
                    # HTML-Body auch erfassen
                    html_body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            ct2 = part.get_content_type()
                            cd2 = str(part.get("Content-Disposition",""))
                            if ct2 == "text/html" and "attachment" not in cd2:
                                try:
                                    html_body = part.get_payload(decode=True).decode("utf-8","replace")
                                except:
                                    html_body = str(part.get_payload())
                                break
                    mails.append({
                        "uid":           "uid_" + uid_bytes.decode(),
                        "from":          decode_str(msg.get("From","")),
                        "reply_to":      decode_str(msg.get("Reply-To","")),
                        "to":            to_field,
                        "subject":       decode_str(msg.get("Subject","")),
                        "date":          msg.get("Date",""),
                        "body":          body[:10000] if body else html_body[:10000],
                        "html_body":     html_body[:100000],
                        "all_rcpt":      all_rcpt,
                        "message_id":    decode_str(msg.get("Message-ID","")),
                        "auto_submitted": decode_str(msg.get("Auto-Submitted","")).lower(),
                        "x_autoreply":   decode_str(msg.get("X-Autoreply","")).lower(),
                    })
                except Exception as e:
                    print(f"[mail] Fehler beim Parsen: {e}", flush=True)
    except Exception as e:
        print(f"[mail] IMAP Verbindungsfehler: {e}", flush=True)
    return mails

def fetch_inbox_for_address(catch_email: str) -> list:
    """Filtert alle Mails auf eine bestimmte Catch-All Adresse."""
    all_mails = fetch_all_inbox()
    addr_local = catch_email.split("@")[0].lower()
    addr_domain = catch_email.split("@")[1].lower() if "@" in catch_email else ""
    matched = []
    for m in all_mails:
        rcpt = m.get("all_rcpt","")
        # Match wenn die Adresse irgendwo in den Empfängerfeldern steht
        if catch_email.lower() in rcpt:
            matched.append(m)
        # Auch matchen wenn nur der lokale Teil + Domain passt (Varianten)
        elif addr_local in rcpt and addr_domain in rcpt:
            matched.append(m)
    return matched

def send_mail_smtp(from_addr: str, to_addr: str, subject: str,
                   body: str, attachments: list = None,
                   in_reply_to: str = "", references: str = "") -> dict:
    """
    Sendet Mail über Strato SMTP.
    Strato erlaubt nur Senden von der echten Postfach-Adresse (mail_user).
    From/Reply-To werden auf die generierte Catch-All-Adresse gesetzt,
    SMTP sendmail läuft aber über die echte Adresse - Logitech sieht
    die generierte Adresse und antwortet dorthin.
    in_reply_to: Message-ID der Original-Mail → setzt In-Reply-To Header
                 → Zendesk threaded korrekt, kein neues Ticket / keine Auto-Antwort!
    """
    with get_db() as db:
        user, pwd = get_mail_creds(db)

    if not user or not pwd:
        return {"ok": False, "error": "Keine Mail-Zugangsdaten. Bitte in Einstellungen eintragen."}

    msg = MIMEMultipart()
    msg["From"]     = from_addr   # Logitech sieht diese Adresse
    msg["Reply-To"] = from_addr   # Antworten gehen hierhin
    msg["To"]       = to_addr
    msg["Subject"]  = subject
    # Threading-Header: verhindert dass Zendesk eine neue Anfrage erstellt
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"]  = references or in_reply_to
    msg.attach(MIMEText(body, "plain", "utf-8"))

    if attachments:
        for att in attachments:
            try:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(base64.b64decode(att["data"]))
                encoders.encode_base64(part)
                part.add_header("Content-Disposition",
                                f'attachment; filename="{att["filename"]}"')
                msg.attach(part)
            except Exception as ae:
                print(f"[mail] Anhang Fehler: {ae}", flush=True)

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(user, pwd)
            # Strato erfordert echte Postfach-Adresse als SMTP-Absender
            smtp.sendmail(user, to_addr, msg.as_string())
        print(f"[mail] OK: {user}→{to_addr} (From:{from_addr})", flush=True)
        return {"ok": True}
    except smtplib.SMTPAuthenticationError:
        return {"ok": False, "error": "SMTP Login fehlgeschlagen — Zugangsdaten prüfen"}
    except smtplib.SMTPRecipientsRefused:
        return {"ok": False, "error": f"Empfänger abgelehnt: {to_addr}"}
    except smtplib.SMTPSenderRefused:
        return {"ok": False, "error": "Absender abgelehnt — prüfe Mail-Einstellungen"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_mail_mailgun(from_addr: str, to_addr: str, subject: str,
                      body: str, attachments: list = None,
                      in_reply_to: str = "", references: str = "") -> dict:
    """Sendet Mail über Mailgun API — erlaubt beliebige from_addr auf der Domain."""
    with get_db() as db:
        row = db.execute("SELECT value FROM settings WHERE key='mailgun_key'").fetchone()
        domain_row = db.execute("SELECT value FROM settings WHERE key='mailgun_domain'").fetchone()
    
    api_key = row["value"] if row else ""
    mg_domain = domain_row["value"] if domain_row else "kafka-frame.com"
    
    if not api_key:
        return {"ok": False, "error": "Kein Mailgun API-Key. Bitte in Einstellungen eintragen."}
    
    try:
        # Mailgun EU API
        url = f"https://api.eu.mailgun.net/v3/{mg_domain}/messages"
        data = {
            "from":    from_addr,
            "to":      to_addr,
            "subject": subject,
            "text":    body,
        }
        # Threading-Header: verhindert dass Zendesk eine neue Anfrage erstellt
        if in_reply_to:
            data["h:In-Reply-To"] = in_reply_to
            data["h:References"]  = references or in_reply_to
        files = []
        if attachments:
            for att in attachments:
                try:
                    import base64 as _b64
                    files.append(("attachment", (att["filename"], _b64.b64decode(att["data"]))))
                except Exception as ae:
                    print(f"[mailgun] Anhang Fehler: {ae}", flush=True)
        
        r = requests.post(
            url,
            auth=("api", api_key),
            data=data,
            files=files if files else None,
            timeout=15
        )
        print(f"[mailgun] {r.status_code}: {r.text[:150]}", flush=True)
        if r.status_code in (200, 201, 202):
            return {"ok": True}
        else:
            # Versuche US-API als Fallback
            url_us = f"https://api.mailgun.net/v3/{mg_domain}/messages"
            r2 = requests.post(url_us, auth=("api", api_key), data=data,
                               files=files if files else None, timeout=15)
            print(f"[mailgun] US fallback {r2.status_code}: {r2.text[:150]}", flush=True)
            if r2.status_code in (200, 201, 202):
                return {"ok": True}
            return {"ok": False, "error": f"Mailgun {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"ok": False, "error": f"Mailgun Fehler: {str(e)}"}


def send_mail_auto(from_addr: str, to_addr: str, subject: str,
                   body: str, attachments: list = None,
                   in_reply_to: str = "", references: str = "") -> dict:
    """
    Wählt automatisch den besten Versandweg:
    1. Mailgun (wenn API-Key vorhanden) — erlaubt beliebige from_addr
    2. SMTP (Strato) — nur von erlanger@kafka-frame.com
    """
    with get_db() as db:
        mg_key = db.execute("SELECT value FROM settings WHERE key='mailgun_key'").fetchone()
    
    if mg_key and mg_key["value"]:
        result = send_mail_mailgun(from_addr, to_addr, subject, body, attachments,
                                   in_reply_to=in_reply_to, references=references)
        result["method"] = "mailgun"
        if result["ok"]:
            print(f"[mail] Mailgun: {from_addr} → {to_addr}", flush=True)
            return result
        print(f"[mail] Mailgun fehlgeschlagen, versuche SMTP: {result.get('error')}", flush=True)
    
    # SMTP Fallback
    result = send_mail_smtp(from_addr, to_addr, subject, body, attachments,
                            in_reply_to=in_reply_to, references=references)
    result["method"] = "smtp"
    return result


def gemini_generate_mail(product: str, sender_name: str, lang: str = "de") -> dict:
    """Lässt Gemini einen kurzen, menschlichen Support-Mail-Text generieren."""
    with get_db() as db:
        row = db.execute("SELECT value FROM settings WHERE key='gemini_key'").fetchone()
        api_key = row["value"] if row else ""

    if not api_key:
        return {"ok": False, "error": "Kein Gemini API-Key in Einstellungen gesetzt."}

    # Versuche verschiedene Modelle falls eines Rate-Limited ist.
    # WICHTIG: Das Free-Tier hat RPM-Limits (Requests per Minute), nicht nur Tageslimits.
    # gemini-2.0-flash: 15 RPM, 1500 RPD — gemini-2.0-flash-lite: 30 RPM, 1500 RPD
    # Auch wenn noch Tageskontingent offen ist, können Minuten-Limits greifen!
    models = ["gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"]

    if lang == "de":
        prompt = (
            "Erstelle eine Support-Anfrage an Logitech fuer " + sender_name + " ueber defektes " + product + ". "
            "Antworte NUR mit JSON ohne Markdown-Backticks, Format: "
            "{\"subject\": \"max 8 Woerter\", \"body\": \"3-5 natuerliche Saetze Deutsch\"}"
        )
    else:
        prompt = (
            "Create a Logitech support request for " + sender_name + " about broken " + product + ". "
            "Reply ONLY with JSON no markdown backticks, format: "
            "{\"subject\": \"max 8 words\", \"body\": \"3-5 natural sentences English\"}"
        )
    last_error = ""
    for attempt, model in enumerate(models):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            r = requests.post(url, json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=20)
            if r.status_code == 429:
                # Progressiver Backoff: 4s, 8s, 12s, 16s
                # Das RPM-Limit (Requests per Minute) greift auch wenn Tageskontingent noch offen ist!
                wait_secs = 4 * (attempt + 1)
                last_error = f"Rate limit für {model}"
                print(f"[gemini] 429 für {model} (RPM-Limit), warte {wait_secs}s vor nächstem Versuch", flush=True)
                time.sleep(wait_secs)
                continue
            if r.status_code == 404:
                last_error = f"Modell {model} nicht gefunden"
                print(f"[gemini] 404 für {model}, versuche nächstes", flush=True)
                continue
            if r.status_code == 400:
                err_msg = r.json().get("error",{}).get("message","Bad Request")
                print(f"[gemini] 400 für {model}: {err_msg}", flush=True)
                last_error = f"400: {err_msg}"
                continue
            r.raise_for_status()
            raw = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            raw_clean = raw.replace("```json","").replace("```","").strip()
            try:
                data = json.loads(raw_clean)
                return {"ok": True, "subject": data.get("subject",""), "body": data.get("body","")}
            except json.JSONDecodeError:
                lines = [l.strip() for l in raw.split("\n") if l.strip()]
                return {"ok": True, "subject": lines[0][:80] if lines else "Support-Anfrage", "body": raw}
        except Exception as e:
            last_error = str(e)
            if "429" in str(e):
                print(f"[gemini] Rate limit {model}: {e}", flush=True)
                continue
            return {"ok": False, "error": str(e)}
    return {"ok": False, "error": f"Alle Modelle rate-limited. {last_error}"}

def init_mail_tables():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS mail_messages (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                reg_id       INTEGER,
                direction    TEXT,  -- 'out' | 'in'
                from_addr    TEXT,
                to_addr      TEXT,
                subject      TEXT,
                body         TEXT,
                sent_at      TEXT,
                read_at      TEXT
            )""")
        for k, v in [
            ("mail_user", ""),  # wird in Einstellungen gesetzt
            ("mail_pass", "05220677dD!"),
            ("gemini_key", ""),  # In Einstellungen eintragen
        ]:
            db.execute("INSERT OR IGNORE INTO settings VALUES (?,?)", (k, v))
        db.commit()

# ── IMAP Poller ───────────────────────────────────────────────────────────────

def imap_poll_loop():
    """Holt alle 90s ALLE Mails und ordnet sie den Registrierungen zu."""
    print("[mail] IMAP Poller gestartet", flush=True)
    while True:
        try:
            # Alle Mails auf einmal holen (effizienter als pro Adresse)
            all_mails = fetch_all_inbox()
            print(f"[mail] {len(all_mails)} Mails im Postfach", flush=True)
            # Globalen Inbox synchronisieren
            new_in_inbox = sync_inbox()
            if new_in_inbox > 0:
                print(f"[mail] {new_in_inbox} neue Mails im Postfach", flush=True)

            with get_db() as db:
                regs = db.execute(
                    "SELECT id, email, serial FROM registrations WHERE email != ''"
                ).fetchall()

            for reg in regs:
                addr_local  = reg["email"].split("@")[0].lower()
                addr_domain = reg["email"].split("@")[1].lower() if "@" in reg["email"] else ""
                for m in all_mails:
                    rcpt = m.get("all_rcpt","")
                    # Prüfe ob diese Mail für diese Adresse ist
                    if reg["email"].lower() not in rcpt:
                        if not (addr_local in rcpt and addr_domain in rcpt):
                            continue
                    with get_db() as db:
                        exists = db.execute(
                            "SELECT id FROM mail_messages WHERE reg_id=? AND subject=? AND from_addr=?",
                            (reg["id"], m["subject"], m["from"])
                        ).fetchone()
                        if not exists:
                            db.execute("""
                                INSERT INTO mail_messages
                                (reg_id,direction,from_addr,to_addr,subject,body,sent_at,read_at)
                                VALUES (?,?,?,?,?,?,?,NULL)
                            """, (reg["id"], "in", m["from"], reg["email"],
                                  m["subject"], m["body"], m["date"]))
                            db.commit()
                            print(f"[mail] NEU für {reg['email']}: {m['subject']} (von {m['from']})", flush=True)
                            # RMA automatisch verarbeiten
                            process_mail_for_rma(reg["id"], m.get("body",""), m.get("subject",""), m.get("from",""))
        except Exception as e:
            print(f"[mail] Poll-Fehler: {e}", flush=True)
        time.sleep(60)

# ── Mail API Routes ───────────────────────────────────────────────────────────

class SendMailInput(BaseModel):
    reg_id:      int
    subject:     str
    body:        str
    country:     str = "de"
    attachments: list = []
    from_addr:   str = ""   # Explizite Absender-Adresse vom Frontend
    ticket_id:   str = ""   # Manuelle Ticket-ID Überschreibung
    in_reply_to: str = ""   # Message-ID der Ursprungsmail (für korrektes Threading)

class GeminiInput(BaseModel):
    product:     str
    sender_name: str
    lang:        str = "de"

@app.post("/api/mail/generate")
def mail_generate(inp: GeminiInput):
    return gemini_generate_mail(inp.product, inp.sender_name, inp.lang)

@app.post("/api/mail/send")
def mail_send(inp: SendMailInput):
    with get_db() as db:
        reg = db.execute(
            "SELECT * FROM registrations WHERE id=?", (inp.reg_id,)
        ).fetchone()
    if not reg:
        raise HTTPException(404, "Registrierung nicht gefunden")

    # from_addr: vom Frontend explizit übergeben (korrekte Catch-All Adresse)
    # Fallback auf reg.email aus der DB
    from_addr = inp.from_addr.strip() if inp.from_addr else reg["email"]
    if not from_addr:
        from_addr = reg["email"]
    print(f"[mail] from_addr: {from_addr}", flush=True)

    # Richtige Empfängeradresse ermitteln:
    # 1. Reply-To der letzten eingehenden Logitech-Mail
    # 2. from_addr der letzten eingehenden Mail
    # Fallback falls kein Ticket bekannt: support@logi.com (NICHT support@logitech.com, das ist unmonitored!)
    to_addr = "support@logi.com"
    import re as _re2

    def extract_email(raw: str) -> str:
        """Extrahiert echte E-Mail aus 'Name <email>' oder rohem String."""
        if not raw: return ""
        m = _re2.search(r'<([^>]+)>', raw)
        if m: return m.group(1).strip()
        # Letztes Wort falls kein <> Format
        parts = raw.strip().split()
        for part in reversed(parts):
            if '@' in part:
                return part.strip('<>',)
        return raw.strip()

    with get_db() as db:
        # Letzte eingehende Mail — Reply-To hat Priorität
        last_inbox = db.execute("""
            SELECT from_addr, reply_to FROM inbox
            WHERE reg_id=? 
            ORDER BY id DESC LIMIT 1
        """, (inp.reg_id,)).fetchone()
        last_msg = db.execute("""
            SELECT from_addr FROM mail_messages
            WHERE reg_id=? AND direction='in'
            ORDER BY sent_at DESC LIMIT 1
        """, (inp.reg_id,)).fetchone()

    if last_inbox:
        # Reply-To hat immer Vorrang (Zendesk setzt das korrekt)
        reply_to = extract_email(last_inbox["reply_to"] if last_inbox["reply_to"] else "")
        from_email = extract_email(last_inbox["from_addr"] or "")
        to_addr = reply_to or from_email or to_addr

    # In-Reply-To: vom Frontend übergeben oder automatisch aus der letzten Inbox-Mail
    in_reply_to = inp.in_reply_to.strip() if inp.in_reply_to else ""
    if not in_reply_to:
        with get_db() as db:
            last_mid = db.execute("""
                SELECT message_id FROM inbox
                WHERE reg_id=? AND message_id != '' AND is_auto_reply=0
                ORDER BY id DESC LIMIT 1
            """, (inp.reg_id,)).fetchone()
            if last_mid:
                in_reply_to = last_mid["message_id"]
                print(f"[mail] In-Reply-To automatisch gesetzt: {in_reply_to[:60]}", flush=True)
    elif last_msg:
        to_addr = extract_email(last_msg["from_addr"] or "") or to_addr

    # Ticket-ID: manuell überschrieben oder aus Registrierung
    with get_db() as db:
        ticket_id = inp.ticket_id.strip() if inp.ticket_id else (reg["ticket_id"] or "")
    print(f"[mail] ticket_id: {ticket_id!r}", flush=True)

    print(f"[mail] Sende Antwort für reg {inp.reg_id}, ticket={ticket_id}, from={from_addr}", flush=True)

    result = {"ok": False, "error": "Kein Sendeweg gefunden"}

    # ── Versand: Zendesk Reply-Adresse hat immer Vorrang ─────────────────
    if ticket_id:
        # Direkt an Zendesk Ticket über die korrekte Zendesk-Subdomain.
        # WICHTIG: support@logitech.com ist UNMONITORED (Einwegadresse für Auto-Replies).
        # Die richtige Adresse ist support+id{TICKET}@logitech.zendesk.com
        zendesk_reply_addr = f"support+id{ticket_id}@logitech.zendesk.com"
        print(f"[mail] Sende an Zendesk To: {zendesk_reply_addr} Von: {from_addr} In-Reply-To: {in_reply_to[:40]}", flush=True)
        result = send_mail_auto(
            from_addr=from_addr,
            to_addr=zendesk_reply_addr,
            subject=inp.subject,
            body=inp.body,
            attachments=inp.attachments or [],
            in_reply_to=in_reply_to,
        )
        result["to_addr"] = zendesk_reply_addr
        if result["ok"]:
            print(f"[mail] Erfolgreich an Ticket #{ticket_id}", flush=True)
        else:
            # Fallback: logitech.com versuchen (funktioniert normalerweise nicht)
            zendesk_reply_addr2 = f"support+id{ticket_id}@logitech.com"
            print(f"[mail] Fallback: {zendesk_reply_addr2}", flush=True)
            result = send_mail_auto(
                from_addr=from_addr,
                to_addr=zendesk_reply_addr2,
                subject=inp.subject,
                body=inp.body,
                attachments=inp.attachments or [],
                in_reply_to=in_reply_to,
            )
            result["to_addr"] = zendesk_reply_addr2
    else:
        # Kein Ticket: direkt an support@logi.com
        print(f"[mail] Kein Ticket-ID, sende an: {to_addr}", flush=True)
        result = send_mail_auto(
            from_addr=from_addr,
            to_addr=to_addr,
            subject=inp.subject,
            body=inp.body,
            attachments=inp.attachments or [],
            in_reply_to=in_reply_to,
        )
        result["to_addr"] = to_addr

    if result["ok"]:
        with get_db() as db:
            db.execute("""
                INSERT INTO mail_messages
                (reg_id,direction,from_addr,to_addr,subject,body,sent_at,read_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (inp.reg_id, "out", from_addr,
                  result.get("to_addr", to_addr),
                  inp.subject, inp.body,
                  datetime.now(timezone.utc).isoformat(),
                  datetime.now(timezone.utc).isoformat()))
            db.commit()
    return result

@app.get("/api/mail/thread/{reg_id}")
def mail_thread(reg_id: int):
    with get_db() as db:
        msgs = db.execute(
            "SELECT * FROM mail_messages WHERE reg_id=? ORDER BY sent_at ASC",
            (reg_id,)
        ).fetchall()
        # Als gelesen markieren
        db.execute(
            "UPDATE mail_messages SET read_at=? WHERE reg_id=? AND read_at IS NULL AND direction='in'",
            (datetime.now(timezone.utc).isoformat(), reg_id)
        )
        db.commit()
    return [dict(m) for m in msgs]

@app.get("/api/mail/unread")
def mail_unread():
    with get_db() as db:
        rows = db.execute("""
            SELECT mm.reg_id, r.email, r.serial, COUNT(*) as count,
                   MAX(mm.sent_at) as latest
            FROM mail_messages mm
            JOIN registrations r ON r.id = mm.reg_id
            WHERE mm.direction='in' AND mm.read_at IS NULL
            GROUP BY mm.reg_id
        """).fetchall()
    return [dict(r) for r in rows]

@app.post("/api/mail/fetch/{reg_id}")
def mail_fetch_now(reg_id: int):
    """Manuell Mails für eine Registrierung abrufen."""
    with get_db() as db:
        reg = db.execute("SELECT * FROM registrations WHERE id=?", (reg_id,)).fetchone()
    if not reg:
        raise HTTPException(404, "Nicht gefunden")
    try:
        mails = fetch_inbox_for_address(reg["email"])
        new_count = 0
        for m in mails:
            with get_db() as db:
                exists = db.execute(
                    "SELECT id FROM mail_messages WHERE reg_id=? AND subject=? AND from_addr=?",
                    (reg_id, m["subject"], m["from"])
                ).fetchone()
                if not exists:
                    db.execute("""
                        INSERT INTO mail_messages
                        (reg_id,direction,from_addr,to_addr,subject,body,sent_at,read_at)
                        VALUES (?,?,?,?,?,?,?,NULL)
                    """, (reg_id, "in", m["from"], reg["email"],
                          m["subject"], m["body"], m["date"]))
                    db.commit()
                    new_count += 1
        return {"ok": True, "new": new_count, "total": len(mails)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

