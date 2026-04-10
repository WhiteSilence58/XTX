// ── Invoice ───────────────────────────────────────────────────────────────────
let invTemplates={}, currentInvB64=null, currentInvName='';
async function loadInvoicePage(){
  try{
    const idents=await api('/api/identities');
    const sel=$('inv-profile');
    if(sel)sel.innerHTML='<option value="">— Profil wählen —</option>'+
      idents.map(i=>`<option value="${i.id}" data-fn="${escH(i.first_name)}" data-ln="${escH(i.last_name)}" data-st="${escH(i.street||'')}" data-ci="${escH(i.city||'')}" data-zp="${escH(i.zip||'')}">${escH(i.first_name)} ${escH(i.last_name)} · ${escH(i.city||'—')}</option>`).join('');
  }catch(e){}
  try{
    const regs=await api('/api/registrations');
    const sel=$('inv-serial');
    if(sel)sel.innerHTML='<option value="">— aus Registrierung —</option>'+
      regs.map(r=>`<option value="${r.id}" data-prd="${escH(r.product||r.name||'')}" data-srl="${escH(r.serial||'')}">${escH(r.serial||'—')} · ${escH(r.name||'')}</option>`).join('');
  }catch(e){}
  const today=new Date().toISOString().split('T')[0];
  if($('inv-date'))$('inv-date').value=today;
  const yn=new Date().getFullYear(),mn=String(new Date().getMonth()+1).padStart(2,'0');
  if($('inv-number'))$('inv-number').value=yn+'-'+mn+'-'+String(Math.floor(Math.random()*900)+100);
  await renderInvTemplateList();
  const dz=$('inv-drop-zone');
  if(dz){
    dz.ondragover=e=>{e.preventDefault();dz.style.borderColor='var(--blue)';dz.style.background='var(--blue-bg)';};
    dz.ondragleave=()=>{dz.style.borderColor='var(--border)';dz.style.background='';};
    dz.ondrop=e=>{e.preventDefault();dz.style.borderColor='var(--border)';dz.style.background='';const f=e.dataTransfer.files[0];if(f&&f.type==='application/pdf'){document.getElementById('inv-file-input').files=e.dataTransfer.files;loadInvoicePDF();}};
  }
}
async function loadInvoicePDF(){
  const file=$('inv-file-input')?.files[0];if(!file)return;
  const isDocx=file.name.toLowerCase().endsWith('.docx');
  currentInvName=file.name.replace(/\.(docx|pdf)$/i,'');
  window._invIsDocx=isDocx;
  const b64=await new Promise(r=>{const fr=new FileReader();fr.onload=e=>r(e.target.result.split(',')[1]);fr.readAsDataURL(file);});
  currentInvB64=b64;
  const info=$('inv-pdf-info');
  if(info){
    const typeLabel=isDocx
      ?'<span style="color:var(--blue);background:var(--blue-bg);padding:1px 6px;border-radius:10px;font-size:10px">Word .docx</span>'
      :'<span style="color:var(--text3);background:var(--surface2);padding:1px 6px;border-radius:10px;font-size:10px">PDF</span>';
    info.innerHTML='✓ '+typeLabel+' <strong style="margin-left:4px">'+escH(file.name)+'</strong> ('+Math.round(file.size/1024)+'KB)';
    const btn=document.createElement('button');btn.className='btn xs pr';btn.style.marginLeft='8px';btn.textContent='💾 Als Vorlage speichern';btn.onclick=()=>saveInvTemplate();info.appendChild(btn);
  }
  const fc=$('inv-fields-card');if(fc)fc.style.display='';
  const ab=$('inv-analyze-btn');if(ab)ab.style.display='';
  if(isDocx){
    const area=$('inv-preview-area');
    if(area)area.innerHTML='<div style="padding:12px;background:var(--blue-bg);border-radius:var(--radius-sm);font-size:11px;color:var(--blue)"><strong>📝 Word-Vorlage geladen</strong><br>Marker werden beim Erstellen automatisch ersetzt und als PDF ausgegeben.<br><br>Erkannte Marker werden hier angezeigt...</div>';
    // Show markers found in name only (can't parse docx in browser)
  } else {
    showInvPreview(b64,file.name);
  }
}
async function showInvPreview(b64,name){
  const area=$('inv-preview-area');if(!area)return;
  area.innerHTML='<span class="spin"></span> Analysiere PDF...';
  try{
    const res=await api('/api/invoice/analyze','POST',{pdf_b64:b64});
    if(res.ok){
      let html='<div style="font-size:11px;color:var(--text2);margin-bottom:8px">Erkannter Text:</div>';
      html+='<div style="font-size:11px;background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius-sm);padding:10px;max-height:200px;overflow-y:auto;font-family:monospace;white-space:pre-wrap;line-height:1.5">'+escH(res.text.substring(0,1500))+'</div>';
      if(res.fields_found?.length){html+='<div style="margin:8px 0 4px;font-size:10px;font-weight:700;color:var(--text2)">Gefundene Felder:</div><div style="display:flex;flex-wrap:wrap;gap:4px">'+res.fields_found.map(f=>'<span style="font-size:10px;padding:2px 7px;background:var(--green-bg);color:var(--green);border-radius:20px">'+escH(f)+'</span>').join('')+'</div>';}
      area.innerHTML=html;
    } else area.innerHTML='<div style="font-size:11px;color:var(--text2)">PDF geladen — bereit.</div>';
  }catch(e){area.innerHTML='<div style="font-size:11px;color:var(--text2)">PDF geladen — bereit.</div>';}
}
function fillInvFromProfile(){const o=$('inv-profile')?.selectedOptions[0];if(!o?.dataset.fn)return;if($('inv-fname'))$('inv-fname').value=o.dataset.fn;if($('inv-lname'))$('inv-lname').value=o.dataset.ln;if($('inv-street'))$('inv-street').value=o.dataset.st;if($('inv-city'))$('inv-city').value=o.dataset.ci;if($('inv-zip'))$('inv-zip').value=o.dataset.zp;}
function fillInvFromSerial(){const o=$('inv-serial')?.selectedOptions[0];if(!o?.dataset.prd)return;if($('inv-product'))$('inv-product').value=o.dataset.prd;}
async function saveInvTemplate(){
  if(!currentInvB64||!currentInvName){toast('Keine Datei geladen','err');return;}
  const name=prompt('Vorlagenname:',currentInvName);
  if(!name)return;
  const isDocx=window._invIsDocx||false;
  const res=await api('/api/invoice-templates','POST',{
    name,
    filename:currentInvName+(isDocx?'.docx':'.pdf'),
    data_b64:currentInvB64,
    file_type:isDocx?'docx':'pdf'
  });
  if(res.ok){toast('Vorlage gespeichert: '+name,'ok');renderInvTemplateList();}
  else toast('Fehler: '+(res.error||'?'),'err');
}
async function renderInvTemplateList(){
  const el=$('inv-templates-list');if(!el)return;
  el.innerHTML='<span class="spin"></span>';
  try{
    const templates=await api('/api/invoice-templates');
    if(!templates.length){el.innerHTML='<div class="empty" style="padding:16px">Noch keine Vorlagen.<br><small style="color:var(--text3)">Datei hochladen → Vorlage speichern</small></div>';return;}
    el.innerHTML=templates.map(t=>`
      <div style="display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid var(--border)">
        <span style="font-size:16px">${t.file_type==='docx'?'📝':'📄'}</span>
        <div style="flex:1;min-width:0">
          <div style="font-size:12px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escH(t.name)}</div>
          <div style="font-size:10px;color:var(--text3)">${escH(t.filename||'')} · ${t.created_at?new Date(t.created_at).toLocaleDateString('de'):''}</div>
        </div>
        <div style="display:flex;gap:4px;flex-shrink:0">
          <button class="btn xs pr" onclick="useInvTemplateById(${t.id},'${escH(t.name)}','${t.file_type}')">Laden</button>
          <button class="btn xs" onclick="renameInvTemplate(${t.id},'${escH(t.name)}')" title="Umbenennen">✏</button>
          <button class="btn xs da" onclick="deleteInvTemplate(${t.id},'${escH(t.name)}')" title="Löschen">🗑</button>
        </div>
      </div>`).join('');
  }catch(e){el.innerHTML='<div class="empty" style="padding:16px;color:var(--red)">Fehler beim Laden</div>';}
}
async function useInvTemplateById(id, name, fileType){
  const res=await api('/api/invoice-templates/'+id+'/data');
  if(!res.data_b64){toast('Fehler beim Laden','err');return;}
  currentInvB64=res.data_b64;
  currentInvName=name;
  window._invIsDocx=(fileType==='docx');
  const fc=$('inv-fields-card');if(fc)fc.style.display='';
  const ab=$('inv-analyze-btn');if(ab)ab.style.display='';
  const info=$('inv-pdf-info');
  if(info){
    const typeLabel=fileType==='docx'
      ?'<span style="color:var(--blue);background:var(--blue-bg);padding:1px 6px;border-radius:10px;font-size:10px">Word .docx</span>'
      :'<span style="color:var(--text3);background:var(--surface2);padding:1px 6px;border-radius:10px;font-size:10px">PDF</span>';
    info.innerHTML='✓ '+typeLabel+' <strong style="margin-left:4px">'+escH(name)+'</strong>';
  }
  if(fileType==='docx'){
    const area=$('inv-preview-area');
    if(area)area.innerHTML='<div style="padding:12px;background:var(--blue-bg);border-radius:var(--radius-sm);font-size:11px;color:var(--blue)"><strong>📝 Word-Vorlage geladen:</strong> '+escH(name)+'<br>Marker werden beim Erstellen ersetzt und als PDF ausgegeben.</div>';
  } else {
    showInvPreview(res.data_b64,name);
  }
  toast('Vorlage geladen: '+name,'ok');
}
async function renameInvTemplate(id, oldName){
  const name=prompt('Neuer Name:',oldName);
  if(!name||name===oldName)return;
  const res=await api('/api/invoice-templates/'+id,'PATCH',{name});
  if(res.ok){toast('Umbenannt','ok');renderInvTemplateList();}
  else toast('Fehler','err');
}
async function deleteInvTemplate(id, name){
  if(!confirm('Vorlage "'+name+'" löschen?'))return;
  await api('/api/invoice-templates/'+id,'DELETE');
  toast('Gelöscht','ok');
  renderInvTemplateList();
  // Falls aktuelle Vorlage gelöscht
  if(currentInvName===name){currentInvB64=null;currentInvName='';}
}
function toggleMarkersRef(){
  const el=$('markers-ref'),ar=$('markers-arrow');if(!el)return;
  const open=el.style.display!=='none';
  el.style.display=open?'none':'block';
  if(ar)ar.textContent=open?'▾':'▴';
  // Render markers list once
  const ml=$('markers-list');
  if(ml&&!ml.children.length){
    const markers=[["{{NAME}}","Vor- und Nachname"],["{{VORNAME}}","Vorname"],["{{NACHNAME}}","Nachname"],["{{STRASSE}}","Straße + Nr."],["{{ORT}}","Stadt"],["{{PLZ}}","Postleitzahl"],["{{PLZ_ORT}}","PLZ + Stadt"],["{{DATUM}}","Kaufdatum"],["{{RECHNUNGSNR}}","Rechnungsnummer"],["{{PRODUKT}}","Produktname"],["{{PREIS}}","Bruttopreis"],["{{BRUTTO}}","Bruttopreis"],["{{NETTO}}","Nettopreis"],["{{MWST}}","MwSt-Betrag"],["{{SERIAL}}","Seriennummer"]];
    ml.innerHTML=markers.map(([mk,desc])=>`<div style="display:flex;gap:6px;padding:3px 5px;border-radius:4px;background:var(--surface2)"><code style="color:var(--blue);font-size:9px;flex-shrink:0">${escH(mk)}</code><span style="color:var(--text3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escH(desc)}</span></div>`).join('');
  }
}
async function generateInvoice(){
  if(!currentInvB64&&!$('inv-fname')?.value){toast('Word/.docx hochladen oder Felder ausfüllen','err');return;}
  const isDocx=window._invIsDocx||false;
  const endpoint=isDocx?'/api/invoice/from-docx':'/api/invoice/generate';
  const b64key=isDocx?'docx_b64':'template_b64';
  const data={name:(($('inv-fname')?.value||'')+' '+($('inv-lname')?.value||'')).trim(),street:$('inv-street')?.value||'',city:$('inv-city')?.value||'',zip:$('inv-zip')?.value||'',product:$('inv-product')?.value||'',price:parseFloat($('inv-price')?.value||0),date:$('inv-date')?.value||'',number:$('inv-number')?.value||'',shop:'',ship_date:$('inv-ship-date')?.value||'',order_number:$('inv-order-number')?.value||'',country:'de'};
  data[b64key]=currentInvB64||null;
  const btn=$('inv-gen-btn'),result=$('inv-result');
  if(btn){btn.disabled=true;btn.textContent='⏳ Erstelle...';}
  if(result)result.innerHTML='<span class="spin"></span>';
  const res=await api(endpoint,'POST',data);
  if(btn){btn.disabled=false;btn.textContent='🧾 Rechnung erstellen';}
  if(res?.ok&&res.pdf_b64){
    const link=document.createElement('a');link.href='data:application/pdf;base64,'+res.pdf_b64;link.download='Rechnung_'+(data.number||'neu')+'_'+(data.name.replace(/ /g,'_'))+'.pdf';link.click();
    if(result)result.innerHTML='<span style="color:var(--green)">✓ Heruntergeladen! ('+res.method+')</span>';toast('Rechnung erstellt','ok');
  }else{if(result)result.innerHTML='<span style="color:var(--red)">✗ '+(res?.error||'Fehler')+'</span>';toast('Fehler','err');}
}
async function analyzeInvoice(){if(!currentInvB64)return;showInvPreview(currentInvB64,currentInvName);}

