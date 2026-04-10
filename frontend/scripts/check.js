// ── Quick Check ───────────────────────────────────────────────────────────────
async function qCheck(){
  const serial = ($('qs')?.value || '').trim().toUpperCase();
  const note   = ($('qn')?.value || '');

  if(!serial){
    toast('Seriennummer eingeben','err');
    return;
  }

  const el = $('qr');
  if(el) el.innerHTML = '<span class="spin"></span>';

  let res;
  try{
    res = await api('/api/check','POST',{ serial, note });
  }catch(e){
    if(el){
      el.innerHTML = `
        <div style="background:var(--red-bg);border-radius:var(--radius-sm);padding:11px;font-size:12px;color:var(--red)">
          <div style="font-weight:700;margin-bottom:4px">Fehler</div>
          <div>${escH(e.message || 'Anfrage fehlgeschlagen')}</div>
        </div>
      `;
    }
    return;
  }

  if(!el) return;

  if(res.status === 'valid'){
    el.innerHTML = `
      <div style="background:var(--green-bg);border-radius:var(--radius-sm);padding:11px;font-size:12px">
        <div style="font-weight:700;color:var(--green);margin-bottom:4px">Gültig ✓</div>
        <div>${escH(res.product || '—')}</div>
        <div class="mono" style="color:var(--text2)">${escH(res.part_number || '')}</div>
        <div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;align-items:center">
          ${wp(res.warranty_status)}
          ${res.warranty_end ? `<span>${escH(res.warranty_end)}</span>` : ''}
        </div>
      </div>
    `;
  }
  else if(res.status === 'registered'){
    el.innerHTML = `
      <div style="background:var(--amber-bg);border-radius:var(--radius-sm);padding:11px;color:var(--amber);font-size:12px">
        <div style="font-weight:700;margin-bottom:4px">Bereits registriert</div>
        <div>Diese Seriennummer ist schon registriert.</div>
      </div>
    `;
  }
  else if(res.status === 'rate_limited'){
    el.innerHTML = `
      <div style="background:var(--amber-bg);border-radius:var(--radius-sm);padding:11px;font-size:12px;color:var(--amber)">
        <div style="font-weight:700;margin-bottom:4px">Zu viele Anfragen</div>
        <div>${escH(res.note || 'Bitte kurz warten und erneut versuchen.')}</div>
      </div>
    `;
  }
  else if(res.status === 'error'){
    el.innerHTML = `
      <div style="background:var(--red-bg);border-radius:var(--radius-sm);padding:11px;font-size:12px;color:var(--red)">
        <div style="font-weight:700;margin-bottom:4px">Prüfung fehlgeschlagen</div>
        <div>${escH(res.note || 'Unbekannter Fehler')}</div>
      </div>
    `;
  }
  else {
    el.innerHTML = `
      <div style="background:var(--surface2);border-radius:var(--radius-sm);padding:11px;color:var(--text2);font-size:12px">
        <div style="font-weight:700;margin-bottom:4px">Ungültig</div>
        <div>${escH(res.note || 'Keine gültigen Produktdaten gefunden.')}</div>
      </div>
    `;
  }

  loadDash();
}