// ── Dashboard ─────────────────────────────────────────────────────────────────
let dpData=[], dpSort={col:'valid',dir:-1};

async function loadDash(){
  try{stats=await api('/api/stats');}catch(e){
    $('sg').innerHTML='<div style="color:var(--red);font-size:12px;padding:10px">Verbindungsfehler — '+e.message+'</div>';return;
  }
  $('dot').className='dot'+(stats.scanner_running?' on':'');
  const chk=(stats.total_checked||0).toLocaleString('de');
  const est=(stats.estimated_total||0).toLocaleString('de');
  const pct=Math.min(stats.progress_pct||0,100);

  // Stats row
  const sg=$('sg');
  if(sg) sg.innerHTML=
    '<div class="stat cg"><div class="sv">'+( stats.valid||0)+'</div><div class="sl">Gültig</div></div>'+
    '<div class="stat ca"><div class="sv">'+(stats.registered||0)+'</div><div class="sl">Registriert</div></div>'+
    '<div class="stat"><div class="sv">'+(stats.total||0)+'</div><div class="sl">Gesamt</div></div>'+
    '<div class="stat cb"><div class="sv">'+chk+'</div><div class="sl">Geprüft</div></div>';

  // Scanner card
  const sc=$('sc');
  if(sc){
    const running=stats.scanner_running;
    const ys=stats.year_start||23, ye=stats.year_end||26;
    const hitRate=stats.total>0?((stats.valid/stats.total)*100).toFixed(1):0;
    const statusDot=running
      ?'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#22c55e;margin-right:5px;box-shadow:0 0 0 3px rgba(34,197,94,.2)"></span><span style="color:var(--green);font-weight:600">Läuft</span>'
      :'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--text3);margin-right:5px"></span><span style="color:var(--text3)">Gestoppt</span>';

    sc.innerHTML=
      // Header row
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'+
        '<div style="display:flex;align-items:center;gap:8px">'+statusDot+
          '<span style="font-size:10px;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.5px">Scanner</span>'+
        '</div>'+
        '<div style="display:flex;gap:5px;align-items:center">'+
          '<span style="font-size:10px;color:var(--text3)">Jahr:</span>'+
          '<input type="number" id="sys2" value="'+ys+'" min="20" max="30" style="width:46px;padding:2px 5px;font-size:11px;text-align:center">'+
          '<span style="font-size:10px;color:var(--text3)">–</span>'+
          '<input type="number" id="sye2" value="'+ye+'" min="20" max="30" style="width:46px;padding:2px 5px;font-size:11px;text-align:center">'+
          '<button class="btn xs" onclick="setYears()">OK</button>'+
        '</div>'+
      '</div>'+
      // Progress bar
      '<div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text2);margin-bottom:4px">'+
        '<span><strong style="color:var(--text);font-size:12px">'+chk+'</strong> geprüft von ~'+est+'</span>'+
        '<span style="font-weight:700;color:var(--blue)">'+pct.toFixed(5)+'%</span>'+
      '</div>'+
      '<div style="height:6px;background:var(--surface3);border-radius:3px;overflow:hidden;margin-bottom:10px">'+
        '<div style="height:100%;width:'+pct+'%;background:linear-gradient(90deg,var(--blue),#4a90d9);border-radius:3px;transition:width 1s ease"></div>'+
      '</div>'+
      // Mini stats
      '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:10px">'+
        '<div style="text-align:center;padding:5px;background:var(--green-bg);border-radius:var(--radius-sm)"><div style="font-size:14px;font-weight:700;color:var(--green)">'+(stats.valid||0)+'</div><div style="font-size:9px;color:var(--text3)">Gültig</div></div>'+
        '<div style="text-align:center;padding:5px;background:var(--amber-bg);border-radius:var(--radius-sm)"><div style="font-size:14px;font-weight:700;color:var(--amber)">'+(stats.registered||0)+'</div><div style="font-size:9px;color:var(--text3)">Registriert</div></div>'+
        '<div style="text-align:center;padding:5px;background:var(--surface2);border-radius:var(--radius-sm)"><div style="font-size:14px;font-weight:700;color:var(--text)">'+(stats.total||0)+'</div><div style="font-size:9px;color:var(--text3)">Gesamt</div></div>'+
        '<div style="text-align:center;padding:5px;background:var(--blue-bg);border-radius:var(--radius-sm)"><div style="font-size:14px;font-weight:700;color:var(--blue)">'+hitRate+'%</div><div style="font-size:9px;color:var(--text3)">Trefferrate</div></div>'+
      '</div>'+
      // Controls row
      '<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">'+
        '<span class="ls" style="flex:1;font-size:10px">'+(stats.last_serial||'Noch nichts gescannt')+'</span>'+
        '<label style="font-size:10px;color:var(--text2)">Pause(s):</label>'+
        '<input type="number" id="di" value="'+(stats.scan_delay||5)+'" min="2" max="120" style="width:48px;padding:3px 6px;font-size:11px">'+
        '<button class="btn xs" onclick="setDelay()">OK</button>'+
        (running
          ? '<button class="btn da sm" onclick="tgScan(false)">■ Stoppen</button>'
          : '<button class="btn su sm" onclick="tgScan(true)">▶ Starten</button>')+
        '<button class="btn xs" onclick="rstScan()" title="Scanner zurücksetzen und von vorne beginnen">↺ Reset</button>'+
      '</div>';
  }
  loadProducts(true);
  loadNewestSerials();
}

async function loadNewestSerials(){
  const nb=$('dp-newest-body');if(!nb)return;
  try{
    const data=await api('/api/serials?page=1&limit=10');
    const items=Array.isArray(data)?data:(data.items||[]);
    if(!items.length){nb.innerHTML='<tr><td class="empty" colspan="4">Keine Serials</td></tr>';return;}
    nb.innerHTML=items.map(s=>`<tr onclick="go('serials')" style="cursor:pointer;border-top:1px solid var(--border);transition:.1s" onmouseover="this.style.background='var(--surface2)'" onmouseout="this.style.background=''">
      <td style="padding:5px 10px;font-family:monospace;font-size:10px;font-weight:600">${escH(s.serial)}</td>
      <td style="padding:5px 8px">${sp(s.status)}</td>
      <td style="padding:5px 8px;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:10px;color:var(--text2)">${escH(s.product||'—')}</td>
      <td style="padding:5px 8px;font-size:10px;color:var(--text3)">${s.checked_at?new Date(s.checked_at).toLocaleDateString('de',{day:'2-digit',month:'2-digit'}):''}</td>
    </tr>`).join('');
  }catch(e){}
}
async function tgScan(s){await api('/api/scanner/'+(s?'start':'stop'),'POST');toast(s?'Gestartet':'Gestoppt','ok');loadDash();}
async function setYears(){
  const ys=parseInt($('sys2')?.value||23);
  const ye=parseInt($('sye2')?.value||26);
  if(ys>ye){toast('Jahr von muss kleiner sein','err');return;}
  await api('/api/scanner/years','POST',{year_start:ys,year_end:ye});
  toast('Jahre gesetzt: 20'+ys+'–20'+ye,'ok');
  loadDash();
}
async function rstScan(){if(!confirm('Von vorne?'))return;await api('/api/scanner/reset','POST');toast('Reset','ok');loadDash();}
async function setDelay(){const v=parseInt($('di').value);if(v<2||v>120){toast('2–120s','err');return;}await api('/api/scanner/delay/'+v,'POST');toast('Pause: '+v+'s','ok');}

