# ── API Routes ────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    try:
        with get_db() as db:
            total      = db.execute("SELECT COUNT(*) as c FROM serials").fetchone()["c"]
            valid      = db.execute("SELECT COUNT(*) as c FROM serials WHERE status='valid'").fetchone()["c"]
            registered = db.execute("SELECT COUNT(*) as c FROM serials WHERE status='registered'").fetchone()["c"]
            running    = cfg_get(db, "scanner_running", "0")
            delay      = cfg_get(db, "scan_delay", "5")
            total_chk  = int(cfg_get(db, "total_checked", "0"))
            ys         = int(cfg_get(db, "year_start", "23"))
            ye         = int(cfg_get(db, "year_end", "26"))
            last       = cfg_get(db, "last_serial", "")
        est      = estimate_total(ys, ye)
        progress = round(total_chk / max(est["total_estimate"], 1) * 100, 6)
        return {
            "total":           total,
            "valid":           valid,
            "registered":      registered,
            "scanner_running": running == "1",
            "scan_delay":      int(delay),
            "total_checked":   total_chk,
            "estimated_total": est["total_estimate"],
            "progress_pct":    progress,
            "year_start":      ys,
            "year_end":        ye,
            "last_serial":     last,
        }
    except Exception as e:
        print(f"[stats] Fehler: {e}", flush=True)
        return {
            "total":0,"valid":0,"registered":0,
            "scanner_running":False,"scan_delay":5,
            "total_checked":0,"estimated_total":1,
            "progress_pct":0,"year_start":23,"year_end":26,"last_serial":"",
        }

@app.get("/api/serials")
def get_serials(status: str = "", product: str = "", search: str = "",
                page: int = 1, limit: int = 50):
    with get_db() as db:
        q, p = "SELECT * FROM serials WHERE 1=1", []
        if status:
            q += " AND status=?";  p.append(status)
        if product:
            q += " AND product LIKE ?"; p.append(f"%{product}%")
        if search:
            q += " AND (serial LIKE ? OR product LIKE ? OR part_number LIKE ? OR note LIKE ?)"
            p += [f"%{search}%"] * 4
        # Count total
        count_row = db.execute("SELECT COUNT(*) as c FROM serials WHERE 1=1" +
            (" AND status=?" if status else "") +
            (" AND product LIKE ?" if product else "") +
            (" AND (serial LIKE ? OR product LIKE ? OR part_number LIKE ? OR note LIKE ?)" if search else ""),
            p).fetchone()
        total = count_row["c"]
        offset = (page - 1) * limit
        rows = db.execute(q + " ORDER BY checked_at DESC LIMIT ? OFFSET ?",
                          p + [limit, offset]).fetchall()
    return {
        "items":  [dict(r) for r in rows],
        "total":  total,
        "page":   page,
        "pages":  max(1, (total + limit - 1) // limit),
        "limit":  limit,
    }

@app.get("/api/serials/all")
def get_serials_all(status: str = "", search: str = ""):
    """Alle Serials ohne Pagination - nur für Export."""
    with get_db() as db:
        q, p = "SELECT * FROM serials WHERE 1=1", []
        if status:
            q += " AND status=?"; p.append(status)
        if search:
            q += " AND (serial LIKE ? OR product LIKE ?)"; p += [f"%{search}%"]*2
        rows = db.execute(q + " ORDER BY checked_at DESC", p).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/serial-detail/{serial}")
def get_serial_detail(serial: str):
    """Gibt alle Daten einer Serial in einem einzigen API-Call zurück."""
    with get_db() as db:
        s = db.execute("SELECT * FROM serials WHERE serial=?", (serial,)).fetchone()
        if not s:
            raise HTTPException(404, "Serial nicht gefunden")
        tags = [r["tag"] for r in db.execute(
            "SELECT tag FROM serial_tags WHERE serial=?", (serial,)).fetchall()]
        all_tags = [r["tag"] for r in db.execute(
            "SELECT DISTINCT tag FROM serial_tags").fetchall()]
        pv = db.execute(
            "SELECT * FROM product_values WHERE part_number=?",
            (s["part_number"] or "",)).fetchone()
        idents = db.execute(
            "SELECT * FROM identities ORDER BY name").fetchall()
        preset_tags = ["Lager A","Lager B","verkauft","defekt",
                       "in Bearbeitung","RMA","archiviert","wertvoll"]
        combined_tags = list(dict.fromkeys(preset_tags + all_tags))
    return {
        "serial":   dict(s),
        "tags":     tags,
        "all_tags": combined_tags,
        "pv":       dict(pv) if pv else {},
        "identities": [dict(i) for i in idents],
    }

@app.get("/api/products")
def get_products():
    with get_db() as db:
        rows = db.execute("""
            SELECT product, product_type, part_number, marketing_id,
                   COUNT(*) as total,
                   SUM(CASE WHEN status='valid'           THEN 1 ELSE 0 END) as valid,
                   SUM(CASE WHEN status='registered'      THEN 1 ELSE 0 END) as registered,
                   SUM(CASE WHEN warranty_status='active' THEN 1 ELSE 0 END) as warranty_active
            FROM serials WHERE product != ''
            GROUP BY product, part_number ORDER BY total DESC
        """).fetchall()
    return [dict(r) for r in rows]

class SerialInput(BaseModel):
    serial: str
    note:   str = ""

@app.post("/api/check")
def check_single(inp: SerialInput):
    serial = inp.serial.strip().upper()
    result = check_serial_api(serial)
    with get_db() as db:
        save_result(db, serial, result, inp.note)
        db.commit()
    _scanner_state["checked"].add(serial)
    return {"serial": serial, **result}

@app.post("/api/scanner/start")
def scanner_start():
    with get_db() as db:
        cfg_set(db, "scanner_running", "1"); db.commit()
    log.info("[api] Scanner gestartet")
    return {"ok": True}

@app.post("/api/scanner/stop")
def scanner_stop():
    with get_db() as db:
        cfg_set(db, "scanner_running", "0"); db.commit()
    log.info("[api] Scanner gestoppt")
    return {"ok": True}

@app.post("/api/scanner/reset")
def scanner_reset():
    _scanner_state["reset"] = True
    with get_db() as db:
        cfg_set(db, "total_checked", "0")
        cfg_set(db, "last_serial", "")
        db.commit()
    log.info("[api] Reset angefordert")
    return {"ok": True}

@app.post("/api/scanner/delay/{seconds}")
def set_delay(seconds: int):
    if not (2 <= seconds <= 120):
        raise HTTPException(400, "2–120 Sekunden")
    with get_db() as db:
        cfg_set(db, "scan_delay", str(seconds)); db.commit()
    return {"ok": True}

@app.post("/api/scanner/years")
def set_years(body: dict):
    ys = int(body.get("year_start", 23))
    ye = int(body.get("year_end",   26))
    if not (20 <= ys <= ye <= 30):
        raise HTTPException(400, "Ungültiger Jahrgang")
    with get_db() as db:
        cfg_set(db, "year_start", str(ys))
        cfg_set(db, "year_end",   str(ye))
        db.commit()
    _scanner_state["reset"] = True
    return {"ok": True}

@app.patch("/api/serials/{serial}/note")
def update_note(serial: str, body: dict):
    with get_db() as db:
        db.execute("UPDATE serials SET note=? WHERE serial=?",
                   (body.get("note",""), serial))
        db.commit()
    return {"ok": True}

@app.delete("/api/serials/{serial}")
def delete_serial(serial: str):
    with get_db() as db:
        db.execute("DELETE FROM serials WHERE serial=?", (serial,))
        db.commit()
    return {"ok": True}

