// ── Products ──────────────────────────────────────────────────────────────────
async function loadProducts(dashOnly=false){
  const [products,pvs]=await Promise.all([api('/api/products'),api('/api/product-values')]);
  const pvm={};pvs.forEach(p=>pvm[p.part_number]=p);
  window._dpPvm=pvm;
  dpData=products;

  // Full products page: grid cards
  if(!dashOnly){
    const el=$('pg');
    if(el){
      if(!products.length){el.innerHTML='<div class="empty">Noch keine Produkte</div>';}
      else el.innerHTML=products.map(p=>{
        const pv=pvm[p.part_number]||{};
        return`<div class="pc" onclick="filterByP('${(p.product||'').replace(/'/g,"\\'")}')">
          <h3>${escH(p.product||'—')}</h3>
          <div class="sub">${escH(p.product_type||'')}${p.part_number?' · '+p.part_number:''}</div>
          <div style="display:flex;gap:5px;flex-wrap:wrap;margin-top:6px">
            <span class="pill pv">${p.valid} gültig</span>
            ${p.registered?'<span class="pill pr2">'+p.registered+' reg.</span>':''}
            ${pv.val_min?'<span class="vb">'+pv.val_min+'–'+pv.val_max+'€</span>':''}
          </div>
        </div>`;
      }).join('');
    }
  }
  // Dashboard table
  filterDpTable();
}
function filterByP(name){go('serials');const ss=$('ss');if(ss)ss.value=name;loadSerials(1);}

function filterDpTable(){
  const s=($('dp-search')?.value||'').toLowerCase();
  const filtered=s?dpData.filter(p=>(p.product||'').toLowerCase().includes(s)):dpData;
  renderDpTable(filtered);
}
function sortDpTable(col){
  if(dpSort.col===col)dpSort.dir*=-1;
  else{dpSort.col=col;dpSort.dir=-1;}
  document.querySelectorAll('.dp-sort-icon').forEach(el=>{
    el.textContent=el.dataset.col===col?(dpSort.dir===-1?'↓':'↑'):'↕';
    el.style.opacity=el.dataset.col===col?'1':'0.3';
  });
  filterDpTable();
}
function renderDpTable(data){
  const pvm=window._dpPvm||{};
  const sorted=[...data].sort((a,b)=>{
    const col=dpSort.col;
    if(col==='product'){
      const pa=(a.product||'').toLowerCase(), pb=(b.product||'').toLowerCase();
      return dpSort.dir*(pa<pb?-1:pa>pb?1:0);
    }
    const va=col==='valid'?a.valid:col==='registered'?a.registered||0:col==='val'?(pvm[a.part_number]?.val_max||0):0;
    const vb=col==='valid'?b.valid:col==='registered'?b.registered||0:col==='val'?(pvm[b.part_number]?.val_max||0):0;
    return dpSort.dir*(vb-va);
  });
  const dp=$('dp-body');if(!dp)return;
  dp.innerHTML='';
  if(!sorted.length){dp.innerHTML='<tr><td colspan="4" class="empty">Keine Produkte</td></tr>';return;}
  sorted.forEach(p=>{
    const pv=pvm[p.part_number]||{};
    const pct=p.total?Math.round(p.valid/p.total*100):0;
    const tr=document.createElement('tr');
    tr.style.cssText='cursor:pointer;border-top:1px solid var(--border);transition:.1s';
    tr.onmouseover=()=>{tr.style.background='var(--surface2)';};
    tr.onmouseout=()=>{tr.style.background='';};
    tr.onclick=()=>filterByP(p.product||'');
    const tdProd=document.createElement('td');
    tdProd.style.cssText='padding:5px 10px;width:50%';
    const nameDiv=document.createElement('div');
    nameDiv.style.cssText='font-size:11px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:280px';
    nameDiv.textContent=p.product||'—';
    const barWrap=document.createElement('div');
    barWrap.style.cssText='height:2px;background:var(--surface3);border-radius:2px;margin-top:3px';
    const barFill=document.createElement('div');
    barFill.style.cssText='height:100%;width:'+pct+'%;background:var(--green);border-radius:2px';
    barWrap.appendChild(barFill);
    tdProd.appendChild(nameDiv);
    tdProd.appendChild(barWrap);
    const tdV=document.createElement('td');
    tdV.style.cssText='padding:5px 10px;text-align:right;color:var(--green);font-weight:600;white-space:nowrap';
    tdV.textContent=p.valid;
    const tdR=document.createElement('td');
    tdR.style.cssText='padding:5px 10px;text-align:right;color:var(--amber);white-space:nowrap';
    tdR.textContent=p.registered||'—';
    const tdW=document.createElement('td');
    tdW.style.cssText='padding:5px 10px;text-align:right;white-space:nowrap';
    if(pv.val_min){const vb=document.createElement('span');vb.className='vb';vb.textContent=pv.val_min+'–'+pv.val_max+'€';tdW.appendChild(vb);}
    else tdW.textContent='—';
    tr.appendChild(tdProd);tr.appendChild(tdV);tr.appendChild(tdR);tr.appendChild(tdW);
    dp.appendChild(tr);
  });
}
