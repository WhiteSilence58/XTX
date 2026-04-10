# ── Manuelle Registrierung aus Inbox ─────────────────────────────────────────

class ManualRegInput(BaseModel):
    email:  str
    name:   str = ""
    serial: str = ""
    notes:  str = ""

@app.post("/api/registrations/manual")
def create_manual_registration(inp: ManualRegInput):
    """Legt eine Registrierung manuell an — z.B. für Mails die schon da sind."""
    email = inp.email.strip().lower()
    if not email:
        raise HTTPException(400, "E-Mail fehlt")
    parts = inp.name.strip().split(" ", 1) if inp.name.strip() else ["Unbekannt", ""]
    first = parts[0]; last = parts[1] if len(parts) > 1 else parts[0]
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        # Prüfen ob schon vorhanden
        exists = db.execute(
            "SELECT id FROM registrations WHERE email=?", (email,)
        ).fetchone()
        if exists:
            reg_id = exists["id"]
        else:
            cur = db.execute("""
                INSERT INTO registrations
                (serial, email, name, domain, zendesk_uid, ticket_id,
                 reg_status, reg_message, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (inp.serial or "", email, inp.name or f"{first} {last}",
                  email.split("@")[1] if "@" in email else "",
                  "", "", "manual", inp.notes or "Manuell angelegt", now))
            db.commit()
            reg_id = cur.lastrowid
        # Inbox-Mails mit dieser Adresse zuordnen
        updated = db.execute("""
            UPDATE inbox SET reg_id=?
            WHERE reg_id IS NULL AND (
                lower(to_addr) LIKE ? OR
                lower(from_addr) LIKE ? OR
                lower(body) LIKE ?
            )
        """, (reg_id,
              f"%{email}%", f"%{email}%", f"%{email}%")).rowcount
        db.commit()
        # ticket_status anlegen
        db.execute("""
            INSERT OR IGNORE INTO ticket_status (reg_id, status, notes)
            VALUES (?, 'open', ?)
        """, (reg_id, inp.notes or ""))
        db.commit()
    # Alle zugeordneten Mails nochmal verarbeiten
    with get_db() as db:
        mails = db.execute(
            "SELECT body, subject, from_addr FROM inbox WHERE reg_id=?", (reg_id,)
        ).fetchall()
    for m in mails:
        process_mail_for_rma(reg_id, m["body"] or "", m["subject"] or "", m["from_addr"] or "")
    return {"ok": True, "reg_id": reg_id, "mails_assigned": updated}

@app.get("/api/registrations/from-inbox")
def suggest_registrations_from_inbox():
    """Findet alle einzigartigen Catch-All-Adressen in der Inbox die noch keine Registrierung haben."""
    import re as _re
    with get_db() as db:
        # Alle To-Adressen aus Inbox die noch keine reg_id haben
        rows = db.execute("""
            SELECT DISTINCT to_addr, from_addr, subject,
                   COUNT(*) as mail_count,
                   MAX(received_at) as last_mail
            FROM inbox
            WHERE reg_id IS NULL AND to_addr != ''
            GROUP BY to_addr
            ORDER BY mail_count DESC
        """).fetchall()
        regs = db.execute("SELECT email FROM registrations").fetchall()
        existing = {r["email"].lower() for r in regs}

    suggestions = []
    for row in rows:
        to_raw = row["to_addr"] or ""
        # Extrahiere E-Mail aus "Name <email>" Format
        m = _re.search(r'<([^>]+)>', to_raw)
        email = m.group(1).lower() if m else to_raw.lower().strip()
        # Name extrahieren
        nm = _re.match(r'([^<]+)<', to_raw)
        name = nm.group(1).strip().strip('"\' ') if nm else ""
        if email and email not in existing and "@" in email:
            suggestions.append({
                "email":      email,
                "name":       name,
                "to_raw":     to_raw,
                "mail_count": row["mail_count"],
                "last_mail":  row["last_mail"],
                "sample_subject": row["subject"],
            })
    return suggestions


def delete_from_imap(uids: list):
    """Löscht Mails endgültig vom IMAP-Server anhand ihrer UIDs."""
    if not uids:
        return
    try:
        with get_db() as db:
            user, pwd = get_mail_creds(db)
        if not user or not pwd:
            return
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
            imap.login(user, pwd)
            imap.select("INBOX")
            for uid in uids:
                # uid ist gespeichert als "uid_123" → extrahiere nur die Zahl
                raw_uid = str(uid).replace("uid_", "")
                if raw_uid.isdigit():
                    imap.uid("store", raw_uid.encode(), "+FLAGS", r"\Deleted")
            imap.expunge()
            print(f"[imap] {len(uids)} Mails endgültig gelöscht", flush=True)
    except Exception as e:
        print(f"[imap] Löschen fehlgeschlagen: {e}", flush=True)

@app.delete("/api/inbox/{mail_id}")
def delete_inbox_mail(mail_id: int):
    """Löscht Mail aus DB UND endgültig vom IMAP-Server."""
    with get_db() as db:
        row = db.execute("SELECT uid FROM inbox WHERE id=?", (mail_id,)).fetchone()
        if row:
            delete_from_imap([row["uid"]])
        db.execute("DELETE FROM inbox WHERE id=?", (mail_id,))
        db.commit()
    return {"ok": True}

@app.post("/api/inbox/delete-many")
def delete_many_inbox(body: dict):
    """Löscht mehrere Mails aus DB UND endgültig vom IMAP-Server."""
    ids = body.get("ids", [])
    if not ids:
        return {"ok": False, "error": "Keine IDs"}
    with get_db() as db:
        rows = db.execute(f"SELECT uid FROM inbox WHERE id IN ({','.join('?'*len(ids))})", ids).fetchall()
        uids = [r["uid"] for r in rows if r["uid"]]
        delete_from_imap(uids)
        db.execute(f"DELETE FROM inbox WHERE id IN ({','.join('?'*len(ids))})", ids)
        db.commit()
    return {"ok": True, "deleted": len(ids)}

@app.post("/api/inbox/mark-read-many")
def mark_read_many(body: dict):
    ids = body.get("ids", [])
    if not ids: return {"ok": False}
    with get_db() as db:
        db.execute(
            f"UPDATE inbox SET read_at=? WHERE id IN ({','.join('?'*len(ids))})",
            [datetime.now(timezone.utc).isoformat()] + ids
        )
        db.commit()
    return {"ok": True}



@app.post("/api/invoice/from-docx")
def invoice_from_docx(body: dict):
    """
    Nimmt eine Word-Datei (.docx) mit Markern ({{NAME}} etc.),
    ersetzt alle Marker mit den Werten und gibt ein PDF zurück.
    """
    import base64, io, tempfile, os, subprocess, re as _re
    from docx import Document
    from copy import deepcopy

    docx_b64 = body.get("docx_b64", "")
    if not docx_b64:
        return {"ok": False, "error": "Keine Datei"}

    # Werte aus Request
    name         = body.get("name", "")
    street       = body.get("street", "")
    city         = body.get("city", "")
    zip_         = body.get("zip", "")
    product      = body.get("product", "")
    price        = float(body.get("price", 0) or 0)
    date         = body.get("date", "")
    number       = body.get("number", "")
    shop         = body.get("shop", "")
    ship_date    = body.get("ship_date", "")
    order_number = body.get("order_number", "")
    serial       = body.get("serial", "")
    country      = body.get("country", "de")

    # Preise berechnen: Netto = Brutto / 119 * 100, MwSt = Brutto - Netto
    net   = round(price / 119 * 100, 2) if price else 0
    tax   = round(price - net, 2) if price else 0

    name_parts = name.strip().split(" ")
    first_name = name_parts[0] if name_parts else ""
    last_name  = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    def fmt_price(p):
        return f"{p:.2f}".replace(".", ",")

    def _fmt_date(d):
        """Konvertiert YYYY-MM-DD zu DD.MM.YYYY."""
        if not d: return ""
        parts = str(d).replace("/","-").split("-")
        if len(parts) == 3 and len(parts[0]) == 4:
            return f"{parts[2]}.{parts[1]}.{parts[0]}"
        return d

    markers = {
        "{{NAME}}":         name,
        "{{VORNAME}}":      first_name,
        "{{NACHNAME}}":     last_name,
        "{{STRASSE}}":      street,
        "{{ORT}}":          city,
        "{{PLZ}}":          zip_,
        "{{PLZ_ORT}}":      f"{zip_} {city}".strip(),
        "{{ADRESSE}}":      f"{street}, {zip_} {city}".strip(", "),
        "{{DATUM}}":        _fmt_date(date),
        "{{VERSANDDATUM}}": _fmt_date(ship_date),
        "{{VERSAND}}":      _fmt_date(ship_date),
        "{{RECHNUNGSNR}}":  number,
        "{{NUMMER}}":       number,
        "{{BESTELLNR}}":    order_number,
        "{{PRODUKT}}":      product,
        "{{ARTIKEL}}":      product,
        "{{PREIS}}":        fmt_price(price),
        "{{BRUTTO}}":       fmt_price(price),
        "{{NETTO}}":        fmt_price(net),
        "{{MWST}}":         fmt_price(tax),
        "{{STEUER}}":       fmt_price(tax),
        "{{HAENDLER}}":     shop,
        "{{SHOP}}":         shop,
        "{{SERIAL}}":       serial,
    }

    try:
        docx_bytes = base64.b64decode(docx_b64)
        doc = Document(io.BytesIO(docx_bytes))

        def replace_in_para(para):
            """Ersetzt Marker — bewahrt ALLE Formatierung inkl. Schriftart."""
            from lxml import etree
            from copy import deepcopy

            # Prüfe ob Marker vorhanden
            full_text = "".join(r.text for r in para.runs)
            if not any(m in full_text for m in markers):
                return

            # Direkte Ersetzung pro Run (bewahrt Formatierung komplett)
            for run in para.runs:
                if not run.text:
                    continue
                new_text = run.text
                for marker, val in markers.items():
                    if marker in new_text:
                        new_text = new_text.replace(marker, val)
                if new_text != run.text:
                    # Nur w:t Element ändern, KEIN w:rPr anfassen
                    run.text = new_text

            # Prüfe ob Marker über mehrere Runs verteilt (z.B. {{NA||ME}})
            full_text_after = "".join(r.text for r in para.runs)
            if not any(m in full_text_after for m in markers):
                return

            # Fallback: Zusammenbauen mit XML-Manipulation
            # Ersten Run mit ersetztem Text verwenden, XML-Properties komplett erhalten
            replaced = full_text_after
            for marker, val in markers.items():
                replaced = replaced.replace(marker, val)

            if para.runs:
                # XML des ersten Runs direkt manipulieren
                first_run = para.runs[0]
                # Nur w:t Text ändern, alles andere (w:rPr, etc.) bleibt
                ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                t_elem = first_run._r.find(f"{{{ns}}}t")
                if t_elem is not None:
                    t_elem.text = replaced
                    # xml:space preserve setzen
                    t_elem.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                else:
                    first_run.text = replaced
                # Restliche Runs leeren (nur w:t, nicht w:rPr)
                for run in para.runs[1:]:
                    t_elem = run._r.find(f"{{{ns}}}t")
                    if t_elem is not None:
                        t_elem.text = ""
                    else:
                        run.text = ""

        # Alle Paragraphen durchgehen
        for para in doc.paragraphs:
            replace_in_para(para)

        # Tabellen durchgehen
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        replace_in_para(para)

        # Kopf- und Fußzeilen
        for section in doc.sections:
            for hf in [section.header, section.footer]:
                if hf:
                    for para in hf.paragraphs:
                        replace_in_para(para)

        # Dokument in tempfile speichern
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = os.path.join(tmpdir, "rechnung.docx")
            pdf_path  = os.path.join(tmpdir, "rechnung.pdf")
            doc.save(docx_path)

            # LibreOffice Konvertierung zu PDF
            # Suche LibreOffice auf verschiedenen Pfaden
            lo_paths = ["libreoffice", "soffice", "/usr/bin/libreoffice", "/usr/bin/soffice"]
            lo_cmd = None
            import shutil
            for p in lo_paths:
                if shutil.which(p):
                    lo_cmd = p
                    break
            if not lo_cmd:
                return {"ok": False, "error": "LibreOffice nicht gefunden. Server wird neu gestartet..."}

            env = os.environ.copy()
            env["HOME"] = "/tmp"
            env["TMPDIR"] = tmpdir

            # PDF mit eingebetteten Schriften exportieren
            result = subprocess.run(
                [lo_cmd, "--headless", "--norestore",
                 "--convert-to", "pdf:writer_pdf_Export",
                 "--outdir", tmpdir, docx_path],
                capture_output=True, text=True, timeout=60, env=env
            )
            print(f"[invoice] LibreOffice: {result.returncode} {result.stderr[:100]}", flush=True)

            if not os.path.exists(pdf_path):
                return {"ok": False, "error": f"PDF-Konvertierung fehlgeschlagen: {result.stderr[:200]}"}

            with open(pdf_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode()

        return {"ok": True, "pdf_b64": pdf_b64, "method": "docx_marker"}

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"ok": False, "error": str(e)}


@app.post("/api/invoice/analyze")
def analyze_invoice_pdf(body: dict):
    """Extrahiert Text aus der PDF-Vorlage und erkennt Felder."""
    import base64, io
    b64 = body.get("pdf_b64","")
    if not b64:
        return {"ok": False, "error": "Kein PDF"}
    try:
        import pdfplumber
        pdf_bytes = base64.b64decode(b64)
        text_parts = []
        fields_found = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, page in enumerate(pdf.pages[:2]):
                t = page.extract_text() or ""
                text_parts.append(t)
                # Detect common invoice fields
                import re
                if re.search(r'\b(Name|Vorname|Nachname|Customer|Kunde)\b', t, re.I):
                    fields_found.append("Name")
                if re.search(r'\b(Straße|Street|Adresse|Address)\b', t, re.I):
                    fields_found.append("Adresse")
                if re.search(r'\b(Datum|Date|Kaufdatum|Purchase)\b', t, re.I):
                    fields_found.append("Datum")
                if re.search(r'\b(Preis|Price|Betrag|Amount|Total)\b', t, re.I):
                    fields_found.append("Preis")
                if re.search(r'\b(Produkt|Product|Artikel|Item)\b', t, re.I):
                    fields_found.append("Produkt")
                if re.search(r'\b(Rechnung|Invoice|Nr\.?|Number)\b', t, re.I):
                    fields_found.append("Rechnungsnummer")
        return {
            "ok": True,
            "text": "\n".join(text_parts),
            "fields_found": list(set(fields_found)),
            "pages": len(pdf.pages) if pdf else 0
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/invoice/generate")
def generate_invoice(body: dict):
    """Erstellt eine Rechnung als PDF — entweder aus Vorlage oder neu generiert."""
    import base64, io
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER

    name    = body.get("name","")
    street  = body.get("street","")
    city    = body.get("city","")
    zip_    = body.get("zip","")
    country = body.get("country","de")
    serial  = body.get("serial","")
    product = body.get("product","Logitech Gerät")
    price   = float(body.get("price",0) or 0)
    date    = body.get("date","")
    number  = body.get("number","")
    shop    = body.get("shop","Online Shop")
    template_b64 = body.get("template_b64")

    # If template provided, use marker-based replacement
    if template_b64:
        try:
            from pypdf import PdfReader, PdfWriter
            from reportlab.pdfgen import canvas as rl_canvas
            import pdfplumber, re as _re

            template_bytes = base64.b64decode(template_b64)

            # Build marker → replacement map
            # All possible markers the user can put in their PDF template
            tax_rate = 0.19 if country in ("de","at") else 0.077 if country=="ch" else 0.20 if country=="gb" else 0.19
            net = price / (1 + tax_rate) if tax_rate and price else price
            tax_amount = price - net if tax_rate else 0

            # Name parts
            name_parts = name.strip().split(" ")
            first_name = name_parts[0] if name_parts else ""
            last_name  = " ".join(name_parts[1:]) if len(name_parts)>1 else ""

            markers = {
                "{{NAME}}":         name,
                "{{VORNAME}}":      first_name,
                "{{NACHNAME}}":     last_name,
                "{{STRASSE}}":      street,
                "{{ORT}}":          city,
                "{{PLZ}}":          zip_,
                "{{PLZ_ORT}}":      f"{zip_} {city}".strip(),
                "{{ADRESSE}}":      f"{street}, {zip_} {city}".strip(", "),
                "{{DATUM}}":        date,
                "{{RECHNUNGSNR}}":  number,
                "{{NUMMER}}":       number,
                "{{PRODUKT}}":      product,
                "{{ARTIKEL}}":      product,
                "{{PREIS}}":        f"{price:.2f}",
                "{{BRUTTO}}":       f"{price:.2f}",
                "{{NETTO}}":        f"{net:.2f}",
                "{{MWST}}":         f"{tax_amount:.2f}",
                "{{STEUER}}":       f"{tax_amount:.2f}",
                "{{HAENDLER}}":     shop,
                "{{SHOP}}":         shop,
                "{{SERIAL}}":       serial,
                "{{VERSANDDATUM}}": body.get("ship_date",""),
                "{{VERSAND}}":      body.get("ship_date",""),
                "{{BESTELLNR}}":    body.get("order_number",""),
                "{{BESTELLUNG}}":   body.get("order_number",""),
            }

            # Extract words with positions using pdfplumber
            overlay_buf = io.BytesIO()
            c = rl_canvas.Canvas(overlay_buf, pagesize=A4)
            w, h = A4
            replaced_count = 0

            with pdfplumber.open(io.BytesIO(template_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    pw, ph = float(page.width), float(page.height)
                    sx, sy = w/pw, h/ph

                    # Get all words with their bounding boxes
                    words = page.extract_words(
                        keep_blank_chars=True,
                        x_tolerance=3,
                        y_tolerance=3,
                        extra_attrs=["fontname","size"]
                    ) or []

                    # Also try to get chars for better font size info
                    chars = page.chars or []
                    char_by_pos = {}
                    for ch in chars:
                        key = (round(float(ch.get("x0",0))), round(float(ch.get("top",0))))
                        char_by_pos[key] = ch

                    for word in words:
                        word_text = word.get("text","")
                        # Check exact match first
                        replacement = None
                        for marker, val in markers.items():
                            if marker in word_text:
                                replacement = word_text.replace(marker, val)
                                break

                        if replacement is not None:
                            # Get position
                            x0  = float(word["x0"]) * sx
                            top = float(word["top"]) * sy
                            bot = float(word["bottom"]) * sy
                            y   = h - bot  # reportlab y from bottom

                            # Get font size from word or chars
                            font_size = float(word.get("size", 0))
                            if not font_size:
                                # Try chars
                                key = (round(float(word["x0"])), round(float(word["top"])))
                                ch = char_by_pos.get(key,{})
                                font_size = float(ch.get("size",10))
                            if not font_size or font_size < 4:
                                font_size = (bot - top) * sy * 0.85

                            font_size = max(6, min(24, font_size))

                            # White out old text
                            box_w = (float(word["x1"]) - float(word["x0"])) * sx + 4
                            box_h = (bot - top) * sy + 2
                            c.setFillColorRGB(1,1,1)
                            c.rect(x0-1, y-1, box_w, box_h+2, fill=1, stroke=0)

                            # Draw new text with same approximate font
                            c.setFillColorRGB(0,0,0)
                            font_name_raw = word.get("fontname","") or ""
                            if "Bold" in font_name_raw or "bold" in font_name_raw:
                                font = "Helvetica-Bold"
                            elif "Italic" in font_name_raw or "italic" in font_name_raw:
                                font = "Helvetica-Oblique"
                            else:
                                font = "Helvetica"
                            c.setFont(font, font_size)
                            c.drawString(x0, y, replacement)
                            replaced_count += 1

                    if page_num < len(pdf.pages)-1:
                        c.showPage()

            c.save()
            overlay_buf.seek(0)

            print(f"[invoice] Marker-System: {replaced_count} Felder ersetzt", flush=True)

            # Merge overlay onto template
            template_reader = PdfReader(io.BytesIO(template_bytes))
            overlay_reader  = PdfReader(overlay_buf)
            writer = PdfWriter()
            for i, page in enumerate(template_reader.pages):
                if i < len(overlay_reader.pages):
                    page.merge_page(overlay_reader.pages[i])
                writer.add_page(page)

            out_buf = io.BytesIO()
            writer.write(out_buf)
            out_buf.seek(0)
            pdf_b64_out = base64.b64encode(out_buf.read()).decode()
            return {
                "ok": True,
                "pdf_b64": pdf_b64_out,
                "method": f"marker ({replaced_count} Felder ersetzt)",
                "replaced": replaced_count
            }
        except Exception as e:
            print(f"[invoice] Template-Fehler: {e}", flush=True)
            import traceback; traceback.print_exc()
            # Fall through to generated invoice
    # Generate fresh invoice with reportlab
    try:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
            leftMargin=2.5*cm, rightMargin=2.5*cm,
            topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        W, H = A4

        # Custom styles
        s_title  = ParagraphStyle("title",  fontSize=22, fontName="Helvetica-Bold", spaceAfter=4)
        s_sub    = ParagraphStyle("sub",    fontSize=10, fontName="Helvetica",     textColor=colors.HexColor("#666666"), spaceAfter=2)
        s_label  = ParagraphStyle("label",  fontSize=9,  fontName="Helvetica-Bold", textColor=colors.HexColor("#888888"), spaceAfter=1)
        s_value  = ParagraphStyle("value",  fontSize=11, fontName="Helvetica",      spaceAfter=2)
        s_right  = ParagraphStyle("right",  fontSize=11, fontName="Helvetica",      alignment=TA_RIGHT)
        s_total  = ParagraphStyle("total",  fontSize=14, fontName="Helvetica-Bold", textColor=colors.HexColor("#185FA5"))

        country_map = {"de":"Deutschland","us":"USA","gb":"Großbritannien","at":"Österreich","ch":"Schweiz"}
        country_name = country_map.get(country, country.upper())
        tax_rate = 0.19 if country in ("de","at") else 0.077 if country == "ch" else 0.20 if country == "gb" else 0
        net = price / (1 + tax_rate) if tax_rate else price
        tax = price - net if tax_rate else 0

        story = []

        # Header row
        header_data = [
            [Paragraph("RECHNUNG", s_title), Paragraph(f"Nr. {number}", s_right)],
        ]
        header_table = Table(header_data, colWidths=[12*cm, 4*cm])
        header_table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
        story.append(header_table)
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#185FA5"), spaceAfter=16))

        # Addresses: sender (shop) left, recipient right
        addr_data = [[
            [Paragraph("VERKÄUFER", s_label), Paragraph(shop, s_value), Paragraph(" ", s_sub)],
            [Paragraph("KÄUFER", s_label), Paragraph(name, s_value), Paragraph(street, s_value), Paragraph(zip_+" "+city, s_value), Paragraph(country_name, s_sub)],
        ]]
        addr_table = Table(addr_data, colWidths=[8*cm, 8*cm])
        addr_table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP')]))
        story.append(addr_table)
        story.append(Spacer(1, 14))

        # Invoice details
        detail_data = [
            [Paragraph("KAUFDATUM", s_label), Paragraph("RECHNUNGSDATUM", s_label), Paragraph("SERIAL", s_label)],
            [Paragraph(date or "—", s_value), Paragraph(date or "—", s_value), Paragraph(serial or "—", s_value)],
        ]
        detail_table = Table(detail_data, colWidths=[5.3*cm, 5.3*cm, 5.4*cm])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor("#F5F4F0")),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white]),
            ('GRID',(0,0),(-1,-1),0.5,colors.HexColor("#DDDDDD")),
            ('FONTSIZE',(0,0),(-1,-1),10),
            ('TOPPADDING',(0,0),(-1,-1),6),
            ('BOTTOMPADDING',(0,0),(-1,-1),6),
            ('LEFTPADDING',(0,0),(-1,-1),8),
        ]))
        story.append(detail_table)
        story.append(Spacer(1, 20))

        # Product table
        story.append(Paragraph("POSITIONEN", s_label))
        story.append(Spacer(1, 4))
        prod_data = [
            ["Pos.", "Beschreibung", "Menge", "Preis"],
            ["1", product or "Logitech Produkt", "1x", f"{price:.2f} €"],
        ]
        prod_table = Table(prod_data, colWidths=[1.2*cm, 10*cm, 2*cm, 3*cm])
        prod_table.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor("#185FA5")),
            ('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('FONTNAME',(0,0),(-1,0),"Helvetica-Bold"),
            ('FONTSIZE',(0,0),(-1,-1),10),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor("#F9F9F7")]),
            ('GRID',(0,0),(-1,-1),0.5,colors.HexColor("#DDDDDD")),
            ('TOPPADDING',(0,0),(-1,-1),8),
            ('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('LEFTPADDING',(0,0),(-1,-1),8),
            ('ALIGN',(2,0),(-1,-1),'RIGHT'),
        ]))
        story.append(prod_table)
        story.append(Spacer(1, 12))

        # Totals
        totals = []
        if tax_rate:
            totals.append(["Nettobetrag:", f"{net:.2f} €"])
            totals.append([f"MwSt. {int(tax_rate*100)}%:", f"{tax:.2f} €"])
        totals.append(["Gesamtbetrag:", f"{price:.2f} €"])
        totals_table = Table(
            [[Paragraph(r[0], s_right if i<len(totals)-1 else ParagraphStyle("tlbl",fontSize=12,fontName="Helvetica-Bold",alignment=TA_RIGHT)),
              Paragraph(r[1], s_right if i<len(totals)-1 else s_total)] for i,r in enumerate(totals)],
            colWidths=[12*cm, 4*cm]
        )
        totals_table.setStyle(TableStyle([
            ('LINEABOVE',(0,-1),(-1,-1),1.5,colors.HexColor("#185FA5")),
            ('TOPPADDING',(0,0),(-1,-1),4),
            ('BOTTOMPADDING',(0,0),(-1,-1),4),
        ]))
        story.append(totals_table)
        story.append(Spacer(1, 30))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC")))
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            "Vielen Dank für Ihren Einkauf. · Diese Rechnung wurde maschinell erstellt.",
            ParagraphStyle("footer", fontSize=8, textColor=colors.HexColor("#999999"), alignment=TA_CENTER)
        ))

        doc.build(story)
        buf.seek(0)
        pdf_b64 = base64.b64encode(buf.read()).decode()
        return {"ok": True, "pdf_b64": pdf_b64, "method": "generated"}
    except Exception as e:
        print(f"[invoice] Fehler: {e}", flush=True)
        return {"ok": False, "error": str(e)}


@app.get("/api/invoice-templates")
def get_invoice_templates():
    with get_db() as db:
        rows = db.execute(
            "SELECT id, name, filename, file_type, created_at FROM invoice_templates ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]

@app.post("/api/invoice-templates")
def save_invoice_template(body: dict):
    name     = body.get("name","").strip()
    data_b64 = body.get("data_b64","")
    filename = body.get("filename","vorlage.docx")
    file_type= body.get("file_type","docx")
    if not name or not data_b64:
        raise HTTPException(400, "Name und Daten erforderlich")
    with get_db() as db:
        db.execute("""
            INSERT INTO invoice_templates (name, filename, data_b64, file_type, created_at)
            VALUES (?,?,?,?,?)
        """, (name, filename, data_b64, file_type, datetime.now(timezone.utc).isoformat()))
        db.commit()
    return {"ok": True}

@app.delete("/api/invoice-templates/{tpl_id}")
def delete_invoice_template(tpl_id: int):
    with get_db() as db:
        db.execute("DELETE FROM invoice_templates WHERE id=?", (tpl_id,))
        db.commit()
    return {"ok": True}

@app.patch("/api/invoice-templates/{tpl_id}")
def rename_invoice_template(tpl_id: int, body: dict):
    name = body.get("name","").strip()
    if not name: raise HTTPException(400, "Name erforderlich")
    with get_db() as db:
        db.execute("UPDATE invoice_templates SET name=? WHERE id=?", (name, tpl_id))
        db.commit()
    return {"ok": True}

@app.get("/api/invoice-templates/{tpl_id}/data")
def get_invoice_template_data(tpl_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM invoice_templates WHERE id=?", (tpl_id,)).fetchone()
    if not row: raise HTTPException(404)
    return dict(row)


# ── Mail Folders ─────────────────────────────────────────────────────────────
@app.get("/api/mail-folders")
def get_mail_folders():
    with get_db() as db:
        folders = db.execute("SELECT f.*, COUNT(i.id) as count FROM mail_folders f LEFT JOIN inbox i ON i.folder_id=f.id GROUP BY f.id ORDER BY f.name").fetchall()
    return [dict(f) for f in folders]

@app.post("/api/mail-folders")
def create_mail_folder(body: dict):
    name = body.get("name","").strip()
    if not name: raise HTTPException(400,"Name erforderlich")
    with get_db() as db:
        db.execute("INSERT INTO mail_folders (name,color,icon,auto_rule,created_at) VALUES (?,?,?,?,?)",
            (name, body.get("color","#4a90d9"), body.get("icon","📁"), body.get("auto_rule",""), datetime.now(timezone.utc).isoformat()))
        db.commit()
    return {"ok": True}

@app.delete("/api/mail-folders/{fid}")
def delete_mail_folder(fid: int):
    with get_db() as db:
        db.execute("UPDATE inbox SET folder_id=NULL WHERE folder_id=?", (fid,))
        db.execute("DELETE FROM mail_folders WHERE id=?", (fid,))
        db.commit()
    return {"ok": True}

@app.patch("/api/mail-folders/{fid}")
def update_mail_folder(fid: int, body: dict):
    with get_db() as db:
        if "name" in body: db.execute("UPDATE mail_folders SET name=? WHERE id=?", (body["name"], fid))
        if "color" in body: db.execute("UPDATE mail_folders SET color=? WHERE id=?", (body["color"], fid))
        if "icon" in body: db.execute("UPDATE mail_folders SET icon=? WHERE id=?", (body["icon"], fid))
        if "auto_rule" in body: db.execute("UPDATE mail_folders SET auto_rule=? WHERE id=?", (body["auto_rule"], fid))
        db.commit()
    return {"ok": True}

@app.post("/api/inbox/{mail_id}/move/{folder_id}")
def move_mail_to_folder(mail_id: int, folder_id: int):
    with get_db() as db:
        db.execute("UPDATE inbox SET folder_id=? WHERE id=?", (folder_id, mail_id))
        db.commit()
    return {"ok": True}

@app.post("/api/inbox/{mail_id}/unfolder")
def remove_from_folder(mail_id: int):
    with get_db() as db:
        db.execute("UPDATE inbox SET folder_id=NULL WHERE id=?", (mail_id,))
        db.commit()
    return {"ok": True}

@app.post("/api/mail-folders/ai-sort")
def ai_sort_mails():
    """KI liest alle unsortierten Mails und erstellt/weist Ordner zu."""
    import json as _json
    with get_db() as db:
        unsorted = db.execute("""
            SELECT id, subject, body, from_addr, to_addr
            FROM inbox WHERE folder_id IS NULL
            ORDER BY id DESC LIMIT 50
        """).fetchall()
        folders = db.execute("SELECT id, name FROM mail_folders").fetchall()
        row = db.execute("SELECT value FROM settings WHERE key='gemini_key'").fetchone()
        api_key = row["value"] if row else ""

    if not api_key:
        return {"ok": False, "error": "Kein Gemini API-Key"}
    if not unsorted:
        return {"ok": True, "sorted": 0, "message": "Keine unsortierten Mails"}

    existing_folders = {f["name"]: f["id"] for f in folders}

    # Build prompt
    mails_summary = []
    for m in unsorted:
        body_preview = (m["body"] or "")[:200].replace("\n"," ")
        mails_summary.append({"id": m["id"], "subject": m["subject"] or "", "preview": body_preview})

    prompt = f"""Du bist ein E-Mail-Sortiersystem für Logitech-Support-Mails.
Analysiere diese Mails und weise jedem eine Kategorie zu.
Bestehende Ordner: {list(existing_folders.keys()) if existing_folders else "Keine"}.

Erstelle neue Ordner wenn nötig. Benenne sie nach: Produkt (z.B. "G923 Lenkrad", "MX Master 3") oder Ticket-Nummer oder Thema.

Mails:
{_json.dumps(mails_summary, ensure_ascii=False)}

Antworte NUR mit JSON (kein Markdown):
{{
  "assignments": [
    {{"mail_id": 1, "folder_name": "G923 Lenkrad"}},
    ...
  ]
}}"""

    try:
        import requests as _req
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={api_key}"
        r = _req.post(url, json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=30)
        if r.status_code != 200:
            return {"ok": False, "error": f"Gemini {r.status_code}"}
        raw = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        raw = raw.replace("```json","").replace("```","").strip()
        result = _json.loads(raw)
        assignments = result.get("assignments",[])
    except Exception as e:
        return {"ok": False, "error": str(e)}

    sorted_count = 0
    with get_db() as db:
        for a in assignments:
            mail_id = a.get("mail_id")
            folder_name = a.get("folder_name","").strip()
            if not mail_id or not folder_name: continue
            # Get or create folder
            if folder_name not in existing_folders:
                db.execute("INSERT INTO mail_folders (name,color,icon,created_at) VALUES (?,?,?,?)",
                    (folder_name, "#4a90d9", "📁", datetime.now(timezone.utc).isoformat()))
                db.commit()
                new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                existing_folders[folder_name] = new_id
            folder_id = existing_folders[folder_name]
            db.execute("UPDATE inbox SET folder_id=? WHERE id=?", (folder_id, mail_id))
            sorted_count += 1
        db.commit()

    return {"ok": True, "sorted": sorted_count, "folders_created": len([a for a in assignments if a.get("folder_name") not in {f["name"] for f in folders}])}

