"""Build the self-contained HTML viewer and viewing instructions."""
from __future__ import annotations

import json
import os

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
OUT = os.path.join(WS, "可视化")

HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>局部亮度校正 · 可视化查看器</title>
<style>
  :root { --bg:#101418; --panel:#1b2229; --fg:#e8eef4; --muted:#9fb0bf; --red:#c0392b; --green:#27ae60; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 "Microsoft YaHei", "Segoe UI", sans-serif; }
  header { padding:16px 20px 10px; border-bottom:1px solid #2a3440; }
  h1 { margin:0 0 4px; font-size:20px; }
  .muted { color:var(--muted); }
  .cases { display:flex; flex-wrap:wrap; gap:8px; padding:12px 20px; }
  .casebtn { background:var(--panel); color:var(--fg); border:1px solid #2f3b47; border-radius:6px; padding:8px 10px; cursor:pointer; text-align:left; }
  .casebtn.active { border-color:#4da3ff; box-shadow:0 0 0 1px #4da3ff inset; }
  .casebtn b { display:block; font-size:13px; }
  .casebtn span { color:var(--muted); font-size:12px; }
  main { padding:0 20px 24px; max-width:1500px; margin:0 auto; }
  .stage { position:relative; background:#000; border:1px solid #2a3440; border-radius:8px; overflow:hidden; }
  .stage img { display:block; width:100%; height:auto; }
  .stage.inint { outline:3px solid var(--red); outline-offset:-3px; }
  .badge { position:absolute; top:10px; right:12px; background:rgba(0,0,0,.65); padding:4px 8px; border-radius:4px; font-size:12px; }
  .controls { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:12px 0; }
  button, select { background:var(--panel); color:var(--fg); border:1px solid #2f3b47; border-radius:5px; padding:6px 10px; cursor:pointer; }
  button:hover { border-color:#4da3ff; }
  input[type=range] { flex:1; min-width:220px; accent-color:#4da3ff; }
  .info { display:grid; grid-template-columns: 1fr 420px; gap:16px; align-items:start; }
  table { width:100%; border-collapse:collapse; background:var(--panel); border-radius:6px; overflow:hidden; }
  th, td { padding:7px 9px; border-bottom:1px solid #2a3440; text-align:left; font-size:13px; }
  th { color:var(--muted); font-weight:500; }
  td.num { text-align:right; font-variant-numeric: tabular-nums; }
  .note { margin-top:10px; color:var(--muted); font-size:12.5px; }
  .legend { font-size:12px; color:var(--muted); margin-top:6px; }
  @media (max-width: 900px) { .info { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<header>
  <h1>文生视频缺陷区间局部亮度校正 · 可视化查看器</h1>
  <div class="muted">参考帧 | 注入后 | A3 局部线性 | A4 全序列中值 | A7 自适应 gamma。红色边框 = 当前帧在缺陷区间内。</div>
</header>
<div class="cases" id="cases"></div>
<main>
  <div class="stage" id="stage">
    <img id="frame" alt="frame">
    <div class="badge" id="badge"></div>
  </div>
  <div class="controls">
    <button id="prev">◀ 上一帧</button>
    <button id="play">▶ 播放</button>
    <button id="next">下一帧 ▶</button>
    <select id="speed">
      <option value="4">4 fps</option>
      <option value="8" selected>8 fps（演示）</option>
      <option value="12">12 fps</option>
      <option value="16">16 fps</option>
    </select>
    <input type="range" id="slider" min="0" value="0">
    <span id="counter" class="muted"></span>
  </div>
  <div class="info">
    <div>
      <table id="mae">
        <thead><tr><th>画面</th><th>当前帧 Y MAE</th></tr></thead>
        <tbody></tbody>
      </table>
      <div class="note" id="note"></div>
      <div class="legend">空格播放/暂停；←/→ 逐帧；切换案例会重新加载该案例的帧。</div>
    </div>
    <div>
      <table>
        <thead><tr><th>区间内均值</th><th>Y MAE</th></tr></thead>
        <tbody id="agg"></tbody>
      </table>
      <div class="note">GIF 的 8 fps 只是演示帧率；数据集没有提供真实 FPS。所有帧来自真实运行，不是示意图。</div>
    </div>
  </div>
</main>
<script>
const DATA = __DATA__;
let ci = 0, t = 0, timer = null;
const $ = id => document.getElementById(id);

function caseId() { return DATA[ci].id; }
function framePath(i) { return `frames/${caseId()}/${String(i).padStart(3,'0')}.png`; }

function buildCases() {
  const box = $('cases');
  DATA.forEach((c, i) => {
    const b = document.createElement('button');
    b.className = 'casebtn' + (i === 0 ? ' active' : '');
    b.innerHTML = `<b>${c.id}</b><span>${c.seq} · ${c.inj} · len=${c.len}</span>`;
    b.onclick = () => { ci = i; t = 0; document.querySelectorAll('.casebtn').forEach((x,j)=>x.classList.toggle('active', j===i)); reset(); };
    box.appendChild(b);
  });
}

function reset() {
  stop();
  const c = DATA[ci];
  $('slider').max = c.frames - 1;
  $('slider').value = 0;
  t = 0;
  $('note').textContent = c.note;
  renderAgg();
  show();
}

function renderAgg() {
  const c = DATA[ci];
  const names = ["Reference","Injected","A3","A4","A7"];
  $('agg').innerHTML = names.map((n,i)=>`<tr><td>${n}</td><td class="num">${c.interval_mean_y_mae[n].toFixed(2)}</td></tr>`).join('');
}

function show() {
  const c = DATA[ci];
  $('frame').src = framePath(t);
  $('slider').value = t;
  $('counter').textContent = `${t+1} / ${c.frames}`;
  const inInt = t >= c.start && t < c.start + c.len;
  $('stage').classList.toggle('inint', inInt);
  $('badge').textContent = (inInt ? 'IN DEFECT' : 'outside') + `  ·  [${c.start},${c.start+c.len})`;
  const m = c.per_frame[t];
  const names = ["Reference","Injected","A3","A4","A7"];
  $('mae').querySelector('tbody').innerHTML = names.map((n,i)=>`<tr><td>${n}</td><td class="num">${m.ymaes[i].toFixed(2)}</td></tr>`).join('');
}

function step(d) { const n = DATA[ci].frames; t = (t + d + n) % n; show(); }
function stop() { if (timer) { clearInterval(timer); timer = null; } $('play').textContent = '▶ 播放'; }
function play() {
  if (timer) { stop(); return; }
  const fps = Number($('speed').value);
  timer = setInterval(() => { if (t + 1 >= DATA[ci].frames) { t = 0; } else { t++; } show(); }, 1000 / fps);
  $('play').textContent = '⏸ 暂停';
}

$('prev').onclick = () => step(-1);
$('next').onclick = () => step(1);
$('play').onclick = play;
$('slider').oninput = e => { t = Number(e.target.value); show(); };
document.addEventListener('keydown', e => {
  if (e.code === 'Space') { e.preventDefault(); play(); }
  if (e.code === 'ArrowLeft') step(-1);
  if (e.code === 'ArrowRight') step(1);
});
buildCases(); reset();
</script>
</body>
</html>
"""


def main():
    cases = json.load(open(os.path.join(OUT, "cases.json"), encoding="utf-8"))
    for c in cases:
        with open(os.path.join(OUT, "frames", c["id"], "metrics.json"), encoding="utf-8") as fh:
            c["per_frame"] = json.load(fh)["frames"]
    html = HTML.replace("__DATA__", json.dumps(cases, ensure_ascii=False))
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)
    with open(os.path.join(OUT, "打开可视化.cmd"), "w", encoding="gbk", newline="\r\n") as fh:
        fh.write("@echo off\r\nstart \"\" \"%~dp0index.html\"\r\n")
    print("wrote", os.path.join(OUT, "index.html"))


if __name__ == "__main__":
    main()
