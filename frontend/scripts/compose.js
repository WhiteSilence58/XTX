// ── Compose Page ──────────────────────────────────────────────────────────────
async function loadComposePage(){
  try{
    const idents=await api('/api/identities');
    const sel=$('cmp-from-sel');
    if(sel)sel.innerHTML='<option value="">— Profil wählen —</option>'+
      idents.map(i=>`<option value="${i.first_name.toLowerCase()}.${i.last_name.toLowerCase()}@${i.domain}">${escH(i.first_name)} ${escH(i.last_name)} (${escH(i.domain)})</option>`).join('');
  }catch(e){}
  try{
    const ts=await api('/api/templates');
    const sel=$('cmp-tpl');
    if(sel)sel.innerHTML='<option value="">— Vorlage laden —</option>'+
      ts.map(t=>`<option value="${t.id}" data-s="${escH(t.subject)}" data-b="${escH(t.body)}">${escH(t.name)}</option>`).join('');
  }catch(e){}
}
function updateComposeFrom(){const sel=$('cmp-from-sel');const from=$('cmp-from');if(sel&&from&&sel.value)from.value=sel.value;}
function applyCmpTpl(){const o=$('cmp-tpl')?.selectedOptions[0];if(!o?.dataset.s)return;if($('cmp-subject'))$('cmp-subject').value=o.dataset.s;if($('cmp-body'))$('cmp-body').value=o.dataset.b;}
async function genKiCompose(){
  const btn=$('cmp-ki-btn'),spin=$('cmp-spin');
  if(btn)btn.style.display='none';if(spin)spin.style.display='';
  const from=$('cmp-from')?.value||'';
  const name=from.split('@')[0].replace(/[._]/g,' ').replace(/\b\w/g,c=>c.toUpperCase())||'Kunde';
  const res=await api('/api/mail/generate-free','POST',{product:'Logitech Gerät',sender_name:name,lang:$('cmp-lang')?.value||'de'});
  if(btn)btn.style.display='';if(spin)spin.style.display='none';
  if(res.ok){if($('cmp-subject'))$('cmp-subject').value=res.subject;if($('cmp-body'))$('cmp-body').value=res.body;toast('KI-Text generiert','ok');}
  else toast('Fehler: '+res.error,'err');
}
async function sendCompose(){
  const from=($('cmp-from')?.value||'').trim();
  const ticketId=($('cmp-ticket')?.value||'').trim();
  let to=($('cmp-to')?.value||'').trim();
  const subject=($('cmp-subject')?.value||'').trim();
  const body=($('cmp-body')?.value||'').trim();
  const result=$('cmp-result');
  if(!from){toast('Absender eingeben','err');return;}
  if(!subject){toast('Betreff eingeben','err');return;}
  if(!body){toast('Text eingeben','err');return;}
  if(ticketId&&!to)to='support+id'+ticketId+'@logitech.zendesk.com';
  if(!to){toast('Empfänger eingeben','err');return;}
  const btn=$('cmp-send-btn');
  if(btn){btn.disabled=true;btn.textContent='⏳ Senden...';}
  if(result)result.innerHTML='<span class="spin"></span>';
  const files=$('cmp-files')?.files||[],atts=[];
  for(const f of files){const data=await new Promise(r=>{const fr=new FileReader();fr.onload=e=>r(e.target.result.split(',')[1]);fr.readAsDataURL(f);});atts.push({filename:f.name,data});}
  const res=await api('/api/inbox/reply-free','POST',{from_addr:from,to_addr:to,subject,body,attachments:atts});
  if(btn){btn.disabled=false;btn.textContent='📤 Senden';}
  if(res&&res.ok){if(result)result.innerHTML='<span style="color:var(--green)">✓ Gesendet an '+escH(to)+'</span>';toast('Gesendet','ok');}
  else{const err=res?.error||'Fehler';if(result)result.innerHTML='<span style="color:var(--red)">✗ '+escH(err)+'</span>';toast('Fehler: '+err,'err');}
}
function clearCompose(){[$('cmp-from'),$('cmp-to'),$('cmp-subject'),$('cmp-ticket'),$('cmp-body')].forEach(el=>{if(el)el.value='';});if($('cmp-attach-preview'))$('cmp-attach-preview').innerHTML='';if($('cmp-result'))$('cmp-result').innerHTML='';if($('cmp-from-sel'))$('cmp-from-sel').value='';}
async function saveCmpAsTpl(){const n=prompt('Vorlagenname:');if(!n)return;await api('/api/templates','POST',{name:n,subject:$('cmp-subject')?.value||'',body:$('cmp-body')?.value||'',lang:$('cmp-lang')?.value||'de'});toast('Vorlage gespeichert','ok');}

