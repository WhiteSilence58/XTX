// ── RMA ───────────────────────────────────────────────────────────────────────
async function loadRMA(){rmaD=await api('/api/dashboard/rma');renderRMA();}
function rmaFlt(f){
  rmaF2=rmaF2===f?'':f;
  ['positive','waiting','open','negative'].forEach(x=>{
    const el=$('rf'+x[0]);if(el)el.className='ff'+(rmaF2===x?' av':'');
  });
  renderRMA();
}
function renderRMA(){
  const s=($('rs')?.value||'').toLowerCase();let d=rmaD;
  if(rmaF2)d=d.filter(x=>(x.status||'open')===rmaF2);
  if(s)d=d.filter(x=>x.serial?.toLowerCase().includes(s)||x.name?.toLowerCase().includes(s)||x.email?.toLowerCase().includes(s));
  const el=$('rg');if(!el)return;
  if(!d.length){el.innerHTML='<div class="empty" style="grid-column:1/-1">Keine Einträge</div>';return;}
  el.innerHTML=d.map(r=>`<div class="rcard ${r.status||'open'}" onclick="openRMA(${r.id})">
    <div style="display:flex;justify-content:space-between;margin-bottom:7px">
      <div><div style="font-weight:600;font-size:13px">${escH(r.name||'—')}</div><div style="font-size:10px;color:var(--text2)">${escH(r.email||'')}</div></div>
      <span class="pill p${(r.status||'o')[0]}">${r.status||'offen'}</span>
    </div>
    <div style="font-size:11px;color:var(--text2);margin-bottom:6px">${escH(r.product||'—')} · <span class="mono">${escH(r.serial||'—')}</span></div>
    <div style="display:flex;gap:5px;flex-wrap:wrap">
      ${r.rma_number?`<span class="pill pb">RMA: ${escH(r.rma_number)}</span>`:''}
      ${r.tracking?'<span class="pill pb">📦</span>':''}
      ${r.value_eur?`<span class="vb">${r.value_eur}€</span>`:''}
      ${r.unread?`<span class="pill pn">${r.unread} neu</span>`:''}
    </div>
  </div>`).join('');
}
async function openRMA(id){
  const r=rmaD.find(x=>x.id===id);if(!r)return;
  let ts={status:'open'};try{ts=await api('/api/ticket-status/'+id);}catch(e){}
  $('pt').textContent='Ticket: '+(r.serial||'—');
  $('pb').innerHTML=`
    <div class="dr"><span class="k">Status</span><select id="rs2" style="width:auto">${['open','waiting','positive','negative','closed','archived'].map(s=>`<option value="${s}" ${(ts.status||'open')===s?'selected':''}>${s}</option>`).join('')}</select></div>
    <div class="dr"><span class="k">Sachbearbeiter</span><input id="ra" value="${escH(ts.agent_name||'')}" style="text-align:right"></div>
    <div class="dr"><span class="k">RMA-Nr.</span><input id="rr" value="${escH(ts.rma_number||'')}" class="mono" style="text-align:right"></div>
    <div class="dr"><span class="k">Tracking</span><input id="rt" value="${escH(ts.tracking||'')}" class="mono" style="text-align:right"></div>
    <div class="dr"><span class="k">Paketdienst</span><select id="rc" style="width:auto">${['','DHL','UPS','FedEx','Hermes','DPD'].map(c=>`<option ${ts.carrier===c?'selected':''}>${c}</option>`).join('')}</select></div>
    <div class="dr"><span class="k">Wert €</span><input id="rv" type="number" value="${ts.value_eur||0}" style="text-align:right"></div>
    <div class="divl"></div>
    <label class="fl">Notizen</label>
    <textarea id="rn" rows="3" style="margin-bottom:9px">${escH(ts.notes||'')}</textarea>
    <div class="gap">
      <button class="btn pr sm" onclick="saveRMA(${id})">Speichern</button>
      ${ts.tracking?`<button class="btn sm" onclick="openTk(${id})">📦 Tracking</button>`:''}
    </div>`;
  $('ov').style.display='flex';
}
async function saveRMA(id){
  await api('/api/ticket-status','POST',{reg_id:id,status:$('rs2').value,agent_name:$('ra').value,rma_number:$('rr').value,tracking:$('rt').value,carrier:$('rc').value,value_eur:parseFloat($('rv').value)||0,notes:$('rn').value});
  toast('Gespeichert','ok');loadRMA();
}
async function openTk(id){const r=await api('/api/tracking/'+id);if(r.url)window.open(r.url,'_blank');else toast('Kein Tracking','err');}
async function reprocessRMA(){toast('Analysiere...');const r=await api('/api/debug/force-reprocess','POST');toast(`${r.processed} verarbeitet, ${r.newly_assigned} zugeordnet`,'ok');loadRMA();}
async function showDebugInfo(){
  const d=await api('/api/debug/inbox-status');
  alert(['Inbox: '+d.inbox.total+' ('+d.inbox.with_reg+' mit Reg.)','mail_messages: '+d.mail_messages.total,'ticket_status: '+d.ticket_status.count,'Registrierungen: '+d.registrations.length,'','Registrierungen:',...d.registrations.map(r=>'  '+r.email+' ('+r.serial+')'),'','Inbox-Mails:',...d.inbox.sample.map(m=>'  [reg='+m.reg_id+'] '+m.subject)].join('\n'));
}

