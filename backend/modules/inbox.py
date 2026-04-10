# ── Globales Postfach (alle Mails direkt) ─────────────────────────────────────

def init_inbox_table():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS inbox (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                uid       TEXT UNIQUE,
                from_addr TEXT,
                to_addr   TEXT,
                subject   TEXT,
                body      TEXT,
                html_body TEXT DEFAULT '',
                date_raw  TEXT,
                received_at TEXT,
                read_at   TEXT,
                reg_id    INTEGER,
                starred   INTEGER DEFAULT 0,
                folder_id INTEGER DEFAULT NULL,
                message_id  TEXT DEFAULT '',
                is_auto_reply INTEGER DEFAULT 0
            )""")
        db.execute("""
            CREATE TABLE IF NOT EXISTS mail_folders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                color      TEXT DEFAULT '#4a90d9',
                icon       TEXT DEFAULT '📁',
                auto_rule  TEXT DEFAULT '',
                created_at TEXT
            )""")
        # Migrations
        for col, dflt in [
            ("html_body",     "TEXT DEFAULT ''"),
            ("reply_to",      "TEXT DEFAULT ''"),
            ("folder_id",     "INTEGER DEFAULT NULL"),
            ("message_id",    "TEXT DEFAULT ''"),
            ("is_auto_reply", "INTEGER DEFAULT 0"),
            ("replied_at",    "TEXT DEFAULT NULL"),
        ]:
            try: db.execute(f"ALTER TABLE inbox ADD COLUMN {col} {dflt}")
            except: pass
        db.commit()

import re as _re

def _extract_email_addr(s: str) -> str:
    """Extrahiert reine E-Mail-Adresse aus einem Header wie 'Name <addr@domain.com>'."""
    s = s.lower().strip()
    m = _re.search(r'<([^>]+@[^>]+)>', s)
    if m:
        return m.group(1).strip()
    # Kein <>, versuche direkt
    m = _re.search(r'[\w.+%-]+@[\w.-]+\.[a-z]{2,}', s)
    if m:
        return m.group(0).strip()
    return s

def _match_email_in_rcpt(email: str, all_rcpt: str) -> bool:
    """Prüft ob eine E-Mail-Adresse in den Empfängerfeldern vorkommt."""
    email = email.lower().strip()
    all_rcpt = all_rcpt.lower()
    if email in all_rcpt:
        return True
    found = _re.findall(r'[\w.+%-]+@[\w.-]+\.[a-z]{2,}', all_rcpt)
    return email in found

def extract_ticket_number(text: str) -> str:
    """Extrahiert Zendesk Ticket-Nummer aus Mail-Text."""
    import re
    patterns = [
        r'Ticket(?:\s+(?:Number|Nr|#|ID))?[:\s#]+([0-9]{6,10})',
        r'Case(?:\s+(?:Number|Nr|#))?[:\s#]+([0-9]{6,10})',
        r'\[#([0-9]{6,10})\]',
        r'Fallnummer[:\s]+([0-9]{6,10})',
        r'#([0-9]{7,10})',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""

def extract_tracking_numbers(text: str) -> list:
    """Extrahiert Tracking-Nummern von DHL, UPS, FedEx, Hermes aus Mail-Text."""
    import re
    results = []
    patterns = [
        ("DHL",    r'\b(\d{12,22})\b'),
        ("DHL",    r'\b(JD[0-9]{18})\b'),
        ("UPS",    r'\b(1Z[A-Z0-9]{16})\b'),
        ("FedEx",  r'\b(\d{12}|\d{15}|\d{20,22})\b'),
        ("Hermes", r'\b(H\d{18})\b'),
        ("DPD",    r'\b(\d{14}|%5B\d{14}%5D)\b'),
        ("GLS",    r'\b(\d{11})\b'),
    ]
    seen = set()
    for carrier, pat in patterns:
        for m in re.finditer(pat, text):
            num = m.group(1)
            if num not in seen and len(num) >= 10:
                seen.add(num)
                results.append({"carrier": carrier, "tracking": num})
    return results

def extract_agent_name(text: str) -> str:
    """Extrahiert Sachbearbeiter-Name aus Logitech-Mail."""
    import re
    patterns = [
        r'----\s+([A-Z][a-z]+(?:\s+[A-Z])?),',
        r'Mein Name ist ([A-Z][a-zA-ZÀ-ÿ]+)',
        r'My name is ([A-Z][a-zA-Z]+)',
        r'Mit freundlichen Grüßen,\s+([A-Z][a-zA-ZÀ-ÿ]+)',
        r'Best regards,\s+([A-Z][a-zA-Z]+)',
        r'Kind regards,\s+([A-Z][a-zA-Z]+)',
        r'Thank you,?\s+([A-Z][a-zA-Z]+)\s+Logitech',
        r'Sincerely,?\s+([A-Z][a-zA-Z]+)',
        r'Regards,?\s+([A-Z][a-zA-Z]+)',
        r'(?:^|\n)([A-Z][a-z]+)\s+Logitech',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.MULTILINE)
        if m:
            name = m.group(1).strip()
            if 2 < len(name) < 40 and name not in ("Logitech","Support","Team","Please","Thank"):
                return name
    return ""

def analyze_sentiment(text: str) -> str:
    """Analysiert ob eine Logitech-Mail positiv, negativ oder neutral ist."""
    text_lower = text.lower()
    positive_kw = [
        "replacement","austausch","ersatz","new unit","sending","shipping","rma",
        "approved","genehm","schicken","senden","ersatzgerät","gutschrift","refund",
        "we will send","wir senden","warranty replacement","garantieaustausch",
        "ship","versenden","auf dem weg","unterwegs","paket","tracking",
        "exchange","tausch","kostenfrei","kostenlos","free of charge",
        "we are happy to","gerne","freude","ersetzen","replace",
    ]
    negative_kw = [
        "not covered","nicht abgedeckt","unable to","leider nicht","bedauern",
        "abgelehnt","denied","cannot","out of warranty","außerhalb der garantie",
        "no longer","nicht mehr","physical damage","user damage","missbrauch",
        "not eligible","not qualify","kein anspruch","ablehnen","ablehnung",
        "unfortunately we","leider können wir","nicht möglich","not possible",
        "void","ungültig","invalid","expired","abgelaufen",
    ]
    neutral_kw = [
        "please try","bitte versuchen","troubleshoot","fehlerbehebung",
        "we need","wir benötigen","further information","weitere informationen",
        "could you please","könnten sie","can you","können sie",
        "we are investigating","wir prüfen","looking into","untersuchen",
    ]
    pos = sum(1 for k in positive_kw if k in text_lower)
    neg = sum(1 for k in negative_kw if k in text_lower)
    neu = sum(1 for k in neutral_kw if k in text_lower)

    if pos > neg and pos > 0:   return "positive"
    if neg > pos and neg > 0:   return "negative"
    if neu > 0:                 return "waiting"
    return ""  # Unbekannt - nicht überschreiben

def process_mail_for_rma(reg_id: int, body_text: str, subject: str, from_addr: str):
    """
    Zentrale Funktion: analysiert eine eingehende Mail und aktualisiert
    ticket_status, agent_stats automatisch.
    """
    ticket_num    = extract_ticket_number(subject + " " + body_text)
    agent_name    = extract_agent_name(body_text)
    tracking_nums = extract_tracking_numbers(body_text)
    sentiment     = analyze_sentiment(body_text)
    first_track   = tracking_nums[0] if tracking_nums else None

    # Sentiment-Override: Tracking = immer positiv
    if first_track:
        sentiment = "positive"

    print(f"[rma] reg={reg_id} | sentiment={sentiment} | agent={agent_name} | "
          f"ticket={ticket_num} | tracking={first_track}", flush=True)

    try:
        with get_db() as db:
            ts = db.execute(
                "SELECT reg_id, ticket_id, agent_name, tracking, status FROM ticket_status WHERE reg_id=?",
                (reg_id,)
            ).fetchone()

            updates, params = [], []

            if ts:
                # Ticket-Nummer nur setzen wenn noch leer
                if ticket_num and not ts["ticket_id"]:
                    updates.append("ticket_id=?"); params.append(ticket_num)

                # Agent: immer aktualisieren wenn neu erkannt
                if agent_name:
                    updates.append("agent_name=?"); params.append(agent_name)

                # Tracking: setzen wenn neu
                if first_track and not ts["tracking"]:
                    updates.append("tracking=?"); params.append(first_track["tracking"])
                    updates.append("carrier=?");  params.append(first_track["carrier"])

                # Status: nur upgraden (open→waiting→positive/negative), nie downgraden
                status_rank = {"open":0,"waiting":1,"positive":2,"negative":2,"closed":3,"archived":4}
                cur_rank = status_rank.get(ts["status"] or "open", 0)
                new_rank = status_rank.get(sentiment, 0) if sentiment else 0
                if sentiment and new_rank > cur_rank:
                    updates.append("status=?"); params.append(sentiment)
                elif sentiment and ts["status"] in ("open","waiting") and sentiment:
                    updates.append("status=?"); params.append(sentiment)

                if updates:
                    params.append(reg_id)
                    db.execute(f"UPDATE ticket_status SET {chr(44).join(updates)} WHERE reg_id=?", params)
                    db.commit()
                    print(f"[rma] ticket_status aktualisiert: {updates}", flush=True)
            else:
                # Neu anlegen
                db.execute("""
                    INSERT OR IGNORE INTO ticket_status
                    (reg_id, status, agent_name, ticket_id, tracking, carrier)
                    VALUES (?,?,?,?,?,?)
                """, (reg_id,
                      sentiment or "waiting",
                      agent_name or "",
                      ticket_num or "",
                      first_track["tracking"] if first_track else "",
                      first_track["carrier"]  if first_track else ""))
                db.commit()
                print(f"[rma] Neuer ticket_status angelegt für reg {reg_id}", flush=True)

            # Agent-Statistik aktualisieren
            if agent_name:
                is_pos = 1 if sentiment == "positive" else 0
                is_neg = 1 if sentiment == "negative" else 0
                db.execute("""
                    INSERT INTO agent_stats (agent_name,total,positive,negative,updated_at)
                    VALUES (?,1,?,?,?)
                    ON CONFLICT(agent_name) DO UPDATE SET
                        total=total+1,
                        positive=positive+?,
                        negative=negative+?,
                        updated_at=?
                """, (agent_name, is_pos, is_neg, datetime.now(timezone.utc).isoformat(),
                      is_pos, is_neg, datetime.now(timezone.utc).isoformat()))
                db.commit()
    except Exception as e:
        print(f"[rma] process_mail_for_rma Fehler: {e}", flush=True)


def sync_inbox():
    """Holt alle Mails, speichert in inbox-Tabelle und verarbeitet für RMA."""
    all_mails = fetch_all_inbox()
    new_count = 0
    with get_db() as db:
        regs = db.execute("SELECT id, email FROM registrations WHERE email != ''").fetchall()

    for m in all_mails:
        uid = m.get("uid","")
        if not uid:
            continue

        # Registrierung zuordnen
        reg_id = None
        for reg in regs:
            if _match_email_in_rcpt(reg["email"], m.get("all_rcpt","")):
                reg_id = reg["id"]
                break

        body_text = m.get("body","")
        subject   = m.get("subject","") or ""
        message_id = m.get("message_id","") or ""
        from_lower = (m.get("from","") or "").lower()

        # Auto-Reply-Erkennung: Zendesk-Bestätigungen, Bounce-Mails, etc.
        # Diese erscheinen als "komische Mail" wenn man auf Support-Mails antwortet.
        is_auto_reply = 0
        auto_submitted = m.get("auto_submitted","") or ""
        x_autoreply    = m.get("x_autoreply","") or ""
        # UPS, DHL, FedEx Versandbenachrichtigungen NIE als auto_reply markieren
        is_shipping_mail = (
            "ups.com" in from_lower or
            "dhl.com" in from_lower or
            "fedex.com" in from_lower or
            "pkginfo" in from_lower or
            "versandbenachrichtigung" in subject.lower() or
            "shipping notification" in subject.lower() or
            "kontrollnummer" in subject.lower() or
            "tracking" in subject.lower()
        )
        if not is_shipping_mail and (
            auto_submitted and auto_submitted != "no" or
            x_autoreply in ("yes","true","1") or
            "noreply" in from_lower or
            "no-reply" in from_lower or
            "zendesk.com" in from_lower or
            "mailer-daemon" in from_lower or
            (subject.lower().startswith("[logitech]") and "anfrage" in subject.lower()) or
            (subject.lower().startswith("re:") and "logitech" in subject.lower()
             and "ticket" in subject.lower() and not body_text.strip())
        ):
            is_auto_reply = 1
            print(f"[inbox] Auto-Reply erkannt: {subject[:60]} | from={m.get('from','')[:40]}", flush=True)

        with get_db() as db:
            exists = db.execute("SELECT id, reg_id FROM inbox WHERE uid=?", (uid,)).fetchone()
            if not exists:
                # Reply-To Spalte hinzufügen falls nicht vorhanden
                try:
                    db.execute("ALTER TABLE inbox ADD COLUMN reply_to TEXT DEFAULT ''")
                    db.commit()
                except: pass
                db.execute("""
                    INSERT OR IGNORE INTO inbox
                    (uid,from_addr,to_addr,reply_to,subject,body,html_body,date_raw,received_at,read_at,reg_id,starred,message_id,is_auto_reply)
                    VALUES (?,?,?,?,?,?,?,?,?,NULL,?,0,?,?)
                """, (uid, m["from"], m.get("to",""), m.get("reply_to",""), subject,
                      body_text, m.get("html_body",""), m["date"],
                      datetime.now(timezone.utc).isoformat(), reg_id, message_id, is_auto_reply))
                db.commit()
                new_count += 1
                print(f"[inbox] Neu: {subject[:60]} | reg={reg_id}", flush=True)
                # Neue Mail sofort für RMA verarbeiten
                if reg_id:
                    process_mail_for_rma(reg_id, body_text, subject, m["from"])
            else:
                # reg_id nachträglich setzen
                old_reg = exists["reg_id"]
                if reg_id and not old_reg:
                    db.execute("UPDATE inbox SET reg_id=? WHERE uid=?", (reg_id, uid))
                    db.commit()
                # Auch bestehende Mails verarbeiten wenn reg_id neu gesetzt
                if reg_id and not old_reg:
                    process_mail_for_rma(reg_id, body_text, subject, m["from"])

    return new_count

@app.get("/api/inbox")
def get_inbox(limit: int = 100, unread_only: bool = False, hide_auto: bool = False):
    with get_db() as db:
        q = "SELECT i.*, r.serial, r.name as reg_name FROM inbox i LEFT JOIN registrations r ON r.id = i.reg_id"
        where = []
        if unread_only:
            where.append("i.read_at IS NULL")
        if hide_auto:
            where.append("i.is_auto_reply = 0")
        if where:
            q += " WHERE " + " AND ".join(where)
        q += " ORDER BY i.id DESC LIMIT ?"
        rows = db.execute(q, (limit,)).fetchall()
    return [dict(r) for r in rows]

@app.get("/api/inbox/unread-count")
def inbox_unread_count():
    with get_db() as db:
        count = db.execute("SELECT COUNT(*) as c FROM inbox WHERE read_at IS NULL").fetchone()["c"]
    return {"count": count}

@app.post("/api/inbox/{mail_id}/unread")
def mark_unread(mail_id: int):
    with get_db() as db:
        db.execute("UPDATE inbox SET read_at=NULL WHERE id=?", (mail_id,))
        db.commit()
    return {"ok": True}

@app.post("/api/inbox/{mail_id}/read")
def mark_read(mail_id: int):
    with get_db() as db:
        db.execute("UPDATE inbox SET read_at=? WHERE id=?",
                   (datetime.now(timezone.utc).isoformat(), mail_id))
        db.commit()
    return {"ok": True}

@app.post("/api/inbox/read-all")
def mark_all_read():
    with get_db() as db:
        db.execute("UPDATE inbox SET read_at=? WHERE read_at IS NULL",
                   (datetime.now(timezone.utc).isoformat(),))
        db.commit()
    return {"ok": True}

@app.post("/api/inbox/{mail_id}/star")
def toggle_star(mail_id: int):
    with get_db() as db:
        cur = db.execute("SELECT starred FROM inbox WHERE id=?", (mail_id,)).fetchone()
        new_val = 0 if (cur and cur["starred"]) else 1
        db.execute("UPDATE inbox SET starred=? WHERE id=?", (new_val, mail_id))
        db.commit()
    return {"ok": True, "starred": new_val}

@app.post("/api/inbox/sync")
def sync_inbox_now():
    new = sync_inbox()
    return {"ok": True, "new": new}

@app.post("/api/inbox/reprocess-all")
def reprocess_all_for_rma():
    """Verarbeitet alle vorhandenen Mails nochmal für RMA-Status-Updates."""
    with get_db() as db:
        mails = db.execute("""
            SELECT i.id, i.reg_id, i.body, i.subject, i.from_addr
            FROM inbox i
            WHERE i.reg_id IS NOT NULL
            ORDER BY i.id ASC
        """).fetchall()
    processed = 0
    for mail in mails:
        process_mail_for_rma(
            mail["reg_id"],
            mail["body"] or "",
            mail["subject"] or "",
            mail["from_addr"] or ""
        )
        processed += 1
    # Auch mail_messages verarbeiten
    with get_db() as db:
        msgs = db.execute("""
            SELECT reg_id, body, subject, from_addr
            FROM mail_messages
            WHERE direction='in' AND reg_id IS NOT NULL
        """).fetchall()
    for msg in msgs:
        process_mail_for_rma(
            msg["reg_id"],
            msg["body"] or "",
            msg["subject"] or "",
            msg["from_addr"] or ""
        )
        processed += 1
    return {"ok": True, "processed": processed}

@app.post("/api/inbox/{mail_id}/assign/{reg_id}")
def assign_mail_to_reg(mail_id: int, reg_id: int):
    """Ordnet eine Inbox-Mail manuell einer Registrierung zu."""
    with get_db() as db:
        db.execute("UPDATE inbox SET reg_id=? WHERE id=?", (reg_id, mail_id))
        db.commit()
    return {"ok": True}

class FreeReplyInput(BaseModel):
    from_addr:   str
    to_addr:     str
    subject:     str
    body:        str
    attachments: list = []
    in_reply_to: str = ""   # Message-ID der Ursprungsmail (für Threading)
    original_mail_id: int = 0  # inbox DB ID — damit Reply-To und Message-ID automatisch ermittelt werden

@app.post("/api/inbox/reply-free")
def inbox_reply_free(inp: FreeReplyInput):
    """Sendet eine freie Antwort — nutzt Reply-To und In-Reply-To für korrektes Zendesk-Threading."""
    import re as _re3

    to = inp.to_addr.strip()
    in_reply_to = inp.in_reply_to.strip() if inp.in_reply_to else ""

    # Wenn original_mail_id angegeben: Reply-To und Message-ID aus der DB holen
    if inp.original_mail_id:
        with get_db() as db:
            orig = db.execute(
                "SELECT reply_to, from_addr, message_id, subject FROM inbox WHERE id=?",
                (inp.original_mail_id,)
            ).fetchone()
            if orig:
                # Reply-To hat Vorrang vor From
                reply_to_raw = orig["reply_to"] or orig["from_addr"] or ""
                m = _re3.search(r'<([^>]+)>', reply_to_raw)
                resolved_to = m.group(1).strip() if m else reply_to_raw.strip()
                if resolved_to and '@' in resolved_to:
                    to = resolved_to
                    print(f"[reply-free] Reply-To aus DB: {to}", flush=True)
                # In-Reply-To automatisch setzen wenn nicht manuell angegeben
                if not in_reply_to and orig["message_id"]:
                    in_reply_to = orig["message_id"]
                    print(f"[reply-free] In-Reply-To aus DB: {in_reply_to[:60]}", flush=True)

    # Fallback: E-Mail aus <addr> extrahieren
    m = _re3.search(r'<([^>]+)>', to)
    if m: to = m.group(1)

    # WICHTIG: support@logitech.com ist UNMONITORED!
    # Wenn die Zieladresse support@logitech.com ist, versuche Zendesk-Adresse zu ermitteln
    if to.lower() in ('support@logitech.com',):
        # Ticket-Nummer aus Betreff extrahieren
        ticket = extract_ticket_number(inp.subject + " " + inp.body[:500])
        if ticket:
            to = f"support+id{ticket}@logitech.zendesk.com"
            print(f"[reply-free] Korrigiert auf Zendesk: {to}", flush=True)
        else:
            # support@logi.com ist monitored (anders als support@logitech.com!)
            to = "support@logi.com"
            print(f"[reply-free] Fallback auf support@logi.com (monitored)", flush=True)

    result = send_mail_auto(
        from_addr=inp.from_addr,
        to_addr=to,
        subject=inp.subject,
        body=inp.body,
        attachments=inp.attachments or [],
        in_reply_to=in_reply_to,
    )
    result["to_addr"] = to
    # Replied-At auf der Original-Mail setzen damit Frontend das Badge zeigen kann
    if result.get("ok") and inp.original_mail_id:
        with get_db() as db:
            db.execute("UPDATE inbox SET replied_at=? WHERE id=?",
                       (datetime.now(timezone.utc).isoformat(), inp.original_mail_id))
            db.commit()
    return result

class GenerateFreeMailInput(BaseModel):
    product:     str = "Logitech Gerät"
    sender_name: str = "Kunde"
    lang:        str = "de"

@app.post("/api/mail/generate-free")
def mail_generate_free(inp: GenerateFreeMailInput):
    """Gemini Mail-Generator ohne Reg-Bindung."""
    return gemini_generate_mail(inp.product, inp.sender_name, inp.lang)



@app.post("/api/inbox/reassign-all")
def reassign_all_inbox():
    """Versucht alle unzugeordneten Mails nachträglich zuzuordnen."""
    with get_db() as db:
        regs = db.execute("SELECT id, email FROM registrations WHERE email != ''").fetchall()
        # Alle Mails ohne Registrierung
        unassigned = db.execute("SELECT id, to_addr, from_addr, subject, body FROM inbox WHERE reg_id IS NULL").fetchall()

    updated = 0
    for mail in unassigned:
        # Kombination aus To, From, Body für die Suche
        search_text = f"{mail['to_addr']} {mail['from_addr']} {mail['subject']} {mail['body'][:500]}".lower()
        for reg in regs:
            addr = reg["email"].lower()
            if addr in search_text:
                with get_db() as db:
                    db.execute("UPDATE inbox SET reg_id=? WHERE id=?", (reg["id"], mail["id"]))
                    db.commit()
                # Ticket-Nummer, Agent und Tracking extrahieren
                body = mail["body"] or ""
                ticket_num   = extract_ticket_number((mail["subject"] or "") + " " + body)
                agent_name   = extract_agent_name(body)
                tracking_nums = extract_tracking_numbers(body)
                if ticket_num or agent_name or tracking_nums:
                    try:
                        with get_db() as db:
                            ts = db.execute("SELECT reg_id, tracking FROM ticket_status WHERE reg_id=?", (reg["id"],)).fetchone()
                            first_track = tracking_nums[0] if tracking_nums else None
                            if not ts:
                                db.execute("INSERT OR IGNORE INTO ticket_status (reg_id,status,agent_name,tracking,carrier) VALUES (?,?,?,?,?)",
                                           (reg["id"],
                                            "positive" if tracking_nums else "waiting",
                                            agent_name or "",
                                            first_track["tracking"] if first_track else "",
                                            first_track["carrier"]  if first_track else ""))
                            else:
                                if ticket_num:
                                    db.execute("UPDATE ticket_status SET ticket_id=? WHERE reg_id=? AND (ticket_id IS NULL OR ticket_id='')", (ticket_num, reg["id"]))
                                if agent_name:
                                    db.execute("UPDATE ticket_status SET agent_name=? WHERE reg_id=? AND (agent_name IS NULL OR agent_name='')", (agent_name, reg["id"]))
                                if first_track and not ts["tracking"]:
                                    db.execute("UPDATE ticket_status SET tracking=?,carrier=?,status='positive' WHERE reg_id=?",
                                               (first_track["tracking"], first_track["carrier"], reg["id"]))
                                    print(f"[reassign] Tracking: {first_track['carrier']} {first_track['tracking']}", flush=True)
                            db.commit()
                    except Exception as e:
                        print(f"[reassign] ticket_status: {e}", flush=True)
                updated += 1
                print(f"[reassign] Mail {mail['id']} → reg {reg['id']} ({reg['email']})", flush=True)
                break
    return {"ok": True, "updated": updated}


# ── Monatliche Zusammenfassung ────────────────────────────────────────────────

@app.get("/api/stats/monthly")
def stats_monthly():
    with get_db() as db:
        # Letzte 12 Monate
        months = db.execute("""
            SELECT
                strftime('%Y-%m', checked_at) as month,
                COUNT(*) as total_checked,
                SUM(CASE WHEN status='valid' THEN 1 ELSE 0 END) as valid_found,
                SUM(CASE WHEN status='registered' THEN 1 ELSE 0 END) as registered_found
            FROM serials
            WHERE checked_at >= date('now', '-12 months')
            GROUP BY strftime('%Y-%m', checked_at)
            ORDER BY month DESC
        """).fetchall()

        # Tickets pro Monat
        tickets = db.execute("""
            SELECT
                strftime('%Y-%m', created_at) as month,
                COUNT(*) as total,
                SUM(CASE WHEN reg_status='ok' THEN 1 ELSE 0 END) as successful
            FROM registrations
            WHERE created_at >= date('now', '-12 months')
            GROUP BY strftime('%Y-%m', created_at)
            ORDER BY month DESC
        """).fetchall()

        # RMA Status pro Monat
        rma = db.execute("""
            SELECT
                strftime('%Y-%m', r.created_at) as month,
                ts.status,
                COUNT(*) as count,
                SUM(COALESCE(ts.value_eur, 0)) as value_sum
            FROM registrations r
            LEFT JOIN ticket_status ts ON ts.reg_id = r.id
            WHERE r.created_at >= date('now', '-12 months')
              AND ts.status IS NOT NULL
            GROUP BY strftime('%Y-%m', r.created_at), ts.status
            ORDER BY month DESC
        """).fetchall()

        # Aktueller Monat zusammengefasst
        cur_month = datetime.now(timezone.utc).strftime('%Y-%m')
        cur = db.execute("""
            SELECT
                COUNT(*) as tickets_total,
                SUM(CASE WHEN ts.status='positive' THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN ts.status='negative' THEN 1 ELSE 0 END) as negative,
                SUM(COALESCE(ts.value_eur, 0)) as value_sum,
                COUNT(DISTINCT ts.agent_name) as agents_count
            FROM registrations r
            LEFT JOIN ticket_status ts ON ts.reg_id = r.id
            WHERE strftime('%Y-%m', r.created_at) = ?
        """, (cur_month,)).fetchone()

        # Top Agent diesen Monat
        top_agent = db.execute("""
            SELECT ts.agent_name, COUNT(*) as total,
                   SUM(CASE WHEN ts.status='positive' THEN 1 ELSE 0 END) as positive
            FROM registrations r
            JOIN ticket_status ts ON ts.reg_id = r.id
            WHERE strftime('%Y-%m', r.created_at) = ?
              AND ts.agent_name != ''
            GROUP BY ts.agent_name
            ORDER BY positive DESC LIMIT 1
        """, (cur_month,)).fetchone()

        # Serials gefunden diesen Monat
        serials_this_month = db.execute("""
            SELECT COUNT(*) as c FROM serials
            WHERE strftime('%Y-%m', checked_at) = ? AND status='valid'
        """, (cur_month,)).fetchone()

    # Daten zusammenführen
    month_map = {}
    for m in months:
        month_map[m["month"]] = dict(m)
        month_map[m["month"]]["tickets"] = 0
        month_map[m["month"]]["value"] = 0
        month_map[m["month"]]["positive"] = 0

    for t in tickets:
        if t["month"] in month_map:
            month_map[t["month"]]["tickets"] = t["total"]

    for r in rma:
        if r["month"] in month_map:
            if r["status"] == "positive":
                month_map[r["month"]]["positive"] = r["count"]
                month_map[r["month"]]["value"] = float(r["value_sum"] or 0)

    return {
        "months":       list(month_map.values()),
        "current": {
            "month":         cur_month,
            "tickets":       cur["tickets_total"] or 0,
            "positive":      cur["positive"] or 0,
            "negative":      cur["negative"] or 0,
            "value":         float(cur["value_sum"] or 0),
            "serials_found": serials_this_month["c"] or 0,
            "top_agent":     dict(top_agent) if top_agent else None,
        }
    }


@app.post("/api/ticket-status/init-all")
def init_all_ticket_status():
    """Erstellt ticket_status Einträge für alle Registrierungen die noch keinen haben."""
    with get_db() as db:
        regs = db.execute("""
            SELECT r.id, r.ticket_id FROM registrations r
            LEFT JOIN ticket_status ts ON ts.reg_id = r.id
            WHERE ts.reg_id IS NULL
        """).fetchall()
        count = 0
        for reg in regs:
            db.execute("""
                INSERT OR IGNORE INTO ticket_status
                (reg_id, status, rma_number, tracking, carrier, value_eur, archived, agent_name, notes)
                VALUES (?, 'open', '', '', '', 0, 0, '', '')
            """, (reg["id"],))
            count += 1
        db.commit()
    return {"ok": True, "created": count}


@app.get("/api/debug/inbox-status")
def debug_inbox_status():
    """Zeigt den aktuellen Status der inbox und mail_messages Tabellen."""
    with get_db() as db:
        inbox_total = db.execute("SELECT COUNT(*) as c FROM inbox").fetchone()["c"]
        inbox_with_reg = db.execute("SELECT COUNT(*) as c FROM inbox WHERE reg_id IS NOT NULL").fetchone()["c"]
        inbox_no_reg = db.execute("SELECT COUNT(*) as c FROM inbox WHERE reg_id IS NULL").fetchone()["c"]
        
        msgs_total = db.execute("SELECT COUNT(*) as c FROM mail_messages").fetchone()["c"]
        msgs_in = db.execute("SELECT COUNT(*) as c FROM mail_messages WHERE direction='in'").fetchone()["c"]
        msgs_with_reg = db.execute("SELECT COUNT(*) as c FROM mail_messages WHERE reg_id IS NOT NULL AND direction='in'").fetchone()["c"]
        
        regs = db.execute("SELECT id, email, serial FROM registrations WHERE email != '' LIMIT 10").fetchall()
        
        # Sample inbox entries
        sample_inbox = db.execute("""
            SELECT id, uid, from_addr, to_addr, subject, reg_id,
                   substr(body,1,100) as body_preview
            FROM inbox ORDER BY id DESC LIMIT 5
        """).fetchall()
        
        # Sample mail_messages
        sample_msgs = db.execute("""
            SELECT id, reg_id, direction, from_addr, subject
            FROM mail_messages ORDER BY id DESC LIMIT 5
        """).fetchall()
        
        # ticket_status
        ts_count = db.execute("SELECT COUNT(*) as c FROM ticket_status").fetchone()["c"]
        ts_sample = db.execute("""
            SELECT ts.*, r.email, r.serial
            FROM ticket_status ts
            LEFT JOIN registrations r ON r.id = ts.reg_id
            LIMIT 5
        """).fetchall()

    return {
        "inbox": {
            "total": inbox_total,
            "with_reg": inbox_with_reg,
            "no_reg": inbox_no_reg,
            "sample": [dict(r) for r in sample_inbox]
        },
        "mail_messages": {
            "total": msgs_total,
            "incoming": msgs_in,
            "with_reg": msgs_with_reg,
            "sample": [dict(r) for r in sample_msgs]
        },
        "registrations": [dict(r) for r in regs],
        "ticket_status": {
            "count": ts_count,
            "sample": [dict(r) for r in ts_sample]
        }
    }


@app.get("/api/debug/html-body-check")
def debug_html_body_check():
    """Zeigt ob html_body in der DB gefüllt ist — hilft bei der Diagnose weißer Mails."""
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) as c FROM inbox").fetchone()["c"]
        with_html = db.execute("SELECT COUNT(*) as c FROM inbox WHERE html_body != \'\' AND html_body IS NOT NULL").fetchone()["c"]
        without_html = db.execute("SELECT COUNT(*) as c FROM inbox WHERE html_body = \'\' OR html_body IS NULL").fetchone()["c"]
        samples = db.execute("""
            SELECT id, from_addr, subject,
                length(body) as body_len,
                length(html_body) as html_body_len,
                substr(body, 1, 200) as body_preview,
                substr(html_body, 1, 200) as html_preview
            FROM inbox ORDER BY id DESC LIMIT 10
        """).fetchall()
    return {
        "total_mails": total,
        "with_html_body": with_html,
        "without_html_body": without_html,
        "diagnosis": "html_body LEER -> weisse Mails" if with_html == 0 else "html_body vorhanden",
        "samples": [dict(r) for r in samples]
    }

@app.post("/api/debug/force-reprocess")
def force_reprocess():
    """Verarbeitet ALLE Mails inklusive ohne reg_id — versucht zuerst zuzuordnen."""
    with get_db() as db:
        regs = db.execute("SELECT id, email FROM registrations WHERE email != ''").fetchall()
        # Alle inbox Mails
        all_inbox = db.execute("""
            SELECT id, uid, reg_id, body, subject, from_addr, to_addr
            FROM inbox ORDER BY id ASC
        """).fetchall()
        # Alle mail_messages (incoming)
        all_msgs = db.execute("""
            SELECT id, reg_id, body, subject, from_addr
            FROM mail_messages WHERE direction='in' ORDER BY id ASC
        """).fetchall()

    processed = 0
    assigned = 0

    for mail in all_inbox:
        reg_id = mail["reg_id"]
        # Versuche zuzuordnen falls noch nicht
        if not reg_id:
            search = f"{mail['to_addr']} {mail['from_addr']} {mail['subject']} {(mail['body'] or '')[:300]}".lower()
            for reg in regs:
                if reg["email"].lower() in search:
                    reg_id = reg["id"]
                    with get_db() as db:
                        db.execute("UPDATE inbox SET reg_id=? WHERE id=?", (reg_id, mail["id"]))
                        db.commit()
                    assigned += 1
                    print(f"[reprocess] inbox {mail['id']} → reg {reg_id}", flush=True)
                    break

        if reg_id:
            process_mail_for_rma(reg_id, mail["body"] or "", mail["subject"] or "", mail["from_addr"] or "")
            processed += 1

    for msg in all_msgs:
        reg_id = msg["reg_id"]
        if not reg_id:
            search = f"{msg['from_addr']} {msg['subject']} {(msg['body'] or '')[:300]}".lower()
            for reg in regs:
                if reg["email"].lower() in search:
                    reg_id = reg["id"]
                    with get_db() as db:
                        db.execute("UPDATE mail_messages SET reg_id=? WHERE id=?", (reg_id, msg["id"]))
                        db.commit()
                    assigned += 1
                    break
        if reg_id:
            process_mail_for_rma(reg_id, msg["body"] or "", msg["subject"] or "", msg["from_addr"] or "")
            processed += 1

    return {"ok": True, "processed": processed, "newly_assigned": assigned}


