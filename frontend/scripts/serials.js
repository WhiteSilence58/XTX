// ── Serials ───────────────────────────────────────────────────────────────────
function debounceSearch(){clearTimeout(sDebounce);sDebounce=setTimeout(()=>loadSerials(1),350);}
function toggleFilter(f){aF=aF===f?'':f;$('fv').className='ff'+(aF==='valid'?' av':'');$('fr').className='ff'+(aF==='registered'?' ar':'');loadSerials(1);}
async function loadSerials(page=1){
  sCurPage=page;
  const search=($('ss')?.value||'').trim();
  const params=new URLSearchParams({page,limit:50});
  if(aF)params.set('status',aF);
  if(search)params.set('search',search);
  const tb=$('stb');
  tb.innerHTML='<tr><td colspan="8" style="text-align:center;padding:20px"><span class="spin"></span></td></tr>';
  const data=await api('/api/serials?'+params);
  const items=Array.isArray(data)?data:(data.items||[]);
  const total=Array.isArray(data)?items.length:(data.total||0);
  sTotalPages=Array.isArray(data)?1:(data.pages||1);
  aS=items;
  renderSerialsTable(items);
  renderPagination(page,sTotalPages,total);
}
function renderSerialsTable(items){
  const tb=$('stb');
  if(!items.length){tb.innerHTML='<tr><td colspan="8" class="empty">Keine Einträge</td></tr>';return;}
  tb.innerHTML=items.map(s=>{
    const age=s.manufacture_date?Math.floor((Date.now()-new Date(s.manufacture_date))/(365.25*86400000)):null;
    const ageStr=age!==null?`<span style="font-size:9px;color:var(--text3);display:block">${age}J alt</span>`:'';
    return`<tr onclick="openSerial('${s.serial}')" style="cursor:pointer">
      <td><span class="mono" style="font-weight:600">${s.serial}</span>${ageStr}</td>
      <td>${sp(s.status)}</td>
      <td><div style="font-size:12px;font-weight:500;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${s.product||'—'}</div>${s.product_type?`<div style="font-size:10px;color:var(--text2);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${s.product_type}</div>`:''}</td>
      <td id="vv-${(s.part_number||'x').replace(/[^a-z0-9]/gi,'_')}" style="font-size:10px">—</td>
      <td>${wp(s.warranty_status)}${s.warranty_end?`<div style="font-size:9px;color:var(--text3);margin-top:1px">${s.warranty_end.substring(0,10)}</div>`:''}</td>
      <td id="tt-${s.serial}" style="font-size:10px;color:var(--text2)"></td>
      <td style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text2);font-size:11px">${s.note||''}</td>
      <td><button class="btn xs" onclick="event.stopPropagation();openSerial('${s.serial}')">›</button></td>
    </tr>`;
  }).join('');
  items.forEach(async s=>{
    if(s.part_number){try{const v=await api('/api/product-values/'+s.part_number);const el=$('vv-'+(s.part_number||'x').replace(/[^a-z0-9]/gi,'_'));if(el)el.innerHTML=v.val_min?`<span class="vb">${v.val_min}–${v.val_max}€</span>`:'—';}catch(e){}}
    try{const tags=await api('/api/tags/'+s.serial);const el=$('tt-'+s.serial);if(el&&tags.length)el.innerHTML=tags.slice(0,2).map(t=>`<span class="tc sel" style="padding:1px 5px;font-size:10px">${escH(t)}</span>`).join('');}catch(e){}
  });
}
function renderPagination(page,pages,total){
  $('pag-info').textContent=total.toLocaleString('de')+' Einträge';
  if(pages<=1){$('pag-btns').innerHTML='';return;}
  let btns=`<button class="btn xs" onclick="loadSerials(${page-1})" ${page<=1?'disabled':''} style="min-width:28px">‹</button>`;
  let start=Math.max(1,page-3),end=Math.min(pages,start+6);start=Math.max(1,end-6);
  if(start>1)btns+=`<button class="btn xs" onclick="loadSerials(1)">1</button><span style="padding:0 4px;color:var(--text3)">…</span>`;
  for(let p=start;p<=end;p++)btns+=`<button class="btn xs${p===page?' pr':''}" onclick="loadSerials(${p})">${p}</button>`;
  if(end<pages)btns+=`<span style="padding:0 4px;color:var(--text3)">…</span><button class="btn xs" onclick="loadSerials(${pages})">${pages}</button>`;
  btns+=`<button class="btn xs" onclick="loadSerials(${page+1})" ${page>=pages?'disabled':''}>›</button>`;
  $('pag-btns').innerHTML=btns;
}
async function openSerial(serial){
  $('pt').textContent=serial;$('pb').innerHTML='<div style="text-align:center;padding:30px"><span class="spin"></span></div>';$('ov').style.display='flex';
  let detail;
  try{detail=await api('/api/serial-detail/'+serial);}
  catch(e){const cached=aS.find(x=>x.serial===serial);if(!cached){$('pb').innerHTML='<div class="empty">Nicht gefunden</div>';return;}detail={serial:cached,tags:[],all_tags:["Lager A","Lager B","verkauft","defekt","in Bearbeitung","RMA","archiviert","wertvoll"],pv:{},identities:[]};}
  const s=detail.serial,tags=detail.tags,allTags=detail.all_tags,pv=detail.pv,idents=detail.identities;
  $('pb').innerHTML=`
    <div class="dr"><span class="k">Status</span><span class="v">${sp(s.status)}</span></div>
    <div class="dr"><span class="k">Produkt</span><span class="v">${escH(s.product||'—')}</span></div>
    <div class="dr"><span class="k">Typ</span><span class="v">${escH(s.product_type||'—')}</span></div>
    <div class="dr"><span class="k">Teilenummer</span><span class="v mono">${s.part_number||'—'}</span></div>
    <div class="dr"><span class="k">Hergestellt</span><span class="v">${s.manufacture_date||'—'}</span></div>
    <div class="dr"><span class="k">Garantie bis</span><span class="v">${s.warranty_end||'—'} ${wp(s.warranty_status)}</span></div>
    ${pv.val_min?`<div class="dr"><span class="k">Marktwert</span><span class="v" style="color:var(--green)">${pv.val_min}–${pv.val_max}€</span></div>`:''}
    <div class="divl"></div><div class="sl2">Tags</div>
    <div style="padding:4px 0 8px" id="tch">${allTags.map(t=>`<span class="tc${tags.includes(t)?' sel':''}" onclick="tTag('${serial.replace(/'/g,"\\'")}','${t.replace(/'/g,"\\'")}',this)">${escH(t)}</span>`).join('')}<span class="tc" onclick="cTag('${serial.replace(/'/g,"\\'")}')">+ Neu</span></div>
    <div class="divl"></div>
    <label class="fl">Notiz</label><textarea id="dn" style="margin-bottom:8px;height:55px">${escH(s.note||'')}</textarea>
    ${s.status==='valid'?`
    <div class="divl"></div><div class="sl2">Ticket / Registrierung</div>
    <div class="g2" style="margin-bottom:7px"><div><label class="fl">Vorname</label><input id="df"></div><div><label class="fl">Nachname</label><input id="dl"></div></div>
    <div style="margin-bottom:7px"><label class="fl">E-Mail (leer=auto)</label><input id="de"></div>
    <div style="margin-bottom:7px"><label class="fl">Land</label><select id="dcountry"><option value="de">🇩🇪 Deutschland</option><option value="us">🇺🇸 USA</option><option value="gb">🇬🇧 UK</option></select></div>
    <div style="margin-bottom:9px"><label class="fl">Profil</label><select id="dip" onchange="applyId()"><option value="">— Manuell —</option>${idents.map(id=>`<option value="${id.id}" data-f="${escH(id.first_name)}" data-l="${escH(id.last_name)}" data-e="${id.first_name.toLowerCase()}.${id.last_name.toLowerCase()}@${id.domain}" data-c="${id.country||'de'}">${escH(id.first_name)} ${escH(id.last_name)} (${escH(id.domain)})</option>`).join('')}</select></div>
    <div class="gap"><button class="btn su sm" onclick="rS('${serial.replace(/'/g,"\\'")}','register')">Registrieren</button><button class="btn sm" style="background:var(--blue-bg);color:var(--blue)" onclick="rS('${serial.replace(/'/g,"\\'")}','ticket')">Ticket</button><button class="btn sm" style="background:var(--amber-bg);color:var(--amber)" onclick="rS('${serial.replace(/'/g,"\\'")}','both')">Beides</button></div>
    <div id="ro" style="margin-top:8px"></div>`:''}
    <div class="divl"></div>
    <div class="gap"><button class="btn pr sm" onclick="savNote('${serial.replace(/'/g,"\\'")}')">Notiz speichern</button><button class="btn da sm" onclick="delS('${serial.replace(/'/g,"\\'")}')">Löschen</button></div>`;
}
window.applyId=function(){const o=$('dip')?.selectedOptions[0];if(!o?.dataset.f)return;$('df').value=o.dataset.f;$('dl').value=o.dataset.l;$('de').value=o.dataset.e;if($('dcountry')&&o.dataset.c)$('dcountry').value=o.dataset.c;};
async function tTag(serial,tag,el){el.classList.toggle('sel');const chips=document.querySelectorAll('#tch .tc.sel');const tags=[...chips].map(c=>c.textContent.trim()).filter(t=>t!=='+ Neu');await api('/api/tags/'+serial,'POST',{tags});}
async function cTag(serial){const t=prompt('Tag:');if(!t)return;const tags=await api('/api/tags/'+serial);await api('/api/tags/'+serial,'POST',{tags:[...tags,t]});openSerial(serial);}
async function savNote(serial){const note=$('dn').value;await api('/api/serials/'+serial+'/note','PATCH',{note});const s=aS.find(x=>x.serial===serial);if(s)s.note=note;toast('Gespeichert','ok');}
async function delS(serial){if(!confirm(serial+' löschen?'))return;await api('/api/serials/'+serial,'DELETE');aS=aS.filter(x=>x.serial!==serial);closeP();loadSerials(sCurPage);loadDash();toast('Gelöscht');}

async function openRegisterCompose(serial, mode){
  const first = ($('df')?.value || '').trim();
  const last = ($('dl')?.value || '').trim();
  const email = ($('de')?.value || '').trim();
  const country = ($('dcountry')?.value) || 'de';
  const domain = (await api('/api/settings')).email_domain || '';
  if(!first || !last){toast('Vor- und Nachname eingeben','err');return;}

  const out = $('ro');
  if(out) out.innerHTML = '<span class="spin"></span>';

  let prep;
  try{
    prep = await api('/api/register/prepare','POST',{
      serial, domain, mode,
      custom_first:first,
      custom_last:last,
      custom_email:email,
      country
    });
  }catch(e){
    if(out) out.innerHTML = `<div style="color:var(--red);font-size:11px;padding:7px;background:var(--red-bg);border-radius:var(--radius-sm)">${escH(e.message || 'Vorbereitung fehlgeschlagen')}</div>`;
    return;
  }

  if(out) out.innerHTML = '';

  const ov=document.createElement('div');
  ov.id='serial-register-overlay';
  ov.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.45);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);z-index:450;display:flex;align-items:center;justify-content:center;padding:20px';
  ov.onclick=function(e){if(e.target===ov)closeSerialRegisterCompose();};

  const panel=document.createElement('div');
  panel.style.cssText='background:var(--surface);border-radius:var(--radius);width:100%;max-width:700px;max-height:92vh;overflow-y:auto;box-shadow:var(--shadow-lg)';
  panel.innerHTML=`
    <div style="padding:14px 18px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">
      <h2 style="font-size:15px;font-weight:700">Mail vor dem Senden bearbeiten</h2>
      <button class="btn xs" onclick="closeSerialRegisterCompose()">✕</button>
    </div>
    <div style="padding:16px 18px;display:flex;flex-direction:column;gap:10px">
      <div style="display:flex;gap:8px;align-items:center"><label style="font-size:11px;color:var(--text2);width:68px;flex-shrink:0">Modus</label><input value="${escH(mode)}" readonly></div>
      <div style="display:flex;gap:8px;align-items:center"><label style="font-size:11px;color:var(--text2);width:68px;flex-shrink:0">Profil</label><input value="${escH(prep.name)} · ${escH(prep.email)}" readonly></div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <label style="font-size:11px;color:var(--text2);width:68px;flex-shrink:0">Vorlage</label>
        <select id="src-tpl" onchange="applySerialRegTpl()" style="flex:1;min-width:150px;font-size:11px"><option value="">— Vorlage —</option></select>
        <button class="btn xs" id="src-ki-btn" onclick="genSerialRegAi()">✦ KI</button>
        <span id="src-ki-spin" style="display:none"><span class="spin"></span></span>
      </div>
      <input id="src-subject" value="${escH(prep.subject || '')}" placeholder="Betreff..." style="font-size:13px">
      <textarea id="src-body" rows="10" placeholder="Mailtext..." style="resize:vertical;font-size:13px;line-height:1.5">${escH(prep.body || '')}</textarea>
      <div style="display:flex;gap:8px;justify-content:space-between;align-items:center">
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <button class="btn pr sm" id="src-send-btn" onclick="sendSerialRegisterCompose()">📤 Senden</button>
          <button class="btn sm" onclick="closeSerialRegisterCompose()">Abbrechen</button>
        </div>
        <div id="src-result" style="font-size:11px"></div>
      </div>
    </div>`;
  ov.appendChild(panel);
  document.body.appendChild(ov);

  window._serialRegDraft = {
    serial, mode, country,
    first, last, email, domain,
    prep
  };

  loadSerialRegTpls();
}

function closeSerialRegisterCompose(){
  const ov=document.getElementById('serial-register-overlay');
  if(ov) ov.remove();
}

async function loadSerialRegTpls(){
  try{
    const ts = await api('/api/templates');
    const sel = $('src-tpl');
    if(!sel) return;
    sel.innerHTML = '<option value="">— Vorlage —</option>' +
      ts.map(t=>`<option value="${t.id}" data-s="${escH(t.subject)}" data-b="${escH(t.body)}">${escH(t.name)}</option>`).join('');
  }catch(e){}
}

function applySerialRegTpl(){
  const o = $('src-tpl')?.selectedOptions[0];
  if(!o?.dataset.s) return;
  if($('src-subject')) $('src-subject').value = o.dataset.s;
  if($('src-body')) $('src-body').value = o.dataset.b;
}

async function genSerialRegAi(){
  const d = window._serialRegDraft;
  if(!d) return;
  const btn = $('src-ki-btn'), spin = $('src-ki-spin');
  if(btn) btn.style.display='none';
  if(spin) spin.style.display='';
  try{
    const res = await api('/api/mail/generate-free','POST',{
      product: d.prep?.product || 'Logitech Gerät',
      sender_name: d.prep?.name || (d.first + ' ' + d.last),
      lang: d.country === 'de' || d.country === 'at' || d.country === 'ch' ? 'de' : 'en'
    });
    if(res.ok){
      if($('src-subject')) $('src-subject').value = res.subject || '';
      if($('src-body')) $('src-body').value = res.body || '';
      toast('KI-Text generiert','ok');
    } else toast('Fehler: ' + (res.error || '?'),'err');
  }finally{
    if(btn) btn.style.display='';
    if(spin) spin.style.display='none';
  }
}

async function sendSerialRegisterCompose(){
  const d = window._serialRegDraft;
  if(!d) return;
  const btn = $('src-send-btn'), result = $('src-result');
  const subject = ($('src-subject')?.value || '').trim();
  const body = ($('src-body')?.value || '').trim();
  if(!subject || !body){toast('Betreff und Text eingeben','err');return;}
  if(btn){btn.disabled=true;btn.textContent='⏳ Wird gesendet...';}
  if(result) result.innerHTML = '<span class="spin"></span>';
  try{
    const res = await api('/api/register','POST',{
      serial: d.serial,
      domain: d.domain,
      mode: d.mode,
      custom_first: d.first,
      custom_last: d.last,
      custom_email: d.email,
      country: d.country,
      custom_subject: subject,
      custom_body: body
    });

    if(res.error || res.detail){
      if(result) result.innerHTML = `<div style="color:var(--red)">${escH(res.error || res.detail)}</div>`;
      return;
    }

    if(result) result.innerHTML = `<div style="color:var(--green)">✓ Gesendet / verarbeitet</div>`;
    const out = $('ro');
    if(out) out.innerHTML = `<div style="font-size:11px;padding:9px;background:var(--green-bg);border-radius:var(--radius-sm)"><div style="font-weight:700;color:var(--green);margin-bottom:4px">Erfolgreich ✓</div><div>E-Mail: <strong>${escH(res.email||'')}</strong></div>${res.registration?.ok?'<div style="color:var(--green)">✓ Registriert</div>':''}${res.registration?.already_registered?'<div style="color:var(--amber)">Bereits registriert</div>':''}${res.registration?.error?`<div style="color:var(--red)">${escH(res.registration.error)}</div>`:''}${res.ticket?.ok?`<div style="color:var(--blue)">✓ Ticket #${res.ticket.ticket_id}</div>`:''}${res.ticket?.error?`<div style="color:var(--red)">${escH(res.ticket.error)}</div>`:''}</div>`;
    toast('Vorgang abgeschlossen','ok');
    closeSerialRegisterCompose();
    loadDash();
    loadSerials(sCurPage);
  }catch(e){
    if(result) result.innerHTML = `<div style="color:var(--red)">${escH(e.message || 'Fehler')}</div>`;
  }finally{
    if(btn){btn.disabled=false;btn.textContent='📤 Senden';}
  }
}

async function rS(serial,mode){
  const first=($('df')?.value||'').trim(),last=($('dl')?.value||'').trim(),email=($('de')?.value||'').trim(),country=($('dcountry')?.value)||'de';
  const domain=(await api('/api/settings')).email_domain||'';
  if(!first||!last){toast('Vor- und Nachname eingeben','err');return;}
  const out=$('ro');out.innerHTML='<span class="spin"></span>';

  if(mode === 'register'){
    const res=await api('/api/register','POST',{serial,domain,mode,custom_first:first,custom_last:last,custom_email:email,country});
    out.innerHTML=res.error||res.detail?`<div style="color:var(--red);font-size:11px;padding:7px;background:var(--red-bg);border-radius:var(--radius-sm)">${escH(res.error||res.detail)}</div>`:`<div style="font-size:11px;padding:9px;background:var(--green-bg);border-radius:var(--radius-sm)"><div style="font-weight:700;color:var(--green);margin-bottom:4px">Erfolgreich ✓</div><div>E-Mail: <strong>${escH(res.email||'')}</strong></div>${res.registration?.ok?'<div style="color:var(--green)">✓ Registriert</div>':''}${res.registration?.already_registered?'<div style="color:var(--amber)">Bereits registriert</div>':''}${res.registration?.error?`<div style="color:var(--red)">${escH(res.registration.error)}</div>`:''}</div>`;
    loadDash();loadSerials(sCurPage);
    return;
  }

  out.innerHTML='';
  await openRegisterCompose(serial, mode);
}


