#!/usr/bin/env python3
"""
Ryzek AI v2.6 - the sign-in screen.

A single page that handles both signing in and creating an account, in the same
visual language as the app (dark panel, pink-violet gradient, same credit line).
No external assets: everything is inline so it also works inside the Android
WebView and offline.
"""

LOGIN_HTML = r"""<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{{NAME}} · Sign in</title>
<style>
:root{
  --bg:#070910;--panel:#0c101b;--panel2:#111625;--line:#222b42;--txt:#e8ecf8;
  --muted:#98a2c0;--a:#ff5fa8;--a2:#8a7bff;--ok:#39d98a;--bad:#ff6b7a;
}
*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0;background:
    radial-gradient(900px 520px at 12% -10%, #ff5fa81f, transparent 60%),
    radial-gradient(760px 520px at 100% 0%, #8a7bff1f, transparent 55%),
    var(--bg);
  color:var(--txt);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,
  "Helvetica Neue",Arial,sans-serif;display:flex;align-items:center;justify-content:center;
  padding:24px;min-height:100dvh;
}
.card{
  width:100%;max-width:430px;background:linear-gradient(180deg,#101625ee,#0a0e17ee);
  border:1px solid var(--line);border-radius:22px;padding:26px 24px 20px;
  box-shadow:0 28px 80px #000a, inset 0 1px 0 #ffffff0d;
}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:18px}
.logo{
  width:46px;height:46px;border-radius:14px;display:grid;place-items:center;
  font-weight:800;font-size:22px;color:#120c1a;
  background:linear-gradient(135deg,var(--a),var(--a2));
  box-shadow:0 8px 24px #ff5fa833;
}
.brand-name{font-size:19px;font-weight:750;letter-spacing:.2px}
.brand-sub{font-size:10.5px;letter-spacing:.16em;color:var(--muted);text-transform:uppercase}
.ver{margin-left:auto;font-size:11px;color:var(--muted);border:1px solid var(--line);
  border-radius:8px;padding:3px 8px}
h1{font-size:20px;margin:6px 0 4px}
.sub{color:var(--muted);font-size:12.5px;margin-bottom:18px}
.tabs{display:flex;gap:6px;background:#0a0e18;border:1px solid var(--line);
  border-radius:12px;padding:4px;margin-bottom:16px}
.tab{flex:1;border:0;background:transparent;color:var(--muted);font-weight:600;
  padding:9px;border-radius:9px;cursor:pointer;font-size:13px}
.tab.on{background:linear-gradient(135deg,#ff5fa826,#8a7bff26);color:var(--txt);
  box-shadow:inset 0 0 0 1px #ffffff14}
label{display:block;font-size:12px;color:var(--muted);margin:12px 0 6px;font-weight:600}
input{
  width:100%;background:#080c14;border:1px solid var(--line);color:var(--txt);
  border-radius:11px;padding:12px 13px;font-size:14px;outline:none;transition:.15s;
}
input:focus{border-color:var(--a);box-shadow:0 0 0 3px #ff5fa822}
input::placeholder{color:#5c6784}
.btn{
  width:100%;margin-top:18px;border:0;border-radius:12px;padding:13px;font-size:14.5px;
  font-weight:700;cursor:pointer;color:#150c1d;
  background:linear-gradient(135deg,var(--a),var(--a2));
  box-shadow:0 10px 30px #ff5fa833;transition:.15s;
}
.btn:hover{filter:brightness(1.06)}
.btn:disabled{opacity:.6;cursor:progress}
.msg{margin-top:14px;font-size:12.5px;border-radius:10px;padding:10px 12px;display:none}
.msg.bad{display:block;background:#ff6b7a15;border:1px solid #ff6b7a44;color:#ffb3bb}
.msg.ok{display:block;background:#39d98a15;border:1px solid #39d98a44;color:#a8f0c8}
.hint{margin-top:16px;font-size:11.5px;color:#6b7590;line-height:1.6}
.hint b{color:#9aa4c2;font-weight:600}
.role{margin-top:14px;font-size:11.5px;color:#6b7590}
.foot{margin-top:18px;padding-top:14px;border-top:1px solid var(--line);
  font-size:11px;color:#6b7590;text-align:center;line-height:1.7}
.foot b{color:#9aa4c2}
.admin{margin-top:12px;background:#0a0e18;border:1px solid var(--line);border-radius:11px;
  padding:10px 12px;font-size:11.5px;color:#7f8aab;display:none}
.admin.on{display:block}
.admin code{background:#141a28;border-radius:5px;padding:1px 5px;color:#c9d2ee}
@media(max-width:420px){.card{padding:22px 18px 16px;border-radius:18px}}
</style>
</head>
<body>
<form class="card" id="card" autocomplete="on">
  <div class="brand">
    <div class="logo">R</div>
    <div>
      <div class="brand-name">{{NAME}}</div>
      <div class="brand-sub">Accounts &amp; memory</div>
    </div>
    <span class="ver">v{{VERSION}}<span id="buildstamp" title="build"> · 261</span></span>
  </div>

  <div class="tabs" role="tablist">
    <button type="button" class="tab on" id="tabLogin" data-mode="login">Sign in</button>
    <button type="button" class="tab" id="tabSignup" data-mode="signup">Create account</button>
  </div>

  <h1 id="headline">Welcome back</h1>
  <div class="sub" id="subline">Sign in to keep your chats and memory on this account.</div>

  <label for="username">Username</label>
  <input id="username" name="username" placeholder="e.g. ali.khan" autocomplete="username"
         autocapitalize="none" spellcheck="false" required>

  <div id="nameRow" style="display:none">
    <label for="displayName">Your name (shown in the app)</label>
    <input id="displayName" name="displayName" placeholder="e.g. Ali Khan" autocomplete="name">
  </div>

  <label for="password">Password</label>
  <input id="password" name="password" type="password" placeholder="At least 6 characters"
         autocomplete="current-password" required>

  <button class="btn" id="submit" type="submit">Sign in</button>
  <div class="msg" id="msg"></div>

  <div class="admin" id="adminBox">
    <b>First time on this server?</b> The main author account is created automatically:
    username <code>ryzek</code>, password <code>ryzek20</code>. Change it after you sign in -
    Settings, <i>Change my password</i>.
  </div>

  <div class="role">One account is the <b>author</b> (owner). Everyone else creates a normal
  account with their own name and password. Passwords are salted and hashed with PBKDF2 in a
  local SQLite database - never stored as plain text.</div>

  <div class="foot">
    Made by <b>Rasakh Mohsin</b> aka <b>Ryzek_20</b><br>
    AI can also make mistakes.
  </div>
</form>

<script>
(function(){
  'use strict';
  var $=function(s){return document.querySelector(s);};
  var mode='login';
  var msg=$('#msg'), btn=$('#submit');

  // No auto-redirect here on purpose (v2.6.1). The old code redirected
  // whenever a stored token looked valid, but a page load cannot send that
  // header, so "/" kept returning this page and the browser looped forever.
  // The server now sets an HttpOnly cookie on sign-in and checks it on "/",
  // so a signed-in visitor never reaches this screen at all.
  try{ localStorage.removeItem('ryzek_token'); }catch(e){}

  function setMode(next){
    mode=next;
    $('#tabLogin').classList.toggle('on',next==='login');
    $('#tabSignup').classList.toggle('on',next==='signup');
    $('#nameRow').style.display=next==='signup'?'block':'none';
    $('#headline').textContent=next==='signup'?'Create your account':'Welcome back';
    $('#subline').textContent=next==='signup'
      ? 'Your own chats, your own memory. Nothing is shared with other accounts.'
      : 'Sign in to keep your chats and memory on this account.';
    btn.textContent=next==='signup'?'Create account':'Sign in';
    $('#password').setAttribute('autocomplete',next==='signup'?'new-password':'current-password');
    hide();
  }

/* ---------- device fingerprint (one account per person) ----------
   A stable, non-tracking hash of this browser's own traits. It survives
   clearing cookies and using a private window, so the same person cannot
   keep making accounts. Nothing about it leaves this server. */
function deviceId(){
  var parts=[
    navigator.userAgent||'', navigator.platform||'', navigator.language||'',
    (navigator.languages||[]).join(','), screen.width+'x'+screen.height,
    screen.colorDepth||'', (new Date().getTimezoneOffset())||'', navigator.hardwareConcurrency||'',
    navigator.deviceMemory||'', navigator.maxTouchPoints||''
  ];
  try{
    var c=document.createElement('canvas');c.width=220;c.height=40;
    var g=c.getContext('2d');g.textBaseline='top';g.font='15px Arial';
    g.fillStyle='#f60';g.fillRect(0,0,90,22);g.fillStyle='#069';
    g.fillText('Ryzek-2.6-device',2,4);parts.push(c.toDataURL().slice(-96));
  }catch(e){}
  var str=parts.join('|'), h1=0x811c9dc5, h2=0x1000193;
  for(var i=0;i<str.length;i++){
    var ch=str.charCodeAt(i);
    h1^=ch; h1=(h1*0x01000193)>>>0;
    h2=(h2*33+ch)>>>0;
  }
  return ('00000000'+h1.toString(16)).slice(-8)+('00000000'+h2.toString(16)).slice(-8);
}
var DEVICE=deviceId();
try{localStorage.setItem('ryzek_device',DEVICE);}catch(e){}

  function show(kind,text){
    msg.className='msg '+kind; msg.textContent=text;
  }
  function hide(){ msg.className='msg'; msg.textContent=''; }

  $('#tabLogin').onclick=function(){setMode('login');};
  $('#tabSignup').onclick=function(){setMode('signup');};

  // Show the author-account hint until somebody has signed in at least once.
  if(location.search.indexOf('first')>=0){ $('#adminBox').classList.add('on'); }
  if(location.search.indexOf('expired')>=0){
    show('bad','You were signed out. Please sign in again.');
  }

  $('#card').addEventListener('submit',function(ev){
    ev.preventDefault();
    hide();
    var username=$('#username').value.trim();
    var password=$('#password').value;
    var display=$('#displayName').value.trim();
    if(!username||!password){ show('bad','Please fill in both fields.'); return; }
    if(mode==='signup'&&password.length<6){
      show('bad','Password must be at least 6 characters.'); return;
    }
    btn.disabled=true;
    var url=mode==='signup'?'/api/signup':'/api/login';
    fetch(url,{
      method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({username:username,password:password,display_name:display,device:DEVICE})
    }).then(function(r){return r.json().then(function(d){return {ok:r.ok,d:d};});})
      .then(function(res){
        btn.disabled=false;
        if(!res.ok||!res.d.ok){
          show('bad',(res.d&&res.d.error)||'Something went wrong.'); return;
        }
        try{
          localStorage.setItem('ryzek_token',res.d.token);
          localStorage.setItem('ryzek_user',JSON.stringify(res.d.user||{}));
          localStorage.removeItem('ryzek_sid');
        }catch(e){}
        show('ok','Signed in. Loading your chats...');
        // Navigate. If the browser keeps the session cookie we go to a clean
        // "/"; if cookies are blocked we carry the token in the URL instead.
        // Probing the cookie first means the token never lands in the address
        // bar unless it has to.
        var t=res.d.token;
        fetch('/api/me',{headers:{'Authorization':'Bearer '+t},credentials:'same-origin'})
          .then(function(r){
            if(r.ok){ location.replace('/'); }
            else { location.replace('/?t='+encodeURIComponent(t)); }
          })
          .catch(function(){ location.replace('/?t='+encodeURIComponent(t)); });
      }).catch(function(){
        btn.disabled=false;
        show('bad','Could not reach the server. Is it still running?');
      });
  });
})();
</script>
</body>
</html>
"""
