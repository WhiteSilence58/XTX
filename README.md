# LogiCheck – Setup auf Ubuntu

## Voraussetzungen installieren

```bash
# Docker + Compose installieren
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

## Deployment

```bash
# Projekt auf den Server kopieren (von deinem PC aus)
scp -r logicheck/ user@DEIN-SERVER:/opt/logicheck

# Auf dem Server
cd /opt/logicheck
mkdir -p data
docker compose up -d
```

## Läuft auf: http://DEIN-SERVER:8000

## Nützliche Befehle

```bash
# Logs anschauen
docker compose logs -f

# Neu starten
docker compose restart

# Stoppen
docker compose down

# Update nach Code-Änderung
docker compose up -d --build
```

## Serials hinzufügen

**Manuell über die UI:**
- Tab "Queue" → Serials einfügen → "Zur Queue hinzufügen"
- Scanner starten im Dashboard

**Per API (curl):**
```bash
# Serials zur Queue hinzufügen
curl -X POST http://localhost:8000/api/queue \
  -H "Content-Type: application/json" \
  -d '{"serials":["2427LZ90VDA8","2427LZ90VDB8","2427LZ90VDC8"]}'

# Scanner starten
curl -X POST http://localhost:8000/api/scanner/start

# Pause zwischen Requests setzen (Sekunden)
curl -X POST http://localhost:8000/api/scanner/delay/5

# Stats abrufen
curl http://localhost:8000/api/stats
```

## Datenbank-Backup

```bash
cp /opt/logicheck/data/logicheck.db /backup/logicheck-$(date +%Y%m%d).db
```
