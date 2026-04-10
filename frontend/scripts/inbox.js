// ── Inbox ─────────────────────────────────────────────────────────────────────
// ── Inbox Toolbar ─────────────────────────────────────────────────────────────
function renderInboxToolbar(){
  const tb=$('inbox-toolbar');
  if(!tb)return;

  const folders=window._folders||[];
  const sortVal=$('isort')?$('isort').value:'date';
  const folderVal=$('ifolder')?$('ifolder').value:'';

  tb.innerHTML=`
    <div style="display:flex;flex-direction:column;gap:6px;padding:8px 12px;background:var(--surface);border-bottom:1px solid var(--border)">

      <!-- Zeile 1: Filter-Pills -->
      <div style="display:flex;gap:5px;align-items:center;flex-wrap:wrap">
        <button id="iunread" class="ff${inboxUnread?' av':''}" onclick="toggleUnread()"
          style="display:flex;align-items:center;gap:4px;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;border:1px solid var(--border);background:${inboxUnread?'var(--blue)':'var(--surface2)'};color:${inboxUnread?'#fff':'var(--text2)'};cursor:pointer;transition:.15s">
          <span style="width:6px;height:6px;border-radius:50%;background:${inboxUnread?'#fff':'var(--blue)'}"></span> Ungelesen
        </button>
        <button id="istarred" class="ff${inboxStarred?' av':''}" onclick="toggleStarred()"
          style="display:flex;align-items:center;gap:4px;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;border:1px solid var(--border);background:${inboxStarred?'var(--amber)':'var(--surface2)'};color:${inboxStarred?'#fff':'var(--text2)'};cursor:pointer;transition:.15s">
          <span style="font-size:10px">${inboxStarred?'★':'☆'}</span> Markiert
        </button>
        <button id="ilogitech" class="ff${inboxLogitech?' av':''}" onclick="toggleLogitech()"
          style="display:flex;align-items:center;gap:4px;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;border:1px solid var(--border);background:${inboxLogitech?'var(--surface3)':'var(--surface2)'};color:${inboxLogitech?'var(--text)':'var(--text2)'};cursor:pointer;transition:.15s">
          🖱 Logi
        </button>
        <div style="flex:1"></div>
        <button onclick="showFolderManager()" style="padding:4px 10px;border-radius:20px;font-size:11px;border:1px solid var(--border);background:var(--surface2);color:var(--text2);cursor:pointer">
          ＋ Ordner
        </button>
      </div>

      <!-- Zeile 2: Ordner-Tabs + Sortierung -->
      <div style="display:flex;gap:5px;align-items:center">
        <!-- Ordner als scrollbare Pill-Leiste -->
        <div style="display:flex;gap:4px;flex:1;overflow-x:auto;padding-bottom:2px;scrollbar-width:none">
          <button onclick="setFolderFilter('')"
            style="white-space:nowrap;padding:3px 11px;border-radius:20px;font-size:11px;font-weight:600;border:1px solid ${!folderVal?'var(--blue)':'var(--border)'};background:${!folderVal?'var(--blue-bg)':'var(--surface2)'};color:${!folderVal?'var(--blue)':'var(--text2)'};cursor:pointer;transition:.12s;flex-shrink:0">
            Alle
          </button>
          <button onclick="setFolderFilter('__none__')"
            style="white-space:nowrap;padding:3px 11px;border-radius:20px;font-size:11px;font-weight:600;border:1px solid ${'__none__'===folderVal?'var(--blue)':'var(--border)'};background:${'__none__'===folderVal?'var(--blue-bg)':'var(--surface2)'};color:${'__none__'===folderVal?'var(--blue)':'var(--text2)'};cursor:pointer;transition:.12s;flex-shrink:0">
            Kein Ordner
          </button>
          ${folders.map(f=>`
            <button onclick="setFolderFilter('${f.id}')"
              style="white-space:nowrap;padding:3px 11px;border-radius:20px;font-size:11px;font-weight:600;border:1px solid ${String(f.id)===String(folderVal)?'var(--blue)':'var(--border)'};background:${String(f.id)===String(folderVal)?'var(--blue-bg)':'var(--surface2)'};color:${String(f.id)===String(folderVal)?'var(--blue)':'var(--text2)'};cursor:pointer;transition:.12s;flex-shrink:0">
              ${escH(f.name)}
            </button>`).join('')}
        </div>

        <!-- Sortierung kompakt -->
        <select id="isort" onchange="renderInbox()" style="flex-shrink:0;padding:3px 8px;border-radius:20px;font-size:11px;border:1px solid var(--border);background:var(--surface2);color:var(--text2);cursor:pointer">
          <option value="date" ${sortVal==='date'?'selected':''}>↓ Datum</option>
          <option value="unread" ${sortVal==='unread'?'selected':''}>● Ungelesen</option>
          <option value="sender" ${sortVal==='sender'?'selected':''}>A–Z Sender</option>
          <option value="ticket" ${sortVal==='ticket'?'selected':''}>🎫 Ticket</option>
        </select>
      </div>

    </div>`;

  // Verstecktes select für Kompatibilität (filterByFolder() nutzt #ifolder)
  if(!$('ifolder')){
    const hidden=document.createElement('select');
    hidden.id='ifolder';hidden.style.display='none';
    document.body.appendChild(hidden);
  }
  // Sync hidden select value
  const hid=$('ifolder');
  if(hid){hid.value=folderVal;}
}

function setFolderFilter(val){
  inboxFolder=val;
  // Sync hidden select
  const hid=$('ifolder');if(hid)hid.value=val;
  renderInbox();
  renderInboxToolbar();
}

async function loadInbox(){
  try{inboxD=await api('/api/inbox?limit=300');renderInbox();renderInboxToolbar();}
  catch(e){$('inbox-list').innerHTML='<div class="empty">Fehler beim Laden</div>';}
}function toggleUnread(){inboxUnread=!inboxUnread;renderInbox();renderInboxToolbar();}
function toggleStarred(){inboxStarred=!inboxStarred;renderInbox();renderInboxToolbar();}
let inboxLogitech=false, inboxFolder='';
function toggleLogitech(){inboxLogitech=!inboxLogitech;renderInbox();renderInboxToolbar();}
function filterByFolder(){inboxFolder=$('ifolder')?.value||'';renderInbox();}

async function loadFolders(){
  try{
    const folders=await api('/api/mail-folders');
    window._folders=folders;
    // Auch hidden select aktuell halten (Kompatibilität)
    const sel=$('ifolder');
    if(sel){
      const iE=k=>(window._iconMap&&window._iconMap[k])||k||'';
      const unreadByFolder={};
      (window.inboxD||[]).forEach(m=>{
        if(!m.read_at&&m.folder_id) unreadByFolder[m.folder_id]=(unreadByFolder[m.folder_id]||0)+1;
      });
      sel.innerHTML='<option value="">Alle Ordner</option>'+
          '<option value="__none__">Kein Ordner</option>'+
          folders.map(f=>{
            const u=unreadByFolder[f.id]||0;
            return `<option value="${f.id}">${escH(f.name)}${u>0?` (${u})`:''}</option>`;
          }).join('');
    }
    renderInboxToolbar();
  }catch(e){}
}

async function aiSortMails(){
  toast('KI analysiert Mails...','ok');
  const btn=document.querySelector('[onclick="aiSortMails()"]');
  if(btn){btn.disabled=true;btn.textContent='⏳ Sortiere...';}
  const res=await api('/api/mail-folders/ai-sort','POST');
  if(btn){btn.disabled=false;btn.textContent='✦ KI-Sort';}
  if(res.ok){
    toast(`${res.sorted} Mails sortiert in Ordner`,'ok');
    await loadFolders();
    await loadInbox();
  } else toast('Fehler: '+(res.error||'?'),'err');
}

function showFolderManager(){
  $('pt').textContent='Ordner verwalten';
  const folders=window._folders||[];

  // Icon-Map: ASCII-Key → Emoji für Anzeige (Emoji nie im JSON)
  const ICONS=[
    {k:'folder',e:'📁'},{k:'inbox',e:'📬'},{k:'star',e:'⭐'},{k:'tag',e:'🏷️'},
    {k:'tool',e:'🔧'},{k:'ship',e:'📦'},{k:'question',e:'❓'},{k:'check',e:'✅'},
    {k:'clock',e:'⏳'},{k:'alert',e:'⚠️'},{k:'gamepad',e:'🎮'},{k:'mouse',e:'🖱️'},
  ];
  // Icon-Emoji aus Key holen (für Anzeige der gespeicherten Ordner)
  window._iconMap=Object.fromEntries(ICONS.map(i=>[i.k,i.e]));
  function iconEmoji(k){ return window._iconMap[k]||k||'📁'; }

  $('pb').innerHTML=`
    <div style="display:grid;gap:14px">
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:14px;padding:14px">
        <div style="font-size:11px;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px">➕ Neuer Ordner</div>

        <div style="margin-bottom:8px">
          <div style="font-size:10px;color:var(--text3);margin-bottom:5px">Icon wählen</div>
          <div id="folder-icon-picker" style="display:flex;flex-wrap:wrap;gap:5px">
            ${ICONS.map((ic,i)=>`<button
              data-icon="${ic.k}"
              onclick="document.querySelectorAll('#folder-icon-picker button').forEach(b=>b.className='btn xs');this.className='btn xs icon-active pr'"
              class="btn xs${i===0?' icon-active pr':''}"
              style="font-size:15px;padding:5px 8px">${ic.e}</button>`).join('')}
          </div>
        </div>

        <input id="new-folder-name" placeholder="Ordnername z.B. G923 Lenkrad" style="width:100%;padding:8px 12px;border-radius:10px;border:1px solid var(--border);background:var(--surface);margin-bottom:8px">
        <input id="new-folder-rule" placeholder="Auto-Regel (optional) — z.B. g923, logitech, ups" style="width:100%;padding:8px 12px;border-radius:10px;border:1px solid var(--border);background:var(--surface);font-size:12px;margin-bottom:10px">

        <div style="display:flex;gap:8px">
          <button class="btn pr sm" onclick="createFolder()" style="flex:1">+ Ordner erstellen</button>
          <button class="btn sm" onclick="loadFolders().then(()=>showFolderManager())">↻</button>
        </div>
      </div>

      <div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;overflow:hidden">
        <div style="padding:10px 14px;font-size:11px;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border);background:var(--surface2)">
          📁 Vorhandene Ordner (${folders.length})
        </div>
        ${folders.length?`<div>${folders.map((f,i)=>`
          <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;${i>0?'border-top:1px solid var(--border)':''}">
            <span style="font-size:18px;width:28px;text-align:center;flex-shrink:0">${iconEmoji(f.icon)}</span>
            <div style="flex:1;min-width:0">
              <div style="font-size:12px;font-weight:600">${escH(f.name)}</div>
              <div style="font-size:10px;color:var(--text3)">${f.count||0} Mails${f.auto_rule?' · '+escH(f.auto_rule):''}</div>
            </div>
            <button class="btn xs da" onclick="deleteFolderById(${f.id},'${escH(f.name)}')" title="Löschen">🗑</button>
          </div>`).join('')}</div>`
      :'<div class="empty" style="padding:24px">Noch keine Ordner</div>'}
      </div>
    </div>`;
  $('ov').style.display='flex';
}

async function createFolder(){
  const name=($('new-folder-name')?.value||'').trim();
  const rule=($('new-folder-rule')?.value||'').trim()||'';
  const iconEl=document.querySelector('#folder-icon-picker .icon-active');
  const icon=iconEl?iconEl.dataset.icon:'folder';
  if(!name){toast('Name eingeben','err');$('new-folder-name')?.focus();return;}

  // Nur plain ASCII/Text im Payload — kein Emoji
  const payload={name:name, icon:icon, auto_rule:rule};
  console.log('[createFolder] payload:', JSON.stringify(payload));

  let res;
  try{
    res=await api('/api/mail-folders','POST',payload);
    console.log('[createFolder] response:', res);
  }catch(e){
    console.error('[createFolder] fetch error:', e);
    toast('Netzwerkfehler: '+e.message,'err');
    return;
  }

  // Erfolg: id vorhanden oder kein explizites ok:false
  if(res && res.id){
    toast('Ordner "'+name+'" erstellt ✓','ok');
    if($('new-folder-name'))$('new-folder-name').value='';
    if($('new-folder-rule'))$('new-folder-rule').value='';
    await loadFolders();await loadInbox();showFolderManager();
    return;
  }

  // Fehlerdetails aus Response extrahieren und anzeigen
  const errMsg = res?.detail
      || (Array.isArray(res?.detail) ? res.detail.map(d=>d.msg||JSON.stringify(d)).join(', ') : null)
      || res?.error
      || res?.message
      || JSON.stringify(res);
  console.error('[createFolder] API error:', errMsg, res);
  toast('Fehler: '+errMsg,'err');
}

async function deleteFolderById(id,name){
  if(!confirm('Ordner "'+name+'" löschen? Mails bleiben erhalten.'))return;
  await api('/api/mail-folders/'+id,'DELETE');
  toast('Gelöscht','ok');
  closeP();await loadFolders();await loadInbox();
}

async function moveMailToFolder(mailId, folderId){
  if(folderId){await api('/api/inbox/'+mailId+'/move/'+folderId,'POST');}
  else{await api('/api/inbox/'+mailId+'/unfolder','POST');}
  const m=inboxD.find(x=>x.id===mailId);if(m)m.folder_id=folderId||null;
  renderInbox();toast('Verschoben','ok');
}

function renderInbox(){
  const s=($('is')?.value||'').toLowerCase();
  let d=[...inboxD];
  if(inboxUnread) d=d.filter(m=>!m.read_at);
  if(inboxStarred) d=d.filter(m=>m.starred);
  if(inboxLogitech) d=d.filter(m=>m.from_addr?.toLowerCase().includes('logi'));
  if(inboxFolder==='__none__') d=d.filter(m=>!m.folder_id);
  else if(inboxFolder) d=d.filter(m=>String(m.folder_id)===inboxFolder);
  if(s) d=d.filter(m=>
      m.from_addr?.toLowerCase().includes(s)||
      m.subject?.toLowerCase().includes(s)||
      m.body?.toLowerCase().includes(s)||
      m.to_addr?.toLowerCase().includes(s)
  );
  const sortBy=$('isort')?.value||'date';
  if(sortBy==='ticket') d.sort((a,b)=>{
    const ta=extractTicketNum((a.subject||'')+(a.body||'').substring(0,100));
    const tb=extractTicketNum((b.subject||'')+(b.body||'').substring(0,100));
    return tb.localeCompare(ta);
  });
  else if(sortBy==='sender') d.sort((a,b)=>shortFrom(a.from_addr).localeCompare(shortFrom(b.from_addr)));
  else if(sortBy==='unread') d.sort((a,b)=>(!a.read_at&&b.read_at)?-1:(a.read_at&&!b.read_at)?1:0);

  // Build ticket→color map FIRST before rendering
  const ticketColors={};let colorIdx=0;
  d.forEach(m=>{
    const tn=extractTicketNum((m.subject||'')+(m.to_addr||'')+(m.body||'').substring(0,100));
    if(tn&&!(tn in ticketColors)){ticketColors[tn]=colorIdx%8;colorIdx++;}
  });

  const el=$('inbox-list');
  if(!d.length){el.innerHTML='<div class="empty">Keine Mails</div>';return;}

  const today=new Date().toDateString(),yesterday=new Date(Date.now()-86400000).toDateString();
  let lastDate=null, lastTicket=null, html='';

  d.forEach(m=>{
    const dt=m.received_at?new Date(m.received_at):null;
    const ds=dt?dt.toDateString():'';
    const dl=ds===today?'Heute':ds===yesterday?'Gestern':dt?dt.toLocaleDateString('de',{day:'2-digit',month:'2-digit',year:'2-digit'}):'';

    // Date separator (only for date sort)
    if(sortBy==='date' && dl && dl!==lastDate){
      html+=`<div style="padding:4px 12px;font-size:10px;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:.5px;background:var(--surface2);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:1">${dl}</div>`;
      lastDate=dl;
    }

    const mTicket=extractTicketNum((m.subject||'')+(m.to_addr||'')+(m.body||'').substring(0,100));
    const mColorClass=mTicket&&ticketColors[mTicket]!==undefined?'ticket-color-'+ticketColors[mTicket]:'';

    // Ticket group separator (only for ticket sort)
    if(sortBy==='ticket' && mTicket && mTicket!==lastTicket){
      html+=`<div style="padding:4px 12px;font-size:10px;font-weight:700;color:var(--text3);background:var(--surface2);border-bottom:1px solid var(--border)">Ticket #${mTicket}</div>`;
      lastTicket=mTicket;
    }

    const unread=!m.read_at, active=curMailId===m.id, sel=selectedMails.has(m.id);
    const timeStr=dt?dt.toLocaleTimeString('de',{hour:'2-digit',minute:'2-digit'}):'';
    const regBadge=m.reg_name?`<span style="font-size:9px;color:var(--blue);background:var(--blue-bg);padding:1px 5px;border-radius:8px">${escH(m.reg_name)}</span>`:'';
    const ticketBadge=mTicket?`<span style="font-size:9px;color:var(--text3);background:var(--surface2);padding:1px 5px;border-radius:8px">#${mTicket}</span>`:'';
    const isLogitech=m.from_addr?.toLowerCase().includes('logi');
    const logiIcon=isLogitech?'<span style="font-size:9px;color:var(--text3)">🖱</span>':'';
    const folderObj=(window._folders||[]).find(f=>f.id===m.folder_id);
    const folderBadge=folderObj?`<span style="font-size:9px;color:var(--text2);background:var(--surface2);border:1px solid var(--border);padding:1px 6px;border-radius:8px">${escH(folderObj.name)}</span>`:'';
    const repliedBadge=m.replied_at?`<span style="font-size:9px;color:var(--green);background:var(--green-bg);padding:1px 5px;border-radius:8px;border:1px solid rgba(16,185,129,.2)">↩ beantwortet</span>`:'';

    html+=`<div class="mi ${mColorClass}${unread?' unread':''}${active?' active':''}" data-id="${m.id}"
      style="transition:.1s${sel?';background:var(--blue-bg)':''}"
      onclick="handleMailClick(event,${m.id})">
      <input type="checkbox" ${sel?'checked':''} onclick="event.stopPropagation();toggleMailSel(${m.id},this.checked)" style="width:13px;height:13px;flex-shrink:0;margin-top:3px">
      <div style="flex:1;min-width:0">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:1px">
          <span style="font-size:12px;font-weight:${unread?700:500};overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${logiIcon} ${escH(shortFrom(m.from_addr))}</span>
          <div style="display:flex;align-items:center;gap:4px;flex-shrink:0">
            ${m.replied_at?`<span style="font-size:9px;color:var(--green)" title="Beantwortet am ${new Date(m.replied_at).toLocaleString('de')}">↩</span>`:''}
            <span style="font-size:10px;color:var(--text3);white-space:nowrap">${timeStr}</span>
          </div>
        </div>
        <div class="mi-sub" style="font-weight:${unread?600:400};color:${unread?'var(--text)':'var(--text2)'}">${escH(m.subject||'(kein Betreff)')}</div>
        <div class="mi-prev">${escH((m.body||'').replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim().substring(0,70))}</div>
        <div style="margin-top:3px;display:flex;gap:4px;flex-wrap:wrap">${regBadge}${ticketBadge}${folderBadge}${repliedBadge}${m.starred?'<span style="color:var(--amber);font-size:11px">★</span>':''}</div>
      </div>
    </div>`;
  });
  el.innerHTML=html;
  const ic=$('inbox-count');
  if(ic){const unreadCount=d.filter(m=>!m.read_at).length;ic.textContent=d.length+' Mails'+(unreadCount?' · '+unreadCount+' ungelesen':'');}
  updateSelUI();
}

function handleMailClick(e,id){
  if(e.target.type==='checkbox')return;
  if(selectedMails.size>0){toggleMailSel(id,!selectedMails.has(id));return;}
  openMail(id);
}
function toggleMailSel(id,checked){if(checked)selectedMails.add(id);else selectedMails.delete(id);updateSelUI();renderInbox();}
function toggleSelectAll(checked){if(checked)inboxD.forEach(m=>selectedMails.add(m.id));else selectedMails.clear();updateSelUI();renderInbox();}
function clearSelection(){selectedMails.clear();updateSelUI();renderInbox();}
async function starSelected(){
  if(!selectedMails.size)return;
  for(const id of selectedMails){
    await api('/api/inbox/'+id+'/star','POST');
    const m=inboxD.find(x=>x.id===id);if(m)m.starred=!m.starred;
  }
  clearSelection();renderInbox();
}
function updateSelUI(){
  const n=selectedMails.size;
  const tb=$('sel-toolbar');if(tb)tb.style.display=n>0?'flex':'none';
  const sc=$('sel-count');if(sc)sc.textContent=n+' ausgewählt';
  const db=$('del-sel-btn');if(db)db.style.display=n>0?'':'none';
}
async function deleteSelected(){
  if(!selectedMails.size)return;
  if(!confirm(selectedMails.size+' Mail(s) löschen?'))return;
  const ids=[...selectedMails];
  await api('/api/inbox/delete-many','POST',{ids});
  inboxD=inboxD.filter(m=>!selectedMails.has(m.id));
  selectedMails.clear();updateSelUI();renderInbox();updateBell();
  toast(ids.length+' gelöscht','ok');
}
async function markSelectedRead(){
  if(!selectedMails.size)return;
  const ids=[...selectedMails];
  await api('/api/inbox/mark-read-many','POST',{ids});
  inboxD.forEach(m=>{if(selectedMails.has(m.id))m.read_at=new Date().toISOString();});
  selectedMails.clear();updateSelUI();renderInbox();updateBell();
}
async function deleteOneMail(id){
  await api('/api/inbox/'+id,'DELETE');
  inboxD=inboxD.filter(m=>m.id!==id);
  if(curMailId===id){curMailId=null;$('mail-detail').innerHTML='<div class="card" style="padding:50px;text-align:center;color:var(--text3)">Mail auswählen</div>';}
  renderInbox();updateBell();toast('Gelöscht','ok');
}



function isUpsMail(m){
  const from = String((m && m.from_addr) || '').toLowerCase();
  const subject = String((m && m.subject) || '').toLowerCase();
  const htmlBody = String((m && m.html_body) || '').toLowerCase();
  const body = String((m && m.body) || '').toLowerCase();

  return (
    from.includes('@ups.com') ||
    from.includes('ups') ||
    subject.includes('ups versandbenachrichtigung') ||
    subject.includes('ups shipping') ||
    subject.includes('kontrollnummer') ||
    subject.includes('tracking number') ||
    htmlBody.includes('www.ups.com') ||
    htmlBody.includes('upsmychoice') ||
    htmlBody.includes('quantum view') ||
    body.includes('www.ups.com') ||
    body.includes('upsmychoice') ||
    body.includes('quantum view')
  );
}

function looksLikeHtml(s=''){
  const t = String(s || '').trim().toLowerCase();
  return (
    /<(html|body|table|tbody|thead|tfoot|tr|td|th|div|span|p|br|img|a|style|meta|center|font)\b/.test(t) ||
    /<br\s*\/?>/.test(t) ||
    /&nbsp;|&lt;|&gt;/.test(t)
  );
}
function decodeQuotedPrintableLoose(s=''){
  let out=String(s||'');
  out=out.replace(/=\r?\n/g,'');
  out=out.replace(/=3D/gi,'=').replace(/=20/gi,' ').replace(/=09/gi,'\t');
  out=out.replace(/=22/gi,'"').replace(/=27/gi,"'").replace(/=C2=A0/gi,' ');
  return out;
}
function mailPlainText(s=''){
  return decodeQuotedPrintableLoose(String(s || ''))
      .replace(/##-\s*Please type your reply above this line\s*-##/gi,'')
      .replace(/<[^>]*>/g,' ')
      .replace(/\s+\n/g,'\n')
      .replace(/\n\s+/g,'\n')
      .replace(/[ \t]{2,}/g,' ')
      .trim();
}
function parseMailHtml(raw=''){
  let html = decodeQuotedPrintableLoose(raw || '');
  html = html.replace(/##-\s*Please type your reply above this line\s*-##/gi,'');
  html = html.replace(/<script[\s\S]*?<\/script>/gi,'');
  html = html.replace(/<noscript[\s\S]*?<\/noscript>/gi,'');
  html = html.replace(/<link[^>]*>/gi,'');
  html = html.replace(/<img[^>]*width=["']?1["']?[^>]*height=["']?1["']?[^>]*>/gi,'');
  html = html.replace(/<o:p>\s*<\/o:p>/gi,'');
  html = html.replace(/\son\w+="[^"]*"/gi,'');
  html = html.replace(/\son\w+='[^']*'/gi,'');

  let headContent = '';
  const headMatch = html.match(/<head[^>]*>([\s\S]*?)<\/head>/i);
  if(headMatch) headContent = headMatch[1] || '';

  let bodyContent = '';
  const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  if(bodyMatch){
    bodyContent = bodyMatch[1] || '';
  } else {
    bodyContent = html
      .replace(/<!DOCTYPE[^>]*>/gi,'')
      .replace(/<html[^>]*>/gi,'').replace(/<\/html>/gi,'')
      .replace(/<head[\s\S]*?<\/head>/gi,'')
      .replace(/<body[^>]*>/gi,'').replace(/<\/body>/gi,'')
      .trim();
  }

  const candidates = [
    /<div[^>]+class=["'][^"']*mail-content[^"']*["'][^>]*>([\s\S]*)$/i,
    /<div[^>]+id=["']id6["'][^>]*>([\s\S]*)$/i
  ];
  for(const rx of candidates){
    const m = bodyContent.match(rx);
    if(m && m[1] && m[1].trim().length > 200){
      bodyContent = m[1].trim();
      break;
    }
  }

  const nestedDoc = bodyContent.match(/<!DOCTYPE[\s\S]*?<html[\s\S]*$/i) || bodyContent.match(/<html[\s\S]*$/i);
  if(nestedDoc){
    const nested = parseMailHtml(nestedDoc[0]);
    if(nested.bodyContent && nested.bodyContent.trim().length > 100){
      headContent = [headContent, nested.headContent].filter(Boolean).join('\n');
      bodyContent = nested.bodyContent;
    }
  }

  return { headContent, bodyContent };
}
function getMailHtmlSource(m){
  const htmlBody = String((m && m.html_body) || '').trim();
  const rawBody  = String((m && m.body) || '').trim();

  if(htmlBody && htmlBody.length > 20){
    return htmlBody;
  }

  if(rawBody && looksLikeHtml(rawBody)){
    return rawBody;
  }

  return '';
}
function buildRawUpsSrcdoc(rawHtml=''){
  let html = decodeQuotedPrintableLoose(rawHtml || '');
  html = html.replace(/<script[\s\S]*?<\/script>/gi,'');
  html = html.replace(/<noscript[\s\S]*?<\/noscript>/gi,'');

  const helperStyle = `<style>
    html,body{margin:0;padding:0;background:#fff}
    img{max-width:100%!important;height:auto!important}
  </style>`;

  if (/<html[\s\S]*>/i.test(html)) {
    if (/<head[\s\S]*?>/i.test(html)) {
      return html.replace(/<\/head>/i, helperStyle + '</head>');
    }
    return helperStyle + html;
  }

  return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">${helperStyle}</head><body>${html}</body></html>`;
}
function buildMailSrcdoc(rawHtml='', m=null){
  if(!rawHtml) return '';

  if(isUpsMail(m)){
    return buildRawUpsSrcdoc(rawHtml);
  }

  const parsed = parseMailHtml(rawHtml);
  const hc = parsed.headContent || '';
  const bc = parsed.bodyContent || '';

  const baseStyle = `
    <style>
      html,body{margin:0;padding:0;background:#ffffff}
      body{
        color:#111827;
        font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
        font-size:14px;
        line-height:1.68;
        word-break:break-word;
        overflow-wrap:anywhere;
      }
      img{max-width:100%!important;height:auto!important}
      a{color:#2563eb;text-decoration:none}
      pre,code{white-space:pre-wrap !important;word-break:break-word}
      blockquote{margin:12px 0;padding-left:12px;border-left:3px solid #dbe4ff;color:#4b5563}
    </style>
  `;

  return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">${hc}${baseStyle}</head><body>${bc}</body></html>`;
}
function renderMailContentInto(container,m,opt={}){
  if(!container) return;

  const isMobile = window.matchMedia && window.matchMedia('(max-width: 768px)').matches;
  const minHeight = opt.minHeight || (isMobile ? 120 : 200);
  const maxHeight = opt.maxHeight || (isMobile ? 2600 : 3200);
  const rawHtml = getMailHtmlSource(m);
  const plain = mailPlainText((m&&m.html_body)||'') || mailPlainText((m&&m.body)||'') || '(kein Inhalt)';

  container.innerHTML = '';
  container.style.background = 'var(--surface)';
  container.style.width = '100%';
  container.style.height = 'auto';
  container.style.maxHeight = 'none';
  container.style.overflow = 'visible';

  const renderPlain = ()=>{
    container.innerHTML = '';
    const div = document.createElement('div');
    div.style.cssText = 'padding:14px 16px;font-size:'+(isMobile?'12px':'13px')+';line-height:1.72;color:var(--text2);white-space:pre-wrap;font-family:-apple-system,BlinkMacSystemFont,sans-serif;word-break:break-word;overflow-wrap:anywhere';
    div.textContent = plain;
    container.appendChild(div);
  };

  if(!rawHtml){
    renderPlain();
    return;
  }

  const srcdoc = buildMailSrcdoc(rawHtml, m);
  const wrapper = document.createElement('div');
  wrapper.style.cssText = 'width:100%;overflow:visible';
  container.appendChild(wrapper);

  const iframe = document.createElement('iframe');
  iframe.style.cssText = 'width:100%;height:'+minHeight+'px;border:none;display:block;background:#fff;overflow:hidden';
  iframe.setAttribute('sandbox','allow-same-origin allow-scripts');
  iframe.setAttribute('scrolling','no');
  iframe.setAttribute('loading','lazy');
  wrapper.appendChild(iframe);

  const msgId = 'mh_' + Math.random().toString(36).slice(2);
  let heightSet = false;

  const onMsg = (e) => {
    if(!e.data || e.data.id !== msgId) return;
    heightSet = true;
    iframe.style.height = Math.min(Math.max(e.data.h || minHeight, minHeight), maxHeight) + 'px';
  };
  window.addEventListener('message', onMsg);

  const reporter = '<script>window.addEventListener("load",function(){function r(){try{var h=Math.max(document.body?document.body.scrollHeight:0,document.documentElement?document.documentElement.scrollHeight:0,document.body?document.body.offsetHeight:0,document.documentElement?document.documentElement.offsetHeight:0);window.parent.postMessage({id:"'+msgId+'",h:h},"*");}catch(e){}}r();setTimeout(r,80);setTimeout(r,250);setTimeout(r,700);try{new MutationObserver(r).observe(document.body,{childList:true,subtree:true,attributes:true,characterData:true});}catch(e){}});<\/script>';
  const fullSrcdoc = srcdoc.includes('</head>') ? srcdoc.replace('</head>', reporter + '</head>') : (reporter + srcdoc);
  iframe.srcdoc = fullSrcdoc;

  setTimeout(()=>{
    if(heightSet) return;
    try{
      const doc = iframe.contentDocument || iframe.contentWindow.document;
      const h = Math.max(
        doc.body?.scrollHeight || 0,
        doc.documentElement?.scrollHeight || 0,
        doc.body?.offsetHeight || 0,
        doc.documentElement?.offsetHeight || 0,
        minHeight
      );
      iframe.style.height = Math.min(Math.max(h, minHeight), maxHeight) + 'px';
      if(h > minHeight) heightSet = true;
    }catch(e){}
  }, 1200);

  setTimeout(()=>{
    window.removeEventListener('message', onMsg);
    if(heightSet) return;
    try{
      const doc = iframe.contentDocument || iframe.contentWindow.document;
      const text = ((doc.body?.innerText) || '').replace(/\s+/g,' ').trim();
      const markupLen = ((doc.body?.innerHTML) || '').replace(/\s+/g,'').length;
      if(text.length > 0 || markupLen > 80) return;
    }catch(e){}
    renderPlain();
  }, isUpsMail(m) ? 4000 : 2200);
}


async function openMail(id){
  curMailId=id;
  const m=inboxD.find(x=>x.id===id);if(!m)return;
  if(!m.read_at){await api('/api/inbox/'+id+'/read','POST');m.read_at=new Date().toISOString();renderInbox();updateBell();}

  // Load registrations for context
  let reg=null;
  try{const regs=await api('/api/registrations');reg=m.reg_id?regs.find(r=>r.id===m.reg_id):null;}catch(e){}

  const replyFrom=reg?reg.email:(m.to_addr||'').replace(/.*<([^>]+)>.*/,'$1').trim()||m.to_addr||'';
  const replyTo=m.from_addr||'';
  const ticketId=(reg&&reg.ticket_id)||extractTicketNum((m.subject||'')+(m.body||'').substring(0,300))||'';

  // Get thread (all mails for this reg)
  let thread=[];
  if(reg){try{const t=await api('/api/mail/thread/'+reg.id);thread=t||[];}catch(e){}}

  const dt=m.received_at?new Date(m.received_at):null;
  const dtStr=dt?dt.toLocaleString('de',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}):'';

  $('mail-detail').innerHTML=`
  <div style="display:flex;flex-direction:column;height:100%;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden">

    <!-- Mail header -->
    <div style="padding:14px 16px;border-bottom:1px solid var(--border);background:var(--surface)">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:10px">
        <div style="flex:1;min-width:0">
          <h2 style="font-size:15px;font-weight:700;margin-bottom:6px;word-break:break-word;line-height:1.3">${escH(m.subject||'(kein Betreff)')}</h2>
          <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center">
            <div style="width:28px;height:28px;border-radius:50%;background:var(--blue);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff;flex-shrink:0">${escH(shortFrom(m.from_addr)[0]||'?').toUpperCase()}</div>
            <div>
              <div style="font-size:12px;font-weight:600">${escH(shortFrom(m.from_addr))}</div>
              <div style="font-size:10px;color:var(--text3)">${escH(m.from_addr||'')}</div>
            </div>
          </div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex-shrink:0">
          <span style="font-size:10px;color:var(--text3)">${dtStr}</span>
        </div>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:5px;font-size:10px;color:var(--text2)">
        <span>An: ${escH(m.to_addr||'—')}</span>
        ${ticketId?`<span style="color:var(--blue);font-weight:600">· Ticket #${ticketId}</span>`:''}
        ${reg?`<span style="color:var(--green)">· ${escH(reg.name||'')}</span>`:''}
      </div>
    </div>

    <!-- Action bar ABOVE mail body -->
    <div style="padding:8px 16px;border-bottom:1px solid var(--border);background:var(--surface2);display:flex;gap:6px;align-items:center;flex-wrap:wrap">
      <button class="btn sm" onclick="openReplyModal('reply',${m.id})" style="background:var(--blue-bg);color:var(--blue);border-color:rgba(59,91,219,.15)">↩ Antworten</button>
      <button class="btn sm" onclick="openReplyModal('forward',${m.id})">↪ Weiterleiten</button>
      <div style="flex:1"></div>
      <button class="btn xs${m.starred?' pr':''}" onclick="toggleStar(${m.id})" title="${m.starred?'Markierung entfernen':'Markieren'}">${m.starred?'★':'☆'}</button>
      <button class="btn xs" onclick="toggleReadMail(${m.id})" title="Gelesen/Ungelesen">📋</button>
      <button class="btn xs" onclick="showMoveFolderModal(${m.id})" title="In Ordner verschieben">📂</button>
      <button class="btn xs da" onclick="deleteOneMail(${m.id})" title="Löschen">🗑</button>
    </div>

    <!-- Context bar -->
    ${reg?`<div style="padding:7px 16px;background:var(--green-bg);border-bottom:1px solid var(--border);font-size:11px;display:flex;justify-content:space-between;align-items:center">
      <span style="color:var(--green)">✓ Registrierung: <strong>${escH(reg.name||'—')}</strong> · <span class="mono">${escH(reg.serial||'')}</span> · Ticket #${escH(reg.ticket_id||'—')}</span>
      <button class="btn xs" onclick="go('rma')" style="font-size:9px">→ RMA</button>
    </div>`:`<div style="padding:7px 16px;background:var(--amber-bg);border-bottom:1px solid var(--border);font-size:11px;display:flex;justify-content:space-between;align-items:center">
      <span style="color:var(--amber)">⚠ Keine Registrierung zugeordnet</span>
      <button class="btn xs" onclick="showAssignModal(${m.id})">🔗 Zuordnen</button>
    </div>`}

<!-- Mail body -->
<div style="flex:1;overflow:hidden;background:var(--surface);padding:0" id="mail-body-wrap-${m.id}">
  <div id="mail-body-container-${m.id}" style="height:100%;max-height:100%;overflow-y:auto;overflow-x:hidden"></div>
</div>
    <!-- Thread bar -->
    <div id="thread-container"></div>
  </div>`;

  const bodyContainer = document.getElementById('mail-body-container-'+m.id);
  renderMailContentInto(bodyContainer, m, {minHeight: 560});

  // Store mail context for reply modal
  window._currentMail = m;
  window._currentReg = reg;
  window._currentTicketId = ticketId;
  window._curRegId = reg ? reg.id : null;
  window._replyFrom = replyFrom;
  window._replyTo = replyTo;

  // Render thread separately
  renderThread(thread, m.id);
}

function renderThread(thread, mailId){
  const el=document.getElementById('thread-container');
  if(!el||!thread||!thread.length) return;
  const wrap=document.createElement('div');
  wrap.style.cssText='background:var(--surface2);border-top:1px solid var(--border);border-bottom:1px solid var(--border)';
  const hdr=document.createElement('div');
  hdr.style.cssText='padding:8px 16px 6px;font-size:10px;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:.5px';
  hdr.textContent='Verlauf ('+thread.length+')';
  wrap.appendChild(hdr);
  thread.forEach((t,ti)=>{
    const tid='tb-'+mailId+'-'+ti;
    const dt2=t.sent_at?new Date(t.sent_at).toLocaleDateString('de',{day:'2-digit',month:'2-digit'}):'—';
    const col=t.direction==='out'?'var(--blue)':'var(--green)';
    const lbl=t.direction==='out'?'↑ Gesendet':'↓ Empfangen';
    const row=document.createElement('div');
    row.style.borderTop='1px solid var(--border)';
    const hRow=document.createElement('div');
    hRow.style.cssText='display:flex;gap:8px;align-items:center;padding:7px 16px;cursor:pointer;user-select:none;transition:.1s';
    hRow.onmouseover=()=>hRow.style.background='var(--surface3)';
    hRow.onmouseout=()=>hRow.style.background='';
    hRow.onclick=()=>toggleThreadItem(tid);
    const dot=document.createElement('span');
    dot.style.cssText='width:7px;height:7px;border-radius:50%;background:'+col+';flex-shrink:0';
    const subj=document.createElement('span');
    subj.style.cssText='font-size:11px;color:var(--text2);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap';
    subj.textContent=t.subject||'—';
    const meta=document.createElement('span');
    meta.style.cssText='font-size:10px;color:var(--text3)';
    meta.textContent=lbl+' · '+dt2;
    const arrow=document.createElement('span');
    arrow.id=tid+'-arrow';
    arrow.style.cssText='font-size:10px;color:var(--text3);margin-left:4px';
    arrow.textContent='▾';
    hRow.append(dot,subj,meta,arrow);
    const body=document.createElement('div');
    body.id=tid;
    body.style.cssText='display:none;padding:0;background:var(--surface);border-top:1px solid var(--border);font-size:13px;color:var(--text2);line-height:1.65;max-height:520px;overflow-y:auto';
    // Store data for lazy rendering – don't render while hidden (iframe height would be 0)
    body._mailData={body:t.body||'', html_body:t.html_body||''};
    body._rendered=false;
    row.append(hRow,body);
    wrap.appendChild(row);
  });
  el.appendChild(wrap);
}

function toggleThreadItem(id){
  const el=document.getElementById(id);if(!el)return;
  const open=el.style.display!=='none';
  el.style.display=open?'none':'block';
  const arrow=document.getElementById(id+'-arrow');
  if(arrow)arrow.textContent=open?'▾':'▴';
  // Render content lazily on first open (iframe needs visible container for height calc)
  if(!open && !el._rendered){
    el._rendered=true;
    renderMailContentInto(el, el._mailData||{}, {minHeight:180, maxHeight:520});
  }
}

function openReplyModal(mode, mailId){
  const m=window._currentMail;
  const reg=window._currentReg;
  const ticketId=window._currentTicketId||'';
  const replyFrom=window._replyFrom||'';
  const replyTo=window._replyTo||'';
  if(!m)return;

  const isForward=mode==='forward';
  const subjectPrefix=isForward?'Fwd: ':'Re: ';
  const subjectVal=subjectPrefix+escH(m.subject||'');
  const bodyPrefix=isForward?('\n\n---------- Weitergeleitete Nachricht ----------\nVon: '+(m.from_addr||'')+'\nDatum: '+(m.date_raw||m.received_at||'')+'\nBetreff: '+(m.subject||'')+'\nAn: '+(m.to_addr||'')+'\n\n'+(m.body||'').substring(0,2000)):'';

  // Create overlay
  const ov=document.createElement('div');
  ov.id='reply-overlay';
  ov.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.45);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);z-index:400;display:flex;align-items:center;justify-content:center;padding:20px;animation:overlay-in .2s ease';
  ov.onclick=function(e){if(e.target===ov)closeReplyModal();};

  const panel=document.createElement('div');
  panel.style.cssText='background:var(--surface);border-radius:var(--radius);width:100%;max-width:620px;max-height:90vh;overflow-y:auto;box-shadow:var(--shadow-lg);animation:panel-in .25s ease';
  panel.innerHTML=`
    <div style="padding:14px 18px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">
      <h2 style="font-size:15px;font-weight:700">${isForward?'↪ Weiterleiten':'↩ Antworten'}</h2>
      <button class="btn xs" onclick="closeReplyModal()">✕</button>
    </div>
    <div style="padding:16px 18px;display:flex;flex-direction:column;gap:10px">
      <div style="display:flex;gap:8px;align-items:center">
        <label style="font-size:11px;color:var(--text2);white-space:nowrap;flex-shrink:0;width:55px">Von:</label>
        <input id="rm-from" value="${escH(replyFrom)}" style="font-family:monospace;font-size:12px;flex:1" readonly>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <label style="font-size:11px;color:var(--text2);white-space:nowrap;flex-shrink:0;width:55px">An:</label>
        <input id="rm-to" value="${isForward?'':escH(replyTo)}" placeholder="${isForward?'Empfänger eingeben...':'Wird automatisch ermittelt'}" style="font-family:monospace;font-size:12px;flex:1"${isForward?'':' readonly'}>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <label style="font-size:11px;color:var(--text2);white-space:nowrap;flex-shrink:0;width:55px">🎫 Ticket:</label>
        <input id="rm-ticket" value="${escH(ticketId)}" placeholder="z.B. 17082833" style="font-family:monospace;font-size:12px;flex:1">
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
        <select id="rm-tpl" onchange="applyModalTpl()" style="flex:1;min-width:130px;font-size:11px"><option value="">— Vorlage —</option></select>
        <button class="btn xs" style="background:var(--blue-bg);color:var(--blue)" id="rm-ki-btn" onclick="genKiModal()">✦ KI</button>
        <span id="rm-ki-spin" style="display:none"><span class="spin"></span></span>
        <select id="rm-lang" style="width:90px;font-size:11px"><option value="de">Deutsch</option><option value="en">Englisch</option></select>
      </div>
      <input id="rm-subject" value="${subjectVal}" placeholder="Betreff..." style="font-size:13px">
      <textarea id="rm-body" rows="8" placeholder="Nachricht eingeben..." style="resize:vertical;font-size:13px;line-height:1.5">${escH(bodyPrefix)}</textarea>
      <div>
        <label class="fl">Anhänge</label>
        <input type="file" id="rm-files" multiple style="padding:3px">
        <div id="rm-attach-preview" style="margin-top:4px;display:flex;gap:5px;flex-wrap:wrap"></div>
      </div>
      <div style="display:flex;gap:8px;justify-content:space-between;align-items:center">
        <div style="display:flex;gap:6px">
          <button class="btn pr sm" id="rm-send-btn" onclick="doSendModal()">📤 Senden</button>
          <button class="btn sm" onclick="closeReplyModal()">Abbrechen</button>
        </div>
        <div id="rm-result" style="font-size:11px"></div>
      </div>
      <div style="padding:7px 10px;background:var(--surface2);border-radius:var(--radius-sm);font-size:10px;color:var(--text3)">
        Mail-ID: ${mailId} · Reply-To und In-Reply-To werden automatisch aus der Original-Mail gesetzt
      </div>
    </div>`;

  ov.appendChild(panel);
  document.body.appendChild(ov);

  // Store context
  window._replyMailId=mailId;
  window._replyMode=mode;

  // Load templates into modal dropdown
  loadModalTplDrop();

  // File preview handler
  const rmf=document.getElementById('rm-files');
  if(rmf)rmf.onchange=function(){
    const prev=document.getElementById('rm-attach-preview');if(!prev)return;
    prev.innerHTML=[...this.files].map(f=>`<span style="font-size:10px;padding:2px 6px;background:var(--surface2);border-radius:3px;border:1px solid var(--border)">${escH(f.name)} (${(f.size/1024).toFixed(0)}KB)</span>`).join('');
  };
}

function closeReplyModal(){
  const ov=document.getElementById('reply-overlay');
  if(ov)ov.remove();
}

async function loadModalTplDrop(){
  try{
    const ts=await api('/api/templates');
    const sel=document.getElementById('rm-tpl');
    if(!sel)return;
    sel.innerHTML='<option value="">— Vorlage —</option>'+ts.map(t=>`<option value="${t.id}" data-s="${escH(t.subject)}" data-b="${escH(t.body)}">${escH(t.name)}</option>`).join('');
  }catch(e){}
}
function applyModalTpl(){
  const o=document.getElementById('rm-tpl')?.selectedOptions[0];
  if(!o?.dataset.s)return;
  const sub=document.getElementById('rm-subject');
  const body=document.getElementById('rm-body');
  if(sub)sub.value=o.dataset.s;
  if(body)body.value=o.dataset.b;
}
async function genKiModal(){
  const btn=document.getElementById('rm-ki-btn'),spin=document.getElementById('rm-ki-spin');
  if(btn)btn.style.display='none';if(spin)spin.style.display='';
  const reg=window._currentReg;
  const name=reg?reg.name:'Kunde';
  const serial=reg?reg.serial:'Logitech Gerät';
  const lang=document.getElementById('rm-lang')?.value||'de';
  const res=await api('/api/mail/generate-free','POST',{product:serial||'Logitech Gerät',sender_name:name||'Kunde',lang});
  if(btn)btn.style.display='';if(spin)spin.style.display='none';
  if(res.ok){
    const sub=document.getElementById('rm-subject');
    const body=document.getElementById('rm-body');
    if(sub)sub.value=res.subject;
    if(body)body.value=res.body;
    toast('KI-Text generiert','ok');
  } else toast('Fehler: '+res.error,'err');
}

async function doSendModal(){
  const btn=document.getElementById('rm-send-btn'),resultEl=document.getElementById('rm-result');
  const subject=(document.getElementById('rm-subject')?.value||'').trim();
  const body=(document.getElementById('rm-body')?.value||'').trim();
  const fromAddr=(document.getElementById('rm-from')?.value||'').trim();
  const toAddr=(document.getElementById('rm-to')?.value||'').trim();
  const ticketId=(document.getElementById('rm-ticket')?.value||'').trim();
  const isForward = window._replyMode === 'forward';

  if(!subject||!body){toast('Betreff und Text eingeben','err');return;}
  if(isForward && !toAddr){toast('Empfänger eingeben','err');return;}

  if(btn){btn.disabled=true;btn.textContent='⏳ Wird gesendet...';}
  if(resultEl)resultEl.innerHTML='<span class="spin"></span>';

  const files=document.getElementById('rm-files')?.files||[],atts=[];
  for(const f of files){
    const data=await new Promise(r=>{const fr=new FileReader();fr.onload=e=>r(e.target.result.split(',')[1]);fr.readAsDataURL(f);});
    atts.push({filename:f.name,data});
  }

  let res;
  try{
    if(isForward){
      res = await api('/api/inbox/reply-free','POST',{
        from_addr: fromAddr,
        to_addr: toAddr,
        subject,
        body,
        attachments: atts,
        original_mail_id: 0
      });
    } else {
      res = await api('/api/inbox/reply-free','POST',{
        from_addr: fromAddr,
        to_addr: toAddr,
        subject,
        body,
        attachments: atts,
        original_mail_id: window._replyMailId || 0
      });
    }
  }catch(e){
    res = {ok:false,error:e.message};
  }

  if(btn){btn.disabled=false;btn.textContent='📤 Senden';}
  if(res&&res.ok){
    if(resultEl)resultEl.innerHTML=`<div style="font-size:11px;padding:8px 10px;background:var(--green-bg);border-radius:var(--radius-sm)"><div style="font-weight:600;color:var(--green);margin-bottom:3px">✓ Gesendet</div><div style="color:var(--text2)">An: <strong style="color:var(--text)">${escH(res.to_addr||toAddr)}</strong></div></div>`;
    toast('Gesendet an '+(res.to_addr||toAddr),'ok');
    // Lokales replied_at setzen damit Badge sofort erscheint
    const replyId = window._replyMailId;
    if(replyId){
      const mm=inboxD.find(x=>x.id===replyId);
      if(mm) mm.replied_at=new Date().toISOString();
    }
    renderInbox();
    setTimeout(()=>{closeReplyModal();syncInbox();},1200);
  } else {
    const err=res?.error||res?.detail||'Fehler';
    if(resultEl)resultEl.innerHTML=`<div style="color:var(--red);font-size:11px;padding:8px;background:var(--red-bg);border-radius:var(--radius-sm)">✗ ${escH(err)}</div>`;
    toast('Fehler: '+err,'err');
  }
}

// Keep old doSend for backward compat (compose page still uses it indirectly)
async function doSend(){ openReplyModal('reply', curMailId); }

async function toggleStar(id){const r=await api('/api/inbox/'+id+'/star','POST');const m=inboxD.find(x=>x.id===id);if(m)m.starred=r.starred;openMail(id);}
async function toggleReadMail(id){
  const m=inboxD.find(x=>x.id===id);if(!m)return;
  if(m.read_at){
    // Als ungelesen markieren
    await api('/api/inbox/'+id+'/unread','POST');
    m.read_at=null;
  } else {
    await api('/api/inbox/'+id+'/read','POST');
    m.read_at=new Date().toISOString();
  }
  renderInbox();updateBell();openMail(id);
}
async function showMoveFolderModal(mailId){
  const folders=window._folders||[];
  $('pt').textContent='In Ordner verschieben';
  const wrap=document.createElement('div');
  wrap.style.display='grid';wrap.style.gap='7px';
  const mkItem=(label,icon,onclick)=>{
    const d=document.createElement('div');
    d.style.cssText='display:flex;align-items:center;gap:9px;padding:9px 12px;border-radius:var(--radius-sm);border:1px solid var(--border);cursor:pointer;transition:.12s';
    d.onmouseover=()=>d.style.background='var(--surface2)';
    d.onmouseout=()=>d.style.background='';
    d.onclick=onclick;
    d.innerHTML='<span style="font-size:16px">'+icon+'</span><span style="font-size:12px">'+label+'</span>';
    return d;
  };
  wrap.appendChild(mkItem('Ohne Ordner','📭',()=>{moveMailToFolder(mailId,null);closeP();}));
  folders.forEach(f=>{
    const d=mkItem(escH(f.name),f.icon||'📁',()=>{moveMailToFolder(mailId,f.id);closeP();});
    wrap.appendChild(d);
  });
  $('pb').innerHTML='';$('pb').appendChild(wrap);
  $('ov').style.display='flex';
}
async function syncInbox(){toast('Synchronisiere...');try{const r=await api('/api/inbox/sync','POST');await loadInbox();updateBell();toast(r.new+' neue Mails','ok');}catch(e){toast('Fehler','err');}}

async function showAssignModal(mailId){
  const regs=await api('/api/registrations');
  $('pt').textContent='Registrierung zuordnen';
  $('pb').innerHTML=regs.length?regs.map(r=>`<div onclick="assignMail(${mailId},${r.id})" style="padding:9px 12px;border-bottom:1px solid var(--border);cursor:pointer;transition:.12s" onmouseover="this.style.background='var(--surface2)'" onmouseout="this.style.background=''">
    <div style="font-size:12px;font-weight:600">${escH(r.name||'—')}</div>
    <div style="font-size:11px;color:var(--text2)">${escH(r.email)} · Ticket #${escH(r.ticket_id||'—')}</div>
  </div>`).join(''):'<div class="empty">Keine Registrierungen</div>';
  $('ov').style.display='flex';
}
async function assignMail(mailId,regId){
  await api('/api/inbox/'+mailId+'/assign/'+regId,'POST');
  const m=inboxD.find(x=>x.id===mailId);if(m)m.reg_id=regId;
  closeP();await loadInbox();toast('Zugeordnet','ok');
}

async function genGFree(serial,name){
  $('gs').style.display='';const btn=$('genGBtn');if(btn)btn.style.display='none';
  const res=await api('/api/mail/generate-free','POST',{product:serial||'Logitech Gerät',sender_name:name||'Kunde',lang:$('cl')?.value||'de'});
  $('gs').style.display='none';if(btn)btn.style.display='';
  if(res.ok){if($('csub'))$('csub').value=res.subject;if($('cbody'))$('cbody').value=res.body;toast('Generiert','ok');}
  else toast('Gemini Fehler: '+res.error,'err');
}
async function loadTplDrop(){try{const ts=await api('/api/templates');const sel=$('ct');if(!sel)return;sel.innerHTML='<option value="">— Vorlage —</option>'+ts.map(t=>`<option value="${t.id}" data-s="${escH(t.subject)}" data-b="${escH(t.body)}">${escH(t.name)}</option>`).join('');}catch(e){}}
window.applyTpl=function(){const o=$('ct')?.selectedOptions[0];if(!o?.dataset.s)return;if($('csub'))$('csub').value=o.dataset.s;if($('cbody'))$('cbody').value=o.dataset.b;};
async function saveAsTpl(){const n=prompt('Vorlagenname:');if(!n)return;await api('/api/templates','POST',{name:n,subject:$('csub')?.value||'',body:$('cbody')?.value||'',lang:$('cl')?.value||'de'});toast('Gespeichert','ok');loadTplDrop();}