#!/usr/bin/env python3
"""把蒸馏笔记组装成单页学习站 dist/index.html(v2:专题图谱+SRE手册+记忆闪卡+学习路径)。"""
import json
import re
from pathlib import Path

BUILD = Path(__file__).resolve().parent
NOTES = BUILD / "notes"
SYNTH = BUILD / "synthesis"
SRE = BUILD / "sre"
DIST = BUILD / "dist"

MODULES = [
    {"no": 1, "name": "01-开篇词", "blurb": "课程全景:什么是金融级系统,如何成为金融级人才"},
    {"no": 2, "name": "02-金融业务与系统", "blurb": "从扫码支付到领域驱动设计:业务模式决定系统核心需求"},
    {"no": 3, "name": "03-系统正确性保障", "blurb": "单机视角:计算输入、过程、结果与数据传输、存储的正确性"},
    {"no": 4, "name": "04-分布式正确性及高可用", "blurb": "多机视角:一致性分级、共识算法、分布式数据方案与容灾"},
    {"no": 5, "name": "05-春节策划", "blurb": "综合实战:用架构视角解读春运买票与手游,附书单"},
]

SEC = {
    "一句话总结": "summary",
    "知识导图": "mindmap",
    "核心概念": "concepts",
    "核心要点": "points",
    "架构与流程": "arch",
    "关键对比": "compare",
    "易混与坑": "pitfalls",
    "自测问题": "quiz",
}


def parse_frontmatter_and_sections(text: str, sec_map=None):
    fm, body = {}, text
    if text.startswith("---"):
        end = text.index("---", 3)
        for ln in text[3:end].splitlines():
            if ":" in ln:
                k, v = ln.split(":", 1)
                fm[k.strip()] = v.strip()
        body = text[end + 3:]
    sec_map = sec_map or {}
    parts = re.split(r"^## (.+)$", body, flags=re.M)
    sections = {}
    if parts[0].strip():
        sections["_intro"] = parts[0].strip()
    for i in range(1, len(parts), 2):
        name, content = parts[i].strip(), parts[i + 1].strip()
        sections[sec_map.get(name, name)] = content
    return fm, sections


def parse_lecture(path: Path):
    fm, sec = parse_frontmatter_and_sections(path.read_text(encoding="utf-8"), SEC)
    return {
        "id": path.stem, "module": fm.get("module", ""), "moduleNo": int(fm.get("module_no", 0)),
        "order": int(fm.get("order", 0)), "title": fm.get("title", path.stem),
        "isQA": "答疑" in fm.get("title", ""),
        "summary": sec.get("summary", ""), "mindmap": sec.get("mindmap", ""),
        "concepts": sec.get("concepts", ""), "points": sec.get("points", ""),
        "arch": sec.get("arch", ""), "compare": sec.get("compare", ""),
        "pitfalls": sec.get("pitfalls", ""), "quiz": sec.get("quiz", ""),
    }


def parse_module_overview(paths):
    intros, map_children = [], []
    for p in paths:
        _, sec = parse_frontmatter_and_sections(p.read_text(encoding="utf-8"))
        if "模块导读" in sec:
            intros.append(re.sub(r"^###?\s*.*$", "", sec["模块导读"], flags=re.M).strip())
        mm = ""
        for key in ("模块导图", "模块导图(前半)", "模块导图(后半)"):
            if key in sec:
                mm = sec[key]
                break
        lines = [ln for ln in mm.splitlines() if ln.strip()]
        if lines:
            map_children.extend(lines[1:])
    return "\n\n".join(intros), map_children


def parse_synthesis():
    items = []
    if SYNTH.exists():
        for p in SYNTH.glob("*.md"):
            fm, sec = parse_frontmatter_and_sections(p.read_text(encoding="utf-8"))
            body = sec.get("_intro", "")
            items.append({"id": fm.get("id", p.stem), "title": fm.get("title", p.stem),
                          "blurb": fm.get("blurb", ""), "order": int(fm.get("order", 99)),
                          "body": body})
    items.sort(key=lambda x: x["order"])
    return items


SRE_SEC = {"一句话定位": "定位", "典型故障模式": "故障", "观测信号": "观测",
           "应急动作": "应急", "常见误区": "误区"}


def parse_sre_cards():
    cards = []
    d = SRE / "cards"
    if d.exists():
        for p in sorted(d.glob("*.md")):
            fm, sec = parse_frontmatter_and_sections(p.read_text(encoding="utf-8"), SRE_SEC)
            cards.append({"title": fm.get("title", p.stem), "lectures": fm.get("lectures", ""),
                          "定位": sec.get("定位", ""), "故障": sec.get("故障", ""),
                          "观测": sec.get("观测", ""), "应急": sec.get("应急", ""),
                          "误区": sec.get("误区", "")})
    return cards


def build_flashcards(lectures):
    cards = []
    for l in lectures:
        short = l["title"].split("丨")[-1][:22]
        for m in re.finditer(r"^-\s+(.+)$", l["quiz"], flags=re.M):
            q = m.group(1).strip()
            mm = re.match(r"^(.*)（(.*)）\s*$", q, flags=re.S)
            if mm and mm.group(2).strip():
                cards.append({"id": f"{l.id_placeholder}q{len(cards)}", "modNo": l["moduleNo"],
                              "lect": short, "q": mm.group(1).strip(), "a": mm.group(2).strip()})
        for m in re.finditer(r"^-\s*\*\*(.+?)\*\*\s*[:：]\s*(.+)$", l["concepts"], flags=re.M):
            cards.append({"id": f"{l.id_placeholder}c{len(cards)}", "modNo": l["moduleNo"],
                          "lect": short, "q": m.group(1).strip() + " 是什么?",
                          "a": m.group(2).strip()})
    return cards


def main():
    lectures = [parse_lecture(p) for p in NOTES.glob("*.md") if not re.match(r"^M\d", p.name)]
    lectures.sort(key=lambda l: (l["moduleNo"], l["order"], 1 if l["isQA"] else 0, l["title"]))

    mod_map = {int(re.match(r"M(\d+)", p.stem).group(1)): p for p in NOTES.glob("M*.md")}
    overview_data = {}
    for m in MODULES:
        no = m["no"]
        paths = [mod_map[4].with_name("M04a.md"), mod_map[4].with_name("M04b.md")] if no == 4 else [mod_map[no]]
        intro, children = parse_module_overview(paths)
        overview_data[no] = {"intro": intro, "map": children}

    gmap = ["- 分布式金融架构"]
    for m in MODULES:
        gmap.append("  " + f"- {m['name'].split('-', 1)[1]}")
        for ln in overview_data[m["no"]]["map"]:
            gmap.append("  " + ln)
    global_map = "\n".join(gmap)

    # 闪卡(id 需要稳定,用讲次 id 前缀)
    cards = []
    for l in lectures:
        short = l["title"].split("丨")[-1][:22]
        for m in re.finditer(r"^-\s+(.+)$", l["quiz"], flags=re.M):
            q = m.group(1).strip()
            mm = re.match(r"^(.*)（(.*)）\s*$", q, flags=re.S)
            if mm and mm.group(2).strip():
                cards.append({"id": f"{l['id']}#q{len([c for c in cards if c['id'].startswith(l['id'])])}",
                              "modNo": l["moduleNo"], "lect": short,
                              "q": mm.group(1).strip(), "a": mm.group(2).strip()})
        for m in re.finditer(r"^-\s*\*\*(.+?)\*\*\s*[:：]\s*(.+)$", l["concepts"], flags=re.M):
            cards.append({"id": f"{l['id']}#c{len([c for c in cards if c['id'].startswith(l['id'])])}",
                          "modNo": l["moduleNo"], "lect": short,
                          "q": m.group(1).strip() + " 是什么?", "a": m.group(2).strip()})

    sre_metrics = ""
    mp = SRE / "metrics.md"
    if mp.exists():
        sre_metrics = mp.read_text(encoding="utf-8")

    data = {
        "modules": MODULES,
        "overviews": overview_data,
        "lectures": lectures,
        "globalMap": global_map,
        "atlas": parse_synthesis(),
        "sreCards": parse_sre_cards(),
        "sreMetrics": sre_metrics,
        "cards": cards,
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

    html = TEMPLATE.replace("__PAYLOAD__", payload).replace("__COUNT__", str(len(lectures))) \
        .replace("__CARDS__", str(len(cards)))
    DIST.mkdir(exist_ok=True)
    out = DIST / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"构建完成:{out} ({out.stat().st_size / 1024:.0f} KB, {len(lectures)} 讲, "
          f"{len(cards)} 闪卡, {len(data['atlas'])} 张专题图, {len(data['sreCards'])} 张故障卡)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex,nofollow">
<title>分布式金融架构 · 知识地图</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-view@0.18"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.18"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked@12/marked.min.js"></script>
<style>
:root{--bg:#f4f6fb;--card:#fff;--ink:#1f2937;--muted:#6b7280;--accent:#4f46e5;--accent2:#7c3aed;--line:#e5e7eb;--sidebar:#111827;--sidebar-ink:#d1d5db}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--ink);font-size:15px;line-height:1.75}
#app{display:flex;min-height:100vh}
#sidebar{width:288px;flex-shrink:0;background:var(--sidebar);color:var(--sidebar-ink);position:sticky;top:0;height:100vh;overflow-y:auto;padding:18px 0 40px}
.brand{padding:6px 20px 14px;border-bottom:1px solid #1f2937}
.brand h1{font-size:17px;color:#fff;font-weight:700;letter-spacing:.5px}
.brand p{font-size:12px;color:#9ca3af;margin-top:2px}
#search{margin:14px 16px 6px}
#search input{width:100%;background:#1f2937;border:1px solid #374151;color:#e5e7eb;border-radius:8px;padding:8px 12px;font-size:13px;outline:none}
#search input:focus{border-color:var(--accent)}
#nav{padding:8px 10px}
.nav-home,.nav-tool{display:block;padding:8px 12px;border-radius:8px;color:#e5e7eb;text-decoration:none;font-size:14px;margin:2px 0}
.nav-home:hover,.nav-tool:hover,.nav-home.active,.nav-tool.active{background:#1f2937;color:#fff}
.nav-home.active,.nav-tool.active{background:var(--accent)}
.nav-group{margin-top:10px}
.nav-mod{display:flex;align-items:center;justify-content:space-between;padding:8px 12px;color:#9ca3af;font-size:12px;font-weight:700;letter-spacing:.5px;cursor:pointer;border-radius:8px;user-select:none}
.nav-mod:hover{background:#1f2937}
.nav-mod .arrow{transition:transform .2s}
.nav-group.collapsed .arrow{transform:rotate(-90deg)}
.nav-group.collapsed .nav-items{display:none}
.nav-items{list-style:none}
.nav-items a{display:block;padding:6px 12px 6px 18px;color:var(--sidebar-ink);text-decoration:none;font-size:13px;border-radius:8px;line-height:1.5}
.nav-items a:hover{background:#1f2937;color:#fff}
.nav-items a.active{background:var(--accent);color:#fff}
.nav-items a .no{color:#6b7280;font-size:11px;margin-right:6px}
.nav-items a.active .no{color:#c7d2fe}
#main{flex:1;min-width:0}
#topbar{position:sticky;top:0;z-index:30;background:rgba(244,246,251,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:12px 32px;display:flex;align-items:center;gap:14px}
#burger{display:none;background:none;border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-size:16px;cursor:pointer}
#crumb{font-size:13px;color:var(--muted);flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#content{max-width:1020px;margin:0 auto;padding:28px 32px 90px}
.hero{background:linear-gradient(135deg,#4f46e5,#7c3aed 60%,#a855f7);color:#fff;border-radius:18px;padding:34px 36px;margin-bottom:22px}
.hero h2{font-size:26px;font-weight:800;letter-spacing:1px}
.hero p{margin-top:8px;color:#e0e7ff;font-size:14px;max-width:720px}
.stats{display:flex;gap:26px;margin-top:16px;flex-wrap:wrap}
.stats b{font-size:20px}
.stats span{font-size:12px;color:#c7d2fe;display:block}
.panel{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:24px 26px;margin-bottom:22px;box-shadow:0 1px 2px rgba(16,24,40,.04)}
.panel h3{font-size:17px;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.panel h3::before{content:"";width:4px;height:18px;background:linear-gradient(180deg,var(--accent),var(--accent2));border-radius:2px}
.tools{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-top:6px}
.tool-card{display:flex;flex-direction:column;gap:4px;padding:14px 18px;border:1px solid var(--line);border-radius:12px;text-decoration:none;color:var(--ink);font-size:14px;font-weight:600}
.tool-card small{color:var(--muted);font-weight:400;font-size:12px}
.tool-card:hover{border-color:var(--accent)}
.mod-card{border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin-bottom:14px;background:#fafbff}
.mod-card h4{font-size:15px;color:var(--accent)}
.mod-card p{font-size:13px;color:var(--muted);margin:4px 0 10px}
.mod-card .links{display:flex;flex-wrap:wrap;gap:8px}
.mod-card .links a{font-size:12px;color:var(--accent);text-decoration:none;background:#eef2ff;border-radius:999px;padding:3px 12px}
.mod-card .links a:hover{background:var(--accent);color:#fff}
.lecture-head{margin-bottom:18px}
.lecture-head .modtag{display:inline-block;font-size:12px;color:var(--accent);background:#eef2ff;border-radius:999px;padding:2px 12px;margin-bottom:8px}
.lecture-head h2{font-size:23px;font-weight:800;line-height:1.4}
.pageintro{color:var(--muted);font-size:14px;margin:-6px 0 18px;max-width:820px}
.callout{background:linear-gradient(135deg,#eef2ff,#f5f3ff);border:1px solid #e0e7ff;border-radius:14px;padding:16px 20px;margin:14px 0 22px;font-size:15px}
.sec{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px 26px;margin-bottom:18px}
.sec h3{font-size:16px;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.sec h3::before{content:"";width:4px;height:17px;background:linear-gradient(180deg,var(--accent),var(--accent2));border-radius:2px}
.sec h4{margin:16px 0 6px;font-size:14px;color:var(--accent)}
.sec .blurb{color:var(--muted);font-size:13px;margin-bottom:10px}
.sec .md ul,.sec .md ol{padding-left:22px}
.sec .md li{margin:5px 0}
.sec .md strong{color:#111827}
.sec table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13.5px}
.sec th,.sec td{border:1px solid var(--line);padding:7px 11px;text-align:left;vertical-align:top}
.sec th{background:#f3f4f6;font-weight:700;white-space:nowrap}
.sec tr:nth-child(even) td{background:#fafafa}
.lect-tag{font-size:11px;font-weight:400;background:#eef2ff;color:var(--accent);padding:2px 10px;border-radius:999px;margin-left:8px;vertical-align:2px}
.map-box{position:relative}
.map-box .mapctl{position:absolute;top:8px;right:8px;z-index:5;display:flex;gap:6px}
.map-box .mapctl button{font-size:12px;background:#fff;border:1px solid var(--line);border-radius:8px;padding:4px 10px;cursor:pointer;color:var(--muted)}
.map-box .mapctl button:hover{color:var(--accent);border-color:var(--accent)}
.markmap-container{height:480px;border:1px solid var(--line);border-radius:12px;background:#fdfdff;overflow:hidden}
.markmap-container svg{width:100%;height:100%}
.map-wide .markmap-container{height:600px}
pre.mermaid{background:#fdfdff;border:1px solid var(--line);border-radius:12px;padding:18px;display:flex;justify-content:center;overflow-x:auto}
pre.mermaid svg{max-width:100%;height:auto}
.pager{display:flex;justify-content:space-between;gap:12px;margin-top:26px}
.pager a{flex:1;text-decoration:none;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px;font-size:13px}
.pager a:hover{border-color:var(--accent);color:var(--accent)}
.pager .next{text-align:right}
.pager small{display:block;color:var(--muted);font-size:11px}
/* 记忆闪卡 */
.mem-top{display:flex;align-items:center;gap:12px;margin-bottom:14px;font-size:13px;color:var(--muted);flex-wrap:wrap}
.mem-top select{padding:6px 10px;border:1px solid var(--line);border-radius:8px;font-size:13px;background:#fff}
.fc-meta{color:var(--muted);font-size:12px}
.fc-q{font-size:17px;font-weight:600;margin:12px 0}
.fc-a{background:#f8fafc;border:1px dashed var(--line);border-radius:10px;padding:12px 16px;margin:12px 0;font-size:15px}
.hidden{display:none}
.fc-btns{display:flex;gap:10px;margin-top:14px}
.btn{padding:8px 20px;border-radius:10px;border:none;cursor:pointer;font-size:14px;background:var(--accent);color:#fff}
.btn:hover{opacity:.9}
.btn.good{background:#059669}.btn.mid{background:#d97706}.btn.bad{background:#dc2626}
.btn.ghost{background:#e5e7eb;color:var(--ink)}
footer{padding:26px 32px;color:#9ca3af;font-size:12px;text-align:center}
@media (max-width:900px){
#burger{display:block}
#sidebar{position:fixed;left:0;top:0;z-index:50;transform:translateX(-100%);transition:transform .25s}
#sidebar.open{transform:translateX(0)}
#content{padding:20px 16px 70px}
#topbar{padding:10px 14px}
}
</style>
</head>
<body>
<div id="app">
  <nav id="sidebar">
    <div class="brand"><h1>分布式金融架构</h1><p>知识地图 · 学习笔记 · __COUNT__ 讲</p></div>
    <div id="search"><input id="q" type="search" placeholder="搜索讲次 / 关键词…"></div>
    <div id="nav"></div>
  </nav>
  <div id="main">
    <div id="topbar">
      <button id="burger">☰</button>
      <div id="crumb">首页</div>
    </div>
    <div id="content"></div>
    <footer>个人学习笔记 · 内容为对课程的提炼转述与可视化重制</footer>
  </div>
</div>
<script>const COURSE = __PAYLOAD__;</script>
<script>
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const md=s=>marked.parse(s||"");
const byId=id=>COURSE.lectures.find(l=>l.id===id);
const modName=no=>(COURSE.modules.find(m=>m.no===no)||{}).name||"";
function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a}

/* ---------- markmap ---------- */
let transformer=null;
function ensureTransformer(){ if(!transformer){ transformer=new window.markmap.Transformer(); } return transformer; }
function renderMarkmap(container, mdText, opts){
  try{
    const t=ensureTransformer();
    const {root}=t.transform(mdText);
    const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");
    container.innerHTML=""; container.appendChild(svg);
    const mm=window.markmap.Markmap.create(svg, Object.assign({duration:250,initialExpandLevel:2,spacingVertical:6,paddingX:14,maxWidth:260},opts||{}), root);
    setTimeout(()=>{try{mm.fit()}catch(e){}},400);
    return mm;
  }catch(e){ container.innerHTML='<div style="padding:20px;color:#999">导图库加载失败,请检查网络后刷新</div>'; return null; }
}
function lazyMap(box){
  const tpl=box.querySelector('script[type="text/template"]');
  if(!tpl) return;
  const mdText=tpl.textContent, wide=box.classList.contains("map-wide");
  const io=new IntersectionObserver(es=>{
    es.forEach(e=>{
      if(!e.isIntersecting) return;
      io.disconnect();
      const mm=renderMarkmap(box.querySelector('.markmap-container'), mdText, wide?{initialExpandLevel:1}:null);
      const ctl=box.querySelector('.mapctl');
      if(ctl&&mm){
        ctl.innerHTML="";
        const fit=document.createElement("button"); fit.textContent="重置视图"; fit.onclick=()=>mm.fit(); ctl.appendChild(fit);
        let all=false;
        const tog=document.createElement("button"); tog.textContent="展开全部";
        tog.onclick=()=>{ all=!all; tog.textContent=all?"收起":"展开全部";
          const t=ensureTransformer(); const {root}=t.transform(mdText);
          mm.setData(root,{initialExpandLevel:all?-1:2}); mm.fit(); };
        ctl.appendChild(tog);
      }
    });
  },{rootMargin:"200px"});
  io.observe(box);
}

/* ---------- mermaid ---------- */
function runMermaid(scope){
  const blocks=scope.querySelectorAll("pre > code.language-mermaid");
  blocks.forEach(c=>{
    const pre=document.createElement("pre"); pre.className="mermaid"; pre.textContent=c.textContent;
    c.parentElement.replaceWith(pre);
  });
  if(window.mermaid&&scope.querySelector("pre.mermaid")){
    try{ window.mermaid.initialize({startOnLoad:false,theme:"neutral",securityLevel:"loose",flowchart:{useMaxWidth:true},sequence:{useMaxWidth:true}});
      window.mermaid.run({querySelector:"#content pre.mermaid"}); }catch(e){}
  }
}

/* ---------- 闪卡状态(SM-2 lite) ---------- */
const FC={key:"farch_fc_v2",int:[1,3,7,16,35]};
FC.state=(()=>{try{return JSON.parse(localStorage.getItem(FC.key))||{}}catch(e){return{}}})();
FC.save=()=>localStorage.setItem(FC.key,JSON.stringify(FC.state));
const dueCards=(sel)=>{const n=Date.now();return COURSE.cards.filter(c=>(sel===0||c.modNo===sel)&&FC.state[c.id]&&FC.state[c.id].d<=n)};
const newCards=(sel)=>COURSE.cards.filter(c=>(sel===0||c.modNo===sel)&&!FC.state[c.id]);

/* ---------- 侧边栏 ---------- */
function buildNav(){
  const nav=$("#nav"); nav.innerHTML="";
  const due=dueCards(0).length;
  const tools=[["#/home","🏠 课程总览"],["#/atlas","🗺 专题图谱"],["#/sre","🛠 SRE 手册"],["#/mem","🧠 记忆模式"+(due?` (${due})`:"")],["#/path","🧭 学习路径"]];
  tools.forEach(([href,label])=>{
    const a=document.createElement("a"); a.className="nav-tool"; a.href=href; a.textContent=label; nav.appendChild(a);
  });
  COURSE.modules.forEach(m=>{
    const g=document.createElement("div"); g.className="nav-group";
    const head=document.createElement("div"); head.className="nav-mod";
    head.innerHTML=`<span>${m.name}</span><span class="arrow">▾</span>`;
    const ul=document.createElement("ul"); ul.className="nav-items";
    COURSE.lectures.filter(l=>l.moduleNo===m.no).forEach(l=>{
      const li=document.createElement("li");
      const a=document.createElement("a"); a.href="#/"+l.id;
      const no=l.isQA?"答":String(l.order).padStart(2,"0");
      a.innerHTML=`<span class="no">${no}</span>${l.title.split("丨").slice(1).join("丨")||l.title}`;
      li.appendChild(a); ul.appendChild(li);
    });
    head.onclick=()=>g.classList.toggle("collapsed");
    g.appendChild(head); g.appendChild(ul); nav.appendChild(g);
  });
}
$("#q").addEventListener("input",e=>{
  const q=e.target.value.trim().toLowerCase();
  $$("#nav .nav-items a").forEach(a=>{
    const l=byId(a.getAttribute("href").slice(2)); if(!l)return;
    const hay=(l.title+" "+(l.summary||"")).toLowerCase();
    a.parentElement.style.display=(!q||hay.includes(q))?"":"none";
  });
});
$("#burger").onclick=()=>$("#sidebar").classList.toggle("open");

/* ---------- 视图:首页 ---------- */
function secCard(title,bodyMd){ if(!bodyMd||!bodyMd.trim())return ""; return `<div class="sec"><h3>${title}</h3><div class="md">${md(bodyMd)}</div></div>`; }

function viewHome(){
  $("#crumb").textContent="课程总览";
  const st=memStats();
  let h=`<div class="hero"><h2>分布式金融架构 · 知识地图</h2>
  <p>对《分布式金融架构》课程全部 ${COURSE.lectures.length} 讲的蒸馏笔记与可视化导图。建议按模块顺序学习:先业务后技术、先单机正确性再分布式正确性,最后用春节案例综合检验。</p>
  <div class="stats"><div><b>${COURSE.lectures.length}</b><span>讲次笔记</span></div><div><b>${COURSE.atlas.length}</b><span>专题大图</span></div><div><b>${COURSE.sreCards.length}</b><span>SRE 故障卡</span></div><div><b>${COURSE.cards.length}</b><span>记忆闪卡</span></div></div></div>`;
  h+=`<div class="panel"><h3>学习工具</h3><div class="tools">
    <a class="tool-card" href="#/atlas">🗺 专题图谱<small>一致性阶梯 · 知识关联 · 全链路 · 选型决策树</small></a>
    <a class="tool-card" href="#/sre">🛠 SRE 手册<small>故障模式 · 观测信号 · 应急动作</small></a>
    <a class="tool-card" href="#/mem">🧠 记忆模式<small>间隔复习 · 到期 ${st.due} 张</small></a>
    <a class="tool-card" href="#/path">🧭 学习路径<small>SRE 视角的 4 周掌握计划</small></a>
  </div></div>`;
  h+=`<div class="panel map-wide"><h3>全景知识地图(点击节点展开,滚轮缩放,拖拽平移)</h3>
    <div class="map-box"><div class="mapctl"></div><div class="markmap-container"><script type="text/template">${COURSE.globalMap}<\/script></div></div></div>`;
  h+=`<div class="panel"><h3>模块导览</h3>`;
  COURSE.modules.forEach(m=>{
    const ov=COURSE.overviews[m.no]; const ls=COURSE.lectures.filter(l=>l.moduleNo===m.no);
    h+=`<div class="mod-card"><h4>${m.name}</h4><p>${ov.intro.replace(/\n+/g," ").slice(0,180)}…</p><div class="links">`+
      ls.map(l=>`<a href="#/${l.id}">${(l.title.split("丨")[0]||"").replace(/^第?(\d+丨)?/,"")}</a>`).join("")+`</div></div>`;
  });
  h+=`</div>`;
  $("#content").innerHTML=h;
  $("#content").querySelectorAll(".map-box").forEach(lazyMap);
}

/* ---------- 视图:讲次 ---------- */
function viewLecture(l){
  $("#crumb").textContent=modName(l.moduleNo)+" / "+l.title;
  const idx=COURSE.lectures.indexOf(l);
  const prev=COURSE.lectures[idx-1], next=COURSE.lectures[idx+1];
  let h=`<div class="lecture-head"><span class="modtag">${modName(l.moduleNo)}</span><h2>${l.title}</h2></div>`;
  h+=`<div class="callout"><b>💡 一句话总结</b><br>${l.summary}</div>`;
  h+=`<div class="sec map-box"><h3>知识导图</h3><div class="mapctl"></div>
      <div class="markmap-container"><script type="text/template">${l.mindmap}<\/script></div></div>`;
  h+=secCard("核心概念",l.concepts)+secCard("核心要点",l.points)+secCard("架构与流程",l.arch)
    +secCard("关键对比",l.compare)+secCard("易混与坑",l.pitfalls)+secCard("自测问题",l.quiz);
  h+=`<div class="pager">`+
    (prev?`<a href="#/${prev.id}"><small>← 上一篇</small>${prev.title}</a>`:`<a style="visibility:hidden">·</a>`)+
    (next?`<a class="next" href="#/${next.id}"><small>下一篇 →</small>${next.title}</a>`:`<a style="visibility:hidden">·</a>`)+`</div>`;
  $("#content").innerHTML=h;
  lazyMap($("#content .map-box"));
  runMermaid($("#content"));
}

/* ---------- 视图:专题图谱 ---------- */
function viewAtlas(){
  $("#crumb").textContent="专题图谱";
  let h=`<div class="lecture-head"><span class="modtag">专题图谱</span><h2>跨讲次的框架级大图</h2></div>`;
  h+=`<p class="pageintro">把散在 27 讲里的知识重新组织:阶梯图是全课主线,关联图给出复习路径,综合图把全课串成一张生产拓扑,决策树把知识变成选型能力。逐张看,每张图都值得反复对照。</p>`;
  COURSE.atlas.forEach(a=>{
    h+=`<div class="sec"><h3>${a.title}</h3>${a.blurb?`<p class="blurb">${a.blurb}</p>`:""}<div class="md">${md(a.body)}</div></div>`;
  });
  $("#content").innerHTML=h;
  runMermaid($("#content"));
}

/* ---------- 视图:SRE 手册 ---------- */
function viewSRE(){
  $("#crumb").textContent="SRE 手册";
  let h=`<div class="lecture-head"><span class="modtag">SRE 视角</span><h2>故障模式与观测手册</h2></div>`;
  h+=`<p class="pageintro">把课程机制翻译成 SRE 的语言:每个核心机制配典型故障、监控里会看到的信号、第一响应动作。值班时异常来了,从这里反查它背后的一致性机制,再跳去对应讲次深读。</p>`;
  if(COURSE.sreMetrics){ h+=`<div class="sec"><h3>监控指标速查表</h3><div class="md">${md(COURSE.sreMetrics)}</div></div>`; }
  COURSE.sreCards.forEach(c=>{
    h+=`<div class="sec"><h3>${c.title}<span class="lect-tag">详见 L${c.lectures}</span></h3>`;
    if(c["定位"]) h+=`<p style="margin-bottom:4px"><b>${md(c["定位"]).replace(/<[^>]+>/g,"")}</b></p>`;
    h+=secCard("典型故障模式",c["故障"])+secCard("观测信号",c["观测"])+secCard("应急动作",c["应急"])+secCard("常见误区",c["误区"]);
    h+=`</div>`;
  });
  $("#content").innerHTML=h;
}

/* ---------- 视图:记忆模式 ---------- */
function memStats(){
  const s=Object.values(FC.state), n=Date.now();
  return {due:s.filter(x=>x.d<=n).length, seen:s.length, total:COURSE.cards.length};
}
let mq=[],mi=0,mFree=false,mSel=0,mReveal=false;
function memPick(free){
  const inSel=c=>(mSel===0||c.modNo===mSel);
  mq = free ? shuffle(COURSE.cards.filter(inSel)).slice(0,15)
            : [...dueCards(mSel), ...newCards(mSel).slice(0,Math.max(0,15-dueCards(mSel).length))];
  if(mq.length===0){ mq=shuffle(COURSE.cards.filter(inSel)).slice(0,15); mFree=true; }
  mi=0; mFree=free; mReveal=false; renderMemCard();
}
function renderMemCard(){
  const st=memStats();
  const opts=`<select id="msel">${[0,...COURSE.modules.map(m=>m.no)].map(no=>`<option value="${no}" ${no===mSel?"selected":""}>${no===0?"全部模块":modName(no)}</option>`).join("")}</select>`;
  if(mi>=mq.length){
    $("#content").innerHTML=`<div class="lecture-head"><span class="modtag">记忆模式</span><h2>间隔复习</h2></div>
    <div class="sec"><h3>本轮完成 🎉</h3><p>到期 <b>${st.due}</b> · 已学 <b>${st.seen}</b> / 总 <b>${st.total}</b> 张。明天再来,间隔会自动拉长。</p>
    <p style="margin-top:14px"><button class="btn" onclick="memPick(true)">自由复习 15 张</button>
    <button class="btn ghost" style="margin-left:8px" onclick="memPick(false)">再来一轮</button></p></div>`;
    return;
  }
  const c=mq[mi];
  $("#content").innerHTML=`<div class="lecture-head"><span class="modtag">记忆模式</span><h2>间隔复习</h2></div>
  <div class="mem-top"><span>进度 ${mi+1}/${mq.length}</span><span>到期 ${st.due}</span><span>已学 ${st.seen}/${st.total}</span>${opts}</div>
  <div class="sec">
    <div class="fc-meta">${modName(c.modNo)} · ${c.lect}</div>
    <div class="fc-q">${c.q}</div>
    <div class="fc-a ${mReveal?"":"hidden"}" id="fcA">${c.a}</div>
    <div class="fc-btns">${mReveal?`
      <button class="btn bad" onclick="memGrade(0)">忘了</button>
      <button class="btn mid" onclick="memGrade(1)">模糊</button>
      <button class="btn good" onclick="memGrade(2)">会了</button>`
      :`<button class="btn" onclick="memReveal()">翻面</button>`}</div>
  </div>`;
  $("#msel").onchange=e=>{mSel=+e.target.value;memPick(mFree)};
}
function memReveal(){ mReveal=true; renderMemCard(); }
function memGrade(g){
  const c=mq[mi], s=FC.state[c.id]||{b:0,d:0}, day=86400e3;
  if(g===0){ s.b=0; s.d=Date.now()+600e3; }
  else if(g===1){ s.b=Math.max(1,s.b); s.d=Date.now()+day; }
  else { s.b=Math.min(5,s.b+1); s.d=Date.now()+FC.int[s.b-1]*day; }
  FC.state[c.id]=s; FC.save(); mi++; renderMemCard();
}

/* ---------- 视图:学习路径 ---------- */
const WEEKS=[
 {t:"第 1 周 · 业务与资金流",l:"L01-L03,L06",goal:"建立资金视角:钱怎么流、账记在哪、业务分类决定什么系统需求。",
  doing:"通读 L01-L03、L06(答疑一含外汇拓展)。给自己公司的交易链路画一张资金流图,标出每个环节的账记在哪里、由谁清算;列出你负责的系统里所有涉及资金的写路径。",
  check:"能向同事讲清一笔支付从扫码到清结算经过哪些系统、哪个环节最可能丢钱、为什么。"},
 {t:"第 2 周 · 单机正确性",l:"L06-L11",goal:"掌握金融系统'算得对'的五道关:输入时间、处理架构、结果验证、传输质量、存储选型。",
  doing:"通读 L06-L11。审查你负责的一个核心写路径:时间取自哪里(决策时间 vs 交易时间)?失败重试是否幂等?计算结果有没有独立验证?用 SRE 手册的观测信号给它们配监控。",
  check:"能指出本系统 3 个正确性风险点,并给出对应的观测指标与告警阈值建议。"},
 {t:"第 3 周 · 分布式正确性",l:"L12-L16",goal:"建立一致性阶梯心智模型:从单机隔离级别到多机共识,知道每级的保证与代价。",
  doing:"通读 L12-L16(配专题图谱的一致性阶梯图与知识关联图)。给自己系统的每个存储标注当前一致性等级;找出所有跨服务写,判断该用 2PC 还是 TCC 补偿;确认消息重试+服务端去重的闭环。",
  check:"能对着一致性选型决策树说出:为什么这里是这个等级、升一级要付出什么代价。"},
 {t:"第 4 周 · 高可用与容灾",l:"L17-L21 + 春节策划",goal:"从正确性走向可用性:分布式事件溯源、数据方案、动态分库、两地三中心与混沌工程。",
  doing:"通读 L17-L21 与春节策划第 1、3 期(配全链路综合图)。写一份本系统容灾预案(明确 RPO/RTO 目标);设计 3 个混沌实验(杀主、网络分区、分库迁移中杀进程),列出每个实验的观测指标与中止条件。",
  check:"混沌演练清单可以直接提交团队评审执行;容灾预案能回答'机房挂了 RTO 多少、数据丢多少'。"}
];
function viewPath(){
  $("#crumb").textContent="学习路径";
  let h=`<div class="lecture-head"><span class="modtag">SRE 视角</span><h2>4 周掌握计划</h2></div>`;
  h+=`<p class="pageintro">为要深耕金融领域的 SRE 设计:每周"学什么、做什么、怎么算掌握"。任务都绑定你自己的系统,用工作里的真实对象来消化课程概念。配合记忆模式每天 5-10 张闪卡。</p>`;
  WEEKS.forEach((w,i)=>{
    h+=`<div class="sec"><h3>${w.t}<span class="lect-tag">${w.l}</span></h3>
    <h4>目标</h4><p>${w.goal}</p><h4>实践任务</h4><p>${w.doing}</p><h4>检验标准</h4><p>${w.check}</p></div>`;
  });
  h+=`<div class="sec"><h3>总原则</h3><div class="md"><ul>
  <li><b>以自己的系统为实验对象</b>:每学一个机制,先问"我这个系统里对应的是什么",概念才留得住。</li>
  <li><b>先框架后细节</b>:每次复习先过专题图谱(阶梯图/关联图),再下钻单讲导图。</li>
  <li><b>值班反哺学习</b>:每次告警/故障,来 SRE 手册对照故障模式与观测信号,把实战经验挂回课程框架。</li>
  </ul></div></div>`;
  $("#content").innerHTML=h;
}

/* ---------- 路由 ---------- */
function route(){
  const id=decodeURIComponent(location.hash.replace(/^#\//,""));
  $$("#nav a").forEach(a=>a.classList.toggle("active",a.getAttribute("href")==="#/"+id));
  $("#sidebar").classList.remove("open");
  window.scrollTo(0,0);
  if(id==="atlas") return viewAtlas();
  if(id==="sre") return viewSRE();
  if(id==="path") return viewPath();
  if(id==="mem"){ mSel=0; memPick(false); return; }
  if(!id||id==="home") return viewHome();
  const l=byId(id);
  if(l) viewLecture(l); else viewHome();
}
window.addEventListener("hashchange",route);
buildNav(); route();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
