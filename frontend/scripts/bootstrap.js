// ── Init ──────────────────────────────────────────────────────────────────────
async function init(){
  try{await loadDash();}catch(e){console.error('loadDash:',e);}
  try{await updateBell();}catch(e){}
  setInterval(async()=>{
    try{await loadDash();}catch(e){}
    const prev=parseInt($('bell-count')?.textContent||'0');
    try{await updateBell();}catch(e){}
    const curr=parseInt($('bell-count')?.textContent||'0');
    if(curr>prev&&'Notification'in window&&Notification.permission==='granted'){
      const n=new Notification('LogiCheck',{body:(curr-prev)+' neue Mail(s)'});setTimeout(()=>n.close(),4000);
    }
  },30000);
}

async function start(){
  try{if(localStorage&&localStorage.getItem('sb_collapsed')==='1')collapseSidebar();}catch(e){}
  const authed=await checkAuth();
  if(authed)init();
}
start();

