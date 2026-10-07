// NEON RAIN ui: TAP TO ENTER gate, title + settings, HUD, film-style dialogue and intertitles, tutorial cards,
// interrogation (close-up, pulse / eye / hesitation meters, 4 of 8 questions, OFFER, verdict), case file, pause, game over, end card.
(function () {
  const C = NR.cfg; let core = null, root = null; const E = {};
  const CSS = `
#nru{position:absolute;inset:0;z-index:6;pointer-events:none;font-family:Georgia,"Times New Roman",serif;color:#eadfca;-webkit-user-select:none;user-select:none}
#nru *{box-sizing:border-box}
#nru .tap{pointer-events:auto;cursor:pointer}
#nru .hud{position:absolute;inset:0;display:none}
#nru .hud.on{display:block}
#nru .obj{position:absolute;left:0;right:0;top:calc(10px + env(safe-area-inset-top,0px));text-align:center;font-style:italic;font-size:14px;letter-spacing:.04em;color:#eadfca;text-shadow:0 1px 3px #000,0 0 8px #000;padding:0 70px}
#nru .obj:empty{display:none}
#nru .obj::after{content:"";display:block;width:60px;height:1px;margin:6px auto 0;background:rgba(234,223,202,.5)}
#nru .tl{position:absolute;left:12px;top:calc(10px + env(safe-area-inset-top,0px));font-family:"Courier New",monospace;font-weight:bold;font-size:12px;letter-spacing:.1em;line-height:1.7;text-shadow:0 1px 2px #000}
#nru .cyl{display:flex;gap:3px;margin-bottom:2px}
#nru .cyl b{width:9px;height:9px;border-radius:50%;background:#e8b040;box-shadow:0 0 4px rgba(232,176,64,.8)}
#nru .cyl b.x{background:rgba(234,223,202,.18);box-shadow:none}
#nru .tl .rl{color:#e8b040}
#nru .tr{position:absolute;right:10px;top:calc(8px + env(safe-area-inset-top,0px));display:flex;gap:8px}
#nru .ib{width:40px;height:40px;border:1.5px solid rgba(234,223,202,.55);background:rgba(10,9,8,.5);display:flex;align-items:center;justify-content:center;font-family:"Courier New",monospace;font-weight:bold;font-size:11px;letter-spacing:.05em;color:#eadfca}
#nru .xh{position:absolute;left:50%;top:50%;width:26px;height:26px;margin:-13px 0 0 -13px}
#nru .xh i{position:absolute;background:rgba(234,223,202,.85);box-shadow:0 0 2px #000}
#nru .xh i:nth-child(1){left:12px;top:0;width:2px;height:7px}#nru .xh i:nth-child(2){left:12px;bottom:0;width:2px;height:7px}
#nru .xh i:nth-child(3){top:12px;left:0;height:2px;width:7px}#nru .xh i:nth-child(4){top:12px;right:0;height:2px;width:7px}
#nru .xh i:nth-child(5){left:12px;top:12px;width:2px;height:2px}
#nru .xh.on i{background:#d8261a}
#nru .xh.hit{transform:rotate(45deg) scale(1.2)}
#nru .xh.hit i{background:#fff}
#nru .prompt{position:absolute;left:0;right:0;bottom:22%;text-align:center;font-family:"Courier New",monospace;font-weight:bold;font-size:13px;letter-spacing:.14em;text-shadow:0 1px 3px #000}
#nru .toast{position:absolute;left:8%;right:8%;top:16%;text-align:center;padding:10px 12px;background:rgba(10,9,8,.78);border:1px solid #e8b040;color:#ffe2a0;font-size:14px;opacity:0;transition:opacity .3s;line-height:1.35}
#nru .toast.on{opacity:1}
#nru .toast small{display:block;font-family:"Courier New",monospace;font-weight:bold;letter-spacing:.18em;font-size:11px;color:#e8b040;margin-bottom:4px}
#nru .scanbar{position:absolute;left:50%;top:50%;width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;display:none}
#nru .lb{position:absolute;left:0;right:0;height:0;background:#000;transition:height .5s}
#nru .lb.t{top:0}#nru .lb.b{bottom:0}
#nru.cut .lb{height:7%}
#nru .dlg{position:absolute;left:10px;right:10px;bottom:calc(8% + 12px);min-height:120px;padding:14px 16px 26px;background:rgba(6,5,4,.88);border:1px solid rgba(234,223,202,.45);outline:1px solid rgba(234,223,202,.15);outline-offset:3px;display:none;pointer-events:auto}
#nru .dlg.on{display:block}
#nru .dlg .who{font-family:"Courier New",monospace;font-weight:bold;font-size:12px;letter-spacing:.22em;color:#e8b040;margin-bottom:8px}
#nru .dlg .who.vela{color:#e04a3a}
#nru .dlg .txt{font-size:17px;line-height:1.45;color:#f2e8d4;min-height:3em}
#nru .dlg.vo .txt{font-style:italic;color:#d8ceb8}
#nru .dlg .more{position:absolute;right:12px;bottom:6px;font-size:12px;color:#e8b040;animation:nrblink 1s steps(2) infinite}
#nru .card{position:absolute;inset:0;background:#000;display:none;align-items:center;justify-content:center;pointer-events:auto;opacity:0;transition:opacity .6s}
#nru .card.on{display:flex}#nru .card.vis{opacity:1}
#nru .card .fr{width:82%;padding:46px 18px;border:2px solid #eadfca;outline:1px solid #eadfca;outline-offset:6px;text-align:center;font-size:19px;letter-spacing:.07em;line-height:1.7;white-space:pre-line;position:relative}
#nru .card .fr::before,#nru .card .fr::after{content:"\\25C6";position:absolute;left:50%;transform:translateX(-50%);font-size:12px;color:#eadfca}
#nru .card .fr::before{top:12px}#nru .card .fr::after{bottom:12px}
#nru .tut{position:absolute;left:7%;right:7%;top:16%;padding:18px 18px 14px;background:rgba(10,9,8,.92);border:1px solid #e8b040;display:none;pointer-events:auto}
#nru .tut.on{display:block}
#nru .tut h3{margin:0 0 10px;font-family:"Courier New",monospace;letter-spacing:.24em;font-size:14px;color:#e8b040}
#nru .tut p{margin:0;white-space:pre-line;font-size:15px;line-height:1.45}
#nru .tut .go{margin-top:14px;text-align:right;font-family:"Courier New",monospace;font-weight:bold;font-size:12px;letter-spacing:.18em;color:#e8b040}
#nru .scr{position:absolute;inset:0;display:none;pointer-events:auto;background:rgba(5,5,6,.9);flex-direction:column;align-items:center;justify-content:center;text-align:center}
#nru .scr.on{display:flex}
#nru .btn{display:block;min-width:220px;margin:8px auto;padding:13px 18px;border:1.5px solid rgba(234,223,202,.7);background:rgba(10,9,8,.6);font-family:"Courier New",monospace;font-weight:bold;letter-spacing:.2em;font-size:14px;color:#eadfca;text-align:center}
#nru .btn.red{border-color:#b8241c;color:#ffd8cc;box-shadow:0 0 12px rgba(184,36,28,.5)}
#nru .btn:active{background:rgba(234,223,202,.2)}
#nru .title{background:radial-gradient(ellipse at 50% 35%,rgba(0,0,0,.05),rgba(0,0,0,.75) 80%)}
#nru .logo{font-family:Georgia,serif;font-weight:bold;font-size:58px;letter-spacing:.08em;line-height:1;color:#fff4ea;margin-top:-46vh;width:100%}
#nru .logo small{display:block;font-size:13px;letter-spacing:.42em;color:#eadfca;text-shadow:0 1px 3px #000;margin-top:18px;font-weight:normal}
#nru .logo em{display:block;font-style:italic;font-size:22px;letter-spacing:.06em;color:#eadfca;text-shadow:0 1px 4px #000;margin-top:8px;font-weight:normal}
#nru .menu{position:absolute;left:0;right:0;bottom:9%}
#nru .menu .btn{width:66%;margin:8px auto;background:rgba(6,5,4,.55)}
#nru .foot{position:absolute;left:0;right:0;bottom:calc(10px + env(safe-area-inset-bottom,0px));font-size:10px;letter-spacing:.2em;color:#8a8070;font-family:"Courier New",monospace}
#nru .set{width:86%;max-width:360px;text-align:left}
#nru .set .row{display:flex;align-items:center;justify-content:space-between;padding:12px 4px;border-bottom:1px solid rgba(234,223,202,.2);font-family:"Courier New",monospace;font-weight:bold;letter-spacing:.12em;font-size:13px}
#nru .set .row .v{display:flex;gap:6px;align-items:center}
#nru .set .row .v span{min-width:52px;text-align:center;color:#e8b040}
#nru .set .row .v b{width:36px;height:32px;border:1px solid rgba(234,223,202,.6);display:flex;align-items:center;justify-content:center}
#nru .set h2,#nru .cf h2{font-family:"Courier New",monospace;letter-spacing:.3em;font-size:16px;color:#e8b040;margin:0 0 10px}
#nru .itg{position:absolute;inset:0;display:none;pointer-events:auto;background:#060505;flex-direction:column}
#nru .itg.on{display:flex}
#nru .itg .pic{position:relative;height:39%;flex-shrink:0;overflow:hidden;background:#000}
#nru .itg .pic img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 22%;opacity:0;transition:opacity .45s}
#nru .itg .pic img.on{opacity:1}
#nru .itg .pic::after{content:"";position:absolute;inset:0;background:radial-gradient(ellipse at 50% 40%,transparent 45%,rgba(0,0,0,.75));pointer-events:none}
#nru .itg .nm{position:absolute;left:12px;bottom:10px;z-index:2;font-family:"Courier New",monospace;font-weight:bold;letter-spacing:.2em;font-size:12px;text-shadow:0 1px 3px #000}
#nru .itg .nm small{display:block;font-weight:normal;letter-spacing:.1em;color:#b8ac98;font-family:Georgia,serif;font-style:italic;margin-top:2px}
#nru .itg .smk{position:absolute;right:12px;bottom:10px;z-index:2;font-family:"Courier New",monospace;font-size:11px;letter-spacing:.14em;color:#e8b040;text-shadow:0 1px 3px #000}
#nru .met{display:grid;grid-template-columns:1.4fr 1fr 1fr;gap:6px;padding:8px 10px;border-bottom:1px solid rgba(234,223,202,.18);font-family:"Courier New",monospace;font-weight:bold;font-size:10px;letter-spacing:.14em}
#nru .met div{background:rgba(234,223,202,.05);padding:5px 6px;border:1px solid rgba(234,223,202,.15)}
#nru .met canvas{display:block;width:100%;height:26px}
#nru .met .val{font-size:15px;color:#e8b040;letter-spacing:.05em}
#nru .met .bar{height:6px;background:rgba(234,223,202,.12);margin-top:6px;position:relative}
#nru .met .bar i{position:absolute;left:0;top:0;bottom:0;background:#e8b040;transition:width .4s}
#nru .ans{padding:10px 14px;min-height:94px;font-size:15px;line-height:1.42;border-bottom:1px solid rgba(234,223,202,.18)}
#nru .ans .q{font-style:italic;color:#a89c88;font-size:13px;margin-bottom:5px}
#nru .ans .slip{display:block;margin-top:6px;color:#ffb070;font-style:italic}
#nru .ans .slip::before{content:"SLIP  ";font-family:"Courier New",monospace;font-weight:bold;font-style:normal;font-size:10px;letter-spacing:.2em;color:#e8b040}
#nru .qs{flex:1;overflow-y:auto;padding:6px 10px 14px;-webkit-overflow-scrolling:touch}
#nru .qs .hdr{display:flex;justify-content:space-between;font-family:"Courier New",monospace;font-weight:bold;font-size:11px;letter-spacing:.16em;color:#e8b040;padding:4px 2px 6px}
#nru .qs .qb{padding:9px 10px;margin:5px 0;border:1px solid rgba(234,223,202,.35);font-size:14px;line-height:1.3;background:rgba(234,223,202,.03)}
#nru .qs .qb.used{opacity:.35;pointer-events:none;text-decoration:line-through}
#nru .qs .qb.clue{border-color:#e8b040}
#nru .qs .qb.clue::before{content:"CLUE  ";font-family:"Courier New",monospace;font-weight:bold;font-size:10px;letter-spacing:.16em;color:#e8b040}
#nru .qs .row2{display:flex;gap:8px;margin-top:8px}
#nru .qs .row2 .btn{flex:1;min-width:0;margin:0;padding:12px 6px;font-size:13px}
#nru .qs .off{opacity:.35;pointer-events:none}
#nru .cf{position:absolute;inset:0;display:none;pointer-events:auto;background:#1b1712;flex-direction:column;padding:calc(16px + env(safe-area-inset-top,0px)) 16px 16px;overflow-y:auto}
#nru .cf.on{display:flex}
#nru .cf .page{background:#d9cdb2;color:#1e1a14;padding:16px 16px 18px;box-shadow:0 4px 18px rgba(0,0,0,.6);font-family:"Courier New",monospace;font-size:13px;line-height:1.45;position:relative}
#nru .cf .page h4{margin:14px 0 6px;font-size:12px;letter-spacing:.25em;border-bottom:1px solid #6a5a44;padding-bottom:3px}
#nru .cf .page .it{margin:6px 0 10px}
#nru .cf .page .it b{display:block;letter-spacing:.06em}
#nru .cf .page .it i{display:block;color:#7a1810;margin-top:3px}
#nru .cf .page .miss{color:#8a7a62}
#nru .cf .stamp{position:absolute;right:14px;top:12px;border:2px solid #9a1a10;color:#9a1a10;padding:2px 6px;font-weight:bold;letter-spacing:.2em;transform:rotate(6deg);font-size:12px}
#nru .cf .close{margin-top:14px;position:sticky;bottom:6px;background:#1b1712;flex-shrink:0}
#nru .ec .stats{font-family:"Courier New",monospace;font-size:13px;letter-spacing:.12em;line-height:1.9;margin:22px 0;text-align:left;display:inline-block}
#nru .ec .stats b{color:#e8b040}
@keyframes nrblink{50%{opacity:.25}}
#nru .title.jbopen .menu{display:none}
#nru .jb{position:absolute;left:17%;right:17%;bottom:7%;display:none;pointer-events:auto;z-index:25;font-family:"Courier New",monospace;color:#eadfca;max-height:60%;overflow-y:auto;touch-action:pan-y;scrollbar-width:none}
#nru .jb::-webkit-scrollbar{display:none}
#nru .jb.on{display:block}
#nru .jb .row{position:relative;margin:5px 0;padding:8px 10px;border:1px solid rgba(234,223,202,.55);background:rgba(6,5,4,.6);font-weight:bold;font-size:11px;letter-spacing:.14em;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#nru .jb .row.tr{text-align:left;padding-left:22px;margin:4px 0;font-size:10.5px}
#nru .jb .row .mk{position:absolute;left:8px;color:#d8261a;visibility:hidden}
#nru .jb .row.cur{border-color:#b8241c;color:#fff;box-shadow:0 0 10px rgba(184,36,28,.45)}
#nru .jb .row.cur .mk{visibility:visible}
#nru .jb .row .pl{position:absolute;left:0;bottom:0;height:1px;width:0;background:#d8261a}
#nru .jb .row.back{margin-top:10px;font-size:12px;letter-spacing:.2em}
#nru .jb .ctl{display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:0 16px;margin:8px 0 2px;font-weight:bold;font-size:12px;letter-spacing:.12em;text-shadow:0 1px 3px #000}
#nru .jb .ctl span{padding:7px 6px;color:#eadfca;font-size:15px;text-shadow:0 0 4px #000,0 1px 3px #000}
#nru .jb .ctl .pp{color:#ff5a48;font-size:14px}
#nru .jb .ctl .tg{font-size:10px !important;letter-spacing:.16em;color:#a89c88}
#nru .jb .ctl .br{flex-basis:100%;height:0;padding:0}
#nru .jb .ctl .tg.on{color:#e8b040}
#nru .jb .sc{display:flex;align-items:center;gap:6px;font-size:9.5px;color:#a89c88;text-shadow:0 1px 2px #000}
#nru .jb .sc input{flex:1;height:22px;touch-action:pan-x;margin:0;-webkit-appearance:none;appearance:none;background:transparent}
#nru .jb .sc input::-webkit-slider-runnable-track{height:1px;background:rgba(234,223,202,.45)}
#nru .jb .sc input::-moz-range-track{height:1px;background:rgba(234,223,202,.45)}
#nru .jb .sc input::-webkit-slider-thumb{-webkit-appearance:none;width:9px;height:9px;border-radius:50%;background:#d8261a;margin-top:-4px;box-shadow:0 0 6px rgba(216,38,26,.8)}
#nru .jb .sc input::-moz-range-thumb{width:9px;height:9px;border:none;border-radius:50%;background:#d8261a}
#nru .jb.vb{background:linear-gradient(rgba(4,3,2,.0),rgba(4,3,2,.72) 8%,rgba(4,3,2,.72) 92%,rgba(4,3,2,0));padding:10px 4px}
#nru .jb .ln-h{text-align:center;font-size:9.5px;letter-spacing:.3em;color:#e8b040;margin:4px 0 8px}
#nru .jb .ln{display:flex;align-items:baseline;gap:6px;padding:5px 2px;font-size:10.5px;letter-spacing:.08em;color:#d8ceb8}
#nru .jb .ln .n{color:#8a8070}
#nru .jb .ln .tt{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:70%}
#nru .jb .ln .dots{flex:1;border-bottom:1px dotted rgba(234,223,202,.45);transform:translateY(-3px);min-width:12px}
#nru .jb .ln .len{color:#a89c88}
#nru .jb .ln.cur{color:#fff}
#nru .jb .ln.cur .n{color:#d8261a}
#nru .jb .ln.cur .n::before{content:"\\25B8 ";color:#d8261a}
#nru .jb .np{margin:10px 0 4px;font-size:10px;letter-spacing:.14em;color:#eadfca;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#nru .jb .np b{color:#d8261a}
#nru .jb .dial{display:flex;align-items:stretch;border:1px solid #b8241c;background:rgba(6,5,4,.62);box-shadow:0 0 12px rgba(184,36,28,.45);touch-action:pan-y}
#nru .jb .dial .ar{display:flex;align-items:center;padding:0 14px;font-size:22px;color:#ff5a48}
#nru .jb .dial .dm{flex:1;text-align:center;padding:9px 2px 8px;min-width:0}
#nru .jb .dial .lab{display:block;font-size:8.5px;letter-spacing:.3em;color:#e8b040}
#nru .jb .dial .dt{display:block;margin:4px 0 7px;font-family:Georgia,serif;font-size:14px;letter-spacing:.08em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#nru .jb .dial .hl{height:1px;background:rgba(234,223,202,.2);margin:0 6px}
#nru .jb .dial .hl i{display:block;height:1px;width:0;background:#d8261a}
#nru .jb .ctl .lt{color:#e8b040 !important}
#nru .jb .dl{display:none;margin:4px 0 6px;padding:4px 8px;background:rgba(4,3,2,.7)}
#nru .jb .dl.on{display:block}`;

  const h = (tag, cls, html, parent) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; (parent || root).appendChild(e); return e; };
  const tapOnce = (el) => new Promise(r => { const f = (ev) => { ev.preventDefault(); ev.stopPropagation(); el.removeEventListener('pointerup', f); r(); }; el.addEventListener('pointerup', f); });
  function onTap(el, fn) { el.classList.add('tap'); el.setAttribute('data-tap', '1'); el.addEventListener('pointerup', (e) => { e.preventDefault(); e.stopPropagation(); fn(e); }); }

  function build() {
    const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
    root = document.createElement('div'); root.id = 'nru'; document.getElementById('ui').appendChild(root);
    h('div', 'lb t'); h('div', 'lb b');
    // HUD
    E.hud = h('div', 'hud');
    E.obj = h('div', 'obj', '', E.hud);
    E.tl = h('div', 'tl', '<div class="cyl"></div><div class="rl"></div><div class="pk"></div><div class="lv"></div>', E.hud);
    E.cyl = E.tl.querySelector('.cyl'); E.rl = E.tl.querySelector('.rl'); E.pk = E.tl.querySelector('.pk'); E.lv = E.tl.querySelector('.lv');
    for (let i = 0; i < 6; i++) h('b', '', null, E.cyl);
    E.tr = h('div', 'tr', '', E.hud);
    E.caseBtn = h('div', 'ib', 'CASE', E.tr); onTap(E.caseBtn, () => NR.game.openCase());
    E.pauseBtn = h('div', 'ib', '| |', E.tr); onTap(E.pauseBtn, () => NR.game.pause(true));
    E.xh = h('div', 'xh', '<i></i><i></i><i></i><i></i><i></i>', E.hud);
    E.scanbar = h('div', 'scanbar', '', E.hud);
    E.prompt = h('div', 'prompt', '', E.hud);
    E.toast = h('div', 'toast', '');
    // dialogue, cards, tutorials
    E.dlg = h('div', 'dlg', '<div class="who"></div><div class="txt"></div><div class="more">&#x25BC;</div>');
    E.who = E.dlg.querySelector('.who'); E.txt = E.dlg.querySelector('.txt'); E.more = E.dlg.querySelector('.more');
    E.card = h('div', 'card', '<div class="fr"></div>'); E.cardT = E.card.querySelector('.fr');
    E.tut = h('div', 'tut', '<h3></h3><p></p><div class="go">TAP TO CONTINUE &#x25B8;</div>');
    // screens
    E.title = h('div', 'scr title', '<div class="logo"></div><div class="menu"></div>');
    NR.neon.mount(E.title.querySelector('.logo'));
    const menu = E.title.querySelector('.menu');
    E.begin = h('div', 'btn red', 'BEGIN CASE', menu); E.jbBtn = h('div', 'btn', 'JUKEBOX', menu); E.setBtn = h('div', 'btn', 'SETTINGS', menu);
    onTap(E.jbBtn, () => NR.jukebox.open());
    E.jb = h('div', 'jb', '', E.title);
    onTap(E.setBtn, () => settingsOpen(true));
    E.set = h('div', 'scr', '<div class="set"><h2>SETTINGS</h2><div class="rows"></div></div>'); E.set.style.zIndex = 30;
    E.pause = h('div', 'scr', '<h2 style="font-family:Courier New,monospace;letter-spacing:.3em;color:#e8b040">PAUSED</h2>');
    onTap(h('div', 'btn red', 'RESUME', E.pause), () => NR.game.pause(false));
    onTap(h('div', 'btn', 'CASE FILE', E.pause), () => { NR.game.openCase(); });
    onTap(h('div', 'btn', 'SETTINGS', E.pause), () => settingsOpen(true));
    onTap(h('div', 'btn', 'QUIT TO TITLE', E.pause), () => location.reload());
    E.over = h('div', 'scr over', '<div class="card on vis" style="position:relative;background:none;display:block;opacity:1"><div class="fr" style="margin:0 auto">THEY GOT YOU.\nTHE RAIN KEPT FALLING.</div></div>');
    E.retry = h('div', 'btn red', 'RETRY THE SCENE', E.over); E.retry.style.marginTop = '28px';
    E.end = h('div', 'scr ec', '');
    E.cf = h('div', 'cf', '<h2>CASE FILE</h2><div class="page"></div><div class="btn close">CLOSE</div>');
    onTap(E.cf.querySelector('.close'), () => NR.game.closeCase());
    E.itg = h('div', 'itg', '');
  }

  // ---------------------------------------------------------------- settings
  function settingsOpen(on) {
    if (!on) { E.set.classList.remove('on'); return; }
    const s = core.settings, rows = E.set.querySelector('.rows'); rows.innerHTML = '';
    const row = (label, val, dec, inc) => { const r = h('div', 'row', '<span>' + label + '</span><div class="v"></div>', rows); const v = r.querySelector('.v');
      if (dec) onTap(h('b', '', '&minus;', v), () => { dec(); settingsOpen(true); }); h('span', '', val, v); onTap(h('b', '', inc && dec ? '+' : '&#x21C4;', v), () => { (inc || dec)(); settingsOpen(true); }); };
    row('FILM', s.film === 'bwred' ? 'B&amp;W RED' : 'NOIR COLOR', null, () => { s.film = s.film === 'bwred' ? 'noir' : 'bwred'; s.bw = s.film === 'bwred'; core.saveSettings(); });
    row('MUSIC', Math.round(s.music * 10), () => { s.music = Math.max(0, +(s.music - 0.1).toFixed(1)); core.saveSettings(); NR.audio.setVolumes(); }, () => { s.music = Math.min(1, +(s.music + 0.1).toFixed(1)); core.saveSettings(); NR.audio.setVolumes(); });
    row('SOUND', Math.round(s.sfx * 10), () => { s.sfx = Math.max(0, +(s.sfx - 0.1).toFixed(1)); core.saveSettings(); NR.audio.setVolumes(); }, () => { s.sfx = Math.min(1, +(s.sfx + 0.1).toFixed(1)); core.saveSettings(); NR.audio.setVolumes(); });
    row('LOOK SPEED', (s.sens || 1).toFixed(1), () => { s.sens = Math.max(0.4, +((s.sens || 1) - 0.1).toFixed(1)); core.saveSettings(); }, () => { s.sens = Math.min(2.5, +((s.sens || 1) + 0.1).toFixed(1)); core.saveSettings(); });
    row('CHARACTERS', s.chars === '3d' ? '3D' : 'PAINTED', null, () => { s.chars = s.chars === '3d' ? 'painted' : '3d'; core.saveSettings(); });
    row('JUKEBOX: SHOW ALL', s.jbAll === false ? 'OFF' : 'ON', null, () => { s.jbAll = s.jbAll === false; core.saveSettings(); if (NR.jukebox.isOpen) NR.jukebox.render(); });
    row('QUALITY', s.quality.toUpperCase(), null, () => { core.setQuality(s.quality === 'high' ? 'low' : 'high'); });
    if (!E.set.querySelector('.done')) { const d = h('div', 'btn done', 'DONE', E.set.querySelector('.set')); d.style.marginTop = '18px'; onTap(d, () => settingsOpen(false)); }
    E.set.classList.add('on');
  }

  // ---------------------------------------------------------------- gate + title
  function gate() {
    return new Promise(res => {
      try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch (e) {}
      const g = document.createElement('div'); g.id = 'nrgate';
      g.style.cssText = 'position:fixed;inset:0;z-index:50;display:flex;align-items:flex-end;justify-content:center;padding-bottom:16vh;background:rgba(0,0,0,.6);font-family:"Courier New",monospace;color:#eadfca;letter-spacing:6px;font-size:18px;text-shadow:0 0 10px #b8241c;cursor:pointer;touch-action:none';
      g.innerHTML = '<span style="animation:nrblink 1.6s steps(2) infinite">TAP TO ENTER</span>';
      const go = (e) => { if (e) { e.preventDefault(); e.stopPropagation(); } NR.audio.unlock(); g.remove(); removeEventListener('keydown', go, true); res(); };
      g.addEventListener('click', go); g.addEventListener('touchend', go); addEventListener('keydown', go, true);
      document.body.appendChild(g);
    });
  }
  function title() {
    E.title.classList.add('on');
    return new Promise(r => { const f = () => { E.title.classList.remove('on'); r(); }; onTap(E.begin, f); E.beginFn = f; });
  }

  // ---------------------------------------------------------------- dialogue + cards
  let typing = null;
  function say(who, text) {
    return new Promise(async (res) => {
      const vo = /V\.O\./.test(who);
      E.dlg.classList.toggle('vo', vo); E.who.textContent = who; E.who.className = 'who' + (who === 'VELA' ? ' vela' : '');
      E.dlg.classList.add('on'); E.txt.textContent = ''; E.more.style.visibility = 'hidden'; clearTimeout(UI.undT); NR.audio.duck(0.5); // duck the score under VO
      let i = 0, done = false; const speed = UI.fast ? 4000 : 42;
      await new Promise(r2 => {
        let acc = 0, last = performance.now();
        typing = () => { done = true; E.txt.textContent = text; r2(); };
        (function step(now) { if (done) return; acc += (now - last) / 1000 * speed; last = now; const n = Math.min(text.length, Math.floor(acc)); if (n > i) { i = n; E.txt.textContent = text.slice(0, i); if (i % 3 === 0) NR.audio.fx.type(); } if (i >= text.length) { done = true; r2(); } else requestAnimationFrame(step); })(last);
        const skip = (e) => { e.preventDefault(); e.stopPropagation(); E.dlg.removeEventListener('pointerup', skip); if (!done) typing(); };
        E.dlg.addEventListener('pointerup', skip);
      });
      typing = null; E.more.style.visibility = 'visible';
      await advance(E.dlg);
      E.dlg.classList.remove('on'); UI.undT = setTimeout(() => NR.audio.duck(1), 700); res();
    });
  }
  function advance(el) { return new Promise(r => { let done = false; const fin = () => { if (done) return; done = true; el.removeEventListener('pointerup', f); removeEventListener('keydown', k, true); setTimeout(r, 30); };
    const f = (e) => { e.preventDefault(); e.stopPropagation(); fin(); }; const k = (e) => { if (e.code === 'Space' || e.code === 'Enter' || e.code === 'KeyE') { e.preventDefault(); fin(); } };
    setTimeout(() => { el.addEventListener('pointerup', f); addEventListener('keydown', k, true); }, UI.fast ? 0 : 120); }); }
  async function lines(arr) { for (const [w, t] of arr) await say(w, t); }
  async function card(text, hold = 2.6) {
    E.cardT.textContent = text; E.card.classList.add('on'); await NR.core.wait(0.02); E.card.classList.add('vis');
    await Promise.race([NR.core.wait(UI.fast ? 0.3 : hold + 0.6), advance(E.card)]);
    E.card.classList.remove('vis'); await NR.core.wait(0.6); E.card.classList.remove('on');
  }
  async function tutorial(t) {
    E.tut.querySelector('h3').textContent = t.title; E.tut.querySelector('p').textContent = t.body; E.tut.classList.add('on');
    await advance(E.tut); E.tut.classList.remove('on');
  }
  function letterbox(on) { root.classList.toggle('cut', !!on); }
  let toastT = 0;
  function toast(head, text, secs = 3.2) { E.toast.innerHTML = '<small>' + head + '</small>' + text; E.toast.classList.add('on'); toastT = secs; }
  function objective(t) { E.obj.textContent = t || ''; }
  function prompt(t) { E.prompt.textContent = t || ''; }

  // ---------------------------------------------------------------- HUD per frame
  let hitT = 0, vRounds = -1, vPack = -1, vLives = -1, vRel = null;
  NR.bus.on('hitEnemy', () => { hitT = 0.14; });
  function update(dt) {
    const P = NR.player, play = core.state === 'PLAY';
    E.hud.classList.toggle('on', play);
    if (toastT > 0) { toastT -= dt; if (toastT <= 0) E.toast.classList.remove('on'); }
    if (!play) return;
    E.cyl.style.display = P.armed ? 'flex' : 'none';
    if (P.rounds !== vRounds) { vRounds = P.rounds; E.cyl.querySelectorAll('b').forEach((b, i) => b.classList.toggle('x', i >= P.rounds)); }
    const rel = P.reloadT > 0 ? 'RELOADING' : (P.armed && P.rounds === 0 ? 'RELOAD' : '');
    if (rel !== vRel) { vRel = rel; E.rl.textContent = rel; }
    if (P.pack !== vPack) { vPack = P.pack; E.pk.textContent = 'SMOKES ' + P.pack; }
    if (P.lives !== vLives) { vLives = P.lives; E.lv.textContent = 'LIVES ' + '◆'.repeat(Math.max(0, P.lives)) + '◇'.repeat(Math.max(0, C.LIVES - P.lives)); }
    const a = P.armed && P.assistTarget(0.035); E.xh.classList.toggle('on', !!a); E.xh.style.display = P.armed ? 'block' : 'none';
    if (hitT > 0) { hitT -= dt; E.xh.classList.add('hit'); } else E.xh.classList.remove('hit');
    const sc = NR.game.scanProgress || 0; E.scanbar.style.display = sc > 0 ? 'block' : 'none';
    if (sc > 0) E.scanbar.style.background = 'conic-gradient(#e8b040 0 ' + (sc * 100).toFixed(0) + '%,rgba(232,176,64,.15) ' + (sc * 100).toFixed(0) + '% 100%)', E.scanbar.style.webkitMask = E.scanbar.style.mask = 'radial-gradient(circle,transparent 58%,#000 60%)';
  }

  // ---------------------------------------------------------------- case file
  function caseFile(on, data) {
    if (!on) { E.cf.classList.remove('on'); return; }
    const S = NR.story, pg = E.cf.querySelector('.page');
    let html = '<div class="stamp">OPEN</div><b>CASE 01: THE GLASS SAINT</b><br>Client: Vela Castellane. Says her sister Dolores is missing.<h4>CLUES</h4>';
    for (const id of Object.keys(S.clues)) { const c = S.clues[id], f = data.clues[id];
      html += f ? '<div class="it"><b>' + c.name.toUpperCase() + '</b>' + c.note + (f.think ? '<i>THINK: ' + c.think + '</i>' : '') + '</div>' : '<div class="it miss">[ not found ]</div>'; }
    html += '<h4>SUSPECTS</h4>';
    html += '<div class="it"><b>VELA CASTELLANE</b>The client. Blonde, red dress. Lied about a sister.</div>';
    const dv = data.verdicts.dolores;
    html += '<div class="it"><b>DOLORES DELACROIX</b>Singer at the Blue Orchid.' + (dv ? '<i>VERDICT: ' + dv + '</i>' : '<span class="miss"> Not questioned.</span>') + '</div>';
    html += '<div class="it"><b>KASTOR GALE</b>Owns the Blue Orchid. Sends men who do not knock.</div>';
    html += '<h4>NOTES</h4>' + (data.notes.length ? data.notes.map(n => '<div class="it">' + n + '</div>').join('') : '<div class="it miss">Nothing yet.</div>');
    pg.innerHTML = html; E.cf.classList.add('on'); E.cf.scrollTop = 0;
  }

  // ---------------------------------------------------------------- interrogation
  // B&W with red kept, for the painted close-ups (same rule as the in-game grade); cached per image
  const noirCache = {};
  function noirSrc(url) {
    if (noirCache[url]) return noirCache[url];
    return noirCache[url] = new Promise(res => { const im = new Image(); im.onload = () => { try {
      const c = document.createElement('canvas'); c.width = im.naturalWidth; c.height = im.naturalHeight; const g = c.getContext('2d'); g.drawImage(im, 0, 0);
      const d = g.getImageData(0, 0, c.width, c.height), a = d.data;
      for (let i = 0; i < a.length; i += 4) { const r = a[i], gg = a[i + 1], b = a[i + 2], l = 0.299 * r + 0.587 * gg + 0.114 * b;
        const q = r / Math.max(10, Math.max(gg, b)), k = Math.min(1, Math.max(0, (q - 2.0) / 0.8)) * Math.min(1, Math.max(0, (r - 46) / 40));
        a[i] = l + (Math.min(255, r * 1.08) - l) * k; a[i + 1] = l + (gg * 0.9 - l) * k; a[i + 2] = l + (b * 0.9 - l) * k; }
      g.putImageData(d, 0, 0); res(c.toDataURL('image/jpeg', 0.9)); } catch (e) { res(url); } }; im.onerror = () => res(url); im.src = url; });
  }
  function interrogate(who, data, found) {
    const S = NR.story; return new Promise(resolve => {
      const el = E.itg; el.innerHTML = '';
      const pic = h('div', 'pic', '', el); const imgs = {};
      for (const m of ['warm', 'guarded', 'cold']) { const im = h('img', '', null, pic); const u = NR.CLOSE(who, m); im.alt = data.name + ' ' + m; imgs[m] = im; if (core.settings.bw) noirSrc(u).then(s => { im.src = s; }); else im.src = u; }
      h('div', 'nm', data.name + '<small>' + data.role + '</small>', pic);
      const smk = h('div', 'smk', '', pic);
      const met = h('div', 'met', '<div>PULSE <span class="val pv">--</span><canvas width="240" height="52"></canvas></div><div>EYES <span class="val ev">--</span><div class="bar"><i class="eb"></i></div></div><div>HESITATION <span class="val hv">--</span><div class="bar"><i class="hb"></i></div></div>', el);
      const cv = met.querySelector('canvas'), g = cv.getContext('2d'), pv = met.querySelector('.pv'), ev = met.querySelector('.ev'), hv = met.querySelector('.hv'), eb = met.querySelector('.eb'), hb = met.querySelector('.hb');
      const ans = h('div', 'ans', '<div class="q">Detective, the floor is yours.</div><div class="a"></div>', el);
      const qs = h('div', 'qs', '', el);
      let mood = 'guarded', pulse = 62, eye = 0.15, asked = 0, offered = false, busy = false, live = true;
      const setMood = (m) => { mood = m; for (const k in imgs) imgs[k].classList.toggle('on', k === m); };
      setMood('guarded');
      // ECG trace
      let ph = 0, beatAcc = 0; const trace = new Array(120).fill(0);
      let lastT = performance.now();
      (function ecg(now) {
        if (!live) return; requestAnimationFrame(ecg); const dt = Math.min(0.05, (now - lastT) / 1000); lastT = now;
        const bpm = pulse + Math.sin(now / 900) * (data.artificial ? 0.3 : 2);
        ph += dt * bpm / 60; beatAcc += dt * bpm / 60; if (beatAcc >= 1) { beatAcc -= 1; if (!UI.fast) NR.audio.fx.heartbeat(bpm); }
        const f = ph % 1; const y = f < 0.05 ? -f * 6 : f < 0.1 ? (f - 0.05) * 30 - 0.3 : f < 0.15 ? 1.2 - (f - 0.1) * 30 : f < 0.3 ? Math.sin((f - 0.15) / 0.15 * Math.PI) * 0.2 : 0;
        trace.push(y); trace.shift();
        g.clearRect(0, 0, 240, 52); g.strokeStyle = '#e04a3a'; g.lineWidth = 2; g.beginPath(); trace.forEach((v, i) => { const x = i * 2, yy = 30 - v * 18; i ? g.lineTo(x, yy) : g.moveTo(x, yy); }); g.stroke();
        pv.textContent = Math.round(bpm); const ej = Math.max(0, Math.min(1, eye + (Math.random() - 0.5) * eye * 0.4)); eb.style.width = (ej * 100).toFixed(0) + '%'; ev.textContent = eye < 0.3 ? 'STEADY' : eye < 0.6 ? 'SHIFTY' : 'DARTING';
      })(lastT);
      const meterTo = (r) => { pulse = r.pulse; eye = r.eye; hv.textContent = r.hes.toFixed(1) + 's'; hb.style.width = Math.min(100, r.hes / 2.5 * 100) + '%'; };
      const smokeLabel = () => { smk.textContent = 'SMOKES ' + NR.player.pack; };
      smokeLabel();
      async function answer(qText, r, slip, note) {
        busy = true; render();
        ans.innerHTML = '<div class="q">' + qText + '</div><div class="a">&hellip;</div>';
        const a = ans.querySelector('.a');
        hv.textContent = '...'; await NR.core.wait(UI.fast ? 0.05 : Math.min(2.6, r.hes)); meterTo(r); setMood(r.mood);
        a.textContent = '"' + r.a + '"';
        if (slip) { const s = h('span', 'slip', '"' + slip + '"', a); void s; }
        if (note) { const n = h('span', 'slip', note, a); n.style.color = '#d8ceb8'; }
        busy = false; render();
      }
      function render() {
        qs.innerHTML = '';
        const head = h('div', 'hdr', '<span>QUESTIONS LEFT ' + (4 - asked) + '</span><span>' + (asked >= 4 ? 'DECIDE' : 'ASK 4 OF 8') + '</span>', qs); void head;
        if (asked < 4) {
          for (const q of data.questions) {
            const cq = q.clueQ && found[q.clueQ.clue] ? q.clueQ : null; const text = cq ? cq.q : q.q;
            const b = h('div', 'qb' + (q.used ? ' used' : '') + (cq || (q.slip && found[q.slip.clue]) ? ' clue' : '') + (busy ? ' off' : ''), text, qs); b.dataset.q = q.id;
            onTap(b, () => { if (busy || q.used || asked >= 4) return; q.used = true; asked++;
              const r = cq ? { a: cq.a, mood: cq.mood, pulse: cq.pulse, eye: cq.eye, hes: cq.hes } : q;
              const slip = cq ? cq.slip : (q.slip && found[q.slip.clue] ? q.slip.text : null);
              NR.bus.emit('asked', { id: q.id, slip: !!slip });
              answer(text, r, slip); });
          }
        }
        const row = h('div', 'row2', '', qs);
        const off = h('div', 'btn' + (offered || busy || NR.player.pack <= 0 ? ' off' : ''), 'OFFER A SMOKE', row); off.dataset.act = 'offer';
        onTap(off, () => { if (offered || busy || NR.player.pack <= 0) return; offered = true; NR.player.pack--; NR.player.smoked++; smokeLabel(); NR.audio.fx.lighter();
          NR.bus.emit('offer', { who }); answer('You offer her a cigarette and light it.', data.offer, null, data.offer.vo); });
        if (asked >= 4 && !busy) {
          const v = h('div', 'row2', '', qs);
          for (const verdict of ['HUMAN', 'ARTIFICIAL']) { const b = h('div', 'btn red', verdict, v); b.dataset.verdict = verdict; onTap(b, () => { live = false; el.classList.remove('on'); resolve({ verdict, offered }); }); }
        }
      }
      for (const q of data.questions) q.used = false;
      render(); el.classList.add('on'); void S;
    });
  }

  // ---------------------------------------------------------------- end card + game over
  function gameOver() { E.over.classList.add('on'); return new Promise(r => { const f = () => { E.over.classList.remove('on'); r(); }; E.retry.onpointerup = (e) => { e.preventDefault(); f(); }; E.retry.setAttribute('data-tap', '1'); E.retry.classList.add('tap'); }); }
  function endCard(st) {
    const S = NR.story.end;
    E.end.innerHTML = '<div class="card on vis" style="position:relative;background:none;display:block;opacity:1;width:100%"><div class="fr" style="margin:0 auto">' + S.title + '\n\n' + S.sub + '</div></div>' +
      '<div class="stats">CLUES FOUND <b>' + st.clues + '/3</b><br>THINK NOTES <b>' + st.thinks + '</b><br>DOLORES <b>' + (st.verdict || '-') + '</b><br>ACCURACY <b>' + st.acc + '%</b>  HEADS <b>' + st.heads + '</b><br>SMOKES LEFT <b>' + st.pack + '</b><br>TIME <b>' + st.time + '</b></div>';
    const b = h('div', 'btn red', 'PLAY AGAIN', E.end); onTap(b, () => location.reload());
    E.end.classList.add('on');
  }
  function show(name, on) { const m = { pause: E.pause, title: E.title }; if (m[name]) m[name].classList.toggle('on', on); }

  const UI = NR.ui = { init(c) { core = c; build(); }, gate, title, say, lines, card, tutorial, letterbox, toast, objective, prompt, update, caseFile, interrogate, gameOver, endCard, show, settingsOpen, fast: false, get el() { return E; } };
})();

// NEON RAIN jukebox (landing menu), in the menu's own style. Three switchable designs: ?jb=a (inline list),
// ?jb=b (liner notes), ?jb=c (radio dial, default per John 10/7/26). Play/pause, prev/next, scrub, shuffle, repeat; keeps playing after BACK;
// lock-screen controls through the Media Session set in audio.js. Tracks come from assets/music/tracks.json.
(function () {
  const A = () => NR.audio;
  const V = (new URLSearchParams(location.search).get('jb') || 'c').toLowerCase().replace(/[^abc]/g, '') || 'c';
  let el = null, list = [], idx = -1, shuffle = false, repeat = 'all', open = false, raf = 0, dialList = false;
  const fmt = s => isFinite(s) ? Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0') : '0:00';
  const up = s => s.toUpperCase();
  function visible() {
    const all = NR.core.settings.jbAll !== false; let heard = [];
    try { heard = JSON.parse(localStorage.getItem('neonRainFps.heard') || '[]'); } catch (e) {}
    return A().tracks.tracks.filter(t => all || heard.includes(t.id) || t.unlock === 'title');
  }
  const toggles = () => '<i class="br"></i><span data-act="shuf" class="tg">SHUFFLE</span><span data-act="rep" class="tg">REPEAT ALL</span>';
  const scrub = () => '<div class="sc"><span class="ta">0:00</span><input type="range" min="0" max="1000" value="0" data-tap="1"><span class="tb">0:00</span></div>';
  function html() {
    if (V === 'b') return '<div class="ln-h">ORIGINAL SCORE &middot; SIDE A</div>' +
      list.map((t, i) => '<div class="ln" data-i="' + i + '"><span class="n">' + t.id + '</span><span class="tt">' + up(t.title) + '</span><span class="dots"></span><span class="len">' + (t.len || '') + '</span></div>').join('') +
      '<div class="np"></div>' + scrub() + '<div class="ctl"><span data-act="prev">&#x25C2;&#x25C2;</span><span data-act="play" class="pp">&#x25B6;</span><span data-act="next">&#x25B8;&#x25B8;</span>' + toggles() + '</div><div class="row back" data-act="back">BACK</div>';
    if (V === 'c') return '<div class="dial"><span class="ar" data-act="prev">&#x25C2;</span><div class="dm"><small class="lab">NOW PLAYING</small><b class="dt"></b><div class="hl"><i></i></div></div><span class="ar" data-act="next">&#x25B8;</span></div>' +
      '<div class="ctl"><span data-act="play" class="pp">&#x25B6;</span>' + toggles() + '<span data-act="list" class="tg lt">TRACK LIST &#x25BE;</span></div>' +
      '<div class="dl">' + list.map((t, i) => '<div class="ln" data-i="' + i + '"><span class="n">' + t.id + '</span><span class="tt">' + up(t.title) + '</span><span class="dots"></span><span class="len">' + (t.len || '') + '</span></div>').join('') + '</div>' +
      scrub() + '<div class="row back" data-act="back">BACK</div>';
    return list.map((t, i) => '<div class="row tr" data-i="' + i + '"><span class="mk">&#x25B8;</span>' + up(t.title) + '<i class="pl"></i></div>').join('') +
      '<div class="ctl"><span data-act="prev">&#x25C2;&#x25C2;</span><span data-act="play" class="pp">&#x25B6;</span><span data-act="next">&#x25B8;&#x25B8;</span>' + toggles() + '</div>' + scrub() + '<div class="row back" data-act="back">BACK</div>';
  }
  function tap(e, fn) { e.classList.add('tap'); e.setAttribute('data-tap', '1'); e.addEventListener('pointerup', ev => { ev.preventDefault(); ev.stopPropagation(); fn(); }); }
  function render() {
    el = NR.ui.el.jb; list = visible(); el.className = 'jb on v' + V; el.innerHTML = html();
    el.querySelectorAll('[data-i]').forEach(r => tap(r, () => play(+r.dataset.i)));
    const acts = { play: toggle, prev, next, back: close, shuf: () => { shuffle = !shuffle; sync(); }, list: () => { dialList = !dialList; sync(); },
      rep: () => { repeat = repeat === 'all' ? 'one' : repeat === 'one' ? 'off' : 'all'; const c = A().current(); if (c) c.loop = repeat === 'one'; sync(); } };
    el.querySelectorAll('[data-act]').forEach(b => tap(b, acts[b.dataset.act]));
    const rg = el.querySelector('input'); rg.addEventListener('input', () => { const c = A().current(); if (c && isFinite(c.duration)) c.currentTime = rg.value / 1000 * c.duration; });
    if (V === 'c') { const box = el.querySelector('.dial'); let x0 = null; box.addEventListener('pointerdown', e => { x0 = e.clientX; }); box.addEventListener('pointerup', e => { if (x0 != null && Math.abs(e.clientX - x0) > 40) (e.clientX < x0 ? next : prev)(); x0 = null; }); }
    idx = list.findIndex(t => t.id === A().cueId); sync();
  }
  function sync() {
    if (!el) return; const c = A().current(), playing = !!(c && !c.paused), t = list[idx];
    el.querySelectorAll('.pp').forEach(p => { p.innerHTML = playing ? '&#x275A;&#x275A;' : '&#x25B6;'; });
    el.querySelectorAll('[data-i]').forEach(r => { r.classList.toggle('cur', +r.dataset.i === idx); r.classList.toggle('play', +r.dataset.i === idx && playing); });
    const sh = el.querySelector('[data-act="shuf"]'); sh.classList.toggle('on', shuffle);
    const rp = el.querySelector('[data-act="rep"]'); rp.textContent = 'REPEAT ' + up(repeat); rp.classList.toggle('on', repeat !== 'off');
    const np = el.querySelector('.np'); if (np) np.innerHTML = t ? '<b>' + (playing ? '&#x25B8;' : '&#x275A;&#x275A;') + '</b> ' + up(t.title) : 'TAP A TITLE TO PLAY';
    const dt = el.querySelector('.dt'); if (dt) { dt.textContent = t ? up(t.title) : 'THE BLUE ORCHID'; el.querySelector('.lab').textContent = playing ? 'NOW PLAYING' : 'PAUSED'; }
    const dl = el.querySelector('.dl'); if (dl) { dl.classList.toggle('on', dialList); el.querySelector('.lt').innerHTML = 'TRACK LIST ' + (dialList ? '&#x25B4;' : '&#x25BE;'); }
  }
  function tick() {
    raf = requestAnimationFrame(tick); if (!open || !el) return; const c = A().current(); if (!c) return; const f = isFinite(c.duration) && c.duration ? c.currentTime / c.duration : 0;
    const rg = el.querySelector('input'); if (rg && document.activeElement !== rg) rg.value = f * 1000;
    const ta = el.querySelector('.ta'), tb = el.querySelector('.tb'); if (ta) { ta.textContent = fmt(c.currentTime); tb.textContent = fmt(c.duration); }
    const pl = el.querySelector('.row.cur .pl'); if (pl) pl.style.width = (f * 100).toFixed(1) + '%';
    const hl = el.querySelector('.hl i'); if (hl) hl.style.width = (f * 100).toFixed(1) + '%';
  }
  function play(i) { if (!list[i]) return; idx = i; NR.audio.unlock(); A().cue(list[i].id, 1.5, { loop: repeat === 'one', restart: true }).then(sync); A().setOnEnded(onEnd); setTimeout(sync, 80); }
  function onEnd() { if (repeat === 'off' && !shuffle && idx >= list.length - 1) { sync(); return; } next(); }
  function next() { if (!list.length) return; play(shuffle ? pickRandom() : (idx + 1) % list.length); }
  function prev() { const c = A().current(); if (c && c.currentTime > 3) { c.currentTime = 0; return; } play((Math.max(0, idx) - 1 + list.length) % list.length); }
  function pickRandom() { if (list.length < 2) return 0; let j; do { j = Math.floor(Math.random() * list.length); } while (j === idx); return j; }
  function toggle() { const c = A().current(); if (!c || idx < 0) { play(Math.max(0, idx)); return; } if (c.paused) c.play().catch(() => {}); else c.pause(); setTimeout(sync, 40); }
  function close() { open = false; NR.ui.el.jb.classList.remove('on'); NR.ui.el.title.classList.remove('jbopen'); }
  async function openPanel() { await A().loadTracks(); open = true; NR.ui.el.title.classList.add('jbopen'); render(); if (!raf) tick(); A().setOnEnded(onEnd); }
  NR.jukebox = { open: openPanel, close, play, next, prev, toggle, render, variant: V, get isOpen() { return open; }, get index() { return idx; }, get list() { return list; }, get shuffle() { return shuffle; }, get repeat() { return repeat; } };
})();
