# ── E-Mail Generator ──────────────────────────────────────────────────────────

import random
import string as _string

FIRST_NAMES = [
    "anna","ben","clara","david","emma","felix","greta","hans","ida","jan",
    "kira","leon","mia","noah","olivia","paul","quinn","rosa","simon","tina",
    "uwe","vera","walter","xena","yara","zoe","alex","brit","carl","diana",
    "erik","fiona","georg","hanna","ingo","julia","kai","lisa","marc","nina",
    "otto","petra","ralf","sarah","tom","ulrike","viktor","wendy","xaver","yvonne"
]
LAST_NAMES = [
    "mueller","schmidt","schneider","fischer","weber","meyer","wagner","becker",
    "schulz","hoffmann","klein","wolf","richter","bauer","koch","lange","braun",
    "Werner","krause","lehmann","koenig","huber","fuchs","zimmermann","herrmann",
    "baumann","roth","stark","scholz","neumann","schwarz","ziegler","langer",
    "haas","frank","vogt","jung","sauer","berg","kolb","jakobs","otto","maier"
]

def generate_email(domain: str) -> str:
    first = random.choice(FIRST_NAMES)
    last  = random.choice(LAST_NAMES)
    sep   = random.choice([".", "_", ""])
    num   = random.randint(1, 99) if random.random() > 0.6 else ""
    local = f"{first}{sep}{last}{num}"
    return f"{local}@{domain}"

def generate_name():
    first = random.choice(FIRST_NAMES).capitalize()
    last  = random.choice(LAST_NAMES).capitalize()
    return first, last

# ── Zendesk Registration ──────────────────────────────────────────────────────

ZENDESK_BASE    = "https://logitech.zendesk.com"
REGISTER_FORM   = "360000994993"
WORKATO_REG_URL = "https://apim.workato.com/help-center-v10/prod/create-update-myproduct"
WORKATO_REG_TOK = "4b9d6e53565864e218e61cb7ffd0cff85797c3c1ae4da90a501a565415b0d9fd"

def zendesk_create_user(email: str, first: str, last: str) -> dict:
    """Erstellt einen anonymen Zendesk-User über die public HC API."""
    url  = f"{ZENDESK_BASE}/api/v2/users.json"
    body = {"user": {"name": f"{first} {last}", "email": email, "role": "end-user"}}
    try:
        r = requests.post(url, json=body, timeout=15)
        if r.status_code in (200, 201):
            data = r.json()
            return {"ok": True, "user_id": data["user"]["id"], "email": email}
        # User existiert bereits
        if r.status_code == 422:
            # User suchen
            sr = requests.get(
                f"{ZENDESK_BASE}/api/v2/users/search.json?query={email}",
                timeout=10
            )
            if sr.status_code == 200:
                results = sr.json().get("users", [])
                if results:
                    return {"ok": True, "user_id": results[0]["id"], "email": email, "existing": True}
        return {"ok": False, "error": f"Status {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def workato_register_product(serial: str, product_id: str, part_number: str,
                              manufacture_date: str, user_id: int, email: str) -> dict:
    """Registriert das Produkt über die Workato-API (wie auf der Website)."""
    body = {
        "serial_number":      serial,
        "product_id":         product_id,
        "purchase_location":  "",
        "purchase_date":      "",
        "requester_id":       user_id,
        "form_id":            int(REGISTER_FORM),
        "linked_my_product_id": "",
        "email_opt_in":       False,
        "user_id":            user_id,
    }
    try:
        r = requests.post(
            WORKATO_REG_URL,
            json=body,
            headers={"Content-Type": "application/json", "API-TOKEN": WORKATO_REG_TOK},
            timeout=15
        )
        if r.status_code in (200, 201):
            data = r.json()
            status = data.get("Status","")
            msg    = data.get("message","")
            if status == "Created":
                return {"ok": True, "message": "Registriert"}
            elif msg == "Already Registered Serial Number":
                return {"ok": False, "already_registered": True, "message": "Bereits registriert"}
            return {"ok": True, "message": status or msg, "raw": data}
        return {"ok": False, "error": f"Status {r.status_code}: {r.text[:300]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── Ticket Text Generator ────────────────────────────────────────────────────

TICKET_TEMPLATES_DE = [
    (
        "Mein {product} funktioniert nicht mehr",
        "Hallo,\n\nich wende mich an euch, weil mein {product} seit einigen Tagen nicht mehr richtig funktioniert. Das Gerät reagiert teilweise gar nicht mehr und ich habe schon alles versucht – neu starten, andere USB-Anschlüsse, Treiber neu installieren – nichts hat geholfen.\n\nDie Seriennummer meines Geräts ist: {serial}\n\nIch hoffe ihr könnt mir weiterhelfen, ich bin wirklich auf das Gerät angewiesen.\n\nViele Grüße\n{first}",
    ),
    (
        "Problem mit meinem {product} – bitte um Hilfe",
        "Guten Tag,\n\nmein {product} macht seit kurzem Probleme. Es lässt sich nicht mehr einschalten bzw. wird vom Computer nicht erkannt. Ich habe das Gerät erst vor einiger Zeit gekauft und bin sehr unzufrieden mit dieser Situation.\n\nSeriennummer: {serial}\n\nKönnt ihr mir bitte mitteilen, was ich tun kann oder ob eine Reparatur/Austausch möglich ist?\n\nFreundliche Grüße\n{name}",
    ),
    (
        "{product} defekt – was kann ich tun?",
        "Hallo Support-Team,\n\nich habe ein Problem mit meinem {product}. Das Gerät funktioniert seit einigen Tagen nicht mehr einwandfrei – manchmal friert es ein, manchmal reagiert es überhaupt nicht mehr.\n\nMeine Seriennummer lautet: {serial}\n\nBitte helft mir bei der Lösung dieses Problems, ich weiß nicht mehr weiter.\n\nDanke und Grüße\n{first} {last}",
    ),
    (
        "Technisches Problem mit {product}",
        "Liebes Logitech-Team,\n\nleider muss ich euch über ein Problem mit meinem {product} informieren. Das Gerät zeigt seit kurzem ein merkwürdiges Verhalten: Es verbindet sich nicht mehr zuverlässig und fällt während der Nutzung ständig aus.\n\nS/N: {serial}\n\nIch wäre sehr dankbar für eure Unterstützung.\n\nMit freundlichen Grüßen\n{name}",
    ),
    (
        "Mein {product} ist kaputt gegangen",
        "Hi,\n\nleider ist mein {product} kaputt gegangen. Es hat eines Tages einfach aufgehört zu funktionieren, ohne dass ich es fallen gelassen oder anderweitig beschädigt hätte.\n\nSeriennummer: {serial}\n\nWas sind meine Optionen? Kann ich es einschicken oder bekomme ich Ersatz?\n\nDanke!\n{first}",
    ),
    (
        "Hilfe benötigt – {product} funktioniert nicht",
        "Sehr geehrtes Support-Team,\n\nich benötige dringend Hilfe mit meinem {product}. Das Gerät hat aufgehört zu funktionieren und ich kann es seit mehreren Tagen nicht mehr benutzen.\n\nDie Seriennummer ist: {serial}\n\nBitte gebt mir Bescheid, wie ich weiter vorgehen soll.\n\nMit freundlichem Gruß\n{name}",
    ),
]

TICKET_TEMPLATES_EN = [
    (
        "My {product} stopped working",
        "Hello,\n\nI'm reaching out because my {product} has stopped working properly. The device sometimes doesn't respond at all and I've tried everything – restarting, different USB ports, reinstalling drivers – nothing has helped.\n\nSerial number: {serial}\n\nI hope you can help me, I really depend on this device.\n\nBest regards,\n{first}",
    ),
    (
        "Issue with my {product} – need assistance",
        "Hi there,\n\nmy {product} has been having issues lately. It won't turn on anymore or gets not recognized by my computer. I purchased this device not too long ago and I'm quite disappointed.\n\nSerial number: {serial}\n\nCould you please let me know what I can do or whether a repair/replacement is possible?\n\nKind regards,\n{name}",
    ),
    (
        "{product} not working – what can I do?",
        "Hello Support Team,\n\nI have a problem with my {product}. The device has not been working properly for a few days – it sometimes freezes, sometimes doesn't respond at all.\n\nMy serial number is: {serial}\n\nPlease help me resolve this issue, I'm not sure what else to try.\n\nThanks and regards,\n{first} {last}",
    ),
    (
        "Technical problem with {product}",
        "Dear Logitech Team,\n\nunfortunately I need to report a problem with my {product}. The device has been behaving strangely lately: it no longer connects reliably and keeps dropping out during use.\n\nS/N: {serial}\n\nI would greatly appreciate your support.\n\nWith kind regards,\n{name}",
    ),
    (
        "My {product} broke down",
        "Hi,\n\nunfortunately my {product} has broken down. It just stopped working one day without me dropping it or damaging it in any way.\n\nSerial number: {serial}\n\nWhat are my options? Can I send it in or will I get a replacement?\n\nThanks!\n{first}",
    ),
    (
        "Need help – {product} not functioning",
        "Dear Support Team,\n\nI urgently need help with my {product}. The device has stopped working and I haven't been able to use it for several days.\n\nThe serial number is: {serial}\n\nPlease let me know how to proceed.\n\nWith friendly regards,\n{name}",
    ),
]

def generate_ticket_text(serial: str, product: str, first: str, last: str) -> tuple:
    """Generiert zufälligen, realistischen Ticket-Betreff + Text."""
    lang = random.choice(["de", "de", "en"])  # Öfter Deutsch
    templates = TICKET_TEMPLATES_DE if lang == "de" else TICKET_TEMPLATES_EN
    subject_tpl, body_tpl = random.choice(templates)
    
    # Produkt auf sinnvolle Länge kürzen
    short_product = product.split("–")[0].strip() if "–" in product else product
    short_product = short_product.split("-")[0].strip() if len(short_product) > 30 else short_product
    
    fmt = {
        "product": short_product or "Logitech Gerät",
        "serial":  serial,
        "first":   first,
        "last":    last,
        "name":    f"{first} {last}",
    }
    return subject_tpl.format(**fmt), body_tpl.format(**fmt)


# Länder-Mapping: Sprache → Zendesk country tag
LANG_COUNTRY = {
    "de":  "country_de",
    "at":  "country_at",
    "ch":  "country_ch",
    "en":  "country_gb",
}

COUNTRY_TAGS = [
    "country_de", "country_at", "country_ch", "country_gb",
    "country_fr", "country_nl", "country_be", "country_pl",
    "country_it", "country_es", "country_se", "country_no",
]

COUNTRY_MAP = {
    "de": "country_de", "at": "country_at", "ch": "country_ch",
    "gb": "country_gb", "us": "country_us", "fr": "country_fr",
}

def zendesk_create_ticket(serial: str, product: str, part_number: str,
                           manufacture_date: str, warranty_end: str,
                           email: str, name: str,
                           country: str = "de",
                           custom_subject: str = "",
                           custom_body: str = "") -> dict:
    """Erstellt ein realistisches Support-Ticket als anonymer User."""
    first, last = name.split(" ", 1) if " " in name else (name, "")
    # Eigener Text hat Vorrang, sonst zufälliges Template
    if custom_subject and custom_body:
        subject   = custom_subject
        body_text = custom_body
    else:
        lang = "de" if country in ("de","at","ch") else "en"
        subject, body_text = generate_ticket_text(serial, product, first, last)
    country_tag = COUNTRY_MAP.get(country, "country_de")

    url  = f"{ZENDESK_BASE}/api/v2/requests.json"
    body = {
        "request": {
            "requester":      {"name": name, "email": email},
            "subject":        subject,
            "ticket_form_id": 360000621393,  # Contact Us Form
            "comment":        {"body": body_text},
            "custom_fields":  [
                {"id": 360019395193, "value": serial},      # Seriennummer
                {"id": 360019375594, "value": name},         # Name
                {"id": 360019382014, "value": country_tag},  # Land (Pflichtfeld)
                {"id": 360019426873, "value": "routing_logitech"},  # Routing
            ]
        }
    }
    try:
        r = requests.post(url, json=body, timeout=15)
        if r.status_code in (200, 201):
            data = r.json()
            return {
                "ok":        True,
                "ticket_id": data["request"]["id"],
                "subject":   subject,
                "lang":      "de" if country in ("de","at","ch") else "en",
            }
        return {"ok": False, "error": f"Status {r.status_code}: {r.text[:300]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── DB: Registrierungs-Tabelle ────────────────────────────────────────────────


# ── Extended DB Tables ────────────────────────────────────────────────────────

def init_extended_tables():
    with get_db() as db:
        # Tags pro Serial
        db.execute("""
            CREATE TABLE IF NOT EXISTS serial_tags (
                serial TEXT,
                tag    TEXT,
                PRIMARY KEY (serial, tag)
            )""")
        # Produktkategorie-Priorisierung für Scanner
        db.execute("""
            CREATE TABLE IF NOT EXISTS scan_priorities (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT,
                prefix      TEXT,
                active      INTEGER DEFAULT 1,
                sort_order  INTEGER DEFAULT 0
            )""")
        # Produkt-Wertschätzungen
        db.execute("""
            CREATE TABLE IF NOT EXISTS product_values (
                part_number  TEXT PRIMARY KEY,
                product_name TEXT,
                val_min      REAL DEFAULT 0,
                val_max      REAL DEFAULT 0,
                category     TEXT DEFAULT '',
                updated_at   TEXT
            )""")
        # Identitäts-Profile
        db.execute("""
            CREATE TABLE IF NOT EXISTS identities (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT,
                first_name TEXT,
                last_name  TEXT,
                domain     TEXT,
                country    TEXT DEFAULT 'de',
                lang       TEXT DEFAULT 'de',
                street     TEXT DEFAULT '',
                city       TEXT DEFAULT '',
                zip        TEXT DEFAULT '',
                created_at TEXT
            )""")
        # Domains
        db.execute("""
            CREATE TABLE IF NOT EXISTS domains (
                domain     TEXT PRIMARY KEY,
                active     INTEGER DEFAULT 1,
                last_check TEXT,
                status     TEXT DEFAULT 'unknown'
            )""")
        # Mail-Vorlagen
        db.execute("""
            CREATE TABLE IF NOT EXISTS mail_templates (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT,
                subject    TEXT,
                body       TEXT,
                lang       TEXT DEFAULT 'de',
                created_at TEXT
            )""")
        # Ticket-Status & RMA
        db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_status (
                reg_id      INTEGER PRIMARY KEY,
                status      TEXT DEFAULT 'open',
                rma_number  TEXT DEFAULT '',
                tracking    TEXT DEFAULT '',
                carrier     TEXT DEFAULT '',
                value_eur   REAL DEFAULT 0,
                archived    INTEGER DEFAULT 0,
                followup_at TEXT,
                resolved_at TEXT,
                agent_name  TEXT DEFAULT '',
                notes       TEXT DEFAULT ''
            )""")
        # Sachbearbeiter-Statistik
        db.execute("""
            CREATE TABLE IF NOT EXISTS agent_stats (
                agent_name TEXT PRIMARY KEY,
                total      INTEGER DEFAULT 0,
                positive   INTEGER DEFAULT 0,
                negative   INTEGER DEFAULT 0,
                updated_at TEXT
            )""")
        # Aktivitäts-Log
        db.execute("""
            CREATE TABLE IF NOT EXISTS invoice_templates (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                filename   TEXT,
                data_b64   TEXT NOT NULL,
                file_type  TEXT DEFAULT 'docx',
                created_at TEXT
            )""")
        db.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                serial     TEXT,
                reg_id     INTEGER,
                action     TEXT,
                detail     TEXT,
                created_at TEXT
            )""")
        # Adress-Datenbank (deutsche Adressen)
        db.execute("""
            CREATE TABLE IF NOT EXISTS addresses (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                street  TEXT,
                number  TEXT,
                city    TEXT,
                zip     TEXT,
                country TEXT DEFAULT 'DE'
            )""")
        # Default-Domain eintragen
        db.execute("INSERT OR IGNORE INTO domains VALUES ('kafka-frame.com',1,NULL,'unknown')")
        db.commit()

def log_activity(serial: str, reg_id: int, action: str, detail: str = ""):
    with get_db() as db:
        db.execute(
            "INSERT INTO activity_log (serial,reg_id,action,detail,created_at) VALUES (?,?,?,?,?)",
            (serial, reg_id, action, detail, datetime.now(timezone.utc).isoformat())
        )
        db.commit()

def init_reg_table():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                serial       TEXT,
                email        TEXT,
                name         TEXT,
                domain       TEXT,
                zendesk_uid  TEXT,
                ticket_id    TEXT,
                reg_status   TEXT,
                reg_message  TEXT,
                created_at   TEXT
            )""")
        db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            )""")
        db.execute("INSERT OR IGNORE INTO settings VALUES ('email_domain', 'kafka-frame.com')")
        db.commit()

# ── Registration Routes ───────────────────────────────────────────────────────

class RegInput(BaseModel):
    serial:         str
    domain:         str = ""
    mode:           str = "register"  # register | ticket | both
    custom_first:   str = ""
    custom_last:    str = ""
    custom_email:   str = ""
    country:        str = "de"   # de | us | gb | fr | at | ch
    custom_subject: str = ""     # Eigener Betreff fürs Ticket
    custom_body:    str = ""     # Eigener Mail-Text fürs Ticket


@app.post("/api/register/prepare")
def prepare_register_serial(inp: RegInput):
    serial = inp.serial.strip().upper()

    with get_db() as db:
        row = db.execute("SELECT * FROM serials WHERE serial=?", (serial,)).fetchone()
        domain = inp.domain or db.execute(
            "SELECT value FROM settings WHERE key='email_domain'"
        ).fetchone()["value"]

    if not row:
        raise HTTPException(404, "Serial nicht in DB — zuerst prüfen")
    if row["status"] not in ("valid",):
        raise HTTPException(400, f"Serial hat Status '{row['status']}' — nur 'valid' registrierbar")

    if inp.custom_first and inp.custom_last:
        first = inp.custom_first.strip().capitalize()
        last  = inp.custom_last.strip().capitalize()
    else:
        first, last = generate_name()
    name = f"{first} {last}"

    if inp.custom_email:
        email = inp.custom_email.strip()
    else:
        sep   = random.choice([".", "_", ""])
        num   = str(random.randint(1, 99)) if random.random() > 0.5 else ""
        local = f"{first.lower()}{sep}{last.lower()}{num}"
        email = f"{local}@{domain}"

    subject = inp.custom_subject.strip() if inp.custom_subject else ""
    body = inp.custom_body.strip() if inp.custom_body else ""

    if inp.mode in ("ticket", "both") and not (subject and body):
        subject, body = generate_ticket_text(serial, row["product"], first, last)

    return {
        "ok": True,
        "serial": serial,
        "email": email,
        "name": name,
        "first": first,
        "last": last,
        "domain": domain,
        "country": inp.country,
        "mode": inp.mode,
        "product": row["product"],
        "subject": subject,
        "body": body,
    }

@app.post("/api/register")
def register_serial(inp: RegInput):
    serial = inp.serial.strip().upper()

    # Serial aus DB holen
    with get_db() as db:
        row = db.execute("SELECT * FROM serials WHERE serial=?", (serial,)).fetchone()
        domain = inp.domain or db.execute(
            "SELECT value FROM settings WHERE key='email_domain'"
        ).fetchone()["value"]
    
    if not row:
        raise HTTPException(404, "Serial nicht in DB — zuerst prüfen")
    if row["status"] not in ("valid",):
        raise HTTPException(400, f"Serial hat Status '{row['status']}' — nur 'valid' registrierbar")

    # Name: vom User vorgegeben oder zufällig
    if inp.custom_first and inp.custom_last:
        first = inp.custom_first.strip().capitalize()
        last  = inp.custom_last.strip().capitalize()
    else:
        first, last = generate_name()
    name = f"{first} {last}"

    # E-Mail: manuell, oder aus Name+Domain generieren
    if inp.custom_email:
        email = inp.custom_email.strip()
    else:
        sep   = random.choice([".", "_", ""])
        num   = str(random.randint(1, 99)) if random.random() > 0.5 else ""
        local = f"{first.lower()}{sep}{last.lower()}{num}"
        email = f"{local}@{domain}"

    result = {"serial": serial, "email": email, "name": name, "domain": domain}

    # ── Registrierung in DB anlegen (IMMER, unabhängig vom Erfolg) ─────────────
    with get_db() as db:
        existing = db.execute(
            "SELECT id FROM registrations WHERE serial=? AND email=?", (serial, email)
        ).fetchone()
        if not existing:
            db.execute("""
                INSERT INTO registrations
                (serial,email,name,domain,zendesk_uid,ticket_id,reg_status,reg_message,created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (serial, email, name, domain, "", "", "pending", "", 
                  datetime.now(timezone.utc).isoformat()))
            db.commit()
            print(f"[register] Registrierung angelegt: {serial} → {email}", flush=True)

    if inp.mode in ("register", "both"):
        # Zendesk User anlegen
        user_res = zendesk_create_user(email, first, last)
        result["user"] = user_res

        uid = user_res.get("user_id", "")
        if user_res["ok"] and uid:
            # Produkt registrieren
            raw = json.loads(row["raw_json"]) if row["raw_json"] else {}
            product_id = raw.get("ProductList",[{}])[0].get("id","")
            reg_res = workato_register_product(
                serial, product_id, row["part_number"],
                row["manufacture_date"], uid, email
            )
            result["registration"] = reg_res
            reg_ok = reg_res.get("ok", False)
        else:
            reg_res = user_res
            reg_ok = False

        # DB aktualisieren
        with get_db() as db:
            db.execute("""
                UPDATE registrations SET
                    zendesk_uid=?,
                    reg_status=?,
                    reg_message=?
                WHERE serial=? AND email=?
            """, (
                str(uid),
                "ok" if reg_ok else "error",
                reg_res.get("message","") or reg_res.get("error",""),
                serial, email
            ))
            if reg_ok:
                db.execute("UPDATE serials SET status='registered', note=? WHERE serial=?",
                           (f"Registriert als {email}", serial))
            db.commit()

    if inp.mode in ("ticket", "both"):
        ticket_res = zendesk_create_ticket(
            serial, row["product"], row["part_number"],
            row["manufacture_date"], row["warranty_end"], email, name,
            country=inp.country,
            custom_subject=inp.custom_subject,
            custom_body=inp.custom_body,
        )
        result["ticket"] = ticket_res
        if ticket_res.get("ok"):
            ticket_id = str(ticket_res["ticket_id"])
            with get_db() as db:
                db.execute(
                    "UPDATE registrations SET ticket_id=?, reg_status='ticket_sent' WHERE serial=? AND email=?",
                    (ticket_id, serial, email)
                )
                db.commit()
            # ticket_status anlegen
            with get_db() as db:
                reg_row = db.execute(
                    "SELECT id FROM registrations WHERE serial=? AND email=? ORDER BY id DESC LIMIT 1",
                    (serial, email)
                ).fetchone()
                if reg_row:
                    db.execute("""
                        INSERT OR IGNORE INTO ticket_status (reg_id, status, agent_name)
                        VALUES (?, 'open', '')
                    """, (reg_row["id"],))
                    db.commit()

    print(f"[register] {serial} → {email} | mode={inp.mode}", flush=True)
    return result

@app.get("/api/registrations")
def get_registrations():
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM registrations ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
    return [dict(r) for r in rows]

@app.post("/api/settings/test-mailgun")
def test_mailgun():
    """Testet die Mailgun-Verbindung mit einer Test-Mail."""
    with get_db() as db:
        mg_key = db.execute("SELECT value FROM settings WHERE key='mailgun_key'").fetchone()
        mg_dom = db.execute("SELECT value FROM settings WHERE key='mailgun_domain'").fetchone()
        mail_user = db.execute("SELECT value FROM settings WHERE key='mail_user'").fetchone()
    
    api_key = mg_key["value"] if mg_key else ""
    domain  = mg_dom["value"] if mg_dom else "kafka-frame.com"
    test_to = mail_user["value"] if mail_user else ""
    
    if not api_key:
        return {"ok": False, "error": "Kein API-Key eingetragen"}
    if not test_to:
        return {"ok": False, "error": "Kein Mail-Benutzer eingetragen"}
    
    result = send_mail_mailgun(
        from_addr=f"test@{domain}",
        to_addr=test_to,
        subject="LogiCheck Mailgun Test",
        body="Mailgun funktioniert korrekt.",
    )
    return result


@app.get("/api/settings")
def get_settings():
    with get_db() as db:
        rows = db.execute("SELECT * FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}

@app.post("/api/settings")
def update_settings(body: dict):
    with get_db() as db:
        for k, v in body.items():
            db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (k, str(v)))
        db.commit()
    return {"ok": True}

