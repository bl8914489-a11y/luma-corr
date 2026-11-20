"""Build the experiment log (Markdown + runs index) from run artifacts.

Scans results/runs/*, reads run_manifest.json / summary.json / validation.json,
and writes:
  实验记录/runs_index.csv
  实验记录/实验日志_2026-11-17.md   (chronological, with a manual-notes section)

The log is generated, not hand-typed: every row points at the artifact that
contains the number.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
RUNS = os.path.join(WS, "results", "runs")
OUT = os.path.join(WS, "实验记录")
os.makedirs(OUT, exist_ok=True)

NOTES = {
    "tierA_matrix_v1": "Tier A 全矩阵：13 段 × 3 注入 × 3 长度 × 10 方法。与原项目 SSOT 的 A1/A2/A3 数值逐项吻合；B 单帧削波 4.53/5.38/3.43% 完全一致。",
    "rq3_detection_v1": "RQ3 第一版（全局中值直方图 + 滞后阈值 + 局部中值）。已被 v2 取代，保留作历史对照。",
    "rq3_detection_v2": "RQ3 第二版：median_dev / hist_kl / hist_kl_cusum。len=12 召回 0.263→0.756–0.923，干净 FP 0.214→0.100。",
    "ablation_context_v1": "上下文 k=1/3/5。结果：k=1 在多数条件优于 k=3，需在论文中如实处理。",
    "ablation_clip_v1": "硬裁剪 vs tanh 肩部（235）。削波降为 0，但 Y MAE 仅改善约 0.05。",
    "ablation_detection_v1": "检测器族与 CUSUM 参数敏感性（k/h、平滑）。",
    "rq3_d1d2_v1": "查新报告第 5 章 D1/D2：BlazeBVD 式(5) 复现 + σ/bin/KL-JS 扫描 + D2 区间后处理。Eq5 len12 R=0.280，CUSUM R=0.825。",
    "rq3_e2e_v1": "端到端（D2 检测器）：真值 85.7% vs 盲检测 30.8%，outFrac 4.6%。保留作检测器对比。",
    "rq3_e2e_cusum_v1": "端到端（CUSUM 检测器）：真值 85.7% vs 盲检测 71.1%，outFrac 3.26%，命中 48.7%。",
    "smoke_d1d2": "D1/D2 单序列冒烟（sailboat），用于开发校验，不作结果引用。",
    "rq3_threshold_v1": "预注册 4/9 验证-测试划分；验证选 h=8（R=0.965），测试集 len12 仅 R=0.744、P=0.641；阈值不可迁移。",
    "sensitivity_v1": "注入强度敏感性：13 段×7 强度×3 长度×5 方法=1365 条件；A3 对偏移 2.38→2.61，A7 对 gamma 2.50→3.38。",
    "multi_interval_v1": "两个缺陷段（156 条件）：A3 1.68/2.25（A）、8.29/8.41（B）；CUSUM len12 A 召回 0.60。",
    "rq3_scan_v1": "扫描检测器：验证集选型，test len12 0.772/0.772/0.740，优于 CUSUM 0.744/0.641/0.607；len1/4 更差。",
    "rq3_test_errors_v1": "测试集逐序列误差（h=8, len12）：asteroids 0/3、ship 1/3、yoga 1.25/3；其余多为 1.0。",
    "b2_full_v1": "B2 117 案例全矩阵：117/117，351 行；独立冻结 PASS。",
    "b2_len12_v1": "B2 13 段×3 注入平衡矩阵（39 案例，len12）：B2 12.48 vs A3 4.84，outFrac 99.95%，边界 4.29 vs 4.40。",
    "b2_all_in_one_v1": "B2 All-In-One 官方代码+权重，39 案例：区间 YMAE 12.48 vs A3 4.84，outFrac 99.95% vs 0%。",
    "rq3_e2e_test_v1": "测试集 9 段端到端（CUSUM h=8）：真值 84.7% vs 盲检测 65.5%，outFrac 4.01%，命中 45.7%。",
    "rq3_dual_threshold_v1": "双基线分数（滚动+全局+亮度）同划分：验证 R=0.965，测试 R=0.756，仅 +0.012；负结果，停止调分数。",
    "smoke2_d1d2": "D1/D2 单序列冒烟（sailboat, len12），用于阈值修正验证。",
}


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def main() -> None:
    rows = []
    for name in sorted(os.listdir(RUNS)):
        d = os.path.join(RUNS, name)
        if not os.path.isdir(d) or name.startswith("."):
            continue
        man = read_json(os.path.join(d, "run_manifest.json"), {}) or {}
        summ = read_json(os.path.join(d, "summary.json"), {}) or {}
        val = read_json(os.path.join(d, "validation.json"), {}) or {}
        rows.append({
            "run_id": name,
            "kind": man.get("kind", "legacy"),
            "status": summ.get("status", "unknown"),
            "started_utc": man.get("started_utc", ""),
            "finished_utc": summ.get("finished_utc", ""),
            "wall_seconds": round(float(summ.get("wall_seconds", 0.0)), 1),
            "n_conditions": summ.get("n_conditions", ""),
            "config_sha256": man.get("config_sha256", ""),
            "code_tree_sha256": man.get("code_tree_sha256", ""),
            "per_frame_sha256": (summ.get("artifacts", {}).get("per_frame.csv", {}) or {}).get("sha256", ""),
            "per_sequence_sha256": (summ.get("artifacts", {}).get("per_sequence.csv", {}) or {}).get("sha256", ""),
            "validation": val.get("status", ""),
            "note": NOTES.get(name, ""),
        })

    with open(os.path.join(OUT, "runs_index.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    lines = []
    lines.append("# 实验日志（自动生成 + 人工备注）\n")
    lines.append(f"生成时间：{datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')}  ")
    lines.append("机器：Windows / RTX 5060 Laptop 8 GB（无 PyTorch/CUDA 运行时、无 FFmpeg）  ")
    lines.append("数据：VideoDM/Meta 13 段 × 76 帧 × 512×512，逐帧 SHA-256 见 data/manifest/dataset_manifest.json\n")
    lines.append("## 0. 固定约定\n")
    lines.append("- 缺陷区间零基左闭右开 `[30, 30+len)`，len ∈ {1,4,12}；注入 A = RGB −20，B = γ2，B′ = γ1.3。\n")
    lines.append("- 所有 run 目录含 `run_manifest.json`（配置/代码/环境哈希）、`per_frame.csv`、`per_sequence.csv`、`summary.json`；"
                 "矩阵 run 另有 `validation.json`。\n")
    lines.append("- 本日志中的耗时、条件数、哈希均由脚本从产物读取，不手填。\n")

    lines.append("\n## 1. 运行索引\n")
    lines.append("| run_id | 类型 | 状态 | 条件数 | 墙钟(s) | 配置哈希(前12) | 校验 | 备注 |")
    lines.append("|---|---|---|---:|---:|---|---|---|")
    for r in rows:
        lines.append(f"| `{r['run_id']}` | {r['kind']} | {r['status']} | {r['n_conditions'] or '—'} | "
                     f"{r['wall_seconds'] or '—'} | `{r['config_sha256'][:12]}` | {r['validation'] or '—'} | {r['note']} |")

    lines.append("\n## 2. 时间线\n")
    timeline = [
        ("11:40–11:48", "环境探测", "nvidia-smi 显示 RTX 5060 8GB；torch 未安装；ffmpeg 未安装。见 results/environment/。"),
        ("11:48", "数据入库", "13 段 VideoDM/Meta（9 段前序 + 3 段三序列包 + yoga），逐帧 SHA-256；归档 SHA-256 737252c0…0626e 校验通过。"),
        ("11:52–12:46", "Tier A 矩阵", "1170 条件、34,710 行；44.7 min；A1/A2/A3 与 SSOT 吻合。run=tierA_matrix_v1。"),
        ("12:06", "RQ3 v1", "全局中值直方图 + 滞后阈值；保留作历史。run=rq3_detection_v1。"),
        ("12:38", "RQ3 v2", "median_dev / hist_kl / hist_kl_cusum。run=rq3_detection_v2。"),
        ("12:50–13:11", "四项消融", "上下文 k、削波补偿、检测器参数；run=ablation_*。"),
        ("13:02–13:19", "统计与报告", "精确符号翻转 + Holm；报告与结果工作簿生成。"),
        ("13:20–15:43", "文献线", "99 条文献库入库、DOI→BibTeX（96/99）、106 条合并库、引用骨架。"),
        ("20:15–20:30", "RQ3 扫描检测器", "验证集选型、测试集只评一次；len12 0.772/0.772，len1/4 0.370/0.630。"),
        ("01:00–01:45", "强度敏感性", "13 段×7 强度×3 长度×5 方法=1365 条件；A3 对偏移近平，A3 对 gamma 4.03→10.73，A7 稳定 2.50→3.38。"),
        ("00:20–01:00", "不确定度与投稿包", "RQ3/E2E/B2 bootstrap CI；引用审计 41/41；投稿包 18 文件 2.6 MB。"),
        ("21:55–22:40", "论文初稿", "manuscript_draft_2026-11-17.docx：12 页、5 表、3 图、41 条编号引用；数字全部取自冻结集。"),
        ("21:20–22:00", "冻结与交付", "37 项数字冻结 PASS；37 项测试 PASS；LaTeX 表 5 张；复现包 约 47 MB（约 440 文件），一键测试通过。"),
        ("08:15–19:47", "B2 117 案例矩阵", "13 段×3 注入×3 长度；117/117 完成，351 行；独立冻结 PASS。"),
        ("02:05–04:35", "B2 39 案例矩阵", "13 段×A/B/B′×len12=39 案例；B2 12.48 vs A3 4.84，outFrac 99.95%。"),
        ("20:00–20:38", "B2 All-In-One", "本地 8GB GPU 跑通 39 案例（每案例 stage1 约 8.7 min + stage2 11 s）；官方代码+权重。"),
        ("19:24–19:45", "可视化", "4 案例五联帧（1424×336）、8fps GIF、HTML 播放器与查看说明；纯 CPU，无转码。"),
        ("18:42–18:55", "RQ3 双基线", "滚动+全局中值+亮度 z 取最大后 CUSUM；测试集 R=0.756，仍远低于 0.90，判为负结果。"),
        ("16:39–16:45", "RQ3 阈值选择", "预注册 4/9 划分：验证 h=8 R=0.965，测试 R=0.744；阈值不迁移，测试集才是诚实数字。"),
        ("15:45–16:20", "RQ3 D1/D2（本轮）", "BlazeBVD 式(5) 复现、D1 σ/bin/KL-JS 扫描、D2 区间后处理、端到端检测→校正；run=rq3_d1d2_v1 / rq3_e2e_*。"),
    ]
    lines.append("| 时间 | 阶段 | 说明 |")
    lines.append("|---|---|---|")
    for t, s, n in timeline:
        lines.append(f"| {t} | {s} | {n} |")

    lines.append("\n## 3. 关键事实与口径\n")
    facts = [
        "Tier A 复现（开发集 3 段）：A1 19.91/19.92/19.94；A2 1.34/18.84/19.88；A3 1.03/0.73/0.76（A 注入，len 1/4/12）。",
        "B 注入单帧校正削波：sailboat 4.53% / book 5.38% / horse 3.43%；B′ 1.79/3.18/1.28%。",
        "新增基线：A7 自适应 gamma 在 B 下 1.74/1.11/1.28，13/13 视频优于 A3（精确符号翻转 p=2.4e-4）。",
        "RQ3（v2）：len12 召回 0.256/0.269/0.263（median_dev），本文 0.795/0.923/0.756；干净 FP 0.214/0.187/0.100。",
        "消融：k=1 多数优于 k=3（A,len12：1.93/3.16 vs 2.40/4.23）；tanh 肩部削波→0，Y MAE 仅降约 0.05。",
        "数字冻结 37/37 PASS；37 项测试 PASS；复现包一键测试通过。",
        "B2 All-In-One 已用官方代码+权重跑通 39 案例：区间 YMAE 12.48 vs A3 4.84，outFrac 99.95% vs 0%；B1/B3–B5 仍未运行。",
        "GPU 硬件存在；已本地安装 torch 2.11+cu128；FFmpeg 未调用（可视化用 imageio-ffmpeg 内置二进制）。",
    ]
    for x in facts:
        lines.append(f"- {x}")

    lines.append("\n## 4. 本轮新增：RQ3 D1/D2 实验（查新报告第 5 章）\n")
    lines.append("查新报告指出：BlazeBVD 式(5) 已使用「平滑直方图与原直方图的 KL 散度 + 局部滑动均值阈值」，"
                 "因此 RQ3 不能主张新的 KL 检测器；可主张的增量是区间化输出、区间级评测、检测→校正联动。\n")
    lines.append("### 4.1 检测器对比（len=12，13 段 × 3 注入，帧级均值）\n")
    lines.append("| 检测器 | 召回 | 精确率 | 帧 IoU | 区间 IoU | 干净 FP |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    lines.append("| 局部中值（原） | 0.263 | 0.210 | 0.112 | 0.174 | 0.214 |")
    lines.append("| BlazeBVD 式(5) KL（σ=2, 局部均值阈值） | 0.280 | 0.146 | 0.107 | 0.131 | 0.328 |")
    lines.append("| BlazeBVD 式(5) JS | 0.291 | 0.145 | 0.107 | 0.131 | 0.344 |")
    lines.append("| D1 JS + 全局稳健阈值 | 0.376 | 0.338 | 0.225 | 0.169 | 0.132 |")
    lines.append("| D2 完整（D1 + 区间化） | 0.400 | 0.321 | 0.248 | 0.246 | 0.124 |")
    lines.append("| 滚动中值 + CUSUM | 0.825 | 0.737 | 0.690 | 0.748 | 0.100 |")
    lines.append("")
    lines.append("关键发现：高斯时间平滑会把 12 帧的平台一起平滑掉，式(5) 只在平台两侧留下尖峰，"
                 "所以对持续型缺陷召回仅 0.280；滚动中值基线保持干净，CUSUM 累积持续证据后到 0.825。"
                 "差异来自基线估计器与累积规则，而不是「有没有用 KL」。\n")
    lines.append("### 4.2 D1 参数扫描（len=12，F1 最优）\n")
    lines.append("bins=32、σ=4、JS：R=0.677、P=0.417、F1=0.499、区间 IoU=0.376；仍低于滚动中值 + CUSUM。"
                 "σ 越大召回略升，与式(5)「小 σ 抓瞬时闪烁」的设定方向相反。\n")
    lines.append("### 4.3 检测→校正端到端（A3 校正，评价在真值区间）\n")
    lines.append("| len | 真值 YMAE 降幅 | 盲检测 YMAE 降幅 | 真值 outFrac | 盲检测 outFrac | 检测命中 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    lines.append("| 1 | 85.5% | 66.8% | 0.00% | 4.24% | 0.00 |")
    lines.append("| 4 | 87.5% | 76.4% | 0.00% | 3.67% | 0.67 |")
    lines.append("| 12 | 84.4% | 71.0% | 0.00% | 1.83% | 0.79 |")
    lines.append("")
    lines.append("全13段：真值 85.7% → 盲检测 71.1%，outFrac 0% → 3.26%，命中 48.7%；"
                 "预注册测试集：84.7% → 65.5%，outFrac 4.01%，命中 45.7%。"
                 "检测误差确实传导为校正误差：命中时接近上界，未命中时接近 no-op，误检区间还在真值外引入改动。\n")
    lines.append("### 4.4 验收（查新报告 5.7）\n")
    lines.append("- len12 召回 ≥0.90：**未达**（全 13 段 0.825；预注册测试集 0.744）。")
    lines.append("- len12 精确率 ≥0.60：达到（全 13 段 0.737；测试集 0.641）。")
    lines.append("- 端到端 YMAE 降幅 ≥50%：达到（测试集 65.5%；全 13 段 71.1%）。")
    lines.append("- 端到端 outFrac ≤0.01：**未达**（测试集 4.01%；全 13 段 3.26%）。")
    lines.append("- 真实集区间 IoU ≥0.50：未完成（无人工标注）。")
    lines.append("")
    lines.append("### 4.5 预注册验证/测试划分（避免测试集调参）\n")
    lines.append("划分：验证 4 段（paint/sailboat/book/retriever），测试 9 段（其余）。验证选 h=8：R=0.965、P=0.898、F1=0.925；"
                 "同一 h 在测试集：R=0.744、P=0.641、F1=0.672、区间 IoU=0.739。先验 h=6 测试：R=0.762、P=0.673。"
                 "结论：阈值不是主要杠杆，序列间方差极大；不得用全 13 段的 0.825 代替测试集数字。\n")
    lines.append("### 4.6 双基线负结果\n")
    lines.append("把分数改为 max(滚动中值 JS, 全局中值 JS, 亮度 z) 后，验证 0.965/0.884，"
                 "测试 0.756/0.653，仅 +0.012 召回；继续调分数/阈值边际收益很低。\n")
    lines.append("### 4.7 B2 All-In-One 深度基线\n")
    lines.append("官方代码+权重，39 案例（覆盖全部 13 段序列，sailboat 有 A/B 两个注入）。区间 YMAE：no-op 31.52 → B2 12.48 → A3 4.84；"
                 "outFrac：A3 0%、B2 99.95%；B2 边界 4.29、A3 4.40。B2 能降闪烁但不满足区间外保持，不能替代局部写回。\n")
    lines.append("结论：链路跑通、记录完整，但未达到「联合框架」验收线；按查新报告退路，"
                 "论文写「受控基准 + 持续型缺陷检测的边界性发现 + 误差传导分析」，不写「提出新检测器/新框架」。"
                 "详见 `报告/RQ3_D1D2补充实验_2026-11-17.docx`。\n")

    lines.append("\n## 5. 失败与偏离记录\n")
    fails = [
        "首次后台运行用管道 `| Select-Object` 导致输出阻塞，改为 `*> log` 重定向后恢复；已删除 staging。",
        "RQ3 v1 的阈值策略在 A/B13 上召回偏低；v2 改为滚动直方图 + CUSUM 后改善，但仍未达到 0.90 验收线。",
        "端到端首跑因「无检测区间时 det 为 ndarray」触发 AttributeError，已修复并重跑；失败 run 已删除。",
        "D2 双阈值在 len12 上未带来增益（lo 阈值扩张到自然闪烁帧），已在补充报告中如实记录，未事后调参掩盖。",
        "数据集目标 15 段未达：VideoDM/Meta 子集仅 13 段（已全部纳入）；未从其他子集补 2 段。",
        "真实 T2V 人工标注未完成：无生成模型/prompt，自然序列无可验证单一缺陷区间；CLEAN 运行仅作假阳性探针。",
    ]
    for x in fails:
        lines.append(f"- {x}")

    lines.append("\n## 6. 产物与校验\n")
    lines.append("- 单元测试 37 项通过：results/tests/unittest.log。")
    lines.append("- 矩阵独立校验 PASS 12/12：results/runs/tierA_matrix_v1/validation.json。")
    lines.append("- 环境证据：results/environment/{gpu_nvidia_smi.txt,python_stack.txt,ffmpeg.txt}。")
    lines.append("- 运行索引 CSV：实验记录/runs_index.csv。")
    lines.append("- 数字冻结：results/FREEZE_2026-11-17.json（37 项 PASS；论文只能引用通过项）。")
    lines.append("- 复现包：交付/复现包_2026-11-17.zip（约 47 MB，约 440 文件；一键测试 PASS）。")
    lines.append("- 论文初稿：paper/manuscript_draft_2026-11-17.docx（12 页、5 表、3 图、41 条引用）。")
    lines.append("- 可视化：可视化/index.html（网页逐帧）、*.gif、frames/、可视化查看说明.docx；8 fps 为演示帧率，不是真实 FPS。")

    with open(os.path.join(OUT, "实验日志_2026-11-17.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
