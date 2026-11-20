"""Build the full Chinese project summary DOCX."""
from __future__ import annotations

import csv
import json
import os

import numpy as np
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "报告", "项目总结报告_2026-11-18.docx")


def p(doc, text, bold=False, size=10.5):
    par = doc.add_paragraph(); par.paragraph_format.space_after = Pt(4)
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = par.add_run(text); r.font.size = Pt(size); r.font.bold = bold
    r.font.name = "Times New Roman"
    r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")


def h(doc, text, level=1):
    doc.add_heading(text, level=level)


def table(doc, headers, rows, widths=None, size=8.5):
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"
    for i, x in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = ""
        r = c.paragraphs[0].add_run(str(x)); r.font.bold = True; r.font.size = Pt(size)
    for row in rows:
        cells = t.add_row().cells
        for i, x in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(x)); r.font.size = Pt(size)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()


def fig(doc, path, caption, width=16.0):
    if not os.path.exists(path):
        return
    doc.add_picture(path, width=Cm(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = c.add_run(caption); r.font.size = Pt(8); r.font.italic = True


def load_json(rel):
    return json.load(open(os.path.join(WS, rel), encoding="utf-8"))


def read(rel):
    with open(os.path.join(WS, rel), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    matrix = read("results/runs/tierA_matrix_v1/per_sequence.csv")
    dev = {"sailboat", "book", "horse"}

    def dm(inj, L, m, key="y_mae"):
        v = [float(r[key]) for r in matrix if r["injection"] == inj and int(r["length"]) == L
             and r["method"] == m and r["sequence"] in dev]
        return float(np.mean(v))

    def allm(inj, L, m, key="y_mae"):
        v = [float(r[key]) for r in matrix if r["injection"] == inj and int(r["length"]) == L and r["method"] == m]
        return float(np.mean(v))

    b2 = load_json("results/runs/b2_len12_v1/summary.json")["interval_mean"]
    b2full = load_json("results/runs/b2_full_v1/summary.json")["interval_mean"]
    rq3 = load_json("results/runs/rq3_detection_v2/summary.json")
    thr = load_json("results/runs/rq3_threshold_v1/summary.json")
    scan = load_json("results/runs/rq3_scan_v1/summary.json")
    multi = load_json("results/runs/multi_interval_v1/summary.json")
    mixed = load_json("results/runs/multi_mixed_v1/summary.json")
    mscan = load_json("results/runs/multi_scan_v1/summary.json")

    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.0); s.top_margin = s.bottom_margin = Cm(1.9)
    st = doc.styles["Normal"]; st.font.name = "宋体"; st.font.size = Pt(10.5)

    # cover
    for _ in range(4):
        doc.add_paragraph()
    t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("项目总结报告"); r.font.size = Pt(26); r.font.bold = True; r.font.name = "Times New Roman"
    t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("已知区间局部亮度校正的可复现实证研究"); r.font.size = Pt(15); r.font.name = "Times New Roman"
    for _ in range(6):
        doc.add_paragraph()
    for line in ["ZHIKUN（50260258）", "2026-11-18", "Signal, Image and Video Processing（SIVP）投稿项目"]:
        t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = t.add_run(line); r.font.size = Pt(12)
    doc.add_page_break()

    # 摘要
    h(doc, "摘要", 1)
    p(doc, "本项目研究“已知缺陷区间”的视频亮度校正：给定注入或检测到的区间，估计算法能否准确恢复区间亮度，"
           "同时不改变区间外像素，并分析检测误差如何传导为校正误差。工作从复现原项目 A1/A2/A3 开始，扩展到 "
           "13 段序列、3 种注入、3 种长度、10 个确定性方法（1,170 个条件），并补充 RQ3 检测、B2 深度基线、"
           "注入强度/位置/边界敏感性、多区间缺陷与多区间检测器。")
    p(doc, "核心结论：（1）A 注入下 A3 把区间 Y-MAE 从 no-op 的 19.91 降到 1.03/0.73/0.76（len 1/4/12）；"
           "（2）gamma 注入下 A3 仍有 8.65/7.87/7.89 的残差，削波是主因，gamma-aware 的 A7 可降到 1.74/1.11/1.28；"
           "（3）局部写回 A3 区间外改动为 0，而全序列写回 A4 改动 33.2%；"
           "（4）RQ3 主检测器 CUSUM 测试集 len12 为 0.744/0.641，低于 0.90 目标，按边界性发现如实报告；"
           "（5）B2 All-In-One 在 39 个平衡案例上 Y-MAE 12.48 vs A3 4.84，但区间外改动 99.95%，"
           "说明盲全局方法与已知区间局部方法的目标不同。")

    # 1 背景
    h(doc, "1  项目背景与目标", 1)
    p(doc, "文本到视频（T2V）生成与视频修复中，亮度闪烁/曝光漂移是最常见的时序伪影之一。盲去闪烁方法（BlazeBVD、"
           "All-In-One、DiffSynth 等）在不知道缺陷区间的前提下处理整段视频，优化的是整体观感；而编辑、修复、质量控制的"
           "实际管线往往已知或可规则确认缺陷区间，此时问题变成：区间内能恢复多准、区间外能否保持不变、边界是否跳变、"
           "检测误差如何影响校正。")
    p(doc, "项目目标不是提出新的 SOTA 去闪烁网络，而是建立一个可复现的受控基准，量化“已知区间 + 局部写回”的收益与边界，"
           "并把检测—校正链路、深度盲基线、边界/多区间等失效模式如实写清楚，形成可投稿 SIVP 的实证论文与复现包。")

    h(doc, "2  研究问题与贡献", 1)
    for x in [
        "RQ1：在已知区间、受控注入下，确定性校正方法能把区间误差降到多少？哪些方法在 gamma 注入下更好？",
        "RQ2：局部写回与全序列写回在区间外保持、边界误差上的差异有多大？",
        "RQ3：不依赖注入标签，能否定位持续型亮度区间？测试集泛化如何？误差如何传导到校正？",
        "补充：深度盲基线 B2 在同一任务约束下表现如何？注入强度、位置、边界、多区间会改变结论吗？",
    ]:
        doc.add_paragraph(x, style="List Bullet")
    p(doc, "对应贡献：可复现基准（13 段、1,170 条件、逐帧哈希）；局部 vs 全局写回与边界分解；gamma 削波归因；"
           "RQ3 先验边界与预注册测试；B2 深度基线；强度/位置/边界/多区间压力测试；完整复现包与投稿材料。")

    # 3 数据与设计
    h(doc, "3  数据与实验设计", 1)
    p(doc, "数据：Blind-Video-Deflickering-Dataset 的 VideoDM/Meta 子集（Hugging Face，CC BY 4.0），"
           "13 段序列 × 76 帧 × 512×512 RGB。归档 SHA-256 为 737252c0…0626e；逐帧 SHA-256 在 manifest 中。")
    table(doc, ["项目", "设置"], [
        ["序列", "13 段：sailboat、book、horse、paint、fish、unicorn、yoga、knight、rabbit、astronaut、ship、asteroids、retriever"],
        ["帧/分辨率", "76 帧/段，512×512"],
        ["注入", "A：RGB 偏移 −20；B：码值 gamma 2.0；B′：gamma 1.3"],
        ["区间", "零基半开 [s, s+len)，主实验 s=30，len ∈ {1,4,12}"],
        ["方法", "A1–A9（含 A7f），共 10 个确定性实现"],
        ["条件数", "13 × 3 × 3 × 10 = 1,170；逐帧 34,710 行"],
        ["划分", "按序列名 SHA-256 预注册：验证 paint/sailboat/book/retriever；测试其余 9 段"],
    ], [3.2, 13.0])
    p(doc, "gamma 注在码值上，不是物理显示 gamma；注入阶段记录注入削波，校正阶段记录校正削波，二者严格区分。"
           "主实验的削波是校正侧（拉回亮度时高光撞上 255），不是注入侧。")

    # 4 方法
    h(doc, "4  方法与指标", 1)
    p(doc, "A1 no-op；A2 局部 7 帧中值目标；A3 区间外左右各 3 帧线性外推（主方法）；A4 与 A2 同估计器但全序列写回；"
           "A5 STE 风格直方图规格化；A6 CLAHE；A7 自适应 gamma；A7f 固定逆 gamma 2；A8 时间双边；A9 Kalman/RTS。"
           "A3e 是边缘感知变体：单侧上下文缺失时用可用侧最多 2k 帧外推。")
    p(doc, "指标：区间 Y-MAE/RGB-MAE/PSNR/SSIM；区间外改动像素比例 OutFrac 与 outside RGB MAE；"
           "边界误差分解为估计器偏差与区间外跳变；直方图 TV 距离；闪烁一阶/二阶差分。统计：视频级聚类 bootstrap、"
           "精确符号翻转 Wilcoxon、Holm 校正。")
    table(doc, ["检测器", "说明"], [
        ["median_dev", "局部 7 帧中值偏差（legacy）"],
        ["hist_kl", "BlazeBVD Eq.(5) 忠实复现：平滑直方图 KL + 局部均值阈值"],
        ["hist_kl_cusum", "滚动中值 JS + 亮度 z + CUSUM（主检测器）"],
        ["scan", "候选区间内/外 luma/直方图扫描（固定或未知长度）"],
        ["multi-scan", "全窗口扫描 + 贪心/非重叠选择，输出多段"],
    ], [3.2, 13.0])

    # 5 结果
    h(doc, "5  实验结果", 1)

    h(doc, "5.1  RQ1：区间重建", 2)
    rows = []
    for m, label in [("A1", "A1 no-op"), ("A2", "A2 median-7"), ("A3", "A3 linear k=3"),
                     ("A5", "A5 STE"), ("A7", "A7 adaptive γ")]:
        rows.append([label] + [f"{dm(inj,L,m):.2f}" for inj in ("A","B","B13") for L in (1,4,12)])
    table(doc, ["方法", "A 1", "A 4", "A 12", "B 1", "B 4", "B 12", "B′ 1", "B′ 4", "B′ 12"], rows)
    p(doc, "A 注入下 A3 为 1.03/0.73/0.76；A2 在 len4/12 被 7 帧窗口污染（18.84/19.88）。B 注入下 A3 仍有 8.65/7.87/7.89，"
           "A7 为 1.74/1.11/1.28；B′ 下 A3 3.78/3.01/3.18、A7 1.35/0.80/0.91。A3 不是普适最优，gamma 注入下 A7 更好。")

    h(doc, "5.2  gamma 残差与削波归因", 2)
    p(doc, "B 注入的残差不是注入削波（gamma 变暗，注入侧几乎不削波），而是校正把亮度拉回时高光撞上 255。"
           "单帧校正削波比例：sailboat 4.53%、book 5.38%、horse 3.43%；B′ 降到 1.79%/3.18%/1.28%，残差同步下降。"
           "tanh shoulder 能消除硬削波（2.57%→0%），但 Y-MAE 只从 8.164 降到 8.117，说明被裁掉的信息无法靠压缩恢复。"
           "因此正确表述是“加性偏移族的 gamma 残差以削波为主”，不是“任何方法都无法避免”。")

    h(doc, "5.3  RQ2：局部 vs 全序列写回", 2)
    table(doc, ["方法", "OutFrac(A,12)", "区间外 RGB", "边界误差"], [
        ["A2 local median-7", "0.00%", "0.00", "37.20"],
        ["A3 outside linear k=3", "0.00%", "0.00", "4.23"],
        ["A4 full-seq median-7", "33.2%", "0.91", "33.89"],
    ], [5.0, 3.2, 3.0, 3.0])
    p(doc, "A2/A4 共用估计器，只差写回范围：局部 0% 区间外改动，全局 33.2% 且边界误差 33.89；"
           "A4 的误差几乎全是估计器偏差（33.9），不是区间外跳变（3.3）。局部写回不是实现细节，是任务约束。")

    h(doc, "5.4  RQ3：检测与泛化差距", 2)
    table(doc, ["检测器", "R@1", "P@1", "R@4", "P@4", "R@12", "P@12", "Clean FP"], [
        ["Local median (legacy)", "1.000", "0.104", "0.462", "0.144", "0.263", "0.210", "0.214"],
        ["BlazeBVD Eq.(5) KL", "1.000", "0.045", "0.686", "0.111", "0.280", "0.146", "0.328"],
        ["Global JS + hysteresis", "0.667", "0.052", "0.853", "0.289", "0.761", "0.499", "0.187"],
        ["Rolling JS + CUSUM", "0.846", "0.135", "0.897", "0.383", "0.825", "0.737", "0.100"],
    ], [5.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.2])
    p(doc, "Eq.(5) 的失败不是单一机制：knight A 的分数在区间内升高，但被 local-mean 阈值压住（0/12）；"
           "其他序列则是平滑后只剩边缘。CUSUM 全 13 段 len12 为 0.825/0.737/0.690，但预注册测试集只有 0.744/0.641"
           "（95% CI 0.485–0.982），明显泛化差；a-priori h=6 也只有 0.762/0.673。论文因此不主张新检测器，"
           "而写成“基线构造 + 误差传导 + 边界性发现”。")
    p(doc, "补充扫描检测器：固定候选长度 {1,4,12} 时测试 len12 为 0.772/0.772/0.740，但 len1/4 跌到 0.370/0.630；"
           "未知长度扫描召回 0.787、精确率 0.561。说明固定长度扫描的收益部分来自“长度已知”，不能替代 CUSUM。")
    fig(doc, os.path.join(WS, "paper", "figures", "fig2_detection_scores.png"),
        "图 1  knight_A_len12：Eq.(5) 分数升高但 local-mean 阈值压住（0/12）；CUSUM 覆盖 12/12。")

    h(doc, "5.5  B2：All-In-One 深度盲基线", 2)
    table(doc, ["方法", "A", "B", "B′", "总 YMAE", "OutFrac", "区间外 RGB", "边界"], [
        ["no-op", "19.90", "54.02", "20.63", "31.52", "0.00%", "0.00", "62.96"],
        ["A3 local k=3", "2.40", "8.07", "4.03", "4.84", "0.00%", "0.00", "4.40"],
        ["B2 All-In-One", "9.19", "18.56", "9.69", "12.48", "99.95%", "9.79", "4.29"],
    ], [4.0, 2.0, 2.0, 2.0, 2.4, 2.4, 2.8, 2.2])
    p(doc, "B2 是 13 段 × 3 注入 × len12 的 39 个平衡案例，官方代码 + 权重。B2 相对 no-op 降 60.4%，但仍是 A3 的 2.58 倍，"
           "且改动 99.95% 的区间外像素；区间外平均 RGB 差 9.79。它不是 SOTA 排名，而是说明盲全局方法与已知区间局部方法"
           "优化目标不同。")
    p(doc, "117 案例全矩阵（加 len1/4）：A 注入 B2 7.79/7.39/9.19 vs A3 2.06/1.48/2.40；B 注入 B2 8.94/10.94/18.56 vs A3 8.16/7.65/8.07。"
           "B2 随区间长度恶化，尤其 gamma。")
    fig(doc, os.path.join(WS, "报告", "assets", "b2_sailboat_B_034.png"),
        "图 2  sailboat_B_len12 第 34 帧：参考 | 注入 | A3 | B2。A3 只改区间，B2 重绘整帧。")

    h(doc, "5.6  注入强度敏感性", 2)
    table(doc, ["注入", "A1", "A2", "A3", "A7"], [
        ["A −10", "9.98", "9.61", "2.38", "2.95"],
        ["A −20", "19.90", "19.52", "2.40", "3.81"],
        ["A −30", "29.72", "29.35", "2.61", "4.83"],
        ["B γ1.3", "20.63", "20.26", "4.03", "2.50"],
        ["B γ1.5", "31.99", "31.62", "5.24", "2.61"],
        ["B γ2.0", "54.02", "53.66", "8.07", "2.95"],
        ["B γ2.5", "69.71", "69.34", "10.73", "3.38"],
    ], [2.6, 2.6, 2.6, 2.6, 2.6])
    p(doc, "A3 对恒定偏移几乎不敏感（2.38→2.61），A2 随偏移线性恶化；gamma 下 A3 从 4.03 升到 10.73，A7 稳定在 2.50–3.38。"
           "A3 削波 0.80%→2.46%，A7 0.12%→0.71%，与削波归因一致。")
    fig(doc, os.path.join(WS, "paper", "figures", "fig4_sensitivity.png"),
        "图 3  偏移幅度（左）与 gamma 强度（右）对区间 Y-MAE 的影响。")

    h(doc, "5.7  位置、边界与 A3e", 2)
    p(doc, "中部位置 10/30/50：A3 在 A 注入 1.91→2.59、B 8.63→8.07→8.19、B′ 3.83→4.25；A7 单调上升但 B/B′ 仍更好。"
           "位置效应约 0.5–0.7 Y-MAE，小于方法差距。")
    p(doc, "贴边会显著放大误差：len1 start=0 时 A3 为 9.41（中部 2.06），len12 结束于 76 时为 6.49（中部 2.40）。"
           "原因是原 A3 在单侧上下文缺失时把 k 降为 0，目标退化为整段均值。A3e 用可用侧最多 2k 帧外推："
           "start0 len1/len4 A 注入 9.41/7.56→3.06/1.56；start64 len12 B 13.90→10.83；但仍未追平中部。")
    table(doc, ["设置", "A3", "A3e", "中部对照"], [
        ["len1, start=0, A", "9.41", "3.06", "2.06"],
        ["len4, start=0, A", "7.56", "1.56", "1.48"],
        ["len12, 结束于 76, B", "13.90", "10.83", "8.07"],
        ["len1, start=0, B", "14.19", "10.19", "8.16"],
    ], [5.0, 3.0, 3.0, 3.0])
    fig(doc, os.path.join(WS, "paper", "figures", "fig5_position.png"),
        "图 4  区间起点对 A3/A7 的影响（左：偏移 −20；右：γ=2）。")

    h(doc, "5.8  多区间缺陷", 2)
    p(doc, "两个缺陷段 [10,10+L) 与 [50,50+L)，L=4/12：A3 校正仍有效（A 1.68/2.25，B 8.29/8.41），区间外改动 0%；"
           "但 CUSUM 检测退化：len12 A 召回 0.596、段命中 0.54/0.69，B 0.878、0.85/0.85。")
    p(doc, "三段/混合强度/混合长度（len4/8/12，A/B/B′）：mixed 下 A3 4.92、A7 2.79；sameA 下 A3 2.10、A7 3.82；"
           "CUSUM 召回 0.60/0.50，段命中 0.54–0.92。检测比校正更受限。")
    table(doc, ["场景", "方法", "Y MAE", "OutFrac", "CUSUM 召回", "段命中"], [
        ["mixed", "A3", "4.92", "0%", "0.60", "0.62/0.92/0.54"],
        ["mixed", "A7", "2.79", "0%", "0.60", "同上"],
        ["sameA", "A3", "2.10", "0%", "0.50", "0.69/0.54/0.54"],
        ["sameA", "A7", "3.82", "0%", "0.50", "同上"],
    ], [2.4, 2.0, 2.2, 2.0, 2.8, 5.0])

    h(doc, "5.9  多区间专用检测器", 2)
    p(doc, "全窗口扫描 + 贪心非重叠选择（最多 3 段）在 len12 上把两段命中从 CUSUM 的 0.54/0.69 提到 0.94/0.89，"
           "召回 0.905，但精确率 0.637；len4 精确率仅 0.338。限制最多 2 段后，测试召回 0.925、精确率 0.530，"
           "len12 为 0.905/0.639、命中 1.00/0.83。仍是 precision–recall 权衡，不能替代高精确率 CUSUM。")
    table(doc, ["方法", "长度", "召回", "精确率", "段 1 命中", "段 2 命中"], [
        ["CUSUM", "len12 A", "0.596", "0.686", "0.54", "0.69"],
        ["CUSUM", "len12 B", "0.878", "0.820", "0.85", "0.85"],
        ["multi-scan", "len12", "0.905", "0.637", "0.94", "0.89"],
        ["multi-scan v2", "len12", "0.905", "0.639", "1.00", "0.83"],
    ], [3.4, 2.6, 2.2, 2.4, 2.6, 2.6])

    # 6 复现
    h(doc, "6  统计、冻结与复现", 1)
    p(doc, "统计：视频级聚类 bootstrap（2,000–4,000 次）；视频级精确符号翻转 Wilcoxon（n≤20 精确，n>20 Monte Carlo）；"
           "Holm 校正；frame-level p 只作描述。RQ3 测试召回 0.744 的 95% CI 为 0.485–0.982；B2−A3 配对差 7.65 Y-MAE"
           "（95% CI 6.19–9.25）。")
    p(doc, "冻结：主冻结 37/37 PASS；B2 117 案例 PASS；RQ3 扫描 117 条件 PASS；多区间 156 行 PASS；"
           "三段 78 行 PASS；边界 936 行 PASS；多区间扫描 52 行 PASS；A3e 702 行 PASS。")
    table(doc, ["冻结文件", "检查", "状态"], [
        ["FREEZE_2026-11-17.json", "37 项头条数字", "PASS"],
        ["FREEZE_B2_FULL_2026-11-18.json", "117 案例 / 351 行", "PASS"],
        ["FREEZE_RQ3_SCAN_2026-11-18.json", "117 条件", "PASS"],
        ["FREEZE_MULTI_INTERVAL_2026-11-18.json", "156 行", "PASS"],
        ["FREEZE_MULTI_MIXED_2026-11-18.json", "78 行", "PASS"],
        ["FREEZE_EDGE_2026-11-18.json", "936 行", "PASS"],
        ["FREEZE_MULTI_SCAN_2026-11-18.json", "52 行", "PASS"],
        ["FREEZE_EDGE_AWARE_2026-11-18.json", "702 行", "PASS"],
    ], [8.0, 5.0, 2.5])
    p(doc, "复现包：464 文件 / 48.6 MB，包内一键测试 37 项单元测试 + 37 项冻结 PASS；含代码、配置、全部 run 产物、"
           "报告、可视化、投稿包、PDF 与校验和。跨文档审计 0 命中；论文表/图审计 PASS；引用审计 41/41 PASS。")

    # 7 标注
    h(doc, "7  真实 T2V 标注计划", 1)
    p(doc, "现有 13 段来自 VideoDM/Meta 子集，能确认是生成视频子集，但公开数据没有逐段模型名/提示词。"
           "为把“自然闪烁”从 limitations 变成实验，已准备 100 个 24 帧片段（覆盖 13 段，每段 7–8 个）做双人标注。")
    for x in [
        "标注包：100 个正式片段 + 5 个资格测试片段 + 5 个已标注示例 + 双人模板 + 指南。",
        "任务：判断整体亮度/曝光/对比度是否连续 ≥2 帧异常，标出局部帧号 0–23 的起止，填类型、严重度、置信度。",
        "资格测试：5/5 通过再开始；4/5 重读指南；<4/5 补讲。",
        "一致性：20% 双标，Cohen's kappa ≥0.6、区间 IoU≥0.5；低于阈值由第三人仲裁。",
        "时间：每人约 2.5–3.5 小时；拿不准标 confidence=1 + notes，不硬判。",
    ]:
        doc.add_paragraph(x, style="List Bullet")

    # 8 结论与限制
    h(doc, "8  结论与限制", 1)
    for x in [
        "已知区间局部校正的收益是真实的：A3 在 A 注入下把 19.9 降到 1.0–0.8；但 gamma 下需要 gamma-aware 方法（A7）。",
        "局部写回与全局写回不是同一任务：A4 改 33.2% 区间外像素，A3 为 0；论文必须把“保持”作为评价项。",
        "RQ3 测试集 0.744，低于 0.90；扫描检测器 len12 可到 0.772/0.772，但短区间崩；多区间检测更差。",
        "B2 深度盲基线 12.48 vs A3 4.84，outFrac 99.95%；不是 SOTA 排名，是任务差异。",
        "边界、多区间、多段检测是明确开放问题；A3e 只能缓解贴边误差，不能消除。",
        "限制：13 段、合成注入、无自然标注（进行中）、B1 代码未公开、B3–B5 未运行、B2 非逐位复现。",
    ]:
        doc.add_paragraph(x, style="List Bullet")

    # 9 时间与费用
    h(doc, "9  时间表与费用", 1)
    table(doc, ["日期", "事项", "状态"], [
        ["11/17–11/18", "Tier A 矩阵、RQ3、B2 14/39/117、敏感性、位置/边界/多区间", "完成"],
        ["11/18", "数字冻结、复现包、论文初稿、投稿包、标注包", "完成"],
        ["11/19–11/22", "真实标注（进行中）/ 导师审阅", "进行中"],
        ["11/25", "导师修改稿", "待启动"],
        ["11/29", "内容冻结、语言润色、模板排版", "待做"],
        ["12/02", "SIVP 投稿", "目标"],
    ], [3.0, 10.5, 3.0])
    p(doc, "费用台账（截至 11/18）：CPU 3.4 h + GPU 17.16 h，按 65W/85W、¥0.6/kWh 估算约 ¥1.01；"
           "远程 GPU ¥0（未开启）；11/18 晚新增 CPU 小实验未单独计费。")

    # 10 交付
    h(doc, "10  交付物索引", 1)
    table(doc, ["类别", "文件"], [
        ["论文", "paper/manuscript_draft_2026-11-17.docx / .pdf（13 页）"],
        ["B2 报告", "报告/B2_All-In-One补充实验_2026-11-18.pdf；B2_长度扩展_2026-11-18.pdf"],
        ["RQ3 报告", "报告/RQ3_D1D2补充实验_2026-11-17.pdf；RQ3_扫描检测器补充_2026-11-18.pdf"],
        ["敏感性/位置", "报告/参数敏感性补充、位置敏感性、边界位置、边缘感知估计器"],
        ["多区间", "报告/多区间缺陷补充、三段多区间补充、多区间专用检测器补充"],
        ["标注", "标注/标注资料包_2026-11-18.zip（100 片段 + 5 题资格 + 模板 + 指南）"],
        ["复现包", "交付/复现包_2026-11-17.zip（464 文件 / 48.6 MB）"],
        ["投稿包", "投稿/投稿包_2026-11-18.zip"],
        ["冻结", "results/FREEZE_*.json"],
    ], [3.4, 13.0])
    doc.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
