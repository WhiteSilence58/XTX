// ── Stats ─────────────────────────────────────────────────────────────────────
async function loadStats2(){
  const d=await api('/api/stats/detailed');
  const ctx=$('cd')?.getContext('2d');
  if(ctx){
    if(chartD)chartD.destroy();
    chartD=new Chart(ctx,{type:'bar',data:{labels:d.daily.map(x=>x.day),datasets:[{label:'Gültig',data:d.daily.map(x=>x.valid),backgroundColor:'rgba(42,110,53,.7)',borderRadius:3},{label:'Reg.',data:d.daily.map(x=>x.registered),backgroundColor:'rgba(122,74,10,.5)',borderRadius:3}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{boxWidth:10,font:{size:10}}}},scales:{x:{ticks:{color:'#888',font:{size:9}},grid:{display:false}},y:{ticks:{color:'#888',font:{size:9}},grid:{color:'rgba(128,128,128,.08)'}}}}});
  }
  const tpl=$('tpl');if(tpl)tpl.innerHTML=d.top_products.map(p=>`<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--border);font-size:11px"><span class="wrap" style="max-width:180px">${escH(p.product||'—')}</span><span style="color:var(--green);font-weight:700">${p.valid}/${p.count}</span></div>`).join('')||'<div class="empty" style="padding:16px">Keine Daten</div>';
  const wl=$('wl');if(wl)wl.innerHTML=d.werk_stats.map(w=>`<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--border);font-size:11px"><span class="mono">${w.werk}</span><span>${w.valid}/${w.total} <strong style="color:var(--blue)">${w.hit_rate}%</strong></span></div>`).join('')||'<div class="empty" style="padding:16px">Keine Daten</div>';
  const al=$('al');if(al)al.innerHTML=d.agents.length?d.agents.map(a=>`<div style="padding:5px 0;border-bottom:1px solid var(--border);font-size:11px"><div style="display:flex;justify-content:space-between"><span>${escH(a.agent_name||'?')}</span><span style="color:var(--text2)">${a.total}</span></div><div style="display:flex;gap:5px;margin-top:2px"><span class="pill pp">${a.positive}+</span><span class="pill pn">${a.negative}-</span><span style="font-size:10px;color:var(--text3)">${a.total?Math.round(a.positive/a.total*100):0}%</span></div></div>`).join(''):'<div class="empty" style="padding:16px">Noch keine</div>';
  const vt=$('vt');if(vt)vt.innerHTML=`<div style="font-size:26px;font-weight:700;color:var(--green)">${(d.value_min||0).toFixed(0)}–${(d.value_max||0).toFixed(0)} €</div><div style="font-size:11px;color:var(--text2);margin-top:4px">Geschätzter Gesamtwert</div>`;
}

