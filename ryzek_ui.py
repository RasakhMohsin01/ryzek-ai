"""Ryzek AI v2 - single-file web interface (inline CSS/JS, no external assets).

Kept in its own module so ryzek_ai.py stays readable. The server replaces
{{NAME}} / {{VERSION}} before serving.
"""

from ryzek_login import LOGIN_HTML  # noqa: E402

INDEX_HTML = r"""<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{NAME}} · Advanced Research Agent</title>
<style>
:root[data-theme="dark"]{
  --bg:#070910;--panel:#0c101b;--panel2:#111625;--line:#222b42;--txt:#e9edf9;--muted:#8792ad;
  --a:#8b5cf6;--b:#22d3ee;--ok:#34d399;--warn:#fbbf24;--user:#243050;--code:#090d17;
  --shadow:0 12px 40px #00000055;
}
:root[data-theme="light"]{
  --bg:#f3f6fc;--panel:#ffffff;--panel2:#f7f9ff;--line:#dce3f1;--txt:#182138;--muted:#5e6883;
  --a:#6d3df5;--b:#0891b2;--ok:#059669;--warn:#c2740a;--user:#e7ebff;--code:#f1f4fc;
  --shadow:0 12px 34px #1c25401c;
}
/* Each answer depth gets its own accent theme. Set from JS on <html data-depth>. */
:root[data-depth="quick"]{--a:#f59e0b;--b:#fbbf24;--ok:#fbbf24;--glow:rgba(245,158,11,.16)}
:root[data-depth="standard"]{--a:#10b981;--b:#14b8a6;--ok:#10b981;--glow:rgba(16,185,129,.15)}
:root[data-depth="deep"]{--a:#8b5cf6;--b:#22d3ee;--ok:#34d399;--glow:rgba(139,92,246,.16)}
:root[data-depth="exhaustive"]{--a:#f43f5e;--b:#c084fc;--ok:#34d399;--glow:rgba(244,63,94,.14)}
:root{--glow:rgba(139,92,246,.16)}
:root[data-theme="light"][data-depth="quick"]{--a:#d97706;--b:#b45309;--glow:rgba(217,119,6,.13)}
:root[data-theme="light"][data-depth="standard"]{--a:#059669;--b:#0f766e;--glow:rgba(5,150,105,.12)}
:root[data-theme="light"][data-depth="deep"]{--a:#6d3df5;--b:#0891b2;--glow:rgba(109,61,245,.12)}
:root[data-theme="light"][data-depth="exhaustive"]{--a:#e11d48;--b:#9333ea;--glow:rgba(225,29,72,.11)}
html[data-depth]{transition:background-color .35s ease}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--txt);font:14.5px/1.65 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Inter,Arial,sans-serif;overflow:hidden}
button,input,select,textarea{font:inherit}
button{cursor:pointer}
::-webkit-scrollbar{width:9px;height:9px}
::-webkit-scrollbar-thumb{background:var(--line);border-radius:9px}
::-webkit-scrollbar-track{background:transparent}

.app{display:grid;grid-template-columns:274px minmax(0,1fr);grid-template-rows:minmax(0,1fr);height:100vh;height:100dvh;overflow:hidden}

/* The scrim is fixed + hidden by default so it can NEVER become a grid item.
   (An unstyled grid child here would push .main into a second row - the exact
   layout bug this rule prevents.) */
.scrim{position:fixed;inset:0;background:#04060cbb;backdrop-filter:blur(3px);display:none;z-index:25}
.scrim.on{display:block}

/* ---------------- sidebar ---------------- */
.sidebar{grid-column:1;grid-row:1;background:linear-gradient(180deg,var(--panel),var(--panel2));border-right:1px solid var(--line);display:flex;flex-direction:column;min-height:0;min-width:0;z-index:30}
.brand{display:flex;align-items:center;gap:11px;padding:18px 16px 14px}
.logo{width:40px;height:40px;flex:none;border-radius:13px;background:linear-gradient(135deg,var(--a),var(--b));display:grid;place-items:center;font-weight:850;font-size:20px;color:#070910;box-shadow:0 8px 24px #8b5cf655}
.brand-name{font-weight:780;font-size:16px;letter-spacing:.2px;line-height:1.2}
.brand-sub{font-size:10.5px;color:var(--muted);letter-spacing:.3px}
.ver{margin-left:auto;font-size:9.5px;color:var(--muted);border:1px solid var(--line);border-radius:6px;padding:2px 6px}
.pad{padding:0 14px}
.newchat{width:100%;border:0;border-radius:12px;padding:11px 14px;font-weight:700;color:#070910;background:linear-gradient(135deg,var(--a),var(--b));box-shadow:0 8px 22px #8b5cf633;transition:.16s}
.newchat:hover{filter:brightness(1.1);transform:translateY(-1px)}
.search{margin-top:12px;width:100%;background:var(--code);border:1px solid var(--line);color:var(--txt);border-radius:10px;padding:9px 11px;outline:none;font-size:12.5px}
.search:focus{border-color:var(--a)}
.label{font-size:10px;letter-spacing:1.3px;color:var(--muted);font-weight:700;margin:18px 4px 8px}
.chatlist{flex:1;overflow-y:auto;padding:0 8px 10px;min-height:0}
.chat{display:flex;align-items:center;gap:9px;padding:9px 10px;border-radius:10px;cursor:pointer;border:1px solid transparent;transition:.13s;margin-bottom:3px}
.chat:hover{background:#ffffff0a;border-color:var(--line)}
.chat.active{background:linear-gradient(90deg,#8b5cf622,#22d3ee0d);border-color:#8b5cf644}
.chat .ic{font-size:13px;opacity:.7}
.chat .txt{flex:1;min-width:0}
.chat .t{font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600}
.chat .s{font-size:10.5px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chat .del{opacity:0;background:none;border:0;color:var(--muted);font-size:15px;padding:2px 4px;border-radius:6px}
.chat:hover .del{opacity:1}
.chat .del:hover{color:#f87171;background:#f8717122}
.side-bottom{padding:12px 14px 15px;border-top:1px solid var(--line)}
.stat{background:var(--code);border:1px solid var(--line);border-radius:11px;padding:10px 11px;margin-bottom:10px}
.stat .row{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);padding:2px 0}
.stat .row b{color:var(--txt);font-variant-numeric:tabular-nums}
.sidebtn{width:100%;background:#ffffff08;border:1px solid var(--line);color:var(--txt);border-radius:10px;padding:9px;font-size:12.5px;margin-bottom:8px}
.sidebtn:hover{background:#ffffff16}
.engine{display:flex;align-items:center;gap:7px;font-size:11px;color:var(--muted)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--ok);box-shadow:0 0 9px var(--ok)}
.dot.off{background:var(--warn);box-shadow:0 0 9px var(--warn)}

/* ---------------- main ---------------- */
.main{grid-column:2;grid-row:1;display:flex;flex-direction:column;min-width:0;min-height:0;position:relative;background:radial-gradient(900px 520px at 78% -10%,var(--glow),transparent 72%),radial-gradient(700px 480px at 4% 100%,#22d3ee0d,transparent),var(--bg);transition:background .45s ease}
.topbar{display:flex;align-items:center;gap:10px;padding:10px 16px;border-bottom:1px solid var(--line);
  background:#ffffff05;z-index:10;flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none}
.topbar::-webkit-scrollbar{display:none}
.topbar>*{flex:0 0 auto}
.topbar .title-wrap{flex:1 1 200px;min-width:140px;overflow:hidden}
.topbar h1{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
.menu{display:none;background:none;border:1px solid var(--line);border-radius:9px;color:var(--txt);width:34px;height:34px}
.title-wrap{min-width:0;flex:1}
.topbar h1{margin:0;font-size:15px;font-weight:730;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.topbar .sub{font-size:11px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ctrls{display:flex;align-items:center;gap:7px}
select.ctl,.ctl{background:var(--panel2);border:1px solid var(--line);color:var(--txt);border-radius:9px;padding:7px 9px;font-size:11.5px;outline:none}
.ctl:hover{border-color:var(--a)}
.ctl.on{border-color:var(--a);color:var(--a)}
.pill{display:flex;align-items:center;gap:6px;font-size:10.5px;color:var(--muted);background:var(--panel2);border:1px solid var(--line);padding:6px 10px;border-radius:999px;white-space:nowrap}

.messages{flex:1;overflow-y:auto;padding:24px 0 12px;min-height:0;scroll-behavior:smooth}
.inner{max-width:840px;margin:0 auto;padding:0 22px}

/* welcome */
.welcome{padding:26px 0 10px}
.hero{display:flex;align-items:center;gap:14px;margin-bottom:10px}
.hero .big{width:52px;height:52px;border-radius:16px;background:linear-gradient(135deg,var(--a),var(--b));display:grid;place-items:center;font-size:25px;font-weight:850;color:#070910;box-shadow:0 12px 30px #8b5cf644}
.hero h2{margin:0;font-size:24px;letter-spacing:-.4px}
.hero p{margin:2px 0 0;color:var(--muted);font-size:12.5px}
.feature{display:flex;flex-wrap:wrap;gap:7px;margin:16px 0 22px}
.feature span{font-size:10.5px;color:var(--muted);border:1px solid var(--line);background:var(--panel2);padding:5px 10px;border-radius:999px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:11px}
.card{text-align:left;background:linear-gradient(160deg,var(--panel2),var(--panel));border:1px solid var(--line);border-radius:14px;padding:14px;color:var(--txt);transition:.16s;min-height:96px}
.card:hover{border-color:var(--a);transform:translateY(-2px);box-shadow:0 10px 26px #8b5cf622}
.card .ci{font-size:17px;margin-bottom:7px;display:block}
.card b{display:block;font-size:12.5px;margin-bottom:3px}
.card small{color:var(--muted);font-size:11px;line-height:1.45;display:block}

/* messages */
.msg{display:flex;gap:12px;margin:0 0 22px;animation:rise .22s ease-out}
@keyframes rise{from{opacity:0;transform:translateY(9px)}to{opacity:1;transform:none}}
.msg .av{width:31px;height:31px;flex:none;border-radius:10px;display:grid;place-items:center;font-size:11.5px;font-weight:800;margin-top:3px}
.msg.bot .av{background:linear-gradient(135deg,var(--a),var(--b));color:#070910}
.msg.user .av{background:var(--user);border:1px solid var(--line);color:var(--txt)}
.msg .body{min-width:0;flex:1}
.bubble{background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:15px 18px;box-shadow:var(--shadow);overflow-wrap:anywhere}
.msg.user .bubble{background:var(--user);border-color:#8b5cf633}
.bubble p{margin:0 0 10px}
.bubble p:last-child{margin-bottom:0}
.bubble h3{font-size:14px;margin:18px 0 8px;padding-bottom:6px;border-bottom:1px solid var(--line);color:var(--txt);letter-spacing:.1px}
.bubble h3:first-child{margin-top:0}
.bubble h4{font-size:12.5px;margin:14px 0 6px;color:var(--b)}
.bubble ul,.bubble ol{margin:0 0 11px;padding-left:20px}
.bubble li{margin:4px 0}
.bubble strong{color:var(--txt);font-weight:730}
.bubble code{background:var(--code);border:1px solid var(--line);border-radius:5px;padding:1px 5px;font:12px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:var(--b)}
.bubble a{color:var(--b);text-decoration:underline;text-underline-offset:2px}
.bubble blockquote{margin:0 0 10px;padding:8px 12px;border-left:3px solid var(--a);background:#8b5cf60f;border-radius:0 8px 8px 0;color:var(--muted)}
.code-block{margin:0 0 12px;border:1px solid var(--line);border-radius:11px;overflow:hidden;background:var(--code)}
.code-head{display:flex;align-items:center;padding:6px 11px;font-size:10.5px;color:var(--muted);border-bottom:1px solid var(--line);background:var(--panel2)}
.code-head button{margin-left:auto;background:none;border:0;color:var(--muted);font-size:10.5px}
.code-head button:hover{color:var(--b)}
.code-block pre{margin:0;padding:12px 14px;overflow-x:auto;font:12px/1.6 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:var(--txt)}
.meta{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-top:7px;font-size:10.5px;color:var(--muted)}
.meta .tag{border:1px solid var(--line);border-radius:6px;padding:1px 6px}
.acts{display:flex;gap:6px;margin-top:7px}
.acts button{background:none;border:1px solid transparent;color:var(--muted);font-size:10.5px;padding:3px 7px;border-radius:7px}
.acts button:hover{border-color:var(--line);color:var(--txt);background:var(--panel2)}
.sources{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px}
.src{display:inline-flex;align-items:center;gap:5px;max-width:280px;font-size:10.5px;color:var(--b);background:#22d3ee0e;border:1px solid #22d3ee33;border-radius:999px;padding:4px 10px;text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.src:hover{background:#22d3ee22}
.trace{margin-top:9px;border:1px solid var(--line);border-radius:10px;background:var(--panel2);overflow:hidden}
.trace summary{cursor:pointer;padding:8px 11px;font-size:11px;color:var(--muted);list-style:none}
.trace summary::-webkit-details-marker{display:none}
.trace summary:before{content:'▸ ';color:var(--a)}
.trace[open] summary:before{content:'▾ '}
.trace ol{margin:0;padding:2px 12px 10px 28px;font-size:11px;color:var(--muted)}
.trace li{padding:2px 0}
.trace li b{color:var(--txt);font-weight:600}

/* progress */
.progress{max-width:840px;margin:0 auto 10px;padding:0 22px;display:none}
.progress.on{display:block}
.prog-box{background:var(--panel);border:1px solid #8b5cf644;border-radius:13px;padding:12px 15px;box-shadow:var(--shadow)}
.prog-head{display:flex;align-items:center;gap:9px;font-size:12px;font-weight:650;margin-bottom:9px}
.spinner{width:13px;height:13px;border:2px solid var(--line);border-top-color:var(--a);border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.steps{display:flex;flex-direction:column;gap:5px;max-height:150px;overflow-y:auto}
.step{display:flex;gap:8px;font-size:11px;color:var(--muted);animation:rise .18s ease-out}
.step .n{color:var(--a);font-variant-numeric:tabular-nums}
.step b{color:var(--txt);font-weight:600}
.step small{opacity:.75}

/* composer */
.composer-wrap{border-top:1px solid var(--line);background:linear-gradient(180deg,transparent,#ffffff05);padding:10px 22px 14px}
.composer-inner{max-width:840px;margin:0 auto}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:9px}
.chip{font-size:11px;color:var(--muted);background:var(--panel2);border:1px solid var(--line);border-radius:999px;padding:5px 11px}
.chip:hover{color:var(--txt);border-color:var(--a)}
.composer{display:flex;gap:9px;align-items:flex-end;background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:8px 8px 8px 14px;box-shadow:var(--shadow)}
.composer:focus-within{border-color:var(--a);box-shadow:0 0 0 3px #8b5cf61f,var(--shadow)}
textarea{flex:1;resize:none;border:0;background:none;color:var(--txt);outline:none;min-height:42px;max-height:170px;line-height:1.55;padding:10px 0}
textarea::placeholder{color:#6f7a95}
.send{border:0;border-radius:11px;height:42px;padding:0 18px;font-weight:730;color:#070910;background:linear-gradient(135deg,var(--a),var(--b));white-space:nowrap}
.send:disabled{opacity:.45;cursor:wait}
.hint{display:flex;justify-content:space-between;gap:10px;font-size:10px;color:#6f7a95;margin-top:7px}
.hint kbd{background:var(--panel2);border:1px solid var(--line);border-radius:4px;padding:0 4px}

/* modal */
.overlay{position:fixed;inset:0;background:#04060cbb;backdrop-filter:blur(4px);display:none;align-items:center;justify-content:center;z-index:100;padding:16px}
.overlay.on{display:flex}
.modal{width:min(600px,100%);max-height:86vh;overflow-y:auto;background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:20px;box-shadow:0 24px 70px #0009}
.modal h2{margin:0 0 4px;font-size:17px}
.modal .m-sub{color:var(--muted);font-size:11.5px;margin-bottom:16px}
.field{margin-bottom:14px}
.field label{display:block;font-size:11.5px;font-weight:650;margin-bottom:6px}
.field .desc{font-size:10.5px;color:var(--muted);margin-top:5px;line-height:1.5}
.field input,.field select{width:100%;background:var(--code);border:1px solid var(--line);color:var(--txt);border-radius:9px;padding:9px 11px;outline:none;font-size:12.5px}
.switch{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 0;border-top:1px solid var(--line)}
.switch span{font-size:12px}
.switch small{display:block;color:var(--muted);font-size:10.5px}
.toggle{width:40px;height:22px;border-radius:99px;border:1px solid var(--line);background:var(--code);position:relative;flex:none}
.toggle:after{content:'';position:absolute;width:16px;height:16px;border-radius:50%;background:var(--muted);top:2px;left:3px;transition:.18s}
.toggle.on{background:#8b5cf644;border-color:var(--a)}
.toggle.on:after{left:20px;background:var(--a)}
.modal-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:8px}
.btn{padding:9px 15px;border-radius:10px;border:1px solid var(--line);background:var(--panel2);color:var(--txt);font-size:12px}
.btn.primary{background:linear-gradient(135deg,var(--a),var(--b));border:0;color:#070910;font-weight:700}
.learn-row{display:flex;gap:7px}
.learn-row input{flex:1}
.note{font-size:11px;color:var(--muted);background:var(--code);border:1px solid var(--line);border-radius:9px;padding:9px 11px;margin-top:10px;white-space:pre-wrap}
.m-group{font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);font-weight:750;margin:18px 0 9px;padding-top:12px;border-top:1px solid var(--line)}
.secgrid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.secgrid label{display:flex;align-items:center;gap:7px;font-size:11.5px;padding:6px 8px;border:1px solid var(--line);border-radius:8px;background:var(--panel2);cursor:pointer}
.secgrid input{accent-color:var(--a);width:14px;height:14px;flex:none}
.respect-pill{color:var(--a);font-weight:650}

/* ---------------- footer credit + disclaimer ---------------- */
.made{font-size:10px;color:var(--muted);text-align:center;margin-top:9px;line-height:1.5;letter-spacing:.1px}
.made b{color:var(--a);font-weight:700}
.disclaimer{text-align:center;font-size:10.5px;color:var(--muted);margin-top:6px;letter-spacing:.15px;opacity:.82}
.disclaimer:before{content:'✦';color:var(--a);margin-right:6px;font-size:9px}
/* ---------------- extra detailing (accepted theme preserved) ------------- */
.topbar{position:relative}
.topbar:after{content:'';position:absolute;left:0;right:0;bottom:-1px;height:2px;pointer-events:none;background:linear-gradient(90deg,var(--a),var(--b),transparent);opacity:.55;transition:background .35s}
.depthnote{display:inline-flex;align-items:center;gap:5px;padding:1px 8px;border:1px solid var(--a);border-radius:999px;color:var(--a);font-size:9.5px;font-weight:750;letter-spacing:.25px;white-space:nowrap;transition:color .3s,border-color .3s}
.depthnote.bump{animation:pop .32s ease-out}
.bubble{transition:border-color .2s,box-shadow .2s}
.msg.bot .bubble:hover{border-color:var(--a);box-shadow:0 14px 42px var(--glow)}
.src{animation:slideIn .22s ease-out both}
.src.static{color:var(--muted);background:#ffffff08;border-color:var(--line);border-style:dashed}
.meta .tag.ctx{border-color:var(--a);color:var(--a);font-weight:750}
.acts button{transition:.16s}
.acts button:active{transform:scale(.94)}
/* ---------------- v2.4 detailing ---------------- */
@keyframes dotFade{0%,100%{opacity:.3;transform:translateY(0)}50%{opacity:1;transform:translateY(-3px)}}
.memline{font-size:9.5px;color:var(--muted);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;animation:slideIn .3s ease-out both}
.memline b{color:var(--a);font-weight:750}
.chips .chip{animation:pop .34s ease-out both}
.chips .chip:nth-child(2n){animation-delay:.05s}
.chips .chip:nth-child(3n){animation-delay:.1s}
.chips .chip.write{border-color:var(--a);color:var(--a);background:#ffffff08}
.chips .chip.write:hover{background:var(--panel);box-shadow:0 6px 16px var(--glow)}
.tdots{display:inline-flex;align-items:center;gap:3px;margin-left:6px}
.tdots i{width:4px;height:4px;border-radius:50%;background:var(--a);animation:dotFade 1.1s ease-in-out infinite}
.tdots i:nth-child(2){animation-delay:.18s}
.tdots i:nth-child(3){animation-delay:.36s}
.prog-head .tdots{margin-left:auto}
.meta .tag.kind{border-color:var(--b);color:var(--b);font-weight:750}

/* ---------------- About panel ---------------- */
.about-overlay{position:fixed;inset:0;background:#04060ccc;backdrop-filter:blur(6px);display:none;align-items:center;justify-content:center;z-index:110;padding:16px}
.about-overlay.on{display:flex}
.about{width:min(720px,100%);max-height:88vh;overflow-y:auto;border-radius:20px;border:1px solid var(--line);background:var(--panel);box-shadow:0 30px 90px #000b;position:relative}
.about-head{position:relative;padding:26px 26px 20px;background:linear-gradient(135deg,var(--a),var(--b));color:#070910;overflow:hidden}
.about-head:after{content:'';position:absolute;width:230px;height:230px;right:-70px;top:-110px;border-radius:50%;background:#ffffff25;animation:float 7s ease-in-out infinite}
.about-head h2{margin:0 0 3px;font-size:23px;font-weight:850;position:relative}
.about-head p{margin:0;font-size:12.5px;opacity:.78;position:relative}
.about-close{position:absolute;right:16px;top:14px;z-index:2;border:1px solid #07091033;background:#ffffff55;color:#070910;border-radius:9px;width:30px;height:30px;font-size:16px;line-height:1}
.about-body{padding:20px 26px 24px}
.about-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}
.about-card{border:1px solid var(--line);border-radius:13px;background:var(--panel2);padding:14px}
.about-card h3{margin:0 0 8px;font-size:13px;color:var(--a)}
.about-card p,.about-card li{font-size:12px;color:var(--muted);line-height:1.65;margin:0 0 6px}
.about-card ul{margin:0;padding-left:17px}
.about-card b{color:var(--txt)}
.about-insta{display:inline-flex;align-items:center;gap:8px;font-size:12.5px;font-weight:700;color:var(--b);background:var(--code);border:1px solid var(--line);border-radius:10px;padding:9px 13px;text-decoration:none;transition:.18s}
.about-insta:hover{transform:translateY(-2px);border-color:var(--a);box-shadow:0 8px 20px #0003}
.about-foot{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-top:18px;padding-top:14px;border-top:1px solid var(--line);font-size:11px;color:var(--muted)}

/* ---------------- account + memory drawer ---------------- */
.ctl.account{display:flex;align-items:center;gap:8px;padding-right:10px}
.avatar{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font-size:11px;
  font-weight:800;color:#140c1d;background:linear-gradient(135deg,var(--a),var(--a2))}
.avatar.big{width:44px;height:44px;font-size:18px;border-radius:14px}
.scrim2{position:fixed;inset:0;background:#04060bcc;backdrop-filter:blur(3px);opacity:0;
  pointer-events:none;transition:.22s;z-index:120}
.scrim2.on{opacity:1;pointer-events:auto}
.acct-drawer{position:fixed;top:0;right:0;height:100dvh;width:380px;max-width:92vw;
  background:linear-gradient(180deg,#0d1220,#080b13);border-left:1px solid var(--line);
  transform:translateX(102%);transition:transform .26s cubic-bezier(.2,.9,.3,1);
  z-index:130;overflow-y:auto;padding:18px 18px 26px;box-shadow:-24px 0 70px #000a}
.acct-drawer.on{transform:none}
.acct-head{display:flex;align-items:center;gap:12px;padding-bottom:14px;
  border-bottom:1px solid var(--line)}
.acct-name{font-weight:700;font-size:15px}
.acct-role{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.12em}
.acct-head .x{margin-left:auto;background:#141a28;border:1px solid var(--line);color:var(--txt);
  width:30px;height:30px;border-radius:9px;font-size:17px;cursor:pointer;line-height:1}
.acct-section{margin-top:18px}
.acct-label{font-size:10.5px;letter-spacing:.16em;color:var(--muted);font-weight:700;margin-bottom:9px}
.mem-stats{font-size:12px;color:var(--muted);margin-bottom:10px;line-height:1.6}
.facts,.asked,.users{display:flex;flex-direction:column;gap:7px}
.fact{display:flex;gap:8px;align-items:flex-start;background:#0c1220;border:1px solid var(--line);
  border-radius:10px;padding:8px 10px;font-size:12px}
.fact b{color:var(--a2);font-weight:650;text-transform:capitalize}
.fact .del{margin-left:auto;color:#5c6784;cursor:pointer;border:0;background:none;font-size:14px}
.fact .del:hover{color:var(--bad)}
.asked .row{background:#0c1220;border:1px solid var(--line);border-radius:10px;padding:8px 10px;
  font-size:12px;color:#c3cbe4}
.asked .row span{display:block;color:var(--muted);font-size:11px;margin-top:3px}
.user-row{display:flex;align-items:center;gap:8px;background:#0c1220;border:1px solid var(--line);
  border-radius:10px;padding:8px 10px;font-size:12px}
.user-row .u{font-weight:650}
.user-row .r{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:#8a95b5;
  border:1px solid var(--line);border-radius:6px;padding:1px 6px}
.user-row .r.author{color:#140c1d;background:linear-gradient(135deg,var(--a),var(--a2));border:0}
.user-row .ops{margin-left:auto;display:flex;gap:6px}
.user-row .ops button{background:#141a28;border:1px solid var(--line);color:#c3cbe4;border-radius:7px;
  font-size:11px;padding:3px 7px;cursor:pointer}
.user-row .ops button:hover{border-color:var(--a);color:#fff}
/* understood chip under each user message */
.understood{display:inline-flex;align-items:center;gap:6px;margin-top:6px;font-size:10.5px;
  color:#9fb0d8;background:#0d1322;border:1px solid #1e2740;border-radius:999px;padding:3px 9px}
.understood b{color:var(--a2);font-weight:650}
/* ---------------- toast ---------------- */
.toast{position:fixed;left:50%;bottom:26px;transform:translate(-50%,20px);opacity:0;pointer-events:none;z-index:200;background:var(--panel2);border:1px solid var(--a);color:var(--txt);border-radius:11px;padding:10px 16px;font-size:12px;box-shadow:0 14px 40px #0008;transition:.26s cubic-bezier(.2,.9,.3,1.2)}
.toast.on{opacity:1;transform:translate(-50%,0)}
body.hide-sources .sources{display:none}

/* ---------------- little animations ---------------- */
@keyframes pop{from{opacity:0;transform:translateY(16px) scale(.97)}to{opacity:1;transform:none}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
@keyframes glowPulse{0%,100%{box-shadow:0 0 0 0 var(--a)}50%{box-shadow:0 0 0 7px transparent}}
@keyframes dotPulse{0%,100%{box-shadow:0 0 8px var(--ok)}50%{box-shadow:0 0 16px var(--ok)}}
@keyframes slideIn{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}
@keyframes shimmer{0%{background-position:-180% 0}100%{background-position:180% 0}}
.overlay.on .modal,.about-overlay.on .about{animation:pop .26s cubic-bezier(.2,.9,.3,1.2) both}
.dot{animation:dotPulse 2.6s ease-in-out infinite}
.brand .logo,.hero .big{animation:float 6s ease-in-out infinite}
.send{transition:transform .16s,filter .16s,box-shadow .16s}
.send:hover:not(:disabled){transform:translateY(-2px);filter:brightness(1.08);box-shadow:0 10px 26px var(--glow)}
.chip{transition:.16s}
.chip:hover{transform:translateY(-2px);box-shadow:0 6px 16px #0004}
.ctl,.sidebtn,.btn{transition:border-color .16s,background .16s,color .16s,transform .16s}
.ctl:active,.btn:active{transform:scale(.96)}
.aboutBtnActive{border-color:var(--a);color:var(--a)}
.chat{animation:slideIn .22s ease-out both}
.prog-box{border:1px solid #8b5cf644;border-radius:13px;padding:12px 15px;box-shadow:var(--shadow);background:linear-gradient(100%,var(--panel2),var(--panel),var(--panel2));background-size:200% 100%;animation:shimmer 3.2s linear infinite}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important}}

@media(max-width:900px){
  .app{grid-template-columns:minmax(0,1fr)}
  .about-grid{grid-template-columns:1fr}
  .main{grid-column:1;grid-row:1}
  .sidebar{position:fixed;left:0;top:0;bottom:0;width:274px;transform:translateX(-100%);transition:.22s}
  .sidebar.open{transform:none}
  .menu{display:block}
  .cards{grid-template-columns:repeat(2,1fr)}
}
@media(max-width:560px){
  .cards{grid-template-columns:1fr}
  .topbar{padding:10px 12px;gap:8px}.messages{padding-top:16px}.inner,.progress,.composer-inner{padding-left:12px;padding-right:12px}
  .composer-wrap{padding:9px 12px 12px}.pill{display:none}.hint{display:none}
  .ctrls #aboutBtn,.ctrls #sourcesBtn{font-size:0;width:31px;height:31px;padding:0;display:grid;place-items:center}
  .ctrls #aboutBtn:before{content:'ⓘ';font-size:13px}
  .ctrls #sourcesBtn:before{content:'🔗';font-size:12px}
  .depthnote{display:none}
  .memline{display:none}
  .about-head{padding:20px}.about-body{padding:16px 18px 20px}
  .hero h2{font-size:20px}
}

/* =======================================================================
   v2.5 BIG GUI UPGRADE
   Live research rail, sources drawer, RTL Urdu poetry, richer cards.
   The accepted theme (dark glass, purple/cyan gradient, depth accents) is
   preserved: this only adds depth, motion and information density.
   ======================================================================= */
:root{--glass:rgba(255,255,255,.035)}
.topbar{background:linear-gradient(90deg,#ffffff09,#ffffff02);backdrop-filter:blur(18px)}
.topbar h1{letter-spacing:-.2px}
.bubble{position:relative;overflow:hidden}
.msg.bot .bubble:before{content:'';position:absolute;left:0;top:0;height:2px;width:100%;
  background:linear-gradient(90deg,var(--a),var(--b),transparent 78%);opacity:.85}
.msg.bot .bubble{box-shadow:var(--shadow),inset 0 1px 0 #ffffff08}

/* live research rail */
.livebar{display:flex;align-items:center;gap:9px;padding:6px 20px;flex:none;min-height:38px;
  border-bottom:1px solid var(--line);background:linear-gradient(90deg,var(--glow),transparent 62%);
  overflow:hidden;z-index:9}
.live-dot{width:8px;height:8px;border-radius:50%;background:var(--ok);flex:none;animation:pulse 2.1s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(52,211,153,.55)}70%{box-shadow:0 0 0 9px rgba(52,211,153,0)}100%{box-shadow:0 0 0 0 rgba(52,211,153,0)}}
.livebar.busy .live-dot{background:var(--warn)}
.live-label{font-size:9.5px;font-weight:850;letter-spacing:1.2px;color:var(--muted);text-transform:uppercase;white-space:nowrap}
.platform-pills{display:flex;gap:5px;flex:1;min-width:0;overflow:hidden}
.ppill{display:inline-flex;align-items:center;gap:5px;font-size:10px;white-space:nowrap;
  color:var(--muted);border:1px solid var(--line);background:var(--panel2);padding:3px 8px;border-radius:999px}
.ppill .pi{width:15px;height:15px;border-radius:5px;display:grid;place-items:center;
  font-size:8px;font-weight:900;color:#070910;flex:none}
.ppill.on{color:var(--txt);border-color:#ffffff22}
.ppill.off{opacity:.42}
.ppill b{font-weight:800;color:var(--a)}
.live-meta{font-size:10px;color:var(--muted);white-space:nowrap}
.live-open{border:1px solid var(--line);background:var(--panel2);color:var(--txt);
  border-radius:8px;padding:4px 9px;font-size:10.5px;white-space:nowrap}
.live-open:hover{border-color:var(--a);color:var(--a)}
.ctl.live-toggle.on{border-color:var(--ok);color:var(--ok)}
.ctl.live-toggle.off{color:var(--muted)}
.reading-pill{font-size:9.5px;color:var(--muted);border:1px solid var(--line);
  border-radius:999px;padding:3px 8px;white-space:nowrap}

/* sources drawer */
.src-drawer{position:fixed;top:0;right:0;height:100%;width:392px;max-width:94vw;z-index:60;
  display:flex;flex-direction:column;background:linear-gradient(180deg,var(--panel2),var(--bg));
  border-left:1px solid var(--line);box-shadow:-20px 0 60px #00000088;
  transform:translateX(103%);transition:transform .32s cubic-bezier(.2,.8,.2,1)}
.src-drawer.on{transform:none}
.src-head{display:flex;align-items:center;gap:10px;padding:18px 18px 14px;border-bottom:1px solid var(--line)}
.src-head .ic{width:34px;height:34px;border-radius:11px;background:linear-gradient(135deg,var(--a),var(--b));
  display:grid;place-items:center;font-size:17px;color:#070910;flex:none}
.src-head b{font-size:14px;display:block}
.src-head small{font-size:10.5px;color:var(--muted)}
.src-head button{margin-left:auto;background:none;border:1px solid var(--line);color:var(--muted);
  border-radius:8px;width:28px;height:28px;font-size:15px}
.src-body{flex:1;overflow-y:auto;padding:16px 18px 26px}
.src-group{font-size:9.5px;letter-spacing:1.2px;color:var(--muted);font-weight:800;
  text-transform:uppercase;margin:18px 0 9px}
.src-group:first-child{margin-top:0}
.src-card{display:flex;gap:9px;align-items:flex-start;border:1px solid var(--line);
  background:var(--panel);border-radius:11px;padding:10px 11px;margin-bottom:7px}
.src-card .pi{width:24px;height:24px;border-radius:7px;display:grid;place-items:center;
  font-size:10px;font-weight:900;color:#070910;flex:none}
.src-card .txt{min-width:0;flex:1}
.src-card .t{font-size:11.5px;font-weight:750;display:flex;align-items:center;gap:6px}
.src-card .ok{font-size:9px;color:var(--ok);border:1px solid #34d39944;border-radius:5px;padding:1px 5px}
.src-card .no{font-size:9px;color:var(--muted);border:1px solid var(--line);border-radius:5px;padding:1px 5px}
.src-card .d{font-size:10px;color:var(--muted);line-height:1.45;margin-top:3px}
.src-link{display:block;font-size:11px;color:var(--txt);text-decoration:none;
  border-bottom:1px solid var(--line);padding:8px 2px;line-height:1.45}
.src-link:hover{color:var(--a)}
.src-link small{display:block;color:var(--muted);font-size:9.5px;margin-top:2px}

/* Urdu poetry: right-to-left, Nastaliq-friendly */
.urdu-poem{direction:rtl;unicode-bidi:isolate;text-align:right;margin:14px 0 18px;
  padding:16px 20px;border:1px solid var(--line);border-radius:14px;
  background:linear-gradient(160deg,var(--panel2),var(--panel));box-shadow:var(--shadow);
  font-family:'Noto Nastaliq Urdu','Jameel Noori Nastaleeq','Urdu Typesetting','Noto Naskh Arabic','Segoe UI',serif;
  font-size:19px;line-height:2.15;color:var(--txt)}
.urdu-poem:before{content:'✦  ';color:var(--a);font-size:13px}
.sher{margin:0 0 13px;padding-bottom:10px;border-bottom:1px dashed var(--line)}
.sher:last-child{border-bottom:0;margin-bottom:0;padding-bottom:0}
.misra{display:block;white-space:normal}
.misra:last-child{color:color-mix(in srgb,var(--a) 80%,var(--txt))}
/* the second line of a sher sits under the first, as a ghazal is printed */
.sher{display:block}
.urdu-poem .sher .misra+.misra{margin-top:2px}

/* code blocks: clearer, still simple */
.code-head{background:linear-gradient(90deg,var(--panel2),transparent);font-weight:750;letter-spacing:.5px}
.code-block pre{position:relative}
.code-block pre code{letter-spacing:.1px}

/* welcome */
.welcome{padding:30px 0 14px}
.hero .big{box-shadow:0 14px 34px #8b5cf666;animation:float 5s ease-in-out infinite}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
.hero h2{background:linear-gradient(90deg,var(--txt),var(--a));-webkit-background-clip:text;
  background-clip:text;-webkit-text-fill-color:transparent}
.src-strip{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 18px;padding:11px 12px;
  border:1px solid var(--line);border-radius:12px;background:var(--glass)}
.src-strip .lead{font-size:10px;color:var(--muted);font-weight:750;letter-spacing:.4px;
  align-self:center;margin-right:4px}
.src-strip span.p{font-size:10px;color:var(--txt);border:1px solid var(--line);
  background:var(--panel2);border-radius:999px;padding:3px 9px}
.card{min-height:102px}
.card:hover{transform:translateY(-3px)}
.w-note{font-size:10.5px;color:var(--muted);margin-top:16px;text-align:center}
@media(max-width:1200px){.live-meta{display:none}}
@media(max-width:900px){
  .livebar{padding:6px 12px}.live-label{display:none}.platform-pills{gap:4px}
  .src-drawer{width:100%;max-width:100%}
  .urdu-poem{font-size:17px;padding:12px 14px}
}

/* ==========================================================================
   v2.6.2 "Aurora" visual layer
   Adds depth only: no existing class is re-declared destructively.
   ========================================================================== */

/* ---------- ambience, rebuilt for speed (v2.6.3) ----------
   The old version animated a 96px blur over the whole viewport, which pinned
   a core and dropped scrolling to ~12 fps. This paints one pre-composited
   layer and drifts it with transform only: the compositor can do that on the
   GPU with no per-frame repaint. No blur filter, no blend mode, no grain. */
body:before{
  content:'';position:fixed;inset:-20%;z-index:0;pointer-events:none;
  background:
    radial-gradient(38% 32% at 16% 10%,color-mix(in srgb,var(--a) 62%,transparent),transparent 68%),
    radial-gradient(34% 30% at 84% 6%,color-mix(in srgb,var(--b) 55%,transparent),transparent 66%),
    radial-gradient(44% 36% at 66% 94%,color-mix(in srgb,var(--a) 46%,transparent),transparent 70%),
    radial-gradient(30% 26% at 4% 80%,color-mix(in srgb,var(--b) 42%,transparent),transparent 68%);
  opacity:.30;
  transform:translate3d(0,0,0);
  /* static by default: animating a full-viewport layer costs ~20 fps.
     The motion can be switched back on from Settings (data-motion="on"). */
}
:root[data-motion="on"] body:before{will-change:transform;animation:aurora 46s ease-in-out infinite alternate}
:root[data-theme="light"] body:before{opacity:.20}
@keyframes aurora{
  0%{transform:translate3d(0,0,0) scale(1)}
  100%{transform:translate3d(-3%,2%,0) scale(1.12)}
}
@media (prefers-reduced-motion:reduce){body:before{animation:none}}

/* the app sits above the ambience, not under it */
.shell{position:relative;z-index:2}
.main{z-index:2}

/* deeper glass on every floating surface */
.topbar{
  background:linear-gradient(180deg,#ffffff0d,#ffffff03),var(--panel);
  box-shadow:0 1px 0 #ffffff14 inset,0 8px 26px #0000002e;
}
.sidebar{
  background:linear-gradient(180deg,var(--panel),var(--panel2) 65%,var(--panel));
  box-shadow:1px 0 0 #ffffff0a inset,18px 0 44px -30px #000;
}
:root[data-theme="light"] .topbar{background:linear-gradient(180deg,#fff,#fbfcff);box-shadow:0 1px 0 #fff inset,0 8px 22px #1c254012}

/* composer: the thing you touch most, so give it real presence */
.composer{background:linear-gradient(180deg,#0000000a,transparent 55%)}
.composer-inner{
  border:1px solid color-mix(in srgb,var(--a) 26%,var(--line));
  border-radius:20px;
  background:linear-gradient(180deg,#ffffff0a,#ffffff02),var(--panel);
  box-shadow:0 18px 44px -22px color-mix(in srgb,var(--a) 55%,transparent),0 0 0 1px #ffffff0a inset;
  transition:box-shadow .3s,border-color .3s,transform .3s;
}
.composer-inner:focus-within{
  border-color:color-mix(in srgb,var(--a) 55%,var(--line));
  box-shadow:0 22px 60px -24px color-mix(in srgb,var(--a) 78%,transparent),0 0 0 1px color-mix(in srgb,var(--a) 35%,transparent) inset;
  transform:translateY(-1px);
}

/* assistant bubbles: a soft left glow instead of a hard border */
.msg.bot .bubble{
  border-left:2px solid color-mix(in srgb,var(--a) 55%,transparent);
  box-shadow:0 10px 30px -22px #000,0 0 0 1px #ffffff08 inset;
}
.msg.user .bubble{
  background:linear-gradient(180deg,color-mix(in srgb,var(--a) 16%,var(--user)),var(--user));
  box-shadow:0 8px 24px -18px color-mix(in srgb,var(--a) 60%,transparent);
}

/* scroll progress: a hairline of accent across the top of the thread */
#scrollRail{
  position:absolute;left:0;right:0;top:0;height:2px;z-index:11;pointer-events:none;
  background:linear-gradient(90deg,var(--a),var(--b));
  transform-origin:0 50%;transform:scaleX(0);opacity:.9;
  box-shadow:0 0 12px color-mix(in srgb,var(--a) 70%,transparent);
  transition:transform .12s linear;
}

/* headings inside answers get the accent tick */
.bubble h2{
  position:relative;padding-left:13px;
}
.bubble h2:before{
  content:'';position:absolute;left:0;top:.42em;width:4px;height:.95em;border-radius:3px;
  background:linear-gradient(180deg,var(--a),var(--b));
}
.bubble table{border-collapse:separate;border-spacing:0;border-radius:10px;overflow:hidden}
.bubble th{background:color-mix(in srgb,var(--a) 12%,transparent)}

/* chips and pills: subtle lift */
.pill,.chip,.srcpill,.platform-pills span{transition:transform .16s,box-shadow .16s,background .16s}
.chip:hover{transform:translateY(-1px);box-shadow:0 8px 20px -14px color-mix(in srgb,var(--a) 80%,transparent)}

/* =======================  creator console  ============================== */
.cc-badge{
  display:inline-flex;align-items:center;gap:6px;padding:3px 9px;border-radius:999px;
  font-size:10px;font-weight:800;letter-spacing:.09em;text-transform:uppercase;
  color:#0b0616;background:linear-gradient(100deg,var(--a),var(--b));
  box-shadow:0 6px 18px -10px color-mix(in srgb,var(--a) 90%,transparent);
}
.cc-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0 4px}
.cc-stat{
  border:1px solid var(--line);border-radius:13px;padding:10px 11px;
  background:linear-gradient(160deg,#ffffff08,#ffffff02),var(--panel);
  position:relative;overflow:hidden;
}
.cc-stat:before{
  content:'';position:absolute;inset:0 0 auto 0;height:2px;
  background:linear-gradient(90deg,var(--a),var(--b));opacity:.75;
}
.cc-stat b{display:block;font-size:19px;line-height:1.15;letter-spacing:-.02em}
.cc-stat span{font-size:10px;color:var(--muted);letter-spacing:.07em;text-transform:uppercase}
.cc-row{
  display:flex;align-items:center;gap:9px;padding:8px 9px;border-radius:11px;
  border:1px solid var(--line);background:#ffffff03;margin-bottom:6px;
}
.cc-row .who{min-width:0;flex:1}
.cc-row .who b{display:block;font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cc-row .who span{font-size:10.5px;color:var(--muted)}
.cc-row .tag{
  font-size:9.5px;font-weight:800;letter-spacing:.06em;padding:2px 7px;border-radius:999px;
  border:1px solid var(--line);color:var(--muted);text-transform:uppercase;
}
.cc-row .tag.owner{color:#0b0616;background:linear-gradient(100deg,var(--a),var(--b));border-color:transparent}
.cc-row .tag.off{color:#fca5a5;border-color:#fca5a540}
.cc-act{
  border:1px solid var(--line);background:#ffffff06;color:var(--txt);cursor:pointer;
  width:26px;height:26px;border-radius:8px;display:grid;place-items:center;font-size:12px;
  transition:.15s;
}
.cc-act:hover{background:color-mix(in srgb,var(--a) 22%,transparent);border-color:var(--a);transform:translateY(-1px)}
.cc-act.danger:hover{background:#ef444433;border-color:#ef4444}
.cc-hint{font-size:11px;color:var(--muted);line-height:1.5;margin:2px 0 8px}
.cc-pw{
  margin:6px 0 10px;padding:10px 11px;border-radius:11px;font-family:ui-monospace,Menlo,monospace;
  font-size:14px;letter-spacing:.06em;text-align:center;
  border:1px dashed color-mix(in srgb,var(--a) 55%,var(--line));
  background:color-mix(in srgb,var(--a) 10%,transparent);cursor:copy;
}
.cc-toggle{
  width:100%;display:flex;align-items:center;justify-content:space-between;gap:8px;
  border:1px solid var(--line);background:#ffffff05;color:var(--txt);cursor:pointer;
  padding:9px 11px;border-radius:11px;font-size:12px;font-weight:650;margin-top:4px;
}
.cc-toggle:hover{border-color:color-mix(in srgb,var(--a) 60%,var(--line))}
.cc-toggle i{font-style:normal;color:var(--muted);font-size:11px}
#creatorConsole{display:none}
#creatorConsole.on{display:block}
.acct-drawer{width:398px}
@media (max-width:520px){.acct-drawer{width:100%}}


/* ---------- transparency so the aurora reads through the app ---------- */
:root[data-theme="dark"]{
  --panel:rgba(12,16,27,.93);--panel2:rgba(17,22,37,.90);
}
:root[data-theme="light"]{
  --panel:rgba(255,255,255,.90);--panel2:rgba(247,249,255,.92);
}
.sidebar{background:linear-gradient(180deg,var(--panel),var(--panel2) 60%,var(--panel))}
.main{background:
  radial-gradient(760px 460px at 82% -12%,color-mix(in srgb,var(--a) 15%,transparent),transparent 70%),
  radial-gradient(680px 420px at 2% 104%,color-mix(in srgb,var(--b) 11%,transparent),transparent 72%),
  transparent}
.topbar{background:linear-gradient(180deg,#ffffff10,#ffffff04),color-mix(in srgb,var(--panel) 72%,transparent)}
.messages{background:transparent}

.msg.bot .bubble{background:color-mix(in srgb,var(--panel) 96%,transparent)}
.sidebar .card,.sb-card{background:color-mix(in srgb,var(--panel) 70%,transparent)}

/* ---------- command palette (Ctrl+K) ---------- */
#cpWrap{position:fixed;inset:0;z-index:120;display:none;align-items:flex-start;justify-content:center;
  padding-top:11vh;background:#03050ce8}
#cpWrap.on{display:flex}
#cpBox{width:min(620px,92vw);border-radius:18px;overflow:hidden;
  border:1px solid color-mix(in srgb,var(--a) 34%,var(--line));
  background:color-mix(in srgb,var(--panel) 92%,transparent);
  box-shadow:0 34px 90px -30px #000,0 0 0 1px #ffffff0d inset;
  animation:cpIn .16s ease-out}
@keyframes cpIn{from{transform:translateY(-10px) scale(.985);opacity:0}to{transform:none;opacity:1}}
#cpInput{width:100%;border:0;outline:0;background:transparent;color:var(--txt);
  font-size:15.5px;padding:16px 18px;border-bottom:1px solid var(--line)}
#cpList{max-height:52vh;overflow:auto;padding:7px}
.cp-item{display:flex;align-items:center;gap:11px;padding:9px 11px;border-radius:10px;
  cursor:pointer;font-size:13px}
.cp-item .k{font-size:10px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;
  color:var(--muted);min-width:52px}
.cp-item.sel,.cp-item:hover{background:color-mix(in srgb,var(--a) 20%,transparent)}
.cp-item .sub{margin-left:auto;font-size:10.5px;color:var(--muted)}
#cpHint{padding:8px 14px;border-top:1px solid var(--line);font-size:10.5px;color:var(--muted);
  display:flex;gap:14px}

/* ======================= v2.6.2b visual push ============================ */
:root[data-theme="dark"]{
  --panel:rgba(11,15,26,.74);--panel2:rgba(16,21,36,.70);
  --line:rgba(90,110,160,.28);
}
:root[data-theme="light"]{
  --panel:rgba(255,255,255,.80);--panel2:rgba(248,250,255,.84);
}

/* a lit ceiling: the top of the app catches the accent */
.main:before{
  content:'';position:absolute;inset:0 0 auto 0;height:150px;pointer-events:none;z-index:0;
  background:linear-gradient(180deg,color-mix(in srgb,var(--a) 13%,transparent),transparent);
}
.topbar,.messages,.composer{position:relative;z-index:1}

/* sidebar header glow + active chat accent bar */
.sidebar:before{
  content:'';position:absolute;inset:0 0 auto 0;height:130px;pointer-events:none;
  background:linear-gradient(180deg,color-mix(in srgb,var(--a) 16%,transparent),transparent);
}
.chat{position:relative;transition:background .18s,transform .18s,border-color .18s}
.chat:hover{transform:translateX(2px)}
.chat.active{background:linear-gradient(90deg,color-mix(in srgb,var(--a) 24%,transparent),
  color-mix(in srgb,var(--b) 8%,transparent) 60%,transparent)}
.chat.active:before{
  content:'';position:absolute;left:0;top:8px;bottom:8px;width:3px;border-radius:3px;
  background:linear-gradient(180deg,var(--a),var(--b));
  box-shadow:0 0 14px color-mix(in srgb,var(--a) 75%,transparent);
}

/* composer with a slow rotating gradient hairline */
.composer-inner{position:relative;border-color:transparent !important}
.composer-inner:before{
  content:'';position:absolute;inset:-1px;border-radius:21px;padding:1px;pointer-events:none;
  background:conic-gradient(from var(--spin,0deg),
    color-mix(in srgb,var(--a) 85%,transparent),
    color-mix(in srgb,var(--b) 85%,transparent),
    color-mix(in srgb,var(--a) 20%,transparent),
    color-mix(in srgb,var(--a) 85%,transparent));
  -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude;
  opacity:.75;transition:opacity .3s;
}
.composer-inner:focus-within:before{opacity:1}

/* bubbles settle in instead of popping */
@keyframes rise{from{opacity:0;transform:translateY(10px) scale(.995)}to{opacity:1;transform:none}}
.msg{animation:rise .28s cubic-bezier(.22,.61,.36,1) both}
@media (prefers-reduced-motion:reduce){.msg{animation:none}}

.msg{content-visibility:auto;contain-intrinsic-size:auto 220px}

/* refined scrollbars */
*::-webkit-scrollbar{width:10px;height:10px}
*::-webkit-scrollbar-thumb{
  background:linear-gradient(180deg,color-mix(in srgb,var(--a) 55%,transparent),
    color-mix(in srgb,var(--b) 45%,transparent));
  border-radius:20px;border:3px solid transparent;background-clip:padding-box;
}
*::-webkit-scrollbar-thumb:hover{background-color:color-mix(in srgb,var(--a) 80%,transparent)}
*::-webkit-scrollbar-track{background:transparent}

/* the big round buttons get a real light source */
.btn-primary,#sendBtn,.send{
  background:linear-gradient(135deg,var(--a),var(--b));
  box-shadow:0 12px 28px -12px color-mix(in srgb,var(--a) 85%,transparent),
             0 1px 0 #ffffff40 inset;
  transition:transform .16s,box-shadow .16s,filter .16s;
}
.btn-primary:hover,#sendBtn:hover,.send:hover{
  transform:translateY(-1px);filter:brightness(1.07);
  box-shadow:0 18px 38px -14px color-mix(in srgb,var(--a) 95%,transparent),
             0 1px 0 #ffffff55 inset;
}

/* ---------- the composer must be the top layer, not a window ---------- */
.composer{
  background:linear-gradient(180deg,
    color-mix(in srgb,var(--bg) 52%,transparent) 0,
    color-mix(in srgb,var(--bg) 94%,transparent) 22px,
    var(--bg) 46px) !important;
  border-top:1px solid color-mix(in srgb,var(--line) 70%,transparent);
  z-index:6;
}
.composer-inner{
  background:linear-gradient(180deg,#ffffff0e,#ffffff03),
    color-mix(in srgb,var(--panel2) 96%,transparent) !important;
}
/* (mask removed: it forced a full repaint on every scroll frame) */

/* ==========================================================================
   v2.6.3 "Nebula" - a new visual language, kept cheap to render
   Everything here is paint-only: gradients, borders, shadows. No blur, no
   blend mode, no full-screen animation, so scrolling stays smooth.
   ========================================================================== */

/* ---------- dark: deep space, two cool accents and one warm signal ---------- */
:root[data-theme="dark"]{
  --bg:#05060d; --panel:rgba(12,16,30,.82); --panel2:rgba(16,21,40,.78);
  --line:rgba(96,122,178,.22); --txt:#eaf0ff; --muted:#8b96b4;
  --a:#7c5cff; --b:#20d6f0; --ok:#2ee6a8; --warn:#ffb84d;
  --user:rgba(38,50,86,.9);
  --shadow:0 20px 50px -24px #000000cc;
  --edge:1px solid rgba(255,255,255,.06);
}
/* ---------- light: paper, ink, and a violet pen ---------- */
:root[data-theme="light"]{
  --bg:#f4f6fc; --panel:rgba(255,255,255,.90); --panel2:rgba(248,250,255,.92);
  --line:#dbe2f2; --txt:#131b31; --muted:#5b6683;
  --a:#5b3df5; --b:#0a90b8; --ok:#0a9d6e; --warn:#b46a00;
  --user:#e9ecff;
  --shadow:0 16px 40px -22px #1b25401f;
  --edge:1px solid rgba(20,30,60,.06);
}

/* the topbar becomes a lit shelf */
.topbar{
  background:linear-gradient(180deg,rgba(255,255,255,.055),rgba(255,255,255,.012)),var(--panel);
  border-bottom:1px solid var(--line);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.07),0 14px 34px -30px #000;
}
:root[data-theme="light"] .topbar{background:linear-gradient(180deg,#fff,#fbfcff);box-shadow:inset 0 1px 0 #fff,0 10px 26px -24px #1b254066}

/* the sidebar gets a real edge and a quiet gradient */
.sidebar{
  background:linear-gradient(170deg,var(--panel) 0%,var(--panel2) 52%,var(--panel) 100%);
  border-right:1px solid var(--line);
}
.sidebar .brand h1,.brand h1{letter-spacing:-.02em}

/* buttons: a cut-stone look with a light top edge */
.btn-primary,#sendBtn,.send{
  background:linear-gradient(160deg,var(--a),color-mix(in srgb,var(--b) 65%,var(--a)));
  color:#fff;border:1px solid rgba(255,255,255,.22);
  box-shadow:0 14px 30px -16px color-mix(in srgb,var(--a) 90%,transparent),
             inset 0 1px 0 rgba(255,255,255,.35);
  letter-spacing:.01em;
}
.btn-primary:hover,#sendBtn:hover,.send:hover{filter:brightness(1.06);transform:translateY(-1px)}

/* composer: a slate slab with an accent underline, no glass */
.composer{
  background:linear-gradient(180deg,transparent,var(--bg) 22px) !important;
  border-top:1px solid var(--line);
}
.composer-inner{
  border:1px solid var(--line) !important;
  background:linear-gradient(180deg,rgba(255,255,255,.055),rgba(255,255,255,.012)),var(--panel2) !important;
  box-shadow:0 22px 50px -34px #000,inset 0 1px 0 rgba(255,255,255,.08);
  border-radius:16px !important;
}
.composer-inner:focus-within{
  border-color:color-mix(in srgb,var(--a) 62%,var(--line)) !important;
  box-shadow:0 22px 54px -30px color-mix(in srgb,var(--a) 80%,transparent),
             inset 0 1px 0 rgba(255,255,255,.1);
}
.composer-inner:before{display:none !important}   /* the old conic ring */

/* answers: a card with a spine, so long answers are scannable */
.msg.bot .bubble{
  background:linear-gradient(180deg,rgba(255,255,255,.045),rgba(255,255,255,.008)),var(--panel);
  border:1px solid var(--line);
  border-left:3px solid color-mix(in srgb,var(--a) 70%,transparent);
  border-radius:14px;
  box-shadow:0 18px 40px -32px #000;
}
:root[data-theme="light"] .msg.bot .bubble{background:#fff;box-shadow:0 14px 30px -26px #1b254033}
.msg.user .bubble{
  background:linear-gradient(180deg,color-mix(in srgb,var(--a) 22%,var(--user)),var(--user));
  border:1px solid color-mix(in srgb,var(--a) 30%,transparent);
}
/* headings inside answers get a numbered, spaced rhythm */
.bubble h2{font-size:15.5px;letter-spacing:-.01em;margin:22px 0 8px}
.bubble h2:before{width:3px;height:.85em;top:.5em}
.bubble blockquote{
  border-left:2px solid color-mix(in srgb,var(--b) 70%,transparent);
  background:color-mix(in srgb,var(--b) 7%,transparent);
  border-radius:0 10px 10px 0;padding:10px 14px;margin:12px 0;
}
.bubble code{background:rgba(255,255,255,.07);border:1px solid var(--line);border-radius:6px;padding:1px 5px}
:root[data-theme="light"] .bubble code{background:#eef2fb}

/* the conversation list: a quiet rail with an unmistakable active state */
.chat.active{
  background:linear-gradient(90deg,color-mix(in srgb,var(--a) 26%,transparent),transparent 78%);
  border:1px solid color-mix(in srgb,var(--a) 34%,transparent);
}
.chat.active:before{width:3px;box-shadow:none}

/* depth accent is now a coloured underline on the topbar instead of a glow */
.topbar:after{height:1px;background:linear-gradient(90deg,var(--a),var(--b),transparent);opacity:.9}

/* pills, chips, source rows: consistent, flat, legible */
.pill,.chip,.srcpill{
  border:1px solid var(--line);background:rgba(255,255,255,.035);
  border-radius:8px;font-weight:600;
}
:root[data-theme="light"] .pill,:root[data-theme="light"] .chip,
:root[data-theme="light"] .srcpill{background:#f2f5fd}
.chip:hover{border-color:color-mix(in srgb,var(--a) 55%,var(--line));background:color-mix(in srgb,var(--a) 12%,transparent)}

/* stats block in the sidebar: tighter, more like a console readout */
.sidebar .rows .row{padding:6px 0;border-bottom:1px dashed color-mix(in srgb,var(--line) 70%,transparent)}

.bubble blockquote{
  font-size:15px;line-height:1.9;
}
.bubble blockquote:lang(ur),.bubble blockquote[dir="rtl"]{
  font-family:"Noto Nastaliq Urdu","Jameel Noori Nastaleeq","Alvi Nastaleeq",
    "Segoe UI",system-ui,sans-serif;
  font-size:19px;line-height:2.3;text-align:right;direction:rtl;
  padding:14px 18px;
}

/* the drawer and modals: solid, so text never fights the page behind */
.acct-drawer,.panel,.modal{
  background:linear-gradient(180deg,var(--panel2),var(--panel));
  border-left:1px solid var(--line);
  box-shadow:-30px 0 70px -40px #000;
}
#cpBox{background:var(--panel2);border:1px solid color-mix(in srgb,var(--a) 40%,var(--line))}


/* ==========================================================================
   v2.6.4  depth palettes that actually win
   The Nebula block above sets --a/--b inside :root[data-theme=...], which has
   the same specificity as :root[data-depth=...] and came later in the sheet -
   so it silently flattened every mode to one colour. These rules are ordered
   last and are not inside a theme block, so each mode now has its own palette.
   ========================================================================== */

/* ---- dark: each depth is a different temperature ---- */
:root[data-theme="dark"][data-depth="quick"]{
  --a:#ffb020; --b:#ff7a1a; --ok:#ffc65c; --warn:#ffd166;
  --glow:rgba(255,176,32,.18); --depth-tint:#ffb020;
}
:root[data-theme="dark"][data-depth="standard"]{
  --a:#22e0a1; --b:#12b8c9; --ok:#34e3b0; --warn:#fbbf24;
  --glow:rgba(34,224,161,.17); --depth-tint:#22e0a1;
}
:root[data-theme="dark"][data-depth="deep"]{
  --a:#8b7cff; --b:#34d9f0; --ok:#5eead4; --warn:#fbbf24;
  --glow:rgba(139,124,255,.19); --depth-tint:#8b7cff;
}
:root[data-theme="dark"][data-depth="exhaustive"]{
  --a:#ff5c8a; --b:#c084fc; --ok:#f0abfc; --warn:#fda4af;
  --glow:rgba(255,92,138,.18); --depth-tint:#ff5c8a;
}
/* ---- light: deeper ink, same families ---- */
:root[data-theme="light"][data-depth="quick"]{
  --a:#c2410c; --b:#d97706; --ok:#b45309; --glow:rgba(194,65,12,.12); --depth-tint:#c2410c;
}
:root[data-theme="light"][data-depth="standard"]{
  --a:#047857; --b:#0d9488; --ok:#059669; --glow:rgba(4,120,87,.12); --depth-tint:#047857;
}
:root[data-theme="light"][data-depth="deep"]{
  --a:#5b3df5; --b:#0891b2; --ok:#0d9488; --glow:rgba(91,61,245,.12); --depth-tint:#5b3df5;
}
:root[data-theme="light"][data-depth="exhaustive"]{
  --a:#be123c; --b:#7c3aed; --ok:#0d9488; --glow:rgba(190,18,60,.11); --depth-tint:#be123c;
}

/* ---- make the change unmistakable, not just a hue shift ---- */

/* 1. the ambient field takes the mode colour */
body:before{
  background:
    radial-gradient(38% 32% at 16% 10%,color-mix(in srgb,var(--a) 62%,transparent),transparent 68%),
    radial-gradient(34% 30% at 84% 6%,color-mix(in srgb,var(--b) 52%,transparent),transparent 66%),
    radial-gradient(44% 36% at 66% 94%,color-mix(in srgb,var(--a) 42%,transparent),transparent 70%);
  transition:background .4s ease;
}
/* 2. the topbar underline thickens and runs the full width */
.topbar:after{height:2px;opacity:1;
  background:linear-gradient(90deg,var(--a),var(--b) 55%,transparent 92%)}
/* 3. the new-chat button and send button carry the palette */
#newChat,.btn-primary,#sendBtn,.send{
  background:linear-gradient(155deg,var(--a),color-mix(in srgb,var(--b) 72%,var(--a)));
  box-shadow:0 16px 34px -18px color-mix(in srgb,var(--a) 90%,transparent),
             inset 0 1px 0 rgba(255,255,255,.32);
}
/* 4. the active conversation and the composer ring */
.chat.active{
  background:linear-gradient(90deg,color-mix(in srgb,var(--a) 26%,transparent),transparent 80%);
  border-color:color-mix(in srgb,var(--a) 40%,var(--line));
}
.chat.active:before{background:linear-gradient(180deg,var(--a),var(--b))}
.composer-inner{
  border-color:color-mix(in srgb,var(--a) 34%,var(--line)) !important;
  box-shadow:0 22px 50px -34px #000,inset 0 1px 0 color-mix(in srgb,var(--a) 22%,transparent);
}
.composer-inner:focus-within{
  border-color:color-mix(in srgb,var(--a) 70%,var(--line)) !important;
  box-shadow:0 22px 54px -28px color-mix(in srgb,var(--a) 80%,transparent),
             inset 0 1px 0 color-mix(in srgb,var(--a) 34%,transparent);
}
/* 5. answer cards take a spine in the mode colour */
.msg.bot .bubble{border-left-color:color-mix(in srgb,var(--a) 78%,transparent)}
/* 6. chips, pills and the depth badge */
.chip:hover,.pill.on,.srcpill:hover{
  border-color:color-mix(in srgb,var(--a) 60%,var(--line));
  background:color-mix(in srgb,var(--a) 14%,transparent);
}
#depthNote,.depthnote{color:var(--a)}
/* 7. the depth dropdown itself gets a tinted edge so the mode is visible there too */
#depth{border-color:color-mix(in srgb,var(--a) 45%,var(--line));
  background:color-mix(in srgb,var(--a) 10%,transparent)}
/* 8. sidebar brand mark follows the mode */
.brand .logo,.brand-mark,#logoMark{background:linear-gradient(150deg,var(--a),var(--b))}

/* 9. a short, honest transition when the mode changes - no layout thrash */
html[data-depth] *{transition:background-color .3s ease,border-color .3s ease,color .18s ease;
  transition-property:background-color,border-color,box-shadow,color}
@media (prefers-reduced-motion:reduce){html[data-depth] *{transition:none}}

/* 10. two new eye-candy themes on top of the four modes ------------------- */
/* "Neon" - maximum contrast, for showing the app off */
:root[data-theme="dark"][data-skin="neon"]{
  --bg:#03040a; --panel:rgba(8,12,26,.86); --panel2:rgba(12,18,38,.82);
  --line:rgba(120,150,255,.3); --txt:#f2f6ff; --muted:#8fa0c8;
}
:root[data-theme="dark"][data-skin="neon"] .msg.bot .bubble{
  border-left-width:4px;
  box-shadow:0 0 0 1px color-mix(in srgb,var(--a) 18%,transparent),
             0 22px 50px -34px color-mix(in srgb,var(--a) 60%,transparent);
}
/* "Paper" - warm, print-like light theme for long reading */
:root[data-theme="light"][data-skin="paper"]{
  --bg:#f6f2e9; --panel:rgba(255,252,244,.94); --panel2:rgba(252,248,238,.96);
  --line:#e0d7c3; --txt:#241f17; --muted:#6b6152; --user:#efe6d3;
}
:root[data-theme="light"][data-skin="paper"] .msg.bot .bubble{
  background:#fffdf8;border-color:#e6dcc8;
}


/* ---------- v2.6.4 theme picker ---------- */
#depthWrap{display:flex;align-items:center;gap:7px}
.dswatch{display:flex;gap:5px;align-items:center;padding:6px 8px;border:1px solid var(--line);
  border-radius:10px;background:rgba(255,255,255,.04);flex:0 0 auto}
.dswatch i{width:13px;height:13px;border-radius:999px;display:block;opacity:.6;transition:.18s;
  cursor:pointer;border:1px solid rgba(255,255,255,.18)}
.dswatch i:hover{opacity:1;transform:scale(1.1)}
.dswatch i.on{opacity:1;transform:scale(1.16);
  box-shadow:0 0 0 2px var(--panel),0 0 0 3.5px currentColor}
.dswatch i[data-d="quick"]{background:#ffb020;color:#ffb020}
.dswatch i[data-d="standard"]{background:#22e0a1;color:#22e0a1}
.dswatch i[data-d="deep"]{background:#8b7cff;color:#8b7cff}
.dswatch i[data-d="exhaustive"]{background:#ff5c8a;color:#ff5c8a}
.dswatch i[data-d="quick"]{background:#ffb020}
.dswatch i[data-d="standard"]{background:#22e0a1}
.dswatch i[data-d="deep"]{background:#8b7cff}
.dswatch i[data-d="exhaustive"]{background:#ff5c8a}
#skinBtn{display:inline-flex;align-items:center;gap:5px;font-weight:650}
#skinBtn span{font-size:11px}
:root[data-theme="light"] .dswatch{background:#eef2fb}

/* one segmented control instead of two loose buttons */
.look-group{display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:10px;
  overflow:hidden;background:rgba(255,255,255,.035)}
.look-group .ctl.ghost{border:0;border-radius:0;background:transparent;padding:7px 9px;font-size:12px}
.look-group .ctl.ghost+ .ctl.ghost{border-left:1px solid var(--line)}
.look-group .ctl.ghost:hover{background:color-mix(in srgb,var(--a) 18%,transparent)}
:root[data-theme="light"] .look-group{background:#f2f5fd}

/* keep the conversation title readable: drop the least useful controls first */
@media (max-width:1620px){.reading-pill{display:none}}
@media (max-width:1500px){#aboutBtn{display:none}}
@media (max-width:1400px){.topbar .pill{display:none}}
@media (max-width:1300px){#skinName{display:none}}
@media (max-width:1200px){#level{display:none}}
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar" id="sidebar">
    <div class="brand">
      <div class="logo">R</div>
      <div><div class="brand-name">{{NAME}}</div><div class="brand-sub">ADVANCED RESEARCH AGENT</div></div>
      <span class="ver">v{{VERSION}} · 264</span>
    </div>
    <div class="pad">
      <button class="newchat" id="newChat">＋ &nbsp;New chat</button>
      <input class="search" id="searchChats" placeholder="Search conversations…" autocomplete="off">
      <div class="label">CONVERSATIONS</div>
    </div>
    <div class="chatlist" id="chatList"></div>
    <div class="side-bottom">
      <div class="stat">
        <div class="row"><span>Curated topics</span><b id="stTopics">—</b></div>
        <div class="row"><span>Cached articles</span><b id="stCached">—</b></div>
        <div class="row"><span>Indexed chunks</span><b id="stChunks">—</b></div>
        <div class="row"><span>Tools</span><b id="stTools">—</b></div>
        <div class="row"><span>Respect policy</span><b class="respect-pill" id="stRespect">—</b></div>
      </div>
      <button class="sidebtn" id="openSettings">⚙ &nbsp;Settings &amp; knowledge</button>
      <button class="sidebtn" id="openAbout" style="margin-bottom:8px">✦ &nbsp;About Ryzek &amp; creator</button>
      <div class="engine"><span class="dot" id="dot"></span><span id="engineLabel">connecting…</span></div>
      <div class="made">Made by <b>Rasakh Mohsin</b> aka <b>Ryzek_20</b></div>
    </div>
  </aside>

  <div class="scrim" id="scrim"></div>

  <section class="main">
    <header class="topbar">
      <button class="menu" id="menuBtn">☰</button>
      <div class="title-wrap">
        <h1 id="chatTitle">New chat</h1>
        <div class="sub" id="chatSub">Every question gets a detailed, sourced answer</div>
        <div class="memline" id="memLine">💾 Remembers this chat · ✍ Writes emails, essays, letters &amp; Python · 💬 Natural small talk</div>
      </div>
      <div class="ctrls">
        <button class="ctl" id="aboutBtn" title="About Ryzek AI and its creator">About</button>
        <button class="ctl account" id="acctBtn" title="Your account, memory and sign out">
          <span class="avatar" id="acctAvatar">?</span>
          <span id="acctName">Account</span>
        </button>
        <button class="ctl live-toggle on" id="webBtn" title="Turn live web research on or off">🌐 Live web · ON</button>
        <select class="ctl" id="level" title="English reading level">
          <option value="simple">Simple</option>
          <option value="intermediate" selected>Intermediate</option>
          <option value="detailed">Detailed</option>
        </select>
        <div id="depthWrap"></div>
        <select class="ctl" id="depth" title="Answer detail">
          <option value="quick">Quick</option>
          <option value="standard">Standard</option>
          <option value="deep">Deep</option>
          <option value="exhaustive" selected>Exhaustive</option>
        </select>
        <button class="ctl" id="sourcesBtn" title="Show or hide source chips">Sources</button>
        <span class="reading-pill" id="readingPill">English · Intermediate</span>
        <span class="look-group" title="Theme and look">
          <button class="ctl ghost" id="themeBtn" title="Toggle light or dark">◐</button>
          <button class="ctl ghost" id="skinBtn" title="Switch look: Nebula, Neon or Paper"><span id="skinName">Nebula</span></button>
        </span>
        <span class="pill"><span class="dot" id="dot2"></span><span id="enginePill">—</span></span>
      </div>
    </header>

    <div class="livebar" id="liveBar">
      <span class="live-dot"></span>
      <span class="live-label">Live research</span>
      <div class="platform-pills" id="platformPills"><span class="ppill">connecting…</span></div>
      <span class="live-meta" id="liveMeta">checking platforms…</span>
      <button class="live-open" id="openSources">View sources ▸</button>
    </div>

    <div id="scrollRail"></div>
<div class="messages" id="messages">
      <div class="inner" id="messageList"></div>
    </div>

    <div class="progress" id="progress">
      <div class="inner" style="padding:0">
        <div class="prog-box">
          <div class="prog-head"><span class="spinner"></span><span id="progTitle">Ryzek is researching…</span><span class="tdots"><i></i><i></i><i></i></span></div>
          <div class="steps" id="stepList"></div>
        </div>
      </div>
    </div>

    <footer class="composer-wrap">
      <div class="composer-inner">
        <div class="chips" id="chips">
          <button class="chip" data-q="explain black holes in detail">🔭 Black holes</button>
          <button class="chip" data-q="why is the sky blue?">🌤 Why is the sky blue?</button>
          <button class="chip" data-q="how does photosynthesis work?">🌱 Photosynthesis</button>
          <button class="chip" data-q="what is retrieval-augmented generation?">🧠 RAG</button>
          <button class="chip" data-q="what is 17% of 240?">🧮 Worked maths</button>
          <button class="chip" data-q="/help">✨ Everything I can do</button>
          <button class="chip write" data-q="write an email to my teacher asking for leave">✉️ Email</button>
          <button class="chip write" data-q="write an essay on climate change">📝 Essay</button>
          <button class="chip write" data-q="write a letter to my friend">✍️ Letter</button>
          <button class="chip write" data-q="write a python function that reverses a string">🐍 Python function</button>
        </div>
        <div class="composer">
          <textarea id="input" rows="1" placeholder="Ask Ryzek anything…" title="Ask anything - I research real sources, cite them and explain in detail."></textarea>
          <button class="send" id="sendBtn">Send ➤</button>
        </div>
        <div class="hint"><span><kbd>Enter</kbd> send · <kbd>Shift+Enter</kbd> newline · <kbd>Ctrl+K</kbd> palette · try <b>/learn topic</b></span><span class="depthnote" id="depthNote">Exhaustive · everything</span><span id="charCount">0 chars</span></div>
        <div class="disclaimer">AI can also make mistakes.</div>
      </div>
    </footer>
  </section>
</div>

<aside class="src-drawer" id="srcDrawer" aria-label="Live research sources">
  <div class="src-head">
    <span class="ic">🌐</span>
    <div><b>Live research sources</b><small id="srcHeadSub">Every platform Ryzek checks in real time</small></div>
    <button id="closeSources" title="Close">×</button>
  </div>
  <div class="src-body" id="srcBody"></div>
</aside>

<div class="overlay" id="overlay">
  <div class="modal">
    <h2>Settings &amp; knowledge</h2>
    <div class="m-sub">Answer depth, respect policy, wording, research and sections. Saved on the server and in this browser.</div>

    <div class="field">
      <label>Engine</label>
      <input id="mEngine" readonly>
      <div class="desc">Offline brain = retrieval + Wikipedia research. Set <b>RYZEK_API_KEY</b> to switch to the tool-calling LLM agent.</div>
    </div>

    <div class="m-group">Answer depth &amp; display</div>
    <div class="field">
      <label>Default answer depth</label>
      <select id="mDepth"><option value="quick">Quick — short &amp; structured</option><option value="standard">Standard — moderate detail</option><option value="deep">Deep — long, multi-source answer</option><option value="exhaustive">Exhaustive — everything about the topic (recommended)</option></select>
      <div class="desc">Exhaustive adds mechanism, types, history, timeline, uses, limitations, related ideas, FAQs and a glossary. Each heading appears only once.</div>
    </div>
    <div class="switch"><span>Live Wikipedia research<small>Fetch and cache real articles. Turn off for fully offline use.</small></span><div class="toggle on" id="mOnline"></div></div>
    <div class="switch"><span>Show source chips<small>Display the articles used under each answer.</small></span><div class="toggle on" id="mSources"></div></div>
    <div class="switch"><span>Dark theme<small>Switch between dark and light palettes.</small></span><div class="toggle on" id="mDark"></div></div>

    <div class="m-group">Respect for religions &amp; prophets</div>
    <div class="switch"><span>Respect policy<small>Courteous, neutral language for all faiths; no jokes about prophets, no sectarian verdicts, no religious rulings.</small></span><div class="toggle on" id="mRespect"></div></div>
    <div class="field">
      <label>Respect mode</label>
      <select id="mRespectMode">
        <option value="balanced">Balanced — neutral and courteous for every tradition</option>
        <option value="islamic">Islamic — also add honorifics to every prophet</option>
        <option value="off">Off — no courtesy note or honorifics</option>
      </select>
    </div>
    <div class="field">
      <label>Prophetic honorific</label>
      <select id="mHonorifics">
        <option value="arabic">ﷺ — Arabic symbol after Prophet Muhammad</option>
        <option value="english">(peace be upon him) — written out</option>
        <option value="none">None — names only</option>
      </select>
    </div>

    <div class="m-group">Grammar &amp; writing style</div>
    <div class="switch"><span>Grammar and heading polish<small>Repairs stitched sentences, spacing and fragments; removes any heading that repeats.</small></span><div class="toggle on" id="mGrammar"></div></div>
    <div class="field">
      <label>English reading level</label>
      <select id="mLevel">
        <option value="simple">Simple — shortest words and sentences</option>
        <option value="intermediate">Intermediate — clear, everyday English (default)</option>
        <option value="detailed">Detailed — keep the fuller register</option>
      </select>
    </div>
    <div class="field">
      <label>Writing style</label>
      <select id="mStyle">
        <option value="structured">Structured — clear, organised, thorough</option>
        <option value="simple">Simple — plain language, short sentences</option>
        <option value="academic">Academic — formal register, scope notes</option>
        <option value="exam">Exam-ready — definition, mechanism, example, summary</option>
      </select>
    </div>

    <div class="m-group">Research &amp; language</div>
    <div class="field">
      <label>Sources read per question</label>
      <select id="mBreadth"><option value="1">1 — fastest</option><option value="2">2 — balanced</option><option value="3">3 — broader</option><option value="4">4 — broadest</option></select>
    </div>
    <div class="switch"><span>Plain English sources<small>Use Simple English Wikipedia and shorter sentences.</small></span><div class="toggle" id="mSimple"></div></div>
    <div class="switch"><span>Auto-cache articles<small>Save fetched articles to disk so later answers work offline.</small></span><div class="toggle on" id="mAutoLearn"></div></div>

    <div class="m-group">Sections in exhaustive answers</div>
    <div class="secgrid" id="mSections">
      <label><input type="checkbox" data-sec="overview" checked> Overview &amp; definition</label>
      <label><input type="checkbox" data-sec="mechanism" checked> How it works</label>
      <label><input type="checkbox" data-sec="types" checked> Types &amp; classifications</label>
      <label><input type="checkbox" data-sec="history" checked> Background &amp; history</label>
      <label><input type="checkbox" data-sec="timeline" checked> Dated timeline</label>
      <label><input type="checkbox" data-sec="applications" checked> Real-world uses</label>
      <label><input type="checkbox" data-sec="limitations" checked> Limits &amp; mistakes</label>
      <label><input type="checkbox" data-sec="comparison" checked> Related ideas</label>
      <label><input type="checkbox" data-sec="faq" checked> FAQs</label>
      <label><input type="checkbox" data-sec="glossary" checked> Glossary</label>
    </div>

    <div class="m-group">Teach Ryzek a topic</div>
    <div class="field">
      <div class="learn-row"><input id="learnInput" placeholder="e.g. Rayleigh scattering"><button class="btn primary" id="learnBtn">Learn</button></div>
      <div class="desc">Fetches the full Wikipedia article and caches it in <code>data/learned/</code> so future answers work offline.</div>
      <div class="note" id="learnNote" style="display:none"></div>
    </div>
    <div class="note" id="setNote" style="display:none"></div>

    <div class="modal-actions">
      <button class="btn" id="resetSettings">Reset defaults</button>
      <button class="btn" id="closeSettings">Close</button>
      <button class="btn primary" id="saveSettings">Save settings</button>
    </div>
  </div>
</div>

<div class="about-overlay" id="aboutOverlay">
  <div class="about">
    <div class="about-head">
      <button class="about-close" id="closeAbout" title="Close">×</button>
      <h2>About Ryzek AI</h2>
      <p>Advanced Python research agent · <span id="aboutVersion">v2.5.0</span></p>
    </div>
    <div class="about-body">
      <div class="about-grid">
        <div class="about-card">
          <h3>✦ What Ryzek AI is</h3>
          <p>An advanced research chatbot and agent written entirely in <b>Python</b>, built to answer <b>every single question in detail</b> — never a blank reply or a shrug.</p>
          <ul>
            <li>Curated knowledge base + BM25 retrieval</li>
            <li>Live Wikipedia research with disk caching</li>
            <li>14 tools and an optional tool-calling LLM brain</li>
            <li>Four answer depths: quick, standard, deep, exhaustive</li>
            <li>Respectful, neutral handling of prophets and religions</li>
            <li>Grammar polish and no repeated headings</li>
            <li>A library of English and Urdu poetry</li>
          </ul>
        </div>
        <div class="about-card">
          <h3>✦ About my creator</h3>
          <p><b>Rasakh Mohsin aka Ryzek</b> — also known online as <b>Ryzek_20</b> — is my creator, CEO, owner, boss, master and developer.</p>
          <p>He is a <b>data scientist</b>: very intelligent, sharply analytical and exacting about quality. He works with data, models, statistics and code, and he asks pointed questions until a system actually behaves the way he wants.</p>
          <p>He cares about answers that are detailed, factually careful, respectful and grammatically clean — and about both English and Urdu poetry.</p>
        </div>
      </div>
      <a class="about-insta" id="aboutInsta" href="https://www.instagram.com/rasakh_mohsin/" target="_blank" rel="noopener noreferrer">◉ &nbsp;Instagram · @rasakh_mohsin</a>
      <div class="about-foot">
        <span>AI can also make mistakes. Verify important information.</span>
        <button class="btn primary" id="aboutAsk">Read the full write-up in chat</button>
      </div>
      <div class="made" style="margin-top:14px">Made by <b>Rasakh Mohsin</b> aka <b>Ryzek_20</b></div>
    </div>
  </div>
</div>

<!-- account / memory drawer -->
<div class="scrim2" id="acctScrim"></div>
<aside class="acct-drawer" id="acctDrawer" aria-hidden="true">
  <div class="acct-head">
    <div class="avatar big" id="acctAvatar2">?</div>
    <div>
      <div class="acct-name" id="acctName2">Account</div>
      <div class="acct-role" id="acctRole">user</div>
    </div>
    <button class="x" id="acctClose" title="Close">×</button>
  </div>

  <div class="acct-section">
    <div class="acct-label">MEMORY</div>
    <div class="mem-stats" id="memStats">—</div>
    <div class="facts" id="factsList"></div>
    <button class="sidebtn" id="forgetAll">🗑 &nbsp;Forget everything</button>
  </div>

  <div class="acct-section">
    <div class="acct-label">ASKED RECENTLY</div>
    <div class="asked" id="askedList"></div>
  </div>

  <div class="acct-section" id="adminSection" style="display:none">
    <div class="acct-label" style="display:flex;align-items:center;justify-content:space-between">
      <span>ACCOUNTS ON THIS SERVER</span><span class="cc-badge" id="ccBadge">creator</span>
    </div>
    <div class="users" id="usersList"></div>
  </div>

  <!-- Creator Console: author account only (v2.6.2) -->
  <div class="acct-section" id="creatorConsole" style="display:none">
    <button class="cc-toggle" id="ccToggle">
      <span>⚡ Creator Console</span><i id="ccToggleNote">open</i>
    </button>
    <div id="ccBody" style="display:none;margin-top:10px">
      <div class="cc-grid" id="ccGrid"></div>
      <div class="acct-label" style="margin-top:12px">SERVER REACH</div>
      <div class="cc-hint" id="ccReach">—</div>
      <div class="cc-toggle" id="ccReachRow" style="cursor:default">
        <span>Live server</span><i id="ccServer">—</i>
      </div>
      <div class="acct-label" style="margin-top:12px">SEAT OF THE CREATOR</div>
      <div class="cc-hint">Your account is the only one that can see or touch other accounts,
        reset a forgotten password, or open this console. Nobody else can even tell it exists.</div>
      <div class="cc-pw" id="ccMyRole" title="click to copy">author · owner</div>
    </div>
  </div>

  <div class="acct-section">
    <div class="acct-label">THIS ACCOUNT</div>
    <div class="mem-stats" id="loginStats">—</div>
    <button class="sidebtn" id="changePw">🔑 &nbsp;Change my password</button>
    <button class="sidebtn" id="signOut">⏻ &nbsp;Sign out</button>
  </div>

  <div class="made" style="margin-top:14px">Made by <b>Rasakh Mohsin</b> aka <b>Ryzek_20</b></div>
</aside>

<div id="cpWrap" role="dialog" aria-label="Command palette">
  <div id="cpBox">
    <input id="cpInput" placeholder="Jump to a chat, change depth, open settings..." autocomplete="off">
    <div id="cpList"></div>
    <div id="cpHint"><span>↑↓ move</span><span>Enter run</span><span>Esc close</span></div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
(function(){
'use strict';
var NAME='{{NAME}}', $ = function(s){return document.querySelector(s);};
window.__USER__ = {{USER}};
var S={sid:null,sessions:[],busy:false,lastUser:'',cfg:null,webStatus:null,platforms:[],lastSources:[],lastQuery:'',pendingUnderstanding:null};

var DEF_SETTINGS={respect:true,respect_mode:'balanced',honorifics:'arabic',grammar:true,
  style:'structured',breadth:2,simple_english:false,english_level:'intermediate',auto_learn:true,
  sections:{overview:true,mechanism:true,types:true,history:true,timeline:true,
            applications:true,limitations:true,comparison:true,faq:true,glossary:true}};
function cloneSettings(o){

  var out={},i,j;
  for(i in DEF_SETTINGS){if(i!=='sections')out[i]=DEF_SETTINGS[i];}
  out.sections={};for(i in DEF_SETTINGS.sections)out.sections[i]=DEF_SETTINGS.sections[i];
  if(o){for(i in o){
    if(i==='sections'&&o.sections){for(j in o.sections){if(j in out.sections)out.sections[j]=!!o.sections[j];}}
    else if(i in out&&i!=='sections')out[i]=o[i];
  }}
  return out;
}
function loadCfg(){
  try{S.cfg=JSON.parse(localStorage.getItem('ryzek_cfg')||'null');}catch(e){S.cfg=null;}
  if(!S.cfg||typeof S.cfg!=='object')S.cfg={};
  if(['quick','standard','deep','exhaustive'].indexOf(S.cfg.depth)<0)S.cfg.depth='exhaustive';
  if(!S.cfg.theme)S.cfg.theme='dark';
  if(typeof S.cfg.online!=='boolean')S.cfg.online=true;
  if(typeof S.cfg.sources!=='boolean')S.cfg.sources=true;
  S.cfg.settings=cloneSettings(S.cfg.settings);
  applyCfg();
}
var DEPTH_HINT={quick:'Quick — short structured answer, roughly 600–1200 characters',
  standard:'Standard — moderate detail, roughly 2500–4000 characters',
  deep:'Deep — long multi-source answer, roughly 5000–7000 characters',
  exhaustive:'Exhaustive — every section, roughly 9000+ characters'};
function saveCfg(){localStorage.setItem('ryzek_cfg',JSON.stringify(S.cfg));}
function setToggle(id,on){var e=$(id);if(e)e.classList.toggle('on',!!on);}
var TOAST_T=null;
function toast(msg){
  var t=$('#toast');if(!t)return;
  t.textContent=msg;t.classList.add('on');
  if(TOAST_T)clearTimeout(TOAST_T);
  TOAST_T=setTimeout(function(){t.classList.remove('on');},2600);
}
function applyCfg(){
  document.documentElement.dataset.theme=S.cfg.theme;
  document.documentElement.dataset.depth=S.cfg.depth;
  buildDepthStrip();paintDepthStrip();
  document.body.classList.toggle('hide-sources',!S.cfg.sources);
  $('#depth').value=S.cfg.depth;
  $('#mDepth').value=S.cfg.depth;
  setToggle('#mOnline',S.cfg.online);
  setToggle('#mSources',S.cfg.sources);
  setToggle('#mDark',S.cfg.theme==='dark');
  $('#sourcesBtn').classList.toggle('on',!!S.cfg.sources);
  $('#themeBtn').textContent=S.cfg.theme==='dark'?'◐':'☀';
  var lv=(S.cfg.settings.english_level||'intermediate');
  if($('#level'))$('#level').value=lv;
  if($('#mLevel'))$('#mLevel').value=lv;
  if($('#readingPill'))$('#readingPill').textContent='English · '+
    ({simple:'Simple',intermediate:'Intermediate',detailed:'Detailed'}[lv]||'Intermediate');
  var wb=$('#webBtn');if(wb){wb.classList.toggle('on',!!S.cfg.online);wb.classList.toggle('off',!S.cfg.online);
    wb.textContent=S.cfg.online?'🌐 Live web · ON':'🌐 Live web · OFF';}
  var bar=$('#liveBar');if(bar)bar.style.opacity=S.cfg.online?'1':'.55';
  var DN={quick:'Quick · short, direct',standard:'Standard · balanced',
          deep:'Deep · long & sourced',exhaustive:'Exhaustive · everything'};
  var dn=$('#depthNote');
  if(dn){dn.textContent=DN[S.cfg.depth]||S.cfg.depth;dn.classList.remove('bump');void dn.offsetWidth;dn.classList.add('bump');}
  var dsel=$('#depth');
  for(var di=0;di<dsel.options.length;di++){dsel.options[di].title=DEPTH_HINT[dsel.options[di].value]||'';}
  var o=cloneSettings(S.cfg.settings),i,boxes;
  setToggle('#mRespect',o.respect);setToggle('#mGrammar',o.grammar);
  setToggle('#mSimple',o.simple_english);setToggle('#mAutoLearn',o.auto_learn);
  $('#mRespectMode').value=o.respect_mode;
  $('#mHonorifics').value=o.honorifics;
  $('#mStyle').value=o.style;
  if($('#mLevel'))$('#mLevel').value=o.english_level||'intermediate';
  $('#mBreadth').value=String(o.breadth);
  boxes=document.querySelectorAll('#mSections input[data-sec]');
  for(i=0;i<boxes.length;i++)boxes[i].checked=!!o.sections[boxes[i].getAttribute('data-sec')];
  var badge=$('#stRespect');
  if(badge)badge.textContent=(o.respect&&o.respect_mode!=='off')?(o.respect_mode==='islamic'?'Islamic':'Balanced'):'Off';
}
function collectSettings(){
  var o=cloneSettings(S.cfg.settings),i,boxes;
  o.respect=$('#mRespect').classList.contains('on');
  o.grammar=$('#mGrammar').classList.contains('on');
  o.simple_english=$('#mSimple').classList.contains('on');
  o.auto_learn=$('#mAutoLearn').classList.contains('on');
  o.respect_mode=$('#mRespectMode').value;
  o.honorifics=$('#mHonorifics').value;
  o.style=$('#mStyle').value;
  if($('#mLevel'))o.english_level=$('#mLevel').value;
  o.breadth=parseInt($('#mBreadth').value,10)||2;
  boxes=document.querySelectorAll('#mSections input[data-sec]');
  for(i=0;i<boxes.length;i++)o.sections[boxes[i].getAttribute('data-sec')]=boxes[i].checked;
  return o;
}
function showSetNote(msg){var n=$('#setNote');if(!n)return;n.style.display='block';n.textContent=msg;}
async function loadServerSettings(){
  try{
    var d=await api('/api/settings');
    if(d&&d.settings)S.cfg.settings=cloneSettings(d.settings);
    if(d&&d.depth&&['quick','standard','deep','exhaustive'].indexOf(d.depth)>=0)S.cfg.depth=d.depth;
    saveCfg();applyCfg();
  }catch(e){/* offline preview: keep local settings */}
}
function persistDepth(depth){
  return post('/api/settings',{settings:S.cfg.settings,depth:depth}).catch(function(){});
}
function openAbout(){
  $('#aboutOverlay').classList.add('on');$('#aboutBtn').classList.add('aboutBtnActive');
  api('/api/about').then(function(d){
    if(d.version)$('#aboutVersion').textContent='v'+d.version;
    if(d.url)$('#aboutInsta').href=d.url;
    if(d.instagram)$('#aboutInsta').textContent='◉  Instagram · '+d.instagram;
  }).catch(function(){});
}
function closeAbout(){
  $('#aboutOverlay').classList.remove('on');$('#aboutBtn').classList.remove('aboutBtnActive');
}
function esc(t){return String(t==null?'':t);}
function el(tag,cls,text){var e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e;}

function urlToken(){
  try{
    var m=/[?&]t=([^&#]+)/.exec(location.search);
    if(m){var t=decodeURIComponent(m[1]);try{localStorage.setItem('ryzek_token',t);}catch(e){}return t;}
  }catch(e){}
  return '';
}
function token(){
  var u=urlToken(); if(u)return u;
  try{return localStorage.getItem('ryzek_token')||'';}catch(e){return '';}
}
function authHeaders(extra){
  var h=extra||{};var t=token();if(t)h['Authorization']='Bearer '+t;return h;
}
function toLogin(){try{localStorage.removeItem('ryzek_sid');}catch(e){}location.replace('/login?expired=1');}
async function api(path,opts){
  opts=opts||{};
  opts.headers=authHeaders(opts.headers||{});
  var r=await fetch(path,opts);
  if(r.status===401){toLogin();throw new Error('signed out');}
  if(!r.ok)throw new Error('HTTP '+r.status);
  return r.json();
}
var ME=(window.__USER__&&window.__USER__.id)?window.__USER__:null;
function post(path,obj){return api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj||{})});}

/* ---------- safe markdown (DOM based, never innerHTML with user text) ---------- */
function inline(text,parent){
  var re=/(\[[^\]]+\]\(https?:\/\/[^)\s]+\)|\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g,m,last=0;
  while((m=re.exec(text))!==null){
    parent.appendChild(document.createTextNode(text.slice(last,m.index)));
    var t=m[0];
    if(t.charAt(0)==='['){
      var mm=/^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)$/.exec(t);
      if(mm){var a=el('a',null,mm[1]);a.href=mm[2];a.target='_blank';a.rel='noopener noreferrer';parent.appendChild(a);}
    }else if(t.slice(0,2)==='**'){parent.appendChild(el('strong',null,t.slice(2,-2)));}
    else if(t.charAt(0)==='`'){parent.appendChild(el('code',null,t.slice(1,-1)));}
    else{parent.appendChild(el('em',null,t.slice(1,-1)));}
    last=re.lastIndex;
  }
  parent.appendChild(document.createTextNode(text.slice(last)));
}
function markdown(container,text){
  var lines=esc(text).replace(/\r/g,'').split('\n'),i=0,list=null,ordered=false;
  while(i<lines.length){
    var line=lines[i],t=line.trim();
    if(t.indexOf(':::urdu')===0){
      var ubuf=[];i++;
      while(i<lines.length&&lines[i].trim().indexOf(':::')!==0){ubuf.push(lines[i]);i++;}
      i++;
      var ubox=el('div','urdu-poem');ubox.setAttribute('dir','rtl');ubox.setAttribute('lang','ur');
      ubuf.forEach(function(ul){
        var parts=ul.split('|'),sher=el('div','sher');
        parts.forEach(function(piece){sher.appendChild(el('div','misra',piece.trim()));});
        ubox.appendChild(sher);
      });
      container.appendChild(ubox);list=null;continue;
    }
    if(t.indexOf('```')===0){
      var lang=t.slice(3).trim(),buf=[];i++;
      while(i<lines.length&&lines[i].trim().indexOf('```')!==0){buf.push(lines[i]);i++;}
      i++;
      var wrap=el('div','code-block'),head=el('div','code-head',lang||'code');
      var cp=el('button',null,'Copy');cp.onclick=function(b){return function(){navigator.clipboard&&navigator.clipboard.writeText(b.join('\n'));cp.textContent='Copied';setTimeout(function(){cp.textContent='Copy';},1200);};}(buf);
      head.appendChild(cp);
      var pre=el('pre'),code=el('code',null,buf.join('\n'));pre.appendChild(code);
      wrap.appendChild(head);wrap.appendChild(pre);container.appendChild(wrap);list=null;continue;
    }
    if(/^#{1,4}\s/.test(t)){
      var lvl=(/^#+/.exec(t)[0]).length;
      container.appendChild(el(lvl<=2?'h3':'h4',null,t.replace(/^#+\s*/,'')));list=null;i++;continue;
    }
    var isBullet=/^[-*]\s+/.test(t),isNum=/^\d+\.\s+/.test(t);
    if(isBullet||isNum){
      if(!list||ordered!==isNum){list=el(isNum?'ol':'ul');container.appendChild(list);ordered=isNum;}
      var li=el('li');inline(t.replace(/^(?:[-*]|\d+\.)\s+/,''),li);list.appendChild(li);i++;continue;
    }
    if(t.indexOf('> ')===0){
      // a poem or a quoted passage arrives as several '> ' lines; keep them
      // in ONE blockquote so the verse breaks stay verse breaks
      var bq=el('blockquote'),first=true;
      while(i<lines.length&&lines[i].trim().indexOf('> ')===0){
        if(!first)bq.appendChild(el('br'));
        var seg=lines[i].trim().slice(2);
        // 'line  ' + two trailing spaces = markdown hard break
        seg=seg.replace(/\s+$/,'');
        inline(seg,bq);first=false;i++;
      }
      container.appendChild(bq);list=null;continue;
    }
    if(t===''){list=null;i++;continue;}
    var p=el('p');inline(t,p);container.appendChild(p);list=null;i++;
  }
}

/* ---------- messages ---------- */
function timeStr(ts){try{return new Date(ts*1000).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});}catch(e){return '';}}
function addMessage(m,scroll){
  var list=$('#messageList');
  var welcome=$('#welcome');if(welcome)welcome.remove();
  var isBot=m.role!=='user';
  var wrap=el('div','msg '+(isBot?'bot':'user'));
  var av=el('div','av',m.role==='user'?'You':'R');
  var body=el('div','body'),bubble=el('div','bubble');
  if(isBot){
    S.lastSources=m.sources||[];
    if(m.web&&m.web.length)S.webStatus=m.web;
  }
  if(m.role==='user'){
    // the understanding for this message arrives with the stream; if we have
    // it, attach it now so it survives re-renders
    if(!m.understanding&&S.pendingUnderstanding&&m.content===S.lastUser){
      m.understanding=S.pendingUnderstanding;
    }
    var p=el('p',null,m.content);bubble.appendChild(p);
    if(m.understanding&&m.understanding.intent){
      var u=m.understanding;
      var chip=el('div','understood');
      chip.innerHTML='<span>understood:</span>';
      if(u.subject){var b=el('b',null,u.subject);chip.appendChild(b);}
      chip.appendChild(el('span',null,'· '+u.intent));
      if(u.audience)chip.appendChild(el('span',null,'· '+u.audience));
      bubble.appendChild(chip);
    }
  }
  else{markdown(bubble,m.content||'');}
  body.appendChild(bubble);
  if(isBot){
    if(m.sources&&m.sources.length){
      var src=el('div','sources');
      m.sources.forEach(function(s){
        var node;
        if(s.url){node=el('a','src','🔗 '+(s.title||'Source')+' · '+(s.kind||'reference'));
          node.href=s.url;node.target='_blank';node.rel='noopener noreferrer';}
        else{node=el('span','src static','✦ '+(s.title||'Curated knowledge')+' · '+(s.kind||'local'));}
        node.title=s.excerpt||s.title||'';
        src.appendChild(node);
      });
      body.appendChild(src);
    }else if(m.content&&m.content.length>600){
      var f=el('div','sources');f.appendChild(el('span','src static','✦ Curated knowledge · local'));
      body.appendChild(f);
    }
    var meta=el('div','meta');
    meta.appendChild(el('span','tag',(m.engine||'offline').toUpperCase()));
    if(m.depth)meta.appendChild(el('span','tag',m.depth));
    var kind='';
    if(/^## (Hey|Good morning|Good afternoon|Good evening|Anytime|See you|Thank you|I'm here)/.test(m.content||''))kind='💬 CHAT';
    else if(/```python/.test(m.content||''))kind='🐍 CODE';
    else if(/:::urdu/.test(m.content||''))kind='✒️ URDU POETRY';
    else if(/^## (Email|Letter|Essay|Short story|Poem|Speech|Article|Report|Note)/.test(m.content||''))kind='✍ WRITING';
    else if(/^## I can't help with that part/.test(m.content||''))kind='🛡 SAFETY';
    if(kind)meta.appendChild(el('span','tag kind',kind));
    if(m.content&&m.content.indexOf('*Continuing our discussion of')===0)
      meta.appendChild(el('span','tag ctx','↳ context used'));
    if(m.web&&m.web.length)meta.appendChild(el('span','tag src','🌐 '+m.web.filter(function(x){return x.ok;}).length+' LIVE'));
    meta.appendChild(el('span','tag level','EN · '+(S.cfg.settings.english_level||'intermediate')));
    if(m.elapsed!=null)meta.appendChild(el('span',null,m.elapsed+'s'));
    meta.appendChild(el('span',null,timeStr(m.ts)));
    if(m.note)meta.appendChild(el('span',null,m.note));
    body.appendChild(meta);
    if(m.trace&&m.trace.length){
      var det=el('details','trace'),sum=el('summary',null,'View '+m.trace.length+' research steps');det.appendChild(sum);
      var ol=el('ol');m.trace.forEach(function(st){var li=el('li');li.appendChild(el('b',null,st.label));if(st.detail)li.appendChild(document.createTextNode(' — '+st.detail));ol.appendChild(li);});
      det.appendChild(ol);body.appendChild(det);
    }
    var acts=el('div','acts');
    var cp=el('button',null,'⧉ Copy');cp.onclick=function(){navigator.clipboard&&navigator.clipboard.writeText(m.content);cp.textContent='✓ Copied';setTimeout(function(){cp.textContent='⧉ Copy';},1300);};
    var rg=el('button',null,'↻ Regenerate');rg.onclick=function(){if(S.lastUser)send(S.lastUser);};
    acts.appendChild(cp);acts.appendChild(rg);body.appendChild(acts);
  }
  wrap.appendChild(av);
  wrap.appendChild(body);
  list.appendChild(wrap);
  if(scroll!==false)$('#messages').scrollTop=$('#messages').scrollHeight;
}

/* ---------- live research rail + sources drawer (v2.5) ---------- */
var PLATFORM_FALLBACK=[
  {id:'google',label:'Google',icon:'G',color:'#4285f4',desc:'Google News, Books and web'},
  {id:'wikipedia',label:'Wikipedia',icon:'W',color:'#a6a6a6',desc:'Encyclopedia articles'},
  {id:'simplewiki',label:'Simple Wiki',icon:'S',color:'#4f8ef7',desc:'Plain-English definitions'},
  {id:'bing',label:'Bing',icon:'b',color:'#00b4d8',desc:'Web results'},
  {id:'duckduckgo',label:'DuckDuckGo',icon:'D',color:'#de5833',desc:'Independent results'},
  {id:'wikidata',label:'Wikidata',icon:'Q',color:'#339966',desc:'Structured facts'},
  {id:'stackoverflow',label:'Stack Overflow',icon:'SO',color:'#f48024',desc:'Code answers'},
  {id:'openlibrary',label:'Open Library',icon:'OL',color:'#6b8e23',desc:'Books'},
  {id:'github',label:'GitHub',icon:'GH',color:'#8b949e',desc:'Open-source code'},
  {id:'webpages',label:'Web pages',icon:'↗',color:'#a78bfa',desc:'Pages read in full'}
];
function loadPlatforms(){
  return api('/api/web').then(function(d){
    S.platforms=d.platforms||PLATFORM_FALLBACK;
    if(d.last&&d.last.status&&d.last.status.length)S.webStatus=d.last.status;
    renderPlatformPills(S.webStatus||S.platforms.map(function(p){
      return {id:p.id,label:p.label,icon:p.icon,color:p.color,ok:false,count:0,note:'ready'};}));
    $('#liveMeta').textContent=(d.online?'Live research ready · ':'Live research off · ')+
      S.platforms.length+' platforms';
    renderDrawer();
  }).catch(function(){
    S.platforms=PLATFORM_FALLBACK;
    renderPlatformPills(S.webStatus||[]);
    $('#liveMeta').textContent='status unavailable';
  });
}
function renderPlatformPills(status){
  var box=$('#platformPills');if(!box)return;
  box.innerHTML='';
  var list=(status&&status.length)?status:PLATFORM_FALLBACK.map(function(p){
    return {id:p.id,label:p.label,icon:p.icon,color:p.color,ok:false,count:0,note:'ready'};});
  list.forEach(function(p){
    var node=el('span','ppill '+(p.ok?'on':'off'));
    var ic=el('span','pi',p.icon||'•');ic.style.background=p.color||'var(--a)';
    node.appendChild(ic);
    node.appendChild(document.createTextNode(p.label));
    if(p.ok&&p.count)node.appendChild(el('b',null,String(p.count)));
    node.title=(p.desc||'')+(p.detail?(' — '+p.detail):(p.note?(' — '+p.note):''));
    box.appendChild(node);
  });
}
function openSources(){
  renderDrawer();
  $('#srcDrawer').classList.add('on');
  $('#srcHeadSub').textContent=S.lastQuery?('Last question: '+S.lastQuery.slice(0,46)):'Every platform Ryzek checks in real time';
}
function closeSources(){$('#srcDrawer').classList.remove('on');}
function renderDrawer(){
  var box=$('#srcBody');if(!box)return;
  box.innerHTML='';
  var st=S.webStatus||[],pl=S.platforms.length?S.platforms:PLATFORM_FALLBACK;
  var g1=el('div','src-group','Connected platforms · '+pl.length);box.appendChild(g1);
  pl.forEach(function(p){
    var found=null;
    for(var i=0;i<st.length;i++){if(st[i].id===p.id){found=st[i];break;}}
    var card=el('div','src-card');
    var ic=el('span','pi',p.icon||'•');ic.style.background=p.color||'var(--a)';card.appendChild(ic);
    var txt=el('div','txt');
    var t=el('div','t');t.appendChild(document.createTextNode(p.label));
    t.appendChild(el('span',found&&found.ok?'ok':'no',found&&found.ok?(found.count+' found'):'standby'));
    txt.appendChild(t);
    txt.appendChild(el('div','d',null,(found&&found.ok&&found.detail)?found.detail:(p.desc||'')));
    card.appendChild(txt);box.appendChild(card);
  });
  var g2=el('div','src-group','Sources used in the last answer');box.appendChild(g2);
  if(!S.lastSources.length){box.appendChild(el('div','d','No live links in this answer yet. Ask a factual question or request an essay and the pages I read will appear here.'));}
  S.lastSources.forEach(function(src){
    if(src.url){
      var a=el('a','src-link',src.title||'Source');
      a.href=src.url;a.target='_blank';a.rel='noopener noreferrer';
      a.appendChild(el('small',null,(src.kind||'source')+' · '+(src.domain||src.url.slice(8,38))));
      box.appendChild(a);
    }else{
      var sp=el('div','src-link',(src.title||'Curated knowledge'));
      sp.appendChild(el('small',null,src.kind||'local'));box.appendChild(sp);
    }
  });
  if(S.lastQuery){
    var g3=el('div','src-group','Run a fresh search');box.appendChild(g3);
    var b=el('button','sidebtn','🔄 Search the live web again');
    b.onclick=function(){
      b.textContent='Searching…';
      post('/api/web/search',{query:S.lastQuery,limit:10}).then(function(d){
        S.webStatus=d.status;S.lastSources=d.items.map(function(x){
          return {title:x.title,url:x.url,kind:x.source,domain:x.domain,excerpt:x.snippet};});
        renderPlatformPills(d.status);renderDrawer();b.textContent='✓ Fresh results loaded';
        setTimeout(function(){b.textContent='🔄 Search the live web again';},1800);
      }).catch(function(){b.textContent='Search failed — try again';});
    };
    box.appendChild(b);
  }
}


function showWelcome(){
  var list=$('#messageList');list.innerHTML='';
  var w=el('div','welcome');w.id='welcome';
  var hero=el('div','hero');
  var big=el('div','big','R');hero.appendChild(big);
  var ht=el('div');ht.appendChild(el('h2',null,'Ask anything. Get the whole answer.'));
  ht.appendChild(el('p',null,NAME+' searches Google, Wikipedia, Bing, DuckDuckGo and more in real time, '
    +'reads the best pages, then writes a clear answer in plain intermediate English — with real links.'));
  hero.appendChild(ht);w.appendChild(hero);
  var feat=el('div','feature');
  ['🌐 Live multi-source research','📚 Wikipedia + Simple English','✍️ Emails, essays & letters',
   '🐍 Python functions (simple)','✒️ Urdu poetry','💬 Natural small talk',
   '🧮 Worked reasoning','💾 Remembers this chat','🔗 Real citations'].forEach(function(x){
     feat.appendChild(el('span',null,x));});
  w.appendChild(feat);
  var strip=el('div','src-strip');
  strip.appendChild(el('span','lead','CONNECTED TO'));
  (S.platforms.length?S.platforms:PLATFORM_FALLBACK).forEach(function(p){
    strip.appendChild(el('span','p',p.label));});
  w.appendChild(strip);
  var cards=el('div','cards');
  var data=[
    ['🔭','Explain black holes in detail','Formation, event horizons, detection, with live sourced caveats.'],
    ['🌤','Why is the sky blue?','Rayleigh scattering, wavelengths, and a worked intuition.'],
    ['🧠','What is retrieval-augmented generation?','Pipeline, why it matters, and its failure modes.'],
    ['🧮','What is 17% of 240?','Not just the number — a full worked solution.'],
    ['🌐','What causes climate change?','A live sweep across Google, Bing, Wikipedia and full pages.'],
    ['📝','Write an essay on climate change','A real essay built from the pages I actually read.'],
    ['✉️','Write an email to my teacher asking for leave','A complete, copy-ready email with a subject line.'],
    ['🐍','Write a Python function that reverses a string','Short beginner-level code, one function, one example.'],
    ['✒️','Type urdu poetry on rain','An original Urdu ghazal with Roman transliteration and meaning.']
  ];
  data.forEach(function(d){
    var c=el('button','card');c.type='button';
    c.appendChild(el('span','ci',d[0]));c.appendChild(el('b',null,d[1]));c.appendChild(el('small',null,d[2]));
    c.onclick=function(){send(d[1]);};cards.appendChild(c);
  });
  w.appendChild(cards);
  w.appendChild(el('div','w-note','Tip: open “View sources” to see every platform and every link Ryzek used.'));
  list.appendChild(w);
  var msgs=$('#messages');
  // The container uses smooth scrolling. Without this, a new chat opened
  // half-way down the welcome screen while the browser animated to the top.
  msgs.style.scrollBehavior='auto';msgs.scrollTop=0;
  setTimeout(function(){msgs.style.scrollBehavior='';},60);
}

/* ---------- account + memory ---------- */
var AC={open:false,user:null};
function initials(name){
  var parts=(name||'?').trim().split(/\s+/);
  return ((parts[0]||'?')[0]+(parts.length>1?(parts[1]||'')[0]:'')).toUpperCase();
}
async function loadMe(){
  try{
    var d=await api('/api/me');
    AC.user=d.user; ME=d.user;
    $('#acctName').textContent=d.user.display_name||d.user.username;
    $('#acctAvatar').textContent=initials(d.user.display_name||d.user.username);
    $('#acctName2').textContent=d.user.display_name||d.user.username;
    $('#acctAvatar2').textContent=initials(d.user.display_name||d.user.username);
    $('#acctRole').textContent=d.user.role==='author'?'author account':'normal account';
    $('#acctRole').className='acct-role'+(d.user.role==='author'?' author':'');
    renderMemory(d.memory,d.logins||[]);
    if(d.user.role==='author'){
      loadUsers();$('#adminSection').style.display='block';
      var cc=$('#creatorConsole');if(cc)cc.style.display='block';
      loadCreatorConsole();
    }
  }catch(e){}
}
function renderMemory(stats,logins){
  $('#memStats').innerHTML='<b>'+(stats?stats.facts:0)+'</b> saved facts · <b>'+
    (stats?stats.questions:0)+'</b> questions remembered';
  if(logins&&logins.length){
    var last=logins[0];
    $('#loginStats').textContent='Last sign-in '+new Date(last.ts*1000).toLocaleString()+
      (last.ip?' from '+last.ip:'');
  }
}
async function loadMemory(){
  try{
    var d=await api('/api/memory');
    var box=$('#factsList');box.innerHTML='';
    if(!d.facts.length){box.innerHTML='<div class="mem-stats">Nothing saved yet. Tell me your name, city or what you are working on.</div>';}
    d.facts.forEach(function(f){
      var el=document.createElement('div');el.className='fact';
      var k=document.createElement('b');k.textContent=f.key.replace(/_/g,' ');
      var v=document.createElement('span');v.textContent=f.value;
      var del=document.createElement('button');del.className='del';del.textContent='×';
      del.title='Forget this';
      del.onclick=async function(){
        await post('/api/memory/forget',{key:f.key});toast('Forgot: '+f.key.replace(/_/g,' '));loadMemory();loadMe();
      };
      el.appendChild(k);el.appendChild(v);el.appendChild(del);box.appendChild(el);
    });
    var asked=$('#askedList');asked.innerHTML='';
    if(!d.questions.length){asked.innerHTML='<div class="mem-stats">No questions stored yet.</div>';}
    d.questions.slice(0,10).forEach(function(q){
      var el=document.createElement('div');el.className='row';
      var t=document.createElement('div');t.textContent=q.question;
      var s=document.createElement('span');s.textContent=(q.answer||'').slice(0,120);
      el.appendChild(t);el.appendChild(s);asked.appendChild(el);
    });
    renderMemory(d.stats,[]);
  }catch(e){}
}
async function loadUsers(){
  try{
    var d=await api('/api/users');
    if(d&&d.users&&$('#usersList')&&$('#creatorConsole')&&
       $('#creatorConsole').style.display!=='none'){renderConsoleUsers(d.users);return;}
    var box=$('#usersList');box.innerHTML='';
    d.users.forEach(function(u){
      var row=document.createElement('div');row.className='user-row';
      var n=document.createElement('span');n.className='u';n.textContent=u.display_name||u.username;
      var r=document.createElement('span');r.className='r'+(u.role==='author'?' author':'');
      r.textContent=u.role;
      var ops=document.createElement('span');ops.className='ops';
      if(u.role!=='author'){
        var del=document.createElement('button');del.textContent='delete';
        del.onclick=async function(){
          if(!confirm('Delete account '+u.username+'? Its chats and memory go too.'))return;
          await post('/api/users/delete',{id:u.id});loadUsers();
        };
        ops.appendChild(del);
      }else{
        var me=document.createElement('span');me.className='r';me.textContent='owner';
        ops.appendChild(me);
      }
      row.appendChild(n);row.appendChild(r);row.appendChild(ops);box.appendChild(row);
    });
  }catch(e){}
}

/* ===================== v2.6.2 Creator Console (author only) ============== */
function relTime(ts){
  if(!ts)return 'never';
  var d=Date.now()/1000-ts;
  if(d<90)return 'just now';
  if(d<3600)return Math.round(d/60)+' min ago';
  if(d<86400)return Math.round(d/3600)+' h ago';
  if(d<2592000)return Math.round(d/86400)+' d ago';
  return new Date(ts*1000).toLocaleDateString();
}
function ccStat(label,value,sub){
  var d=document.createElement('div');d.className='cc-stat';
  var b=document.createElement('b');b.textContent=value;
  var s=document.createElement('span');s.textContent=label;
  d.appendChild(b);d.appendChild(s);
  if(sub){var i=document.createElement('div');i.style.cssText='font-size:10px;color:var(--muted)';
    i.textContent=sub;d.appendChild(i);}
  return d;
}
async function loadCreatorConsole(){
  try{
    var d=await api('/api/author/overview');
    if(!d||!d.ok)return;
    var st=d.stats||{};
    var g=$('#ccGrid');g.innerHTML='';
    g.appendChild(ccStat('Accounts',st.users||0,(st.authors||0)+' author · '+(st.members||0)+' members'));
    g.appendChild(ccStat('New this week','+'+(st.new_this_week||0),'sign-ups'));
    g.appendChild(ccStat('Active sessions',st.active_sessions||0,'live tokens'));
    g.appendChild(ccStat('Sign-ins / week',st.logins_this_week||0,'all accounts'));
    var mine=d.mine||{};
    $('#ccReach').textContent=(mine.chats||0)+' chats · '+(mine.facts||0)+
      ' facts · '+(mine.questions||0)+' questions on this account.';
    var srv=d.server||{};
    $('#ccServer').textContent='v'+(srv.version||'?')+' · '+(srv.topics||0)+' topics loaded';
    renderConsoleUsers(d.users||[]);
  }catch(e){}
}
function renderConsoleUsers(users){
  var box=$('#usersList');if(!box)return;box.innerHTML='';
  if(!users.length){box.innerHTML='<div class="mem-stats">Only you so far.</div>';return;}
  users.forEach(function(u){
    var row=document.createElement('div');row.className='cc-row';
    var av=document.createElement('div');av.className='avatar';
    av.textContent=initials(u.display_name||u.username);av.style.width='26px';
    av.style.height='26px';av.style.fontSize='11px';
    var who=document.createElement('div');who.className='who';
    var b=document.createElement('b');b.textContent=u.display_name||u.username;
    var sp=document.createElement('span');
    sp.textContent='@'+u.username+' · joined '+(u.created_at?
      new Date(u.created_at*1000).toLocaleDateString():'—')+' · seen '+relTime(u.last_login);
    who.appendChild(b);who.appendChild(sp);
    var tag=document.createElement('span');
    tag.className='tag'+(u.role==='author'?' owner':'')+(u.disabled?' off':'');
    tag.textContent=u.disabled?'suspended':(u.role==='author'?'owner':'member');
    row.appendChild(av);row.appendChild(who);row.appendChild(tag);

    if(u.role!=='author'){
      var reset=document.createElement('button');
      reset.className='cc-act';reset.textContent='↻';
      reset.title='Reset this password to a random one';
      reset.onclick=async function(){
        if(!confirm('Reset the password for @'+u.username+'?'))return;
        try{
          var r=await post('/api/author/reset',{user_id:u.id});
          if(r&&r.password){
            box.insertBefore(mkPwCard(u.username,r.password),box.firstChild);
            toast('Password reset for @'+u.username);
          }
        }catch(e){toast('Could not reset that password.');}
      };
      var suspend=document.createElement('button');
      suspend.className='cc-act';suspend.textContent=u.disabled?'▶':'⏸';
      suspend.title=u.disabled?'Restore this account':'Suspend this account';
      suspend.onclick=async function(){
        try{
          await post('/api/users/disable',{id:u.id,disabled:!u.disabled});
          toast((u.disabled?'Restored ':'Suspended ')+'@'+u.username);
          loadCreatorConsole();
        }catch(e){}
      };
      var del=document.createElement('button');
      del.className='cc-act danger';del.textContent='✕';
      del.title='Delete this account and everything it owns';
      del.onclick=async function(){
        if(!confirm('Delete @'+u.username+'? Their chats and memory are erased.'))return;
        await post('/api/users/delete',{id:u.id});toast('Deleted @'+u.username);
        loadCreatorConsole();
      };
      row.appendChild(reset);row.appendChild(suspend);row.appendChild(del);
    }
    box.appendChild(row);
  });
}
function mkPwCard(username,pw){
  var d=document.createElement('div');d.className='cc-pw';
  d.textContent=pw;d.title='Click to copy — give this to @'+username;
  d.onclick=function(){
    try{navigator.clipboard.writeText(pw);d.textContent='copied ✓';
      setTimeout(function(){d.textContent=pw;},1200);}catch(e){}
  };
  return d;
}

function acctOpen(on){
  AC.open=on;
  $('#acctDrawer').classList.toggle('on',on);
  $('#acctScrim').classList.toggle('on',on);
  $('#acctDrawer').setAttribute('aria-hidden',on?'false':'true');
  if(on){loadMemory();loadMe();}
}
$('#acctBtn').onclick=function(){acctOpen(true);};
$('#acctClose').onclick=function(){acctOpen(false);};
$('#acctScrim').onclick=function(){acctOpen(false);};
$('#signOut').onclick=async function(){
  try{await api('/api/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});}catch(e){}
  try{localStorage.removeItem('ryzek_token');localStorage.removeItem('ryzek_user');localStorage.removeItem('ryzek_sid');}catch(e){}
  location.replace('/login?out=1');
};
$('#forgetAll').onclick=async function(){
  if(!confirm('Erase every saved fact and stored question on this account?'))return;
  await post('/api/memory/forget',{});
  toast('Memory erased for this account');loadMemory();loadMe();
};
$('#changePw').onclick=async function(){
  var cur=prompt('Your current password:');
  if(!cur)return;
  var pw=prompt('New password (at least 6 characters):');
  if(!pw)return;
  try{
    var d=await post('/api/account/password',{current:cur,password:pw});
    if(d&&d.token){try{localStorage.setItem('ryzek_token',d.token);}catch(e){}}
    toast('Password changed. Other devices were signed out.');
  }catch(e){
    toast('Password not changed — check your current password.');
  }
};

/* ---------- sessions ---------- */
function renderChatList(){
  var box=$('#chatList'),q=($('#searchChats').value||'').toLowerCase();box.innerHTML='';
  var items=S.sessions.filter(function(s){return !q||(s.title||'').toLowerCase().indexOf(q)>=0;});
  if(!items.length){box.appendChild(el('div','label','No conversations yet'));return;}
  items.forEach(function(s){
    var row=el('div','chat'+(s.id===S.sid?' active':''));
    row.appendChild(el('span','ic','💬'));
    var tx=el('div','txt');tx.appendChild(el('div','t',s.title||'New chat'));
    tx.appendChild(el('div','s',s.count+' messages · '+new Date(s.updated_at*1000).toLocaleDateString()));
    row.appendChild(tx);
    var del=el('button','del','×');del.title='Delete chat';
    del.onclick=function(e){e.stopPropagation();removeChat(s.id);};row.appendChild(del);
    row.onclick=function(){selectChat(s.id);closeSidebar();};
    box.appendChild(row);
  });
}
async function loadSessions(){
  try{
    var d=await api('/api/sessions');S.sessions=d.sessions||[];
    if(!S.sessions.length){var n=await post('/api/sessions',{});S.sessions=[{id:n.id,title:'New chat',count:0,updated_at:Date.now()/1000}];}
    var saved=localStorage.getItem('ryzek_sid');
    var found=S.sessions.some(function(s){return s.id===saved;});
    var target=found?saved:S.sessions[0].id;
    await selectChat(target);
  }catch(e){$('#engineLabel').textContent='offline (server unreachable)';}
}
async function newChat(){
  if(S.busy)return;
  try{var n=await post('/api/sessions',{});S.sessions.unshift({id:n.id,title:'New chat',count:0,updated_at:Date.now()/1000});await selectChat(n.id);closeSidebar();$('#input').focus();}catch(e){}
}
async function removeChat(id){
  try{await post('/api/sessions/delete',{id:id});}catch(e){}
  S.sessions=S.sessions.filter(function(s){return s.id!==id;});
  if(S.sid===id){if(S.sessions.length)await selectChat(S.sessions[0].id);else await newChat();}
  renderChatList();
}
async function selectChat(id){
  S.sid=id;localStorage.setItem('ryzek_sid',id);
  var s=S.sessions.find(function(x){return x.id===id;});
  $('#chatTitle').textContent=s?s.title:'New chat';
  try{
    var d=await api('/api/session?id='+encodeURIComponent(id));
    $('#messageList').innerHTML='';
    $('#chatTitle').textContent=d.title||'New chat';
    $('#chatSub').textContent=d.count+' messages · '+NAME+' v{{VERSION}} · persistent memory';
    var ml=$('#memLine');
    if(ml){
      ml.textContent='';
      var put=function(txt){ml.appendChild(document.createTextNode(txt));};
      if(d.user_name){put('💾 Remembering ');ml.appendChild(el('b',null,d.user_name));}
      else put('💾 Remembers this chat');
      if(d.last_topic){put(' · last topic: ');ml.appendChild(el('b',null,String(d.last_topic).slice(0,34)));}
      put(' · ✍ writes emails, essays, letters & Python');
    }
    if(!d.messages||!d.messages.length)showWelcome();
    else{
      d.messages.forEach(function(m){addMessage(m,false);});
      $('#messages').scrollTop=$('#messages').scrollHeight;
    }
  }catch(e){showWelcome();}
  renderChatList();
}
function refreshSessions(){
  api('/api/sessions').then(function(d){S.sessions=d.sessions||[];renderChatList();}).catch(function(){});
}

/* ---------- streaming chat ---------- */
function progress(on,title){
  $('#progress').classList.toggle('on',!!on);
  if(on){$('#stepList').innerHTML='';$('#progTitle').textContent=title||'Ryzek is researching…';}
}
function addStep(label,detail){
  var box=$('#stepList'),row=el('div','step');
  row.appendChild(el('span','n',String(box.children.length+1).padStart(2,'0')));
  var d=el('span');d.appendChild(el('b',null,label));if(detail)d.appendChild(el('small',null,' — '+detail));
  row.appendChild(d);box.appendChild(row);box.scrollTop=box.scrollHeight;
}
function attachUnderstanding(text,u){
  var nodes=document.querySelectorAll('#messageList .msg.user .bubble');
  if(!nodes.length)return;
  var bubble=nodes[nodes.length-1];
  if(bubble.querySelector('.understood'))return;
  var chip=el('div','understood');
  chip.appendChild(el('span',null,'understood:'));
  if(u.subject)chip.appendChild(el('b',null,u.subject));
  chip.appendChild(el('span',null,'· '+u.intent));
  if(u.audience)chip.appendChild(el('span',null,'· '+u.audience));
  bubble.appendChild(chip);
  S.pendingUnderstanding=null;
  var ml=$('#messageList');if(ml)ml.scrollTop=ml.scrollHeight;
}
function handleEvent(ev){
  if(ev.type==='step'){addStep(ev.label,ev.detail);}
  else if(ev.type==='final'){
    progress(false);
    if(ev.understanding&&ev.understanding.intent){
      S.pendingUnderstanding=ev.understanding;
      attachUnderstanding(S.lastUser,ev.understanding);
    }
    addMessage({role:'assistant',content:ev.reply,engine:ev.engine,note:ev.note,sources:ev.sources,trace:ev.trace,elapsed:ev.elapsed,depth:ev.depth,web:ev.web,ts:Date.now()/1000});
    $('#chatTitle').textContent=ev.title||$('#chatTitle').textContent;
    if(ev.web&&ev.web.length){S.webStatus=ev.web;renderPlatformPills(ev.web);}
    $('#liveBar').classList.remove('busy');
    $('#liveMeta').textContent='last answer · '+(S.lastSources.length)+' linked sources';
    renderDrawer();
    refreshSessions();
  }
}
async function streamChat(payload){
  var res=await fetch('/api/chat/stream',{method:'POST',headers:authHeaders({'Content-Type':'application/json'}),body:JSON.stringify(payload)});
  if(!res.ok)throw new Error('HTTP '+res.status);
  if(!res.body)throw new Error('no stream');
  var reader=res.body.getReader(),dec=new TextDecoder(),buf='',gotFinal=false;
  while(true){
    var r=await reader.read();if(r.done)break;
    buf+=dec.decode(r.value,{stream:true});
    var idx;
    while((idx=buf.indexOf('\n'))>=0){
      var line=buf.slice(0,idx).trim();buf=buf.slice(idx+1);
      if(!line)continue;
      try{var ev=JSON.parse(line);if(ev.type==='final')gotFinal=true;handleEvent(ev);}catch(e){}
    }
  }
  if(buf.trim()){try{var ev2=JSON.parse(buf.trim());if(ev2.type==='final')gotFinal=true;handleEvent(ev2);}catch(e){}}
  if(!gotFinal)throw new Error('stream ended early');
}
async function send(text){
  text=String(text||'').trim();if(!text||S.busy)return;
  S.busy=true;S.lastUser=text;$('#sendBtn').disabled=true;
  var welcome=$('#welcome');if(welcome)welcome.remove();
  addMessage({role:'user',content:text,ts:Date.now()/1000});
  $('#input').value='';$('#input').style.height='auto';$('#charCount').textContent='0 chars';
  progress(true,'Ryzek is searching live sources…');addStep('Sending question',text.slice(0,70));
  S.lastQuery=text;
  $('#liveBar').classList.add('busy');
  $('#liveMeta').textContent='searching Google, Bing, DuckDuckGo, Wikipedia…';
  var payload={message:text,session_id:S.sid,depth:S.cfg.depth,online:S.cfg.online,settings:S.cfg.settings};
  try{
    await streamChat(payload);
  }catch(e){
    try{
      var d=await post('/api/chat',payload);
      progress(false);
      if(d.understanding&&d.understanding.intent)attachUnderstanding(text,d.understanding);
      addMessage({role:'assistant',content:d.reply,engine:d.engine,note:d.note,sources:d.sources,trace:d.trace,elapsed:d.elapsed,depth:d.depth,ts:Date.now()/1000});
      refreshSessions();
    }catch(e2){
      progress(false);
      addMessage({role:'assistant',content:'## Connection hiccup\n\nI never leave you hanging. The request did not complete, so here is what to do:\n\n- Resend the message — the research pipeline is stateless and safe to retry.\n- Check that the Ryzek server is still running.\n- Turn off live research in Settings if Wikipedia is rate-limiting.\n\nYour question was: **'+text+'**',engine:'offline',ts:Date.now()/1000});
    }
  }finally{S.busy=false;$('#sendBtn').disabled=false;$('#input').focus();}
}

/* ---------- status / settings ---------- */
async function loadStatus(){
  try{
    var d=await api('/api/status');
    $('#stTopics').textContent=d.topics;$('#stCached').textContent=d.cached;
    $('#stChunks').textContent=d.chunks;$('#stTools').textContent=d.tools;
    var label=d.engine==='llm'?('LLM · '+d.model):'Offline research brain';
    $('#engineLabel').textContent=label;$('#enginePill').textContent=label;
    $('#mEngine').value=label+' · '+d.topics+' topics · '+d.cached+' cached articles';
    var off=d.engine!=='llm';$('#dot').classList.toggle('off',off);$('#dot2').classList.toggle('off',off);
    $('#chatSub').textContent='Every question answered in detail · Respect on · '+label;
  }catch(e){$('#engineLabel').textContent='server unreachable';}
}
function openSettings(){$('#overlay').classList.add('on');loadStatus();}
function closeSettings(){$('#overlay').classList.remove('on');}
function closeSidebar(){$('#sidebar').classList.remove('open');$('#scrim').classList.remove('on');}

/* ---------- live-source events (v2.5) ---------- */
$('#webBtn').onclick=function(){
  S.cfg.online=!S.cfg.online;saveCfg();applyCfg();
  toast(S.cfg.online?'Live web research ON — Google, Bing, DuckDuckGo, Wikipedia and more':'Live web OFF — answering from local knowledge');
};
$('#level').onchange=function(){
  S.cfg.settings.english_level=this.value;saveCfg();applyCfg();persistDepth(S.cfg.depth);
  toast('English reading level: '+({simple:'Simple',intermediate:'Intermediate',detailed:'Detailed'}[this.value]));
};
$('#openSources').onclick=openSources;
$('#closeSources').onclick=closeSources;

/* ---------- events ---------- */
$('#sendBtn').onclick=function(){send($('#input').value);};
$('#input').addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send(this.value);}});
$('#input').addEventListener('input',function(){this.style.height='auto';this.style.height=Math.min(this.scrollHeight,170)+'px';$('#charCount').textContent=this.value.length+' chars';});
$('#chips').addEventListener('click',function(e){var q=e.target.getAttribute('data-q');if(q)send(q);});
$('#newChat').onclick=newChat;
$('#searchChats').addEventListener('input',renderChatList);
var DEPTH_LABEL={quick:'Quick · short, direct answers',standard:'Standard · moderate detail',
  deep:'Deep · long, multi-section explanations',exhaustive:'Exhaustive · everything about the topic'};
function changeDepth(v){
  if(['quick','standard','deep','exhaustive'].indexOf(v)<0)return;
  if(v===S.cfg.depth)return;              // oninput + onchange both fire; save once
  S.cfg.depth=v;$('#mDepth').value=v;saveCfg();applyCfg();persistDepth(v);
  paintDepthStrip();
  toast(DEPTH_LABEL[v]+' — theme updated');
}
$('#depth').onchange=function(){changeDepth(this.value);};
$('#depth').oninput=function(){changeDepth(this.value);};
$('#themeBtn').onclick=function(){S.cfg.theme=S.cfg.theme==='dark'?'light':'dark';saveCfg();applyCfg();};
$('#skinBtn').onclick=cycleSkin;
$('#skinBtn').oncontextmenu=function(e){e.preventDefault();S.cfg.skin='nebula';saveCfg();applySkin();applyCfg();};
if($('#skinBtn'))$('#skinBtn').onclick=cycleSkin;
$('#sourcesBtn').onclick=function(){
  S.cfg.sources=!S.cfg.sources;saveCfg();applyCfg();
  toast(S.cfg.sources?'Source chips shown under each answer':'Source chips hidden');
};
$('#aboutBtn').onclick=openAbout;
$('#openAbout').onclick=function(){closeSidebar();openAbout();};
$('#closeAbout').onclick=closeAbout;
$('#aboutOverlay').onclick=function(e){if(e.target===this)closeAbout();};
$('#aboutAsk').onclick=function(){closeAbout();send('/about');};
$('#menuBtn').onclick=function(){$('#sidebar').classList.add('open');$('#scrim').classList.add('on');};
$('#scrim').onclick=closeSidebar;
$('#openSettings').onclick=function(){closeSidebar();openSettings();};
$('#closeSettings').onclick=closeSettings;
$('#overlay').onclick=function(e){if(e.target===this)closeSettings();};
function bindSettingToggle(id,key){
  var e=$(id);if(!e)return;
  e.onclick=function(){var on=!this.classList.contains('on');this.classList.toggle('on',on);S.cfg.settings[key]=on;saveCfg();applyCfg();};
}
bindSettingToggle('#mRespect','respect');
bindSettingToggle('#mGrammar','grammar');
bindSettingToggle('#mSimple','simple_english');
bindSettingToggle('#mAutoLearn','auto_learn');
$('#mSections').addEventListener('change',function(e){
  var t=e.target;if(!t||!t.getAttribute('data-sec'))return;
  S.cfg.settings.sections[t.getAttribute('data-sec')]=!!t.checked;saveCfg();
});
$('#saveSettings').onclick=async function(){
  S.cfg.depth=$('#mDepth').value;S.cfg.theme=$('#mDark').classList.contains('on')?'dark':'light';
  S.cfg.settings=collectSettings();
  saveCfg();applyCfg();
  try{
    var d=await post('/api/settings',{settings:S.cfg.settings,depth:S.cfg.depth});
    if(d&&d.settings){S.cfg.settings=cloneSettings(d.settings);saveCfg();applyCfg();}
    showSetNote('Saved. Your settings apply to every answer and survive a server restart.');
    toast(DEPTH_LABEL[S.cfg.depth]);
  }catch(e){showSetNote('Saved in this browser. Server persistence was unavailable: '+e);}
  closeSettings();
};
$('#resetSettings').onclick=async function(){
  try{
    var d=await post('/api/settings/reset',{});
    S.cfg.settings=cloneSettings(d&&d.settings?d.settings:null);
    if(d&&d.depth)S.cfg.depth=d.depth;
  }catch(e){S.cfg.settings=cloneSettings();}
  saveCfg();applyCfg();showSetNote('All settings restored to their defaults.');
};
$('#mOnline').onclick=function(){this.classList.toggle('on');S.cfg.online=this.classList.contains('on');saveCfg();};
$('#mSources').onclick=function(){this.classList.toggle('on');S.cfg.sources=this.classList.contains('on');saveCfg();applyCfg();};
$('#mDark').onclick=function(){this.classList.toggle('on');S.cfg.theme=this.classList.contains('on')?'dark':'light';saveCfg();applyCfg();};
$('#learnBtn').onclick=async function(){
  var t=$('#learnInput').value.trim();if(!t)return;
  var note=$('#learnNote');note.style.display='block';note.textContent='Fetching and indexing “'+t+'”…';
  try{var d=await post('/api/learn',{topic:t,session_id:S.sid});note.textContent=d.reply?d.reply.slice(0,700):'Done';loadStatus();}
  catch(e){note.textContent='Could not reach the server: '+e;}
};
document.addEventListener('keydown',function(e){
  if(e.key==='Escape'){closeSettings();closeSidebar();closeAbout();closeSources();}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();newChat();}
});

/* ---------- defensive layout guard ----------
   If an embedding proxy or an old cached stylesheet ever drops the grid
   rules, detect it at runtime and force a two-column flex fallback instead
   of showing everything stacked inside the sidebar column. */
function ensureLayout(){
  var app=$('.app'),side=$('.sidebar'),main=$('.main'),scrim=$('.scrim');
  if(!app||!side||!main||window.innerWidth<=900)return;
  var sr=side.getBoundingClientRect(),mr=main.getBoundingClientRect();
  if(mr.left < sr.right-40 || mr.width < 400){
    app.style.display='flex';app.style.height='100vh';app.style.overflow='hidden';
    side.style.position='relative';side.style.transform='none';
    side.style.flex='0 0 274px';side.style.width='274px';side.style.height='100%';
    main.style.flex='1 1 auto';main.style.minWidth='0';main.style.width='auto';
    if(scrim){scrim.style.position='fixed';scrim.style.display='none';}
  }
}


/* ---------- v2.6.4 theme strip + skins ---------- */
function buildDepthStrip(){
  var host=document.getElementById('depthWrap');
  if(!host||host.dataset.built)return;
  host.dataset.built='1';
  var box=document.createElement('div');box.className='dswatch';
  ['quick','standard','deep','exhaustive'].forEach(function(d){
    var i=document.createElement('i');
    i.dataset.d=d; i.title=DEPTH_LABEL[d]||d;
    i.onclick=function(){changeDepth(d);};
    box.appendChild(i);
  });
  host.appendChild(box);
}
function paintDepthStrip(){
  var box=document.querySelector('.dswatch');if(!box)return;
  Array.prototype.forEach.call(box.children,function(i){
    i.classList.toggle('on', i.dataset.d===S.cfg.depth);
  });
  var nm=document.getElementById('skinName');
  if(nm)nm.textContent=({nebula:'Nebula',neon:'Neon',paper:'Paper'}[(S.cfg.skin||'nebula')]||'Nebula');
}
function applySkin(){
  var skin=S.cfg.skin||'nebula';
  if(skin==='nebula'){document.documentElement.removeAttribute('data-skin');}
  else{document.documentElement.dataset.skin=skin;
    // Neon is a dark look, Paper is a light look: flip the base theme with it
    S.cfg.theme = skin==='neon' ? 'dark' : 'light';
    document.documentElement.dataset.theme=S.cfg.theme;
  }
  paintDepthStrip();
}
function cycleSkin(){
  var order=['nebula','neon','paper'],cur=S.cfg.skin||'nebula';
  S.cfg.skin=order[(order.indexOf(cur)+1)%order.length];
  saveCfg();applySkin();applyCfg();
  toast('Look: '+({nebula:'Nebula',neon:'Neon',paper:'Paper'}[S.cfg.skin]));
}

/* ---------- v2.6.2 wiring ---------- */
(function(){
  var ccT=document.getElementById('ccToggle');
  if(ccT)ccT.onclick=function(){
    var body=document.getElementById('ccBody');
    var open=body.style.display==='none';
    body.style.display=open?'block':'none';
    document.getElementById('ccToggleNote').textContent=open?'close':'open';
  };
  var role=document.getElementById('ccMyRole');
  if(role)role.onclick=function(){
    try{navigator.clipboard.writeText('author · owner');role.textContent='copied ✓';
      setTimeout(function(){role.textContent='author · owner';},1100);}catch(e){}
  };
  // scroll progress rail on the thread
  var rail=document.getElementById('scrollRail');
  var box=document.getElementById('messages');
  if(rail&&box){
    var upd=function(){
      var h=box.scrollHeight-box.clientHeight;
      var p=h>0?box.scrollTop/h:0;
      rail.style.transform='scaleX('+Math.max(0,Math.min(1,p))+')';
    };
    box.addEventListener('scroll',upd,{passive:true});
    setInterval(upd,1200);
  }
})();

/* ===================== v2.6.2 command palette (Ctrl/Cmd+K) ============== */
var CP={items:[],sel:0,open:false};
function cpActions(){
  var a=[
    {k:'Chat',  label:'New chat',           sub:'fresh', run:function(){newChat();}},
    {k:'Panel', label:'Settings & knowledge',sub:'',        run:function(){openSettings();}},
    {k:'Panel', label:'About Ryzek & creator',sub:'',       run:function(){openAbout();}},
    {k:'Panel', label:'Account & memory',   sub:'',         run:function(){acctOpen(true);}},
    {k:'View',  label:'Toggle light / dark',sub:'',         run:function(){$('#themeBtn').click();}},
    {k:'Depth', label:'Quick answer',       sub:'fast',     run:function(){changeDepth('quick');}},
    {k:'Depth', label:'Standard answer',    sub:'default',  run:function(){changeDepth('standard');}},
    {k:'Depth', label:'Deep answer',        sub:'detailed', run:function(){changeDepth('deep');}},
    {k:'Depth', label:'Exhaustive answer',  sub:'everything',run:function(){changeDepth('exhaustive');}},
    {k:'Web',   label:'Toggle live web research', sub:'', run:function(){var b=$('#webBtn');if(b)b.click();}},
    {k:'Account',label:'Sign out',          sub:'',         run:function(){$('#signOut').click();}}
  ];
  (S.sessions||[]).slice(0,40).forEach(function(x){
    a.push({k:'Chat',label:x.title||'New chat',
            sub:(x.count||0)+' msgs',run:function(){selectChat(x.id);closeSidebar();}});
  });
  return a;
}
function cpRender(){
  var q=($('#cpInput').value||'').toLowerCase().trim();
  var list=CP.items.filter(function(i){
    return !q||(i.label+' '+i.k).toLowerCase().indexOf(q)>=0;
  }).slice(0,60);
  CP.view=list;
  if(CP.sel>=list.length)CP.sel=Math.max(0,list.length-1);
  var box=$('#cpList');box.innerHTML='';
  if(!list.length){box.innerHTML='<div class="cp-item">Nothing matched. Try "deep", "settings" or a chat name.</div>';return;}
  list.forEach(function(it,i){
    var d=document.createElement('div');
    d.className='cp-item'+(i===CP.sel?' sel':'');
    var k=document.createElement('span');k.className='k';k.textContent=it.k;
    var l=document.createElement('span');l.textContent=it.label;
    d.appendChild(k);d.appendChild(l);
    if(it.sub){var sb=document.createElement('span');sb.className='sub';sb.textContent=it.sub;d.appendChild(sb);}
    d.onclick=function(){cpRun(it);};
    box.appendChild(d);
  });
}
function cpRun(it){
  cpClose();
  try{it.run();}catch(e){}
}
function cpClose(){$('#cpWrap').classList.remove('on');CP.open=false;}
function cpOpen(){
  CP.items=cpActions();CP.sel=0;
  $('#cpWrap').classList.add('on');CP.open=true;
  $('#cpInput').value='';cpRender();$('#cpInput').focus();
}
document.addEventListener('keydown',function(e){
  var k=(e.key||'').toLowerCase();
  if((e.ctrlKey||e.metaKey)&&k==='k'){e.preventDefault();CP.open?cpClose():cpOpen();return;}
  if(!CP.open)return;
  if(k==='escape'){e.preventDefault();cpClose();}
  else if(k==='arrowdown'){e.preventDefault();CP.sel++;cpRender();}
  else if(k==='arrowup'){e.preventDefault();CP.sel=Math.max(0,CP.sel-1);cpRender();}
  else if(k==='enter'){
    e.preventDefault();
    if(CP.view&&CP.view[CP.sel])cpRun(CP.view[CP.sel]);
  }
});
$('#cpInput').oninput=cpRender;
$('#cpWrap').onclick=function(e){if(e.target===this)cpClose();};

/* ---------- boot ---------- */
try{
  var BUILD='264';
  if(localStorage.getItem('ryzek_build')&&localStorage.getItem('ryzek_build')!==BUILD){
    localStorage.setItem('ryzek_build',BUILD);
    location.replace(location.pathname+(location.search?location.search:''));
  }else{localStorage.setItem('ryzek_build',BUILD);}
}catch(e){}
loadCfg();loadServerSettings();loadMe();loadSessions();loadStatus();loadPlatforms();$('#input').focus();
ensureLayout();
window.addEventListener('resize',ensureLayout);
setTimeout(ensureLayout,300);
})();
</script>
</body>
</html>
"""
