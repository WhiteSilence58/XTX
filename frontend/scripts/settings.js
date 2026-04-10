// ── Settings ──────────────────────────────────────────────────────────────────
async function loadSettingsTab(){
  const s=await api('/api/settings');
  if($('smu'))$('smu').value=s.mail_user||'';
  if($('smp'))$('smp').value=s.mail_pass||'';
  if($('sgk'))$('sgk').value=s.gemini_key||'';
  if($('sdom'))$('sdom').value=s.email_domain||'';
  if($('smgk'))$('smgk').value=s.mailgun_key||'';
  if($('smgd'))$('smgd').value=s.mailgun_domain||'kafka-frame.com';
  const st=await api('/api/stats');
  if($('sys'))$('sys').value=st.year_start||23;
  if($('sye'))$('sye').value=st.year_end||26;
  if($('sdel'))$('sdel').value=st.scan_delay||5;
  loadPrios();loadTplsList();
}
async function saveSettings(){await api('/api/settings','POST',{mail_user:$('smu').value,mail_pass:$('smp').value,gemini_key:$('sgk').value,email_domain:$('sdom').value});toast('Gespeichert','ok');}
async function saveMailgun(){const key=$('smgk').value.trim();if(!key){toast('API-Key eingeben','err');return;}await api('/api/settings','POST',{mailgun_key:key,mailgun_domain:$('smgd').value||'kafka-frame.com'});toast('Mailgun gespeichert','ok');}
async function testMailgun(){const el=$('mailgun-status');if(el)el.innerHTML='<span class="spin"></span> Teste...';const r=await api('/api/settings/test-mailgun','POST');if(el)el.innerHTML=r.ok?'<span style="color:var(--green)">✓ Mailgun funktioniert</span>':`<span style="color:var(--red)">✗ ${escH(r.error||'Fehler')}</span>`;}
async function saveScanner(){await api('/api/scanner/delay/'+$('sdel').value,'POST');await api('/api/scanner/years','POST',{year_start:parseInt($('sys').value),year_end:parseInt($('sye').value)});toast('Gespeichert','ok');}
async function changePassword(){const user=prompt('Benutzername:','admin');if(!user)return;const pass=prompt('Neues Passwort:');if(!pass||pass.length<4){toast('Mindestens 4 Zeichen','err');return;}const r=await api('/api/auth/set-password','POST',{username:user,password:pass});if(r.ok)toast('Passwort geändert','ok');else toast('Fehler','err');}
async function loadPrios(){
  const ps=await api('/api/priorities');
  const prl=$('prl');if(!prl)return;
  prl.innerHTML=ps.map(p=>`<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--border);font-size:11px"><span>${escH(p.name)} <span class="mono" style="color:var(--text2)">${p.prefix}</span></span><div class="gap"><input type="checkbox" ${p.active?'checked':''} onchange="api('/api/priorities/${p.id}','PATCH',{active:this.checked?1:0}).then(loadPrios)"><button class="btn xs da" onclick="api('/api/priorities/${p.id}','DELETE').then(loadPrios)">✕</button></div></div>`).join('')||'<div style="color:var(--text3);font-size:11px;padding:7px">Keine</div>';
}
async function addPrio(){const n=$('pn').value.trim(),p=$('pp').value.trim();if(!n||!p){toast('Name und Prefix','err');return;}await api('/api/priorities','POST',{name:n,prefix:p});$('pn').value='';$('pp').value='';loadPrios();}
async function loadTplsList(){
  try{
    const ts=await api('/api/templates');
    const tl2=$('tl2');if(!tl2)return;
    if(!ts.length){tl2.innerHTML='<div style="padding:20px;text-align:center;color:var(--text3);font-size:12px">Noch keine Vorlagen — klicke auf "+ Neue Vorlage"</div>';return;}
    tl2.innerHTML=`<div style="display:grid;gap:6px;padding:4px 0">
      ${ts.map(t=>`<div style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--surface2);transition:.15s" onmouseover="this.style.background='var(--surface3)'" onmouseout="this.style.background='var(--surface2)'" >
        <div style="flex:1;min-width:0">
          <div style="font-size:13px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escH(t.name)}</div>
          <div style="font-size:11px;color:var(--text2);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escH(t.subject||'(kein Betreff)')}</div>
          <div style="font-size:10px;color:var(--text3);margin-top:2px">${t.lang==='en'?'🇬🇧 Englisch':'🇩🇪 Deutsch'}</div>
        </div>
        <div style="display:flex;gap:5px;flex-shrink:0">
          <button class="btn xs" onclick="openTplModal(${t.id},'${escH(t.name)}','${escH(t.subject||'')}',\`${(t.body||'').replace(/`/g,'\\`').replace(/\$/g,'\\$')}\`,'${t.lang||'de'}')" title="Bearbeiten">✏</button>
          <button class="btn xs da" onclick="deleteTpl(${t.id},'${escH(t.name)}')" title="Löschen">🗑</button>
        </div>
      </div>`).join('')}
    </div>`;
  }catch(e){const tl2=$('tl2');if(tl2)tl2.innerHTML='<div style="color:var(--red);font-size:11px;padding:10px">Fehler beim Laden</div>';}
}

async function deleteTpl(id,name){
  if(!confirm('Vorlage "'+name+'" löschen?'))return;
  await api('/api/templates/'+id,'DELETE');
  toast('Gelöscht','ok');
  loadTplsList();
  // Reload dropdowns
  try{loadTplDrop();}catch(e){}
  try{loadModalTplDrop();}catch(e){}
  const cmpTpl=$('cmp-tpl');
  if(cmpTpl){try{const ts=await api('/api/templates');cmpTpl.innerHTML='<option value="">— Vorlage laden —</option>'+ts.map(t=>`<option value="${t.id}" data-s="${escH(t.subject)}" data-b="${escH(t.body)}">${escH(t.name)}</option>`).join('');}catch(e){}}
}

function openTplModal(id,name,subject,body,lang){
  const isEdit=!!id;
  const ov=document.createElement('div');
  ov.id='tpl-modal-ov';
  ov.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.45);backdrop-filter:blur(6px);z-index:500;display:flex;align-items:center;justify-content:center;padding:20px;animation:overlay-in .2s ease';
  ov.onclick=e=>{if(e.target===ov)closeTplModal();};
  ov.innerHTML=`
    <div style="background:var(--surface);border-radius:var(--radius);width:100%;max-width:560px;box-shadow:var(--shadow-lg);animation:panel-in .25s ease">
      <div style="padding:14px 18px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">
        <h2 style="font-size:15px;font-weight:700">${isEdit?'✏ Vorlage bearbeiten':'✉ Neue Vorlage'}</h2>
        <button class="btn xs" onclick="closeTplModal()">✕</button>
      </div>
      <div style="padding:16px 18px;display:grid;gap:10px">
        <div><label class="fl">Name</label><input id="tm-name" placeholder="z.B. Garantiebestätigung DE" value="${escH(name||'')}"></div>
        <div><label class="fl">Betreff</label><input id="tm-subject" placeholder="Betreff der Mail..." value="${escH(subject||'')}"></div>
        <div><label class="fl">Inhalt</label><textarea id="tm-body" rows="7" placeholder="Mail-Text eingeben..." style="resize:vertical;font-size:13px;line-height:1.55">${escH(body||'')}</textarea></div>
        <div><label class="fl">Sprache</label>
          <select id="tm-lang" style="width:140px">
            <option value="de"${(!lang||lang==='de')?' selected':''}>🇩🇪 Deutsch</option>
            <option value="en"${lang==='en'?' selected':''}>🇬🇧 Englisch</option>
          </select>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end">
          <button class="btn sm" onclick="closeTplModal()">Abbrechen</button>
          <button class="btn pr sm" onclick="saveTplModal(${id||'null'})">${isEdit?'💾 Speichern':'+ Erstellen'}</button>
        </div>
      </div>
    </div>`;
  document.body.appendChild(ov);
  setTimeout(()=>document.getElementById('tm-name')?.focus(),100);
}

function closeTplModal(){document.getElementById('tpl-modal-ov')?.remove();}

async function saveTplModal(id){
  const name=document.getElementById('tm-name')?.value.trim();
  const subject=document.getElementById('tm-subject')?.value||'';
  const body=document.getElementById('tm-body')?.value||'';
  const lang=document.getElementById('tm-lang')?.value||'de';
  if(!name){toast('Name eingeben','err');return;}
  const isEdit=id&&id!==null&&id!=='null';
  if(isEdit){
    await api('/api/templates/'+id,'PATCH',{name,subject,body,lang});
    toast('Vorlage aktualisiert','ok');
  } else {
    await api('/api/templates','POST',{name,subject,body,lang});
    toast('Vorlage erstellt','ok');
  }
  closeTplModal();
  loadTplsList();
  try{loadModalTplDrop();}catch(e){}
  const cmpTpl=$('cmp-tpl');
  if(cmpTpl){try{const ts=await api('/api/templates');cmpTpl.innerHTML='<option value="">— Vorlage laden —</option>'+ts.map(t=>`<option value="${t.id}" data-s="${escH(t.subject)}" data-b="${escH(t.body)}">${escH(t.name)}</option>`).join('');}catch(e){}}
}

async function saveTpl(){
  // Legacy fallback - redirect to modal
  openTplModal();
}

