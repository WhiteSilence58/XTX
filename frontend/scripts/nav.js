// ── Nav ───────────────────────────────────────────────────────────────────────
const TABS={dash:0,inbox:1,serials:2,products:3,stats:4,rma:5,identities:6,settings:7,monthly:8,check:9,compose:10,invoice:11};
function go(n){
  document.querySelectorAll('[id^="tab-"]').forEach(t=>t.style.display='none');
  const tab=$('tab-'+n);if(tab)tab.style.display='';
  // Update sidebar active state
  document.querySelectorAll('.sb-item').forEach(b=>b.classList.remove('active'));
  const sbItem=$('sb-'+n);if(sbItem)sbItem.classList.add('active');
  closeBell();
  // Close mobile sidebar
  const sb=$('sidebar');if(sb&&sb.classList.contains('mobile-open'))closeSidebar();
  if(n==='inbox'){loadInbox();loadFolders();}
  if(n==='serials')loadSerials(1);
  if(n==='products')loadProducts();
  if(n==='stats')loadStats2();
  if(n==='rma')loadRMA();
  if(n==='identities')loadIdsTab();
  if(n==='settings')loadSettingsTab();
  if(n==='monthly')loadMonthly();
  if(n==='compose')loadComposePage();
  if(n==='invoice')loadInvoicePage();
}

let sidebarCollapsed = false;
function collapseSidebar(){
  sidebarCollapsed=!sidebarCollapsed;
  const sb=$('sidebar');const ic=$('collapse-icon');
  if(sb)sb.classList.toggle('collapsed',sidebarCollapsed);
  if(ic)ic.textContent=sidebarCollapsed?'▶':'◀';
  localStorage&&localStorage.setItem('sb_collapsed',sidebarCollapsed?'1':'0');
}
function toggleSidebar(){
  const sb=$('sidebar'),ov=$('sb-overlay');
  if(!sb)return;
  const open=sb.classList.contains('mobile-open');
  sb.classList.toggle('mobile-open',!open);
  if(ov)ov.classList.toggle('visible',!open);
}
function closeSidebar(){
  const sb=$('sidebar'),ov=$('sb-overlay');
  if(sb)sb.classList.remove('mobile-open');
  if(ov)ov.classList.remove('visible');
}

