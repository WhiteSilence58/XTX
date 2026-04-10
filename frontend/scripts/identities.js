// ── Identities ────────────────────────────────────────────────────────────────
async function loadIdsTab(){
  const [idents,domains,pvs]=await Promise.all([api('/api/identities'),api('/api/domains'),api('/api/product-values')]);
  const idl=$('idl');
  if(idl)idl.innerHTML=idents.length?idents.map(i=>`<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border);font-size:11px">
    <div><strong>${escH(i.first_name)} ${escH(i.last_name)}</strong><div style="color:var(--text2)">${escH(i.domain)} · ${(i.country||'').toUpperCase()}</div>${i.city?`<div style="color:var(--text3)">${escH(i.street||'')} ${escH(i.city)}</div>`:''}</div>
    <button class="btn xs da" onclick="delId(${i.id})">✕</button>
  </div>`).join(''):'<div class="empty">Noch keine</div>';
  const doml=$('doml');
  if(doml)doml.innerHTML=domains.map(d=>`<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border);font-size:11px">
    <div><strong>${escH(d.domain)}</strong> <span class="pill ${d.status==='sent'?'pv':'pi'}" style="font-size:9px">${d.status}</span></div>
    <div class="gap"><button class="btn xs" onclick="testDom('${d.domain}')">Test</button><button class="btn xs da" onclick="delDom('${d.domain}')">✕</button></div>
  </div>`).join('');
  const pvl=$('pvl');
  if(pvl)pvl.innerHTML=pvs.map(p=>`<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--border);font-size:11px"><span>${escH(p.product_name||p.part_number)}</span><span class="vb">${p.val_min}–${p.val_max}€</span></div>`).join('');
}
async function showIdForm(){
  const _dom=(await api('/api/settings')).email_domain||'';
  $('pt').textContent='Neues Profil';
  $('pb').innerHTML=`<div class="g2" style="margin-bottom:7px"><div><label class="fl">Vorname</label><input id="if2"></div><div><label class="fl">Nachname</label><input id="il2"></div></div>
    <div style="margin-bottom:7px"><label class="fl">Domain</label><input id="id2" value="${escH(_dom)}" placeholder="kafka-frame.com"></div>
    <div class="g2" style="margin-bottom:7px"><div><label class="fl">Land</label><select id="ico"><option value="de">DE</option><option value="us">US</option><option value="gb">GB</option></select></div><div><label class="fl">Sprache</label><select id="ila"><option value="de">DE</option><option value="en">EN</option></select></div></div>
    <div class="g2" style="margin-bottom:7px"><div><label class="fl">Straße + Nr.</label><input id="ist"></div><div><label class="fl">Stadt</label><input id="ici"></div></div>
    <div class="g2" style="margin-bottom:10px"><div><label class="fl">PLZ</label><input id="iz"></div><div style="display:flex;align-items:flex-end"><button class="btn sm" onclick="gAddrP()">📍 Auto</button></div></div>
    <button class="btn pr" onclick="crId()">Speichern</button>`;
  $('ov').style.display='flex';
}
async function gAddrP(){const city=($('ici').value||'Berlin').trim();const r=await api('/api/address/generate?city='+encodeURIComponent(city));if(r.street){$('ist').value=r.street+' '+r.number;$('iz').value=r.zip;toast('Adresse generiert','ok');}else toast('Nicht gefunden','err');}
async function crId(){
  const b={name:$('if2').value+' '+$('il2').value,first_name:$('if2').value,last_name:$('il2').value,domain:$('id2').value,country:$('ico').value,lang:$('ila').value,street:$('ist').value,city:$('ici').value,zip:$('iz').value};
  if(!b.first_name||!b.last_name||!b.domain){toast('Felder ausfüllen','err');return;}
  await api('/api/identities','POST',b);toast('Gespeichert','ok');closeP();loadIdsTab();
}
async function delId(id){if(!confirm('Profil löschen?'))return;await api('/api/identities/'+id,'DELETE');loadIdsTab();}
async function addDom(){const d=prompt('Domain:');if(!d)return;await api('/api/domains','POST',{domain:d});toast('Hinzugefügt','ok');loadIdsTab();}
async function testDom(d){toast('Test...');const r=await api('/api/domains/'+d+'/test','POST');toast(r.ok?'OK':'Fehler: '+r.status,r.ok?'ok':'err');loadIdsTab();}
async function delDom(d){if(!confirm(d+' löschen?'))return;await api('/api/domains/'+d,'DELETE');loadIdsTab();}
async function genAddr(){
  const city=($('ac').value||'').trim();if(!city){toast('Stadt eingeben','err');return;}
  $('ar-spin').style.display='';$('ar-list').innerHTML='';
  const results=[];
  for(let i=0;i<5;i++){const r=await api('/api/address/generate?city='+encodeURIComponent(city));if(r.street&&r.zip)results.push(r);}
  $('ar-spin').style.display='none';
  if(!results.length){$('ar-list').innerHTML='<div style="color:var(--red);font-size:11px;padding:8px">Keine gefunden</div>';return;}
  $('ar-list').innerHTML=results.map(r=>`<div onclick="copyAddr('${(r.full||'').replace(/'/g,"\\'")}',this)" style="display:flex;justify-content:space-between;align-items:center;padding:6px 9px;background:var(--surface2);border-radius:var(--radius-sm);margin-bottom:5px;font-size:11px;cursor:pointer;border:1px solid var(--border)"><span class="mono">${escH(r.full)}</span><button class="btn xs">Kopieren</button></div>`).join('');
}
async function copyAddr(text){
  try{
    if(navigator.clipboard && window.isSecureContext){
      await navigator.clipboard.writeText(text);
    } else {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      if(!ok) throw new Error('execCommand copy fehlgeschlagen');
    }
    toast('Kopiert','ok');
  }catch(e){
    console.error('copyAddr failed:', e);
    toast('Kopieren fehlgeschlagen','err');
  }
}
async function savePV(){
  await api('/api/product-values','POST',{part_number:$('pvpn').value,product_name:$('pvn').value,val_min:parseFloat($('pvmin').value)||0,val_max:parseFloat($('pvmax').value)||0,category:$('pvcat').value});
  toast('Gespeichert','ok');loadIdsTab();
}

