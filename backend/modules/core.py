# ── DB ────────────────────────────────────────────────────────────────────────

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    os.makedirs("/data", exist_ok=True)
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS serials (
                serial           TEXT PRIMARY KEY,
                status           TEXT,
                product          TEXT,
                product_type     TEXT,
                part_number      TEXT,
                manufacture_date TEXT,
                warranty_end     TEXT,
                warranty_status  TEXT,
                marketing_id     TEXT,
                raw_json         TEXT,
                checked_at       TEXT,
                note             TEXT DEFAULT ''
            )""")
        db.execute("""
            CREATE TABLE IF NOT EXISTS scan_state (
                key   TEXT PRIMARY KEY,
                value TEXT
            )""")
        for k, v in [
            ("scanner_running",  "0"),
            ("scan_delay",       "5"),
            ("total_checked",    "0"),
            ("total_valid",      "0"),
            ("total_registered", "0"),
            ("year_start",       "23"),
            ("year_end",         "26"),
            ("last_serial",      ""),
        ]:
            db.execute("INSERT OR IGNORE INTO scan_state VALUES (?,?)", (k, v))
        db.commit()

def cfg_get(db, key, default="0"):
    r = db.execute("SELECT value FROM scan_state WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default

def cfg_set(db, key, value):
    db.execute("INSERT OR REPLACE INTO scan_state VALUES (?,?)", (key, str(value)))

# ── Logitech API ──────────────────────────────────────────────────────────────

HEADERS = {
    "Api-Token": API_TOKEN,
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Logicheck/1.0",
}

def parse_product(data: dict) -> dict:
    p        = data.get("ProductList", [{}])[0]
    attr     = p.get("attributes", {})
    wrt      = attr.get("warranty", {})
    mfg_raw  = p.get("manufacture_date", "")
    emea_yrs = wrt.get("region", {}).get("EMEA", {}).get("year", 2)

    mfg_fmt = warranty_end = warranty_status = ""
    try:
        mfg     = datetime.fromisoformat(mfg_raw.replace("Z", "+00:00"))
        mfg_fmt = mfg.strftime("%Y-%m-%d")
        wend    = mfg.replace(year=mfg.year + emea_yrs)
        warranty_end    = wend.strftime("%Y-%m-%d")
        warranty_status = "active" if wend > datetime.now(timezone.utc) else "expired"
    except:
        pass

    return {
        "product":          attr.get("name", ""),
        "product_type":     attr.get("name_2", ""),
        "part_number":      p.get("part_number", ""),
        "manufacture_date": mfg_fmt,
        "warranty_end":     warranty_end,
        "warranty_status":  warranty_status,
        "marketing_id":     attr.get("marketing_id", ""),
        "raw_json":         json.dumps(data),
    }

def check_serial_api(serial: str) -> dict:
    try:
        r = requests.get(
            f"{API_URL}?serial_number={serial}&locale=de",
            headers=HEADERS, timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("ProductList"):
                result = parse_product(data)
                result["status"] = "valid"
                return result
            return {"status": "invalid"}
        elif r.status_code == 500:
            try:
                if r.json().get("message") == "Product_Already_Registered":
                    return {"status": "registered"}
            except:
                pass
            return {"status": "invalid"}
        elif r.status_code == 429:
            return {"status": "rate_limited"}
        return {"status": "invalid"}
    except Exception as e:
        return {"status": "error", "note": str(e)}

def save_result(db, serial: str, result: dict, note: str = ""):
    status = result.get("status", "")
    if status in ("invalid", "error"):
        return
    db.execute("""
        INSERT OR REPLACE INTO serials
        (serial,status,product,product_type,part_number,manufacture_date,
         warranty_end,warranty_status,marketing_id,raw_json,checked_at,note)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        serial, status,
        result.get("product",""), result.get("product_type",""),
        result.get("part_number",""), result.get("manufacture_date",""),
        result.get("warranty_end",""), result.get("warranty_status",""),
        result.get("marketing_id",""), result.get("raw_json",""),
        datetime.now(timezone.utc).isoformat(),
        note or result.get("note","")
    ))
    if status == "valid":
        cfg_set(db, "total_valid", int(cfg_get(db,"total_valid","0")) + 1)
    elif status == "registered":
        cfg_set(db, "total_registered", int(cfg_get(db,"total_registered","0")) + 1)

# ── Scanner thread ────────────────────────────────────────────────────────────
# Kein Lock beim Iterieren — Generator lebt nur im Scanner-Thread

_scanner_state = {
    "generator": None,
    "iterator":  None,
    "checked":   set(),   # bereits geprüfte serials (in-memory)
    "reset":     False,
}

def _rebuild_generator():
    with get_db() as db:
        ys = int(cfg_get(db, "year_start", "23"))
        ye = int(cfg_get(db, "year_end",   "26"))
        # Bereits in DB vorhandene überspringen
        rows = db.execute("SELECT serial FROM serials").fetchall()
        _scanner_state["checked"] = {r["serial"] for r in rows}
    g = SerialGenerator(year_start=ys, year_end=ye)
    _scanner_state["generator"] = g
    _scanner_state["iterator"]  = g.all_serials()
    log.info(f"[scanner] Generator initialisiert ({ys}–{ye})")

def scanner_loop():
    print("[scanner] Thread gestartet", flush=True)
    while True:
        try:
            if _scanner_state["reset"]:
                _scanner_state["reset"]     = False
                _scanner_state["generator"] = None
                _scanner_state["iterator"]  = None
                _scanner_state["checked"]   = set()
                print("[scanner] Reset", flush=True)

            if _scanner_state["iterator"] is None:
                _rebuild_generator()

            with get_db() as db:
                running = cfg_get(db, "scanner_running", "0")
                delay   = int(cfg_get(db, "scan_delay", "5"))

            if running != "1":
                time.sleep(2)
                continue

            # next() direkt — kein for-loop der still blockiert
            try:
                serial = next(_scanner_state["iterator"])
                while serial in _scanner_state["checked"]:
                    serial = next(_scanner_state["iterator"])
            except StopIteration:
                print("[scanner] Generator erschoepft, starte neu", flush=True)
                _scanner_state["generator"] = None
                _scanner_state["iterator"]  = None
                time.sleep(10)
                continue

            _scanner_state["checked"].add(serial)

            print(f"[scanner] Pruefe {serial}", flush=True)
            result = check_serial_api(serial)
            status = result.get("status", "")
            print(f"[scanner] {serial} -> {status}", flush=True)

            if status == "rate_limited":
                print("[scanner] Rate limit, warte 30s", flush=True)
                time.sleep(30)
                continue

            with get_db() as db:
                cfg_set(db, "total_checked", int(cfg_get(db, "total_checked","0")) + 1)
                cfg_set(db, "last_serial", serial)
                if status in ("valid", "registered"):
                    save_result(db, serial, result)
                    print(f"[scanner] GESPEICHERT: {serial} | {result.get('product','?')}", flush=True)
                db.commit()

            time.sleep(delay)

        except Exception as e:
            print(f"[scanner] FEHLER: {e}", flush=True)
            time.sleep(5)

# ── App startup ───────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()
    for fn in [init_reg_table, init_mail_tables, init_extended_tables, init_inbox_table]:
        try:
            fn()
        except Exception as e:
            print(f"[startup] WARNUNG bei {fn.__name__}: {e}", flush=True)
    threading.Thread(target=imap_poll_loop, daemon=True).start()
    threading.Thread(target=followup_check_loop, daemon=True).start()
    threading.Thread(target=scanner_loop, daemon=True).start()
    print("[startup] Alle Threads gestartet", flush=True)
    # Stelle sicher dass alle Registrierungen einen ticket_status haben
    try:
        with get_db() as db:
            regs = db.execute("""
                SELECT r.id FROM registrations r
                LEFT JOIN ticket_status ts ON ts.reg_id = r.id
                WHERE ts.reg_id IS NULL
            """).fetchall()
            for reg in regs:
                db.execute("""
                    INSERT OR IGNORE INTO ticket_status
                    (reg_id,status,rma_number,tracking,carrier,value_eur,archived,agent_name,notes)
                    VALUES (?,'open','','','',0,0,'','')
                """, (reg["id"],))
            if regs:
                db.commit()
                print(f"[startup] {len(regs)} ticket_status Einträge erstellt", flush=True)
    except Exception as e:
        print(f"[startup] ticket_status init: {e}", flush=True)
    log.info("[startup] Scanner-Thread gestartet")
