// ── Monthly ───────────────────────────────────────────────────────────────────
async function loadMonthly(){
  const d=await api('/api/stats/monthly');const cur=d.current;
  const sr=cur.tickets>0?Math.round(cur.positive/cur.tickets*100):0;
  const mk=$('monthly-kpi');
  if(mk)mk.innerHTML=`<div class="stat"><div class="sv">${cur.serials_found}</div><div class="sl">Serials</div></div><div class="stat"><div class="sv">${cur.tickets}</div><div class="sl">Tickets</div></div><div class="stat cg"><div class="sv">${cur.positive}</div><div class="sl">Positiv</div></div><div class="stat cr"><div class="sv">${cur.negative}</div><div class="sl">Negativ</div></div><div class="stat cb"><div class="sv">${sr}%</div><div class="sl">Erfolgsrate</div></div><div class="stat cg"><div class="sv">${(cur.value||0).toFixed(0)}€</div><div class="sl">Wert</div></div>`;
  const ctx=$('monthly-chart')?.getContext('2d');
  if(ctx&&d.months.length){
    if(monthlyChart)monthlyChart.destroy();
    const rev=[...d.months].reverse();
    monthlyChart=new Chart(ctx,{type:'bar',data:{labels:rev.map(m=>m.month),datasets:[{label:'Gefunden',data:rev.map(m=>m.valid_found||0),backgroundColor:'rgba(42,110,53,.6)',borderRadius:3},{label:'Positiv',data:rev.map(m=>m.positive||0),backgroundColor:'rgba(26,95,165,.6)',borderRadius:3}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{boxWidth:10,font:{size:10}}}},scales:{x:{ticks:{color:'#888',font:{size:9}},grid:{display:false}},y:{ticks:{color:'#888',font:{size:9}}}}}});
  }
  const mt=$('monthly-table');
  if(mt)mt.innerHTML='<div style="display:grid;grid-template-columns:80px 1fr 1fr 1fr 1fr 1fr;padding:7px 12px;background:var(--surface2);font-size:10px;font-weight:700;color:var(--text2);text-transform:uppercase;border-bottom:1px solid var(--border)"><span>Monat</span><span>Serials</span><span>Tickets</span><span>Positiv</span><span>Wert</span><span>Rate</span></div>'+d.months.map(m=>`<div style="display:grid;grid-template-columns:80px 1fr 1fr 1fr 1fr 1fr;padding:8px 12px;border-bottom:1px solid var(--border);font-size:11px;align-items:center"><span style="font-weight:600">${m.month}</span><span style="color:var(--text2)">${m.valid_found||0}</span><span>${m.tickets||0}</span><span style="color:var(--green)">${m.positive||0}</span><span style="color:var(--green);font-weight:600">${(m.value||0).toFixed(0)}€</span><span style="color:var(--text3)">${m.tickets?Math.round((m.positive||0)/m.tickets*100):0}%</span></div>`).join('');
}

