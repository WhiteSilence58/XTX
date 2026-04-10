// ── Auth ──────────────────────────────────────────────────────────────────────
async function checkAuth(){
  try{const r=await fetch('/api/auth/check');const d=await r.json();if(!d.logged_in){showLogin(!d.has_password);return false;}hideLogin();return true;}
  catch(e){hideLogin();return true;}
}
function showLogin(isFirst=false){
  const ov=$('login-overlay');ov.style.display='flex';
  if(isFirst){$('login-form').style.display='none';$('first-login-form').style.display='';$('login-subtitle').textContent='Ersteinrichtung';}
  else{$('login-form').style.display='';$('first-login-form').style.display='none';setTimeout(()=>$('l-pass')?.focus(),100);}
}
function hideLogin(){const ov=$('login-overlay');if(ov)ov.style.display='none';}
async function doLogin(){
  const user=$('l-user').value,pass=$('l-pass').value,err=$('login-err');err.textContent='';
  try{const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:user,password:pass})});
  const d=await r.json();if(d.ok){hideLogin();init();}else err.textContent=d.error||'Falsches Passwort';}
  catch(e){err.textContent='Verbindungsfehler';}
}
async function setFirstPassword(){
  const user=$('fl-user').value,pass=$('fl-pass').value,pass2=$('fl-pass2').value,err=$('fl-err');err.textContent='';
  if(pass!==pass2){err.textContent='Passwörter stimmen nicht überein';return;}
  if(pass.length<4){err.textContent='Mindestens 4 Zeichen';return;}
  const lr=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:user,password:''})});
  const ld=await lr.json();if(!ld.ok){err.textContent='Login fehlgeschlagen';return;}
  const sr=await fetch('/api/auth/set-password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:user,password:pass})});
  const sd=await sr.json();if(sd.ok){hideLogin();toast('Passwort gesetzt','ok');init();}else err.textContent='Fehler';
}
async function doLogout(){await fetch('/api/logout',{method:'POST'});showLogin(false);}

