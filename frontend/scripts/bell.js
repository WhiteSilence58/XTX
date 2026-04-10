// ── Bell ──────────────────────────────────────────────────────────────────────
async function updateBell(){
  try{
    const r=await api('/api/inbox/unread-count');const c=r.count||0;
    const bc=$('bell-count');bc.style.display=c>0?'':'none';bc.textContent=c>9?'9+':c;
    // Sidebar badge
    const sb=$('sb-bell-count');
    if(sb){sb.style.display=c>0?'':'none';sb.textContent=c>9?'9+':c;}
  }catch(e){}
}
function toggleBell(){bellOpen?closeBell():openBell();}
function closeBell(){bellOpen=false;$('np').style.display='none';}
async function openBell(){
  bellOpen=true;$('np').style.display='block';
  try{const mails=await api('/api/inbox?limit=15&unread_only=true');
  const el=$('np-list');
  if(!mails.length){el.innerHTML='<div class="empty" style="padding:20px">Keine ungelesenen Mails</div>';return;}
  el.innerHTML=mails.map(m=>`<div class="ni${!m.read_at?' unread':''}" onclick="jumpToMail(${m.id})">
    <div style="font-size:11px;font-weight:600;display:flex;justify-content:space-between"><span>${escH(shortFrom(m.from_addr))}</span><span style="color:var(--text3);font-weight:400">${fmtS(m.received_at)}</span></div>
    <div style="font-size:11px;color:var(--text2)">${escH(m.subject||'(kein Betreff)')}</div>
    ${m.reg_name?`<div style="font-size:10px;color:var(--blue)">→ ${escH(m.reg_name)}</div>`:''}
  </div>`).join('');}catch(e){$('np-list').innerHTML='<div class="empty" style="padding:20px">Fehler</div>';}
}
async function jumpToMail(id){closeBell();go('inbox');await loadInbox();openMail(id);}
async function markAllRead(){await api('/api/inbox/read-all','POST');toast('Alle gelesen','ok');inboxD.forEach(m=>m.read_at=new Date().toISOString());renderInbox();updateBell();}
document.addEventListener('click',e=>{if(bellOpen&&!$('np').contains(e.target)&&!$('bell-btn').contains(e.target))closeBell();});

