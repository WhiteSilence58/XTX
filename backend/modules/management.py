# ── Tags ─────────────────────────────────────────────────────────────────────

PRESET_TAGS = ["Lager A","Lager B","verkauft","defekt","in Bearbeitung","RMA","archiviert","wertvoll"]

@app.get("/api/tags/{serial}")
def get_tags(serial: str):
    with get_db() as db:
        rows = db.execute("SELECT tag FROM serial_tags WHERE serial=?", (serial,)).fetchall()
    return [r["tag"] for r in rows]

@app.post("/api/tags/{serial}")
def set_tags(serial: str, body: dict):
    tags = body.get("tags", [])
    with get_db() as db:
        db.execute("DELETE FROM serial_tags WHERE serial=?", (serial,))
        for t in tags:
            db.execute("INSERT OR IGNORE INTO serial_tags VALUES (?,?)", (serial, t))
        db.commit()
    return {"ok": True}

@app.get("/api/tags")
def all_tags():
    with get_db() as db:
        rows = db.execute("SELECT DISTINCT tag FROM serial_tags").fetchall()
    custom = [r["tag"] for r in rows]
    return list(dict.fromkeys(PRESET_TAGS + custom))

# ── Export ────────────────────────────────────────────────────────────────────

from fastapi.responses import StreamingResponse
import csv, io

@app.get("/api/export/csv")
def export_csv(status: str = ""):
    with get_db() as db:
        q = "SELECT s.*, GROUP_CONCAT(st.tag,',') as tags FROM serials s LEFT JOIN serial_tags st ON s.serial=st.serial"
        p = []
        if status:
            q += " WHERE s.status=?"; p.append(status)
        q += " GROUP BY s.serial ORDER BY s.checked_at DESC"
        rows = db.execute(q, p).fetchall()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Serial","Status","Produkt","Teilenummer","Herst.datum","Garantieende","Garantiestatus","Marketing-ID","Tags","Notiz","Geprüft am"])
    for r in rows:
        w.writerow([r["serial"],r["status"],r["product"],r["part_number"],
                    r["manufacture_date"],r["warranty_end"],r["warranty_status"],
                    r["marketing_id"],r["tags"] or "",r["note"],r["checked_at"]])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=logicheck_export.csv"}
    )

# ── Statistiken ───────────────────────────────────────────────────────────────

@app.get("/api/stats/detailed")
def stats_detailed():
    with get_db() as db:
        # Funde pro Tag (letzte 30 Tage)
        daily = db.execute("""
            SELECT DATE(checked_at) as day, COUNT(*) as total,
                   SUM(CASE WHEN status='valid' THEN 1 ELSE 0 END) as valid,
                   SUM(CASE WHEN status='registered' THEN 1 ELSE 0 END) as registered
            FROM serials
            WHERE checked_at >= DATE('now','-30 days')
            GROUP BY DATE(checked_at) ORDER BY day ASC
        """).fetchall()
        # Top Produkte
        top_products = db.execute("""
            SELECT product, part_number, COUNT(*) as count,
                   SUM(CASE WHEN status='valid' THEN 1 ELSE 0 END) as valid
            FROM serials WHERE product != ''
            GROUP BY product, part_number ORDER BY count DESC LIMIT 10
        """).fetchall()
        # Werk-Code Analyse
        werk_stats = db.execute("""
            SELECT SUBSTR(serial,5,2) as werk,
                   COUNT(*) as total,
                   SUM(CASE WHEN status='valid' THEN 1 ELSE 0 END) as valid,
                   ROUND(100.0*SUM(CASE WHEN status='valid' THEN 1 ELSE 0 END)/COUNT(*),2) as hit_rate
            FROM serials
            GROUP BY werk ORDER BY hit_rate DESC LIMIT 10
        """).fetchall()
        # Ticket-Status Verteilung
        ticket_stats = db.execute("""
            SELECT status, COUNT(*) as count FROM ticket_status GROUP BY status
        """).fetchall()
        # Sachbearbeiter
        agents = db.execute("""
            SELECT * FROM agent_stats ORDER BY total DESC LIMIT 10
        """).fetchall()
        # Gesamtwert
        value_sum = db.execute("""
            SELECT SUM(pv.val_min) as min_total, SUM(pv.val_max) as max_total
            FROM serials s JOIN product_values pv ON s.part_number = pv.part_number
            WHERE s.status = 'valid'
        """).fetchone()

    return {
        "daily":         [dict(r) for r in daily],
        "top_products":  [dict(r) for r in top_products],
        "werk_stats":    [dict(r) for r in werk_stats],
        "ticket_stats":  [dict(r) for r in ticket_stats],
        "agents":        [dict(r) for r in agents],
        "value_min":     value_sum["min_total"] or 0,
        "value_max":     value_sum["max_total"] or 0,
    }

# ── Produkt-Werte ─────────────────────────────────────────────────────────────

class ProductValueInput(BaseModel):
    part_number:  str
    product_name: str = ""
    val_min:      float = 0
    val_max:      float = 0
    category:     str = ""

@app.get("/api/product-values")
def get_product_values():
    with get_db() as db:
        rows = db.execute("SELECT * FROM product_values ORDER BY category,product_name").fetchall()
    return [dict(r) for r in rows]

@app.post("/api/product-values")
def set_product_value(inp: ProductValueInput):
    with get_db() as db:
        db.execute("""
            INSERT OR REPLACE INTO product_values
            (part_number,product_name,val_min,val_max,category,updated_at)
            VALUES (?,?,?,?,?,?)
        """, (inp.part_number, inp.product_name, inp.val_min, inp.val_max,
              inp.category, datetime.now(timezone.utc).isoformat()))
        db.commit()
    return {"ok": True}

@app.get("/api/product-values/{part_number}")
def get_product_value(part_number: str):
    with get_db() as db:
        r = db.execute("SELECT * FROM product_values WHERE part_number=?", (part_number,)).fetchone()
    return dict(r) if r else {}

# ── Identitäts-Profile ────────────────────────────────────────────────────────

class IdentityInput(BaseModel):
    name:       str
    first_name: str
    last_name:  str
    domain:     str
    country:    str = "de"
    lang:       str = "de"
    street:     str = ""
    city:       str = ""
    zip:        str = ""

@app.get("/api/identities")
def get_identities():
    with get_db() as db:
        rows = db.execute("SELECT * FROM identities ORDER BY name").fetchall()
    return [dict(r) for r in rows]

@app.post("/api/identities")
def create_identity(inp: IdentityInput):
    with get_db() as db:
        db.execute("""
            INSERT INTO identities (name,first_name,last_name,domain,country,lang,street,city,zip,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (inp.name, inp.first_name, inp.last_name, inp.domain, inp.country,
              inp.lang, inp.street, inp.city, inp.zip,
              datetime.now(timezone.utc).isoformat()))
        db.commit()
    return {"ok": True}

@app.delete("/api/identities/{identity_id}")
def delete_identity(identity_id: int):
    with get_db() as db:
        db.execute("DELETE FROM identities WHERE id=?", (identity_id,))
        db.commit()
    return {"ok": True}

# ── Domains ───────────────────────────────────────────────────────────────────

@app.get("/api/domains")
def get_domains():
    with get_db() as db:
        rows = db.execute("SELECT * FROM domains ORDER BY domain").fetchall()
    return [dict(r) for r in rows]

@app.post("/api/domains")
def add_domain(body: dict):
    domain = body.get("domain","").strip().lower()
    if not domain: raise HTTPException(400, "Domain fehlt")
    with get_db() as db:
        db.execute("INSERT OR IGNORE INTO domains VALUES (?,1,NULL,'unknown')", (domain,))
        db.commit()
    return {"ok": True}

@app.post("/api/domains/{domain}/test")
def test_domain(domain: str):
    """Sendet eine Test-Mail an eine catch-all Adresse und prüft ob sie ankommt."""
    test_addr = f"catchall-test-{int(time.time())}@{domain}"
    try:
        with get_db() as db:
            user, pwd = get_mail_creds(db)
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(user, pwd)
            msg = MIMEMultipart()
            msg["From"]    = f"test@{domain}"
            msg["To"]      = test_addr
            msg["Subject"] = "Catch-All Test"
            msg.attach(MIMEText("Test", "plain"))
            smtp.sendmail(f"test@{domain}", test_addr, msg.as_string())
        status = "sent"
    except Exception as e:
        status = f"error: {str(e)[:100]}"
    with get_db() as db:
        db.execute("UPDATE domains SET last_check=?,status=? WHERE domain=?",
                   (datetime.now(timezone.utc).isoformat(), status, domain))
        db.commit()
    return {"ok": "error" not in status, "status": status}

@app.delete("/api/domains/{domain}")
def delete_domain(domain: str):
    with get_db() as db:
        db.execute("DELETE FROM domains WHERE domain=?", (domain,))
        db.commit()
    return {"ok": True}

def get_random_domain() -> str:
    """Holt eine zufällige aktive Domain."""
    with get_db() as db:
        rows = db.execute("SELECT domain FROM domains WHERE active=1").fetchall()
    if not rows:
        # Fallback: Standard-Domain aus Einstellungen
        with get_db() as db:
            r = db.execute("SELECT value FROM settings WHERE key='email_domain'").fetchone()
        return r["value"] if r else "kafka-frame.com"
    return random.choice(rows)["domain"]

# ── Mail-Vorlagen ─────────────────────────────────────────────────────────────

class TemplateInput(BaseModel):
    name:    str
    subject: str
    body:    str
    lang:    str = "de"

@app.get("/api/templates")
def get_templates():
    with get_db() as db:
        rows = db.execute("SELECT * FROM mail_templates ORDER BY name").fetchall()
    return [dict(r) for r in rows]

@app.post("/api/templates")
def save_template(inp: TemplateInput):
    with get_db() as db:
        db.execute("""
            INSERT INTO mail_templates (name,subject,body,lang,created_at) VALUES (?,?,?,?,?)
        """, (inp.name, inp.subject, inp.body, inp.lang,
              datetime.now(timezone.utc).isoformat()))
        db.commit()
    return {"ok": True}

@app.delete("/api/templates/{tid}")
def delete_template(tid: int):
    with get_db() as db:
        db.execute("DELETE FROM mail_templates WHERE id=?", (tid,))
        db.commit()
    return {"ok": True}

# ── Ticket-Status & RMA ───────────────────────────────────────────────────────

TICKET_STATUSES = ["open","waiting","positive","negative","closed","archived"]

class TicketStatusInput(BaseModel):
    reg_id:     int
    status:     str = "open"
    rma_number: str = ""
    tracking:   str = ""
    carrier:    str = ""
    value_eur:  float = 0
    archived:   int = 0
    agent_name: str = ""
    notes:      str = ""

@app.get("/api/ticket-status/{reg_id}")
def get_ticket_status(reg_id: int):
    with get_db() as db:
        r = db.execute("SELECT * FROM ticket_status WHERE reg_id=?", (reg_id,)).fetchone()
    return dict(r) if r else {"reg_id": reg_id, "status": "open", "archived": 0}

@app.post("/api/ticket-status")
def set_ticket_status(inp: TicketStatusInput):
    with get_db() as db:
        existing = db.execute("SELECT reg_id FROM ticket_status WHERE reg_id=?", (inp.reg_id,)).fetchone()
        if existing:
            db.execute("""
                UPDATE ticket_status SET status=?,rma_number=?,tracking=?,carrier=?,
                value_eur=?,archived=?,agent_name=?,notes=?
                WHERE reg_id=?
            """, (inp.status, inp.rma_number, inp.tracking, inp.carrier,
                  inp.value_eur, inp.archived, inp.agent_name, inp.notes, inp.reg_id))
        else:
            db.execute("""
                INSERT INTO ticket_status (reg_id,status,rma_number,tracking,carrier,value_eur,archived,agent_name,notes)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (inp.reg_id, inp.status, inp.rma_number, inp.tracking, inp.carrier,
                  inp.value_eur, inp.archived, inp.agent_name, inp.notes))
        # Sachbearbeiter-Statistik aktualisieren
        if inp.agent_name:
            is_pos = 1 if inp.status == "positive" else 0
            is_neg = 1 if inp.status == "negative" else 0
            db.execute("""
                INSERT INTO agent_stats (agent_name,total,positive,negative,updated_at)
                VALUES (?,1,?,?,?)
                ON CONFLICT(agent_name) DO UPDATE SET
                total=total+1,
                positive=positive+?,
                negative=negative+?,
                updated_at=?
            """, (inp.agent_name, is_pos, is_neg,
                  datetime.now(timezone.utc).isoformat(),
                  is_pos, is_neg, datetime.now(timezone.utc).isoformat()))
        db.commit()
    log_activity("", inp.reg_id, f"Status: {inp.status}",
                 f"Agent: {inp.agent_name} RMA: {inp.rma_number}")
    return {"ok": True}

@app.get("/api/tracking/{reg_id}")
def get_tracking(reg_id: int):
    with get_db() as db:
        r = db.execute("SELECT tracking, carrier FROM ticket_status WHERE reg_id=?", (reg_id,)).fetchone()
    if not r or not r["tracking"]: return {"url": None}
    tracking = r["tracking"]
    carrier  = (r["carrier"] or "").lower()
    if "dhl" in carrier:
        url = f"https://www.dhl.de/de/privatkunden/pakete-empfangen/verfolgen.html?idc={tracking}"
    elif "ups" in carrier:
        url = f"https://www.ups.com/track?tracknum={tracking}"
    elif "fedex" in carrier:
        url = f"https://www.fedex.com/fedextrack/?trknbr={tracking}"
    elif "hermes" in carrier or "evri" in carrier:
        url = f"https://www.myhermes.co.uk/track/{tracking}"
    else:
        url = f"https://parcelsapp.com/en/tracking/{tracking}"
    return {"url": url, "tracking": tracking, "carrier": carrier}

# ── Follow-Up Checker ─────────────────────────────────────────────────────────

def followup_check_loop():
    """Prüft täglich ob Follow-Ups nötig sind."""
    print("[followup] Loop gestartet", flush=True)
    while True:
        try:
            now = datetime.now(timezone.utc)
            with get_db() as db:
                # Tickets die seit 3 Tagen keine Antwort haben
                waiting = db.execute("""
                    SELECT r.id, r.email, r.serial, ts.status
                    FROM registrations r
                    JOIN ticket_status ts ON ts.reg_id = r.id
                    LEFT JOIN mail_messages mm ON mm.reg_id = r.id AND mm.direction='in'
                    WHERE ts.status IN ('open','waiting') AND ts.archived=0
                    GROUP BY r.id
                    HAVING MAX(mm.sent_at) < datetime('now','-3 days') OR MAX(mm.sent_at) IS NULL
                """).fetchall()
            for row in waiting:
                print(f"[followup] Follow-Up nötig für {row['email']} (reg {row['id']})", flush=True)
                # Status auf 'waiting' setzen
                with get_db() as db:
                    db.execute(
                        "UPDATE ticket_status SET status='waiting' WHERE reg_id=? AND status='open'",
                        (row["id"],)
                    )
                    db.commit()
        except Exception as e:
            print(f"[followup] Fehler: {e}", flush=True)
        time.sleep(3600)  # Stündlich prüfen

# ── Antwort-Erkennung ─────────────────────────────────────────────────────────

POSITIVE_KEYWORDS = [
    "replacement","austausch","ersatz","new unit","sending","shipping","rma",
    "approved","genehm","schicken","senden","ersatzgerät","gutschrift","refund",
    "we will send","wir senden","warranty replacement","garantieaustausch"
]
NEGATIVE_KEYWORDS = [
    "not covered","nicht abgedeckt","unable to","leider","bedauern","abgelehnt",
    "denied","cannot","out of warranty","außerhalb der garantie","no longer",
    "nicht mehr","physical damage","physical","user damage"
]

def analyze_response(body: str) -> str:
    """Erkennt ob eine Logitech-Antwort positiv oder negativ ist."""
    body_lower = body.lower()
    pos = sum(1 for k in POSITIVE_KEYWORDS if k in body_lower)
    neg = sum(1 for k in NEGATIVE_KEYWORDS if k in body_lower)
    if pos > neg:   return "positive"
    if neg > pos:   return "negative"
    return "waiting"

# ── Adress-Generator ─────────────────────────────────────────────────────────

@app.get("/api/address/generate")
def generate_address(city: str = "Berlin"):
    """
    Sucht über OpenStreetMap Nominatim echte Mehrfamilienhäuser in der Stadt.
    Filtert nach Gebäuden mit mehreren Wohneinheiten (apartments, residential).
    """
    city_clean = city.strip()
    try:
        # Overpass API: Wohngebäude mit mehr als 4 Etagen oder Typ apartment
        overpass_url = "https://overpass-api.de/api/interpreter"
        # Erst Koordinaten der Stadt holen
        geo_url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(city_clean)},+Deutschland&format=json&limit=1"
        geo_r = requests.get(geo_url, headers={"User-Agent": "LogiCheck/1.0"}, timeout=10)
        geo_data = geo_r.json()
        if not geo_data:
            raise Exception("Stadt nicht gefunden")
        lat = float(geo_data[0]["lat"])
        lon = float(geo_data[0]["lon"])

        # Suche Straßen mit Hausnummern im Umkreis von 3km
        # Fokus auf Mehrfamilienhäuser: building=apartments oder levels>=3
        query = f"""
        [out:json][timeout:10];
        (
          node["addr:street"]["addr:housenumber"]["building"~"apartments|residential|yes"]
            (around:3000,{lat},{lon});
          way["addr:street"]["addr:housenumber"]["building"~"apartments|residential"]
            (around:3000,{lat},{lon});
        );
        out 100;
        """
        r = requests.post(overpass_url, data={"data": query},
                         headers={"User-Agent": "LogiCheck/1.0"}, timeout=15)
        elements = r.json().get("elements", [])

        # Filtere auf Einträge mit vollständiger Adresse
        valid = [e for e in elements
                 if e.get("tags",{}).get("addr:street")
                 and e.get("tags",{}).get("addr:housenumber")
                 and e.get("tags",{}).get("addr:postcode")]

        if valid:
            chosen = random.choice(valid)
            tags   = chosen["tags"]
            street = tags["addr:street"]
            number = tags["addr:housenumber"]
            plz    = tags.get("addr:postcode","")
            city_n = tags.get("addr:city", city_clean)
            return {
                "street":  street,
                "number":  number,
                "zip":     plz,
                "city":    city_n,
                "country": "Deutschland",
                "full":    f"{street} {number}, {plz} {city_n}",
                "source":  "openstreetmap"
            }
    except Exception as e:
        print(f"[addr] OSM Fehler: {e}", flush=True)

    # Fallback: einfache Nominatim-Suche nach Straßen
    try:
        search_url = f"https://nominatim.openstreetmap.org/search?q=Wohnhaus+{requests.utils.quote(city_clean)},+Deutschland&format=json&limit=20&addressdetails=1"
        r = requests.get(search_url, headers={"User-Agent": "LogiCheck/1.0"}, timeout=10)
        results = [x for x in r.json() if x.get("address",{}).get("road") and x.get("address",{}).get("postcode")]
        if results:
            chosen = random.choice(results[:10])
            addr   = chosen["address"]
            street = addr.get("road","")
            plz    = addr.get("postcode","")
            city_n = addr.get("city") or addr.get("town") or addr.get("village") or city_clean
            number = str(random.randint(10, 150))
            return {
                "street":  street,
                "number":  number,
                "zip":     plz,
                "city":    city_n,
                "country": "Deutschland",
                "full":    f"{street} {number}, {plz} {city_n}",
                "source":  "nominatim_fallback"
            }
    except Exception as e:
        print(f"[addr] Nominatim Fallback Fehler: {e}", flush=True)

    # Letzter Fallback
    return {
        "street":  "Hauptstraße",
        "number":  str(random.randint(10,150)),
        "zip":     "10115",
        "city":    city_clean,
        "country": "Deutschland",
        "full":    f"Hauptstraße {random.randint(10,150)}, 10115 {city_clean}",
        "source":  "fallback"
    }

@app.get("/api/address/cities")
def get_cities():
    return ["Berlin","Hamburg","München","Köln","Frankfurt","Stuttgart","Düsseldorf","Leipzig","Dresden","Hannover","Nürnberg","Bremen","Dortmund","Essen","Bonn"]

# ── Aktivitäts-Log ────────────────────────────────────────────────────────────

@app.get("/api/activity")
def get_activity(limit: int = 50):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]

# ── Scan-Priorisierung ────────────────────────────────────────────────────────

@app.get("/api/priorities")
def get_priorities():
    with get_db() as db:
        rows = db.execute("SELECT * FROM scan_priorities ORDER BY sort_order").fetchall()
    return [dict(r) for r in rows]

@app.post("/api/priorities")
def add_priority(body: dict):
    with get_db() as db:
        db.execute(
            "INSERT INTO scan_priorities (name,prefix,active,sort_order) VALUES (?,?,1,?)",
            (body.get("name",""), body.get("prefix",""),
             db.execute("SELECT COUNT(*) as c FROM scan_priorities").fetchone()["c"])
        )
        db.commit()
    return {"ok": True}

@app.delete("/api/priorities/{pid}")
def delete_priority(pid: int):
    with get_db() as db:
        db.execute("DELETE FROM scan_priorities WHERE id=?", (pid,))
        db.commit()
    return {"ok": True}

@app.patch("/api/priorities/{pid}")
def toggle_priority(pid: int, body: dict):
    with get_db() as db:
        db.execute("UPDATE scan_priorities SET active=? WHERE id=?",
                   (body.get("active", 1), pid))
        db.commit()
    return {"ok": True}

# ── RMA / Tracking Dashboard ─────────────────────────────────────────────────

@app.get("/api/dashboard/rma")
def rma_dashboard():
    with get_db() as db:
        rows = db.execute("""
            SELECT r.id, r.serial, r.email, r.name,
                   COALESCE(ts.status, 'open')      as status,
                   COALESCE(ts.rma_number, '')       as rma_number,
                   COALESCE(ts.tracking, '')         as tracking,
                   COALESCE(ts.carrier, '')          as carrier,
                   COALESCE(ts.value_eur, 0)         as value_eur,
                   COALESCE(ts.agent_name, '')       as agent_name,
                   COALESCE(ts.archived, 0)          as archived,
                   COALESCE(ts.notes, '')            as notes,
                   s.product, s.part_number,
                   r.ticket_id,
                   r.created_at,
                   -- Ungelesene aus inbox (neue Tabelle)
                   (SELECT COUNT(*) FROM inbox i
                    WHERE i.reg_id = r.id AND i.read_at IS NULL) as unread_inbox,
                   -- Ungelesene aus mail_messages (alte Tabelle, Fallback)
                   (SELECT COUNT(*) FROM mail_messages mm
                    WHERE mm.reg_id=r.id AND mm.direction='in'
                    AND mm.read_at IS NULL) as unread_mm,
                   -- Letzte Mail-Datum
                   (SELECT MAX(i2.received_at) FROM inbox i2
                    WHERE i2.reg_id = r.id) as last_mail_at
            FROM registrations r
            LEFT JOIN ticket_status ts ON ts.reg_id = r.id
            LEFT JOIN serials s ON s.serial = r.serial
            WHERE COALESCE(ts.archived, 0) = 0
            ORDER BY COALESCE(last_mail_at, r.created_at) DESC
        """).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        # Kombiniere ungelesene aus beiden Tabellen
        d["unread"] = (d.pop("unread_inbox") or 0) + (d.pop("unread_mm") or 0)
        result.append(d)
    return result


