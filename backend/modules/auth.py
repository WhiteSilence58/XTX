# ── Login / Auth ──────────────────────────────────────────────────────────────
import secrets, hashlib

SESSION_STORE: dict = {}  # token -> created_at

def get_auth_config(db) -> tuple:
    u = db.execute("SELECT value FROM settings WHERE key='auth_user'").fetchone()
    p = db.execute("SELECT value FROM settings WHERE key='auth_pass_hash'").fetchone()
    return (u["value"] if u else "admin"), (p["value"] if p else "")

def check_session(request: Request) -> bool:
    token = request.cookies.get("lc_session","")
    if not token: return False
    entry = SESSION_STORE.get(token)
    if not entry: return False
    # Session 24h gültig
    if (datetime.now(timezone.utc) - entry).total_seconds() > 86400:
        SESSION_STORE.pop(token, None)
        return False
    return True

def require_auth(request: Request):
    # API-Endpunkte die immer erlaubt sind (Login selbst)
    if request.url.path in ("/api/login", "/api/logout"):
        return
    if not check_session(request):
        raise HTTPException(status_code=401, detail="Nicht angemeldet")

@app.post("/api/login")
async def login(request: Request, response: Response):
    body = await request.json()
    username = body.get("username","").strip()
    password = body.get("password","")
    with get_db() as db:
        stored_user, stored_hash = get_auth_config(db)
    # Wenn noch kein Passwort gesetzt: alles erlauben
    if not stored_hash:
        token = secrets.token_hex(32)
        SESSION_STORE[token] = datetime.now(timezone.utc)
        response.set_cookie("lc_session", token, httponly=True, samesite="lax", max_age=86400)
        return {"ok": True, "first_login": True}
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    if username == stored_user and pw_hash == stored_hash:
        token = secrets.token_hex(32)
        SESSION_STORE[token] = datetime.now(timezone.utc)
        response.set_cookie("lc_session", token, httponly=True, samesite="lax", max_age=86400)
        return {"ok": True}
    return JSONResponse({"ok": False, "error": "Falsches Passwort"}, status_code=401)

@app.post("/api/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("lc_session","")
    SESSION_STORE.pop(token, None)
    response.delete_cookie("lc_session")
    return {"ok": True}

@app.get("/api/auth/check")
async def auth_check(request: Request):
    with get_db() as db:
        _, stored_hash = get_auth_config(db)
    return {"logged_in": check_session(request), "has_password": bool(stored_hash)}

@app.post("/api/auth/set-password")
async def set_password(request: Request):
    if not check_session(request):
        raise HTTPException(401, "Nicht angemeldet")
    body = await request.json()
    username = body.get("username","admin").strip()
    password = body.get("password","")
    if len(password) < 4:
        raise HTTPException(400, "Passwort zu kurz (min. 4 Zeichen)")
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO settings VALUES ('auth_user',?)", (username,))
        db.execute("INSERT OR REPLACE INTO settings VALUES ('auth_pass_hash',?)", (pw_hash,))
        db.commit()
    return {"ok": True}

# Middleware: alle /api/* Endpunkte schützen außer Login
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    # Statische Dateien und Login immer erlaubt
    if not path.startswith("/api/") or path in ("/api/login", "/api/logout", "/api/auth/check"):
        return await call_next(request)
    # API-Zugriff prüfen
    if not check_session(request):
        return JSONResponse({"detail": "Nicht angemeldet"}, status_code=401)
    return await call_next(request)


DB_PATH   = "/data/logicheck.db"
API_URL   = "https://apim.workato.com/product-lookup-v10/prod/serialization-ser-1"
API_TOKEN = "eada23b666b5b1597cac6a0b2b62e219e30f09077fd75cb3ba8c361e74289a0f"
