// ── State ─────────────────────────────────────────────────────────────────────
let aS=[],aF='',rmaD=[],rmaF2='',stats={};
let inboxD=[],inboxUnread=false,inboxStarred=false,curMailId=null;
let selectedMails=new Set(),bellOpen=false,chartD=null,monthlyChart=null;
let sCurPage=1,sTotalPages=1,sDebounce=null;

const $=id=>document.getElementById(id);
const api=async(p,m='GET',b=null)=>{
  const o={method:m,headers:{'Content-Type':'application/json'}};
  if(b)o.body=JSON.stringify(b);
  const r=await fetch(p,o);
  if(r.status===401){showLogin(false);throw new Error('Nicht angemeldet');}
  return r.json();
};
function toast(msg,t=''){const el=document.createElement('div');el.className='toast';el.style.borderLeft=t==='ok'?'3px solid var(--green)':t==='err'?'3px solid var(--red)':'';el.textContent=msg;document.body.appendChild(el);setTimeout(()=>el.remove(),2700);}
const sp=s=>s==='valid'?'<span class="pill pv">Gültig</span>':s==='registered'?'<span class="pill pr2">Registriert</span>':'<span class="pill pi">Ungültig</span>';
const wp=s=>s==='active'?'<span class="pill pb">Aktiv</span>':s==='expired'?'<span class="pill pn">Abgelaufen</span>':'';
function escH(s){return(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function extractTicketNum(text){const p=[/Ticket\s*(?:Number|Nr|#|ID)?[:\s#]+(\d{6,10})/i,/Fallnummer[:\s]+(\d{6,10})/i,/#(\d{7,10})/];for(const r of p){const m=(text||'').match(r);if(m)return m[1];}return'';}
function shortFrom(f){if(!f)return'—';const m=f.match(/"?([^"<]+)"?\s*<?/);return(m?m[1]:f).trim().substring(0,28);}
function fmtS(d){if(!d)return'';try{const dt=new Date(d),now=new Date();return(now-dt)<86400000?dt.toLocaleTimeString('de',{hour:'2-digit',minute:'2-digit'}):dt.toLocaleDateString('de',{day:'2-digit',month:'2-digit'});}catch{return'';}}

