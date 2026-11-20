"""Build the combined research report / reproducibility / journal-fit DOCX."""
from __future__ import annotations

import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.oxml import OxmlElement

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "报告", "研究报告与复现说明_2026-11-20.docx")


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
    trPr = t.rows[0]._tr.get_or_add_trPr(); th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    for i, x in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = ""
        r = c.paragraphs[0].add_run(str(x)); r.font.bold = True; r.font.size = Pt(size)
    for row in rows:
        cells = t.add_row().cells
        for i, x in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(x)); r.font.size = Pt(size)
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr(); cs = OxmlElement("w:cantSplit"); trPr.append(cs)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()


def fig(doc, path, caption, width=15.5):
    if not os.path.exists(path):
        return
    doc.add_picture(path, width=Cm(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = c.add_run(caption); r.font.size = Pt(8); r.font.italic = True


def main():
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.0); s.top_margin = s.bottom_margin = Cm(1.9)
    st = doc.styles["Normal"]; st.font.name = "宋体"; st.font.size = Pt(10.5)

    # cover
    for _ in range(5):
        doc.add_paragraph()
    t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("研究报告与复现说明"); r.font.size = Pt(26); r.font.bold = True; r.font.name = "Times New Roman"
    t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("已知区间局部亮度校正：实验、复现与期刊适配评估"); r.font.size = Pt(14)
    for _ in range(7):
        doc.add_paragraph()
    for line in ["ZHIKUN（50260258）", "2026-11-20", "目标期刊：Signal, Image and Video Processing（SIVP）"]:
        t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = t.add_run(line); r.font.size = Pt(12)
    doc.add_page_break()

    h(doc, "执行摘要", 1)
    p(doc, "本报告回答四个问题：（1）项目做了什么、得到什么；（2）如何复现；（3）这些成果是否支撑投 SIVP；"
           "（4）目前哪些已经落地、哪些还没有。")
    p(doc, "项目研究“已知缺陷区间”的视频亮度校正：给定区间，估计算法能否准确恢复区间亮度、同时不改变区间外像素，"
           "并分析检测误差如何传导为校正误差。实验覆盖 13 段、3 种注入、3 种长度、10 个确定性方法（1,170 条件），"
           "并补充 RQ3 检测、B2 All-In-One 深度基线（208 案例）、注入强度/位置/边界敏感性、2/3/4 段多区间与自然标注预实验。")
    p(doc, "核心结论（全 13 段口径）：A 注入下 A3 把区间 Y-MAE 从 19.90 降到 2.06/1.48/2.40；B 注入下 A3 仍有 8.16/7.65/8.07，"
           "A7f 为 1.46/1.48/1.45、A7 为 2.59/1.97/2.95；B′ 下 A7 为 2.11/1.48/2.50；局部写回 A3 区间外改动 0，全序列写回 A4 改动 33.2%；"
           "RQ3 主检测器测试集 len12 为 0.744/0.641，低于 0.90；B2 在 39 个平衡案例上 12.48 vs A3 4.84，但 outFrac 99.95%；"
           "自然标注上 CUSUM clip 召回只有 0.247，flicker 0/19。")
    p(doc, "期刊适配结论：SIVP 的 scope 与“受控实证 + 复现 + 视频处理”定位匹配度较高，成果数量与复现完整度足以支撑一次 Q3 投稿；"
           "但论文没有新网络/新 SOTA，RQ3 与自然标注结果偏弱，属于“可投、不能保证接收”的稿件，需要按边界性研究来写，"
           "不能包装成方法创新。")

    h(doc, "1  研究问题与贡献", 1)
    for x in [
        "RQ1：已知区间、受控注入下，确定性校正能把区间误差降到多少？哪些方法在 gamma 注入下更好？",
        "RQ2：局部写回与全序列写回在区间外保持、边界误差上的差异有多大？",
        "RQ3：不依赖注入标签，能否定位持续型亮度区间？测试集泛化如何？误差如何传导到校正？",
        "补充：深度盲基线 B2 在同一任务约束下表现如何？强度、位置、边界、多区间会改变结论吗？",
    ]:
        doc.add_paragraph(x, style="List Bullet")
    p(doc, "贡献：1,170 条件可复现基准（逐帧/配置/代码哈希）；局部 vs 全局写回与边界分解；gamma 削波归因；"
           "RQ3 先验边界与预注册测试；B2 深度基线；2/3/4 段多区间压力测试；完整复现包与投稿材料。")

    h(doc, "2  数据、注入与评价", 1)
    table(doc, ["项目", "设置"], [
        ["数据", "Blind-Video-Deflickering-Dataset 的 VideoDM/Meta 子集，13 段 × 76 帧 × 512×512，CC BY 4.0"],
        ["归档 SHA-256", "737252c0aa5f3a73972bec126c7edfe0ec7e19798dce6bc63eb4becd3ae0626e"],
        ["注入", "A：RGB 偏移 −20；B：码值 gamma 2.0；B′：gamma 1.3"],
        ["区间", "零基半开 [s,s+len)，主实验 s=30，len ∈ {1,4,12}"],
        ["方法", "A1–A9（含 A7f），10 个确定性实现；A3e 为边缘感知变体"],
        ["统计", "视频级聚类 bootstrap；精确/ Monte Carlo 符号翻转；Holm 校正"],
    ], [3.2, 12.8])
    p(doc, "gamma 注在码值上，不是物理显示 gamma；注入削波与校正削波严格分开记录。主实验的削波是校正侧（拉回亮度时高光撞 255）。")

    h(doc, "3  主要实验结果", 1)
    h(doc, "3.1  RQ1：区间重建（全 13 段）", 2)
    table(doc, ["方法", "A 1", "A 4", "A 12", "B 1", "B 4", "B 12", "B′ 1", "B′ 4", "B′ 12"], [
        ["A1 no-op", "19.90", "19.89", "19.90", "53.62", "53.68", "54.02", "20.49", "20.54", "20.63"],
        ["A2 median-7", "2.29", "18.26", "19.52", "8.55", "52.05", "53.66", "4.18", "18.83", "20.26"],
        ["A3 linear k=3", "2.06", "1.48", "2.40", "8.16", "7.65", "8.07", "3.92", "3.20", "4.03"],
        ["A5 STE", "2.02", "1.87", "3.09", "2.53", "2.40", "3.52", "2.12", "1.97", "3.16"],
        ["A7 adaptive γ", "3.37", "3.25", "3.81", "2.59", "1.97", "2.95", "2.11", "1.48", "2.50"],
        ["A7f fixed γ=2", "32.87", "33.02", "33.11", "1.46", "1.48", "1.45", "32.24", "32.39", "32.42"],
        ["A9 Kalman/RTS", "2.14", "1.98", "3.42", "8.35", "8.17", "8.75", "3.93", "3.79", "4.77"],
    ], [3.4] + [1.35] * 9)
    p(doc, "全 13 段口径（不是 3 段开发集）：A 注入 A3 为 2.06/1.48/2.40；B 注入 A3 8.16/7.65/8.07，"
           "A5 2.53/2.40/3.52，A7 2.59/1.97/2.95，A7f 1.46/1.48/1.45；B′ 注入 A7 2.11/1.48/2.50、A5 2.12/1.97/3.16、A3 3.92/3.20/4.03。"
           "结论：A 注入 A3 最优；B 注入 A7f 最优；B′ 注入 A7 最优；A5 是跨注入最稳的折中。A7 不是 gamma 的通用最优。")

    h(doc, "3.2  gamma 残差与削波", 2)
    p(doc, "B 注入的残差不是注入削波（gamma 变暗），而是校正把亮度拉回时高光撞 255。单帧校正削波比例："
           "sailboat 4.53%、book 5.38%、horse 3.43%；B′ 降到 1.79%/3.18%/1.28%，残差同步下降。"
           "tanh shoulder 能消除硬削波（2.57%→0%），但 Y-MAE 只从 8.164 降到 8.117——被裁掉的信息无法靠压缩恢复。"
           "正确表述是“加性偏移族的 gamma 残差以削波为主”，不是“任何方法都无法避免”。")

    h(doc, "3.3  RQ2：局部 vs 全序列写回", 2)
    table(doc, ["方法", "OutFrac(A,12)", "区间外 RGB", "边界误差"], [
        ["A2 local median-7", "0.00%", "0.00", "37.20"],
        ["A3 outside linear k=3", "0.00%", "0.00", "4.23"],
        ["A4 full-seq median-7", "33.2%", "0.91", "33.89"],
    ], [5.0, 3.2, 3.0, 3.0])
    p(doc, "A2/A4 共用估计器，只差写回范围：局部 0% 区间外改动，全局 33.2%，边界误差 33.89；"
           "A4 的误差几乎全是估计器偏差（33.9），不是区间外跳变（3.3）。")

    h(doc, "3.4  RQ3：检测与泛化", 2)
    table(doc, ["检测器", "R@1", "P@1", "R@4", "P@4", "R@12", "P@12", "Clean FP"], [
        ["Local median", "1.000", "0.104", "0.462", "0.144", "0.263", "0.210", "0.214"],
        ["BlazeBVD Eq.(5)", "1.000", "0.045", "0.686", "0.111", "0.280", "0.146", "0.328"],
        ["Global JS + hysteresis", "0.667", "0.052", "0.853", "0.289", "0.761", "0.499", "0.187"],
        ["Rolling JS + CUSUM", "0.846", "0.135", "0.897", "0.383", "0.825", "0.737", "0.100"],
    ], [4.8, 1.9, 1.9, 1.9, 1.9, 1.9, 1.9, 2.1])
    p(doc, "Eq.(5) 的失败不是单一机制：knight A 的分数在区间内升高，但被 local-mean 阈值压住（0/12）；"
           "其他序列则是平滑后只剩边缘。CUSUM 全 13 段 len12 为 0.825/0.737/0.690，但预注册测试集只有 0.744/0.641"
           "（95% CI 0.485–0.982），明显泛化差；h=6 也只有 0.762/0.673。论文因此不主张新检测器。")
    p(doc, "补充扫描检测器：固定候选长度时测试 len12 0.772/0.772/0.740，但 len1/4 跌到 0.370/0.630；"
           "未知长度扫描召回 0.787、精确率 0.561。多区间扫描的召回/命中更高，但精确率只有 0.50–0.55。")
    fig(doc, os.path.join(WS, "paper", "figures", "fig2_detection_scores.png"),
        "图 1  knight_A_len12：Eq.(5) 分数升高但被阈值压住（0/12）；CUSUM 覆盖 12/12。")

    h(doc, "3.5  B2 深度盲基线（208 案例）", 2)
    table(doc, ["设置", "案例", "A3", "A7", "B2", "B2 OutFrac"], [
        ["单区间 len12", "39", "4.84", "—", "12.48", "99.95%"],
        ["两区间", "52", "5.16", "3.20", "13.37", "99.95%"],
        ["三段", "26", "3.51", "3.31", "12.83", "99.98%"],
        ["四段", "13", "3.21", "2.77", "11.98", "99.98%"],
    ], [4.0, 2.0, 2.2, 2.2, 2.4, 2.8])
    p(doc, "B2 在所有段数下都明显劣于 A3/A7，且改动约 99.9% 的区间外像素。它不是在“已知区间 + 区间外保持”任务上的竞争者，"
           "而是任务差异的证据。117 案例长度扩展也显示 B2 随长度恶化。")

    h(doc, "3.6  敏感性、位置、边界与 A3e", 2)
    p(doc, "注入强度：A3 对偏移 −10/−20/−30 为 2.38/2.40/2.61，A2 为 9.61/19.52/29.35；gamma 1.3→2.5 时 A3 4.03→10.73，"
           "A7 2.50→3.38；A3 削波 0.80→2.46%，A7 0.12→0.71%。")
    p(doc, "位置：A3 在 start 10/30/50 为 1.91→2.59（A）、8.63→8.07→8.19（B）、3.83→4.25（B′），位置效应小于方法差距。")
    p(doc, "贴边：len1 start0 时 A3 9.41（中部 2.06），len12 结束于 76 时 6.49（中部 2.40）。A3e 用单侧外推把 start0 len1/len4 "
           "A 注入降到 3.06/1.56，把 start64 len12 B 降到 10.83，但未追平中部。")
    fig(doc, os.path.join(WS, "paper", "figures", "fig5_position.png"),
        "图 2  区间起点对 A3/A7 的影响（左：偏移 −20；右：γ=2）。")

    h(doc, "3.7  多区间缺陷（2/3/4 段）", 2)
    table(doc, ["场景", "方法", "Y MAE", "OutFrac", "检测召回"], [
        ["两区间", "A3", "1.68–2.25", "0%", "0.60–0.88"],
        ["两区间", "A7", "2.41–2.80", "0%", "同上"],
        ["三段 mixed", "A3 / A7", "4.92 / 2.79", "0%", "0.60"],
        ["四段 mixed", "A3 / A7", "3.21 / 2.77", "0%", "0.62"],
    ], [3.4, 3.0, 2.8, 2.2, 3.0])
    p(doc, "校正始终稳定、区间外 0%；检测始终差：CUSUM 召回 0.54–0.88，多区间扫描召回 0.77–0.93 但精确率 0.50–0.55，"
           "且四段只输出约 2.8 个 span。多区间检测是明确的开放问题。")

    h(doc, "3.8  自然标注预实验（单标注）", 2)
    p(doc, "100 个 24 帧干净片段，单标注 100/100，73 正例；类型 exposure 32 / flicker 19 / gamma 17 / other 5；"
           "帧号按 1-based 转 0-based；29/73 覆盖 ≥21 帧。")
    table(doc, ["指标", "值"], [
        ["clip 精确率 / 召回", "0.720 / 0.247"],
        ["区间召回", "0.101"],
        ["flicker clip 召回", "0.000（0/19）"],
        ["exposure / gamma", "0.281 / 0.412"],
    ], [6.0, 8.0])
    p(doc, "CUSUM 对自然 flicker 完全失效；自然片段没有干净参考，只评检测，不算校正 YMAE。这是单标注、无 kappa，"
           "论文按 limitations 写，不作为 headline。")

    h(doc, "3.9  论文主张与证据的对应", 2)
    table(doc, ["论文主张", "证据", "强度/边界"], [
        ["已知区间局部校正收益真实", "A 注入 A3 19.90→2.06/1.48/2.40（全 13 段）；B′ 20.63→4.03", "强；仅限加性偏移/gamma 族"],
        ["A3 不是普适最优", "B 注入 A3 8.16/7.65/8.07，A7f 1.46/1.48/1.45，A7 2.59/1.97/2.95；B 注入 A7f/A7/A5 均 13/13 胜 A3", "强；A→A3，B→A7f，B′→A7"],
        ["局部写回是任务约束", "A3 OutFrac 0%，A4 33.2%，边界 4.23 vs 33.89", "强；同一估计器只差范围"],
        ["RQ3 检测存在泛化差距", "全 13 段 0.825/0.737；预注册测试 0.744/0.641", "边界性发现；不能声称 0.90"],
        ["B2 与任务目标不同", "39 案例 12.48 vs 4.84，outFrac 99.95%；208 案例同向", "强；B2 非 SOTA 排名"],
        ["多区间校正可扩展、检测不可扩展", "2/3/4 段 A3 1.68–5.16，OutFrac 0%；CUSUM 0.54–0.88，四段扫描仅 2.8 span", "校正强；检测开放"],
        ["自然 flicker 未被覆盖", "100 片段、73 正例；CUSUM clip 0.247，flicker 0/19，区间 0.101", "单标注、无 kappa；仅作 limitations"],
    ], [4.2, 8.4, 4.2])

    h(doc, "3.10  检测→校正端到端", 2)
    table(doc, ["方法", "Oracle Y-MAE", "Detected Y-MAE", "检测代价", "Detected OutFrac"], [
        ["A3", "4.47", "7.57", "+3.10", "4.0%"],
        ["A5", "2.67", "5.66", "+2.99", "4.6%"],
        ["A7", "2.66", "5.85", "+3.19", "3.9%"],
        ["A7f", "22.31", "21.60", "−0.71", "5.5%"],
    ], [2.4, 3.2, 3.2, 2.8, 3.2])
    p(doc, "CUSUM 预测 span 代替真实区间后，校正误差被放大 1.4–3.0 倍：A3 在 A/B/B′ 注入下从 1.94/7.86/3.62 升到 4.86/10.60/7.25；"
           "预测 span 还会改动真实区间外 3.9%–5.5% 的像素。检测不确定时 A5 的 detected 均值 5.66 最好，A7 5.85，A3 7.57——"
           "与 oracle 下 A3 最好相反，说明“选型要看检测质量”。A7f 只对 B 有效，不能当通用方法。")

    h(doc, "4  复现做法", 1)
    p(doc, "复现包 `交付/复现包_2026-11-17.zip` 包含代码、配置、15+ 个 run 的 CSV/JSON/manifest、报告、可视化、"
           "投稿材料、冻结文件与校验和；不含 2.4GB 原始帧和 All-In-One 权重，按官方地址获取。")
    table(doc, ["步骤", "命令/说明"], [
        ["环境", "Windows 10/11，Python 3.12；numpy/pandas/Pillow/openpyxl；B2 需 torch 2.11+cu128，RTX 5060 8GB"],
        ["数据", "下载 All-In-One-Deflicker-Dataset.zip（SHA-256 737252c0…0626e），按 manifest 解出 13 段 76 帧"],
        ["一键测试", "包内 `一键测试.ps1`：37 项单元测试 + 37 项冻结检查"],
        ["重算表格", "包内 `一键重算表格.ps1`：只读现有 run，重写报告/表格"],
        ["Tier A", "python project/scripts/run_matrix.py --config project/configs/matrix.json --run-id tierA_matrix_v1（约 45 分钟 CPU）"],
        ["RQ3", "run_detection.py / run_detection_d1d2.py / run_threshold_selection.py"],
        ["B2", "run_b2_full_matrix.py / run_b2_multi.py / run_b2_three.py / run_b2_four.py；每案例约 9 分钟 GPU"],
        ["评测", "eval_all_in_one.py / eval_b2_multi.py / eval_b2_three.py / eval_b2_four.py"],
        ["报告", "build_report.py / build_rq3_supplement.py / build_b2_*.py / build_repro_package.py"],
    ], [3.0, 13.0])
    p(doc, "复现验证：包内一键测试实测 37 项测试 OK + 37 项冻结 PASS；validator 抽样重算 12/12 PASS；"
           "论文表/图审计 PASS；跨文档旧数字审计 0 命中。")
    p(doc, "耗时与磁盘：Tier A 约 45 分钟 CPU；B2 每案例约 8.7 分钟 GPU + 12 秒 stage2；B2 中间文件很大，"
           "Full 117 案例曾把 212GB 磁盘写满，复现时需预留 ≥100GB 或及时清理 stage_1/neural_filter。")

    h(doc, "4.1  复现包目录", 2)
    p(doc, "包根目录下按“代码 / 配置 / 结果 / 论文 / 报告 / 投稿”组织；所有 run 目录都带 summary.json 与 per-condition CSV，"
           "冻结文件在 results/ 根下，校验和清单在包根。")
    for line in [
        "复现包_2026-11-17/",
        "  README.md                    包说明、快速开始、已知限制",
        "  requirements.txt             固定版本依赖",
        "  一键测试.ps1                 37 项单元测试 + 37 项冻结检查",
        "  一键重算表格.ps1             只读 run，重写报告/表格",
        "  MANIFEST.sha256              全部文件校验和",
        "  project/src/luma_corr/       校正、检测、注入、指标、统计",
        "  project/scripts/             run_matrix / run_detection / run_b2_* / eval_*",
        "  project/configs/             matrix、RQ3 threshold、B2 配置",
        "  results/runs/                tierA_matrix_v1、rq3_*、b2_*、multi_*、edge_*",
        "  results/FREEZE_*.json        主冻结 + 15 个独立冻结",
        "  paper/                       manuscript.docx / .pdf、图、引用",
        "  报告/                        执行报告与各补充报告",
        "  投稿/                        投稿包与检查清单",
    ]:
        par = doc.add_paragraph(); r = par.add_run(line); r.font.name = "Consolas"; r.font.size = Pt(8)

    h(doc, "4.2  论文表格到 run 的对应", 2)
    table(doc, ["论文表/图", "数据来源", "重算入口"], [
        ["RQ1 主表", "results/runs/tierA_matrix_v1/per_sequence.csv", "run_matrix.py → make_tables.py"],
        ["RQ2 写回表", "tierA_matrix_v1 的 A2/A3/A4 行", "make_tables.py"],
        ["RQ3 检测表", "rq3_detection_v1 / rq3_detection_v2", "run_detection.py → build_rq3_supplement.py"],
        ["B2 单区间表", "b2_len12_v1、b2_full_v1", "run_b2_full_matrix.py → eval_all_in_one.py"],
        ["B2 多区间表", "b2_multi_v1 / b2_three_v1 / b2_four_v1", "run_b2_*.py → eval_b2_*.py"],
        ["敏感性/位置/边界", "sensitivity_* / position_* / edge_* / edge_aware_*", "对应 run_matrix 配置 + 报告脚本"],
        ["多区间校正/检测", "multi_interval_v1 / multi_mixed_v1 / multi_four_v1 / multi_scan_*", "run_multi_*.py"],
        ["自然标注表", "natural_detection_v3", "run_natural_detection.py → build_natural_final_report.py"],
    ], [3.6, 8.0, 5.2])

    h(doc, "4.3  常见失败与处理", 2)
    for x in [
        "MPLCONFIGDIR 被沙箱拒绝：设置 MPLCONFIGDIR 到工作区可写目录。",
        "torch.load 默认 weights_only 报错：B2 兼容补丁显式传 weights_only=False。",
        "B2 在 10000 iter 不产出：配置改为 10001，使 eval 在 10000 步触发。",
        "B2 中间文件写满磁盘：只保留 final/output，删除 stage_1 / neural_filter / data/test；Full 117 案例曾占 100GB+。",
        "视频/图像编码依赖 imageio_ffmpeg：把 third_party/pylibs 加入 PYTHONPATH。",
        "冻结失败先看 verify_numbers 报的字段；多数是聚合口径（选中 vs 基线）或四舍五入差异。",
    ]:
        doc.add_paragraph(x, style="List Bullet")

    h(doc, "5  成果落地清单", 1)
    table(doc, ["类别", "产物", "状态"], [
        ["数字冻结", "FREEZE_2026-11-17 + 15 个独立冻结（B2 117/52/26/13、RQ3 扫描、多区间 2/3/4、边界、A3e、自然）", "全部 PASS"],
        ["论文", "manuscript_draft_2026-11-17.docx / .pdf（13 页、5 表、3 图、41 引用）", "初稿完成"],
        ["复现包", "交付/复现包_2026-11-17.zip（575 文件 / 57 MB）", "一键测试 PASS"],
        ["投稿包", "投稿/投稿包_2026-11-18.zip（36 文件 / 6.1 MB）", "材料齐"],
        ["标注", "100 片段 + 5 题资格 + 模板 + 指南；单标注 100/100", "完成（无第二标注者）"],
        ["报告", "执行报告、RQ3 补充、B2 系列、敏感性/位置/边界/多区间/自然标注", "完成"],
    ], [2.6, 11.0, 3.0])

    h(doc, "5.1  已落地与未落地", 2)
    table(doc, ["已落地", "未落地/边界"], [
        ["1,170 条件 Tier A、10 个方法、3 种注入", "没有新网络/新 SOTA；B1 代码未公开，B3–B5 无权重"],
        ["208 个 B2 案例（单/两/三/四段）", "B2 只跑 512×512、10,001 iter、down=4；非逐位复现"],
        ["RQ3 全 13 段 + 预注册测试 + 扫描/多区间", "测试集 0.744；自然 flicker 0/19；检测未解决"],
        ["强度/位置/边界/A3e 压力测试", "只测一种四段布局；更多布局未测"],
        ["100 片段单标注 + 资格测试 + 指南", "无第二标注者、无 kappa；016/018/091/099/100 为保守处理"],
        ["主冻结 37/37 + 15 个独立冻结", "冻结是“数字一致”，不是“结论正确”"],
        ["论文 13 页 + 5 表 + 3 图 + 41 引用", "不是 SIVP 模板稿；作者/基金/润色/查重未做"],
        ["复现包 575 文件 / 57 MB + 一键测试", "不含原始帧与 B2 权重；需外网下载"],
    ], [7.5, 8.5])

    doc.add_page_break()
    h(doc, "6  是否支撑投 SIVP：评估", 1)
    table(doc, ["维度", "评估", "说明"], [
        ["Scope 匹配", "高", "SIVP 覆盖图像/视频处理与应用；受控基准、视频亮度校正、复现研究都在范围内。"],
        ["新颖性", "中", "不是新网络/新 SOTA；贡献是受控实证、局部 vs 全局、削波归因、检测-校正误差传导、复现包。"],
        ["证据强度", "较强", "1,170 条件 + 208 个 B2 案例 + 2/3/4 段多区间 + 强度/位置/边界；冻结与审计完整。"],
        ["复现性", "强", "逐帧/配置/代码哈希；一键包；37 测试 + 37 冻结；validator 抽样。"],
        ["主要弱点", "明显", "RQ3 测试 0.744；自然 flicker 0/19；单标注无 kappa；13 段、合成注入；B2 非逐位复现。"],
        ["SIVP 适配", "中高", "可投，属于“实证/复现型 Q3 尝试”，不能保证接收。"],
    ], [2.8, 2.2, 12.0])
    p(doc, "判断：**这些成果足以支撑一次 SIVP 投稿，但不构成“稳过”**。原因是论文的强项在实验完整性、复现性和边界分析，"
           "弱项在方法新颖性与自然场景泛化；审稿人很可能要求补真实数据、双标注或更强的检测器。按当前定位写，"
           "是诚实且有辨识度的 Q3 稿件；如果包装成“新方法/新 SOTA”，反而容易被拒。")
    p(doc, "审稿人最可能问的四个问题及现有回答：")
    for x in [
        "为什么没有和 SOTA 比？→ B2 官方权重已跑 208 案例；B1 代码未公开，B3–B5 无权重；且任务是已知区间保持，不是盲去闪烁排名。",
        "检测召回只有 0.744？→ 预注册测试集如实报告，全 13 段 0.825 只作上限；扫描/多区间扫描作为补充，未在测试集调参。",
        "合成注入不真实？→ 已有 100 片段自然标注预实验；但只有单标注，且自然 flicker 检测失败，已写 limitations。",
        "A3 不是最优（A7 更好）？→ 论文明确写 A3 非普适最优；B 注入 A7f/A7/A5 均 13/13 胜 A3；A7 不是 B 最优（A7f 1.46 vs A7 2.59）。",
    ]:
        doc.add_paragraph(x, style="List Bullet")
    p(doc, "建议：按 SIVP 投，定位为“controlled empirical + reproducibility + boundary findings”；不要改标题去承诺新方法。"
           "若审稿人要求方法创新，备选是扩展为“多区间专用检测器”或“边缘感知校正”的完整方法论文，但 12/02 前来不及。")

    h(doc, "6.1  支撑 SIVP 的点", 2)
    for x in [
        "Scope：SIVP 接收信号/图像/视频处理与应用型实证；受控基准、局部校正、检测-校正链路都在范围内。",
        "证据量：1,170 条件 + 208 个 B2 案例 + 2/3/4 段多区间，超过一般 Q3 实证稿的实验量。",
        "复现性：逐帧/配置/代码哈希、37 项测试、37 项冻结、validator 抽样；这是 SIVP 审稿的加分项。",
        "边界性发现：RQ3 0.744、自然 flicker 0/19、多区间检测不扩展，都是可发表的负结果/边界结果，不是硬伤。",
        "写作诚实：明确 A3 非最优、B2 非 SOTA、单标注无 kappa；审稿人不容易抓“过度声明”。",
    ]:
        doc.add_paragraph(x, style="List Bullet")

    h(doc, "6.2  不支撑/可能被拒的点", 2)
    for x in [
        "没有新方法：审稿人若按“方法创新”标准，会认为贡献不足；这是最大风险。",
        "RQ3 测试 0.744 低于论文自己设的 0.90；虽然如实报告，但会被追问“为什么不再改检测器”。",
        "自然标注单标注、无 kappa、flicker 0/19；真实场景证据弱，审稿人可能要求补双标注。",
        "13 段、合成注入、512×512；外部有效性有限。",
        "B2 只跑官方默认配置，不是逐位复现；审稿人可能要求更多 baseline。",
    ]:
        doc.add_paragraph(x, style="List Bullet")

    h(doc, "6.3  投稿策略", 2)
    p(doc, "定位：把论文写成“known-interval local correction 的受控实证 + 可复现基准 + 边界发现”，不要写成“新去闪烁网络”。"
           "标题/摘要突出 controlled、reproducible、boundary；贡献列 5 条，方法创新只占 1 条。")
    p(doc, "Cover letter 主动说明：B2 是 blind global baseline，不作为 SOTA 排名；RQ3 测试 0.744 是预注册结果；"
           "自然标注是单标注 preliminary。主动交代比被审稿人发现更好。")
    p(doc, "如果被拒：优先补“多区间专用检测器”或“边缘感知 + 多区间联合校正”的方法稿，而不是把现稿反复投；"
           "现稿的实验/复现资产可以复用到方法稿。")

    h(doc, "7  风险、时间与费用", 1)
    table(doc, ["日期", "事项", "状态"], [
        ["11/20", "实验/冻结/论文/复现包/自然标注", "完成"],
        ["11/21–11/22", "作者信息、模板、参考文献样式", "待做"],
        ["11/23–11/24", "英文润色、查重", "待做"],
        ["11/25", "导师修改稿（G4）", "目标"],
        ["11/29", "内容冻结（G5）", "目标"],
        ["12/02", "SIVP 投稿（G6）", "目标"],
    ], [3.0, 10.5, 3.0])
    p(doc, "费用：CPU 约 5 小时、GPU 约 30 小时（按 B2 stage 实测累计），按 65W/85W、¥0.6/kWh 估算约 **¥1.8**；"
           "远程 GPU ¥0；LLM/平台账单未暴露。旧台账 ¥1.01 未包含 11/18 后的多区间与自然实验。")

    doc.add_page_break()
    h(doc, "8  交付物索引", 1)
    table(doc, ["类别", "路径"], [
        ["论文", "paper/manuscript_draft_2026-11-17.docx / .pdf"],
        ["复现包", "交付/复现包_2026-11-17.zip"],
        ["投稿包", "投稿/投稿包_2026-11-18.zip"],
        ["冻结", "results/FREEZE_*.json"],
        ["B2 报告", "报告/B2_All-In-One补充实验_2026-11-18；B2_长度扩展；B2_两区间/三段/四段"],
        ["RQ3 报告", "报告/RQ3_D1D2补充实验；RQ3_扫描检测器补充；自然标注_单标注"],
        ["多区间", "报告/多区间缺陷、三段、四段、专用检测器"],
        ["标注", "标注/标注资料包_2026-11-18.zip；标注/回收/标注_最终_确认_2026-11-20.csv"],
    ], [3.0, 13.0])

    h(doc, "9  冻结清单", 1)
    table(doc, ["冻结文件", "检查内容", "状态"], [
        ["FREEZE_2026-11-17.json", "37 项头条数字", "PASS"],
        ["FREEZE_B2_FULL_2026-11-18.json", "117 案例 / 351 行", "PASS"],
        ["FREEZE_RQ3_SCAN_2026-11-18.json", "117 条件", "PASS"],
        ["FREEZE_MULTI_INTERVAL_2026-11-18.json", "156 行", "PASS"],
        ["FREEZE_MULTI_MIXED_2026-11-18.json", "78 行", "PASS"],
        ["FREEZE_EDGE_2026-11-18.json", "936 行", "PASS"],
        ["FREEZE_MULTI_SCAN_2026-11-18.json", "52 行", "PASS"],
        ["FREEZE_EDGE_AWARE_2026-11-18.json", "702 行", "PASS"],
        ["FREEZE_MULTI_SCAN_THREE_2026-11-18.json", "26 行", "PASS"],
        ["FREEZE_B2_MULTI_2026-11-19.json", "208 行", "PASS"],
        ["FREEZE_B2_THREE_2026-11-19.json", "104 行", "PASS"],
        ["FREEZE_MULTI_FOUR_2026-11-19.json", "78 行", "PASS"],
        ["FREEZE_B2_FOUR_2026-11-19.json", "52 行", "PASS"],
        ["FREEZE_MULTI_SCAN_FOUR_2026-11-19.json", "26 行", "PASS"],
        ["FREEZE_NATURAL_PRE_2026-11-19.json", "95 行（已被 v3 取代）", "PASS"],
        ["FREEZE_NATURAL_SINGLE_2026-11-20.json", "100 行，单标注/no-inter-rater", "PASS"],
    ], [7.2, 6.0, 2.6])

    h(doc, "10  复现检查清单", 1)
    for x in [
        "环境：Python 3.12；numpy/pandas/Pillow/openpyxl/pytest；B2 另需 torch 2.11+cu128 与 CUDA。",
        "数据：按 README 下载归档，核对 SHA-256；解出 13 段 × 76 帧 × 512×512。",
        "一键测试：在包根运行 `一键测试.ps1`，应看到 37 tests OK + 37 freeze PASS。",
        "关键表：先跑 `run_matrix.py`，再跑 `make_tables.py`；RQ3/B2 各自 run → eval → build 报告。",
        "冻结：任何数字改动后必须重跑对应 verify_*.py，生成新 freeze；不要手改 JSON。",
        "磁盘：B2 每案例约 300MB 中间文件；Full 117 案例需 ≥100GB，跑完只留 final/output。",
        "已知例外：B1 代码未公开；B3–B5 无权重；B2 非逐位复现；原始帧/权重不入包。",
    ]:
        doc.add_paragraph(x, style="List Bullet")

    h(doc, "11  一页结论", 1)
    p(doc, "这个项目已经完成了一个可复现的受控实证：校正方法在已知区间上有效、局部写回是任务约束、gamma 残差主要来自削波；"
           "检测在预注册测试集只有 0.744，自然 flicker 0/19，多区间检测不扩展。这些结果足以支撑一篇诚实的 Q3 实证/复现论文，"
           "但不足以支撑“新 SOTA 方法”的声明。")
    p(doc, "对 SIVP：scope 匹配、证据量足够、复现完整，属于“可投、不能保证接收”；最大风险是方法新颖性与自然场景证据。"
           "按当前边界性定位投稿，比包装成新方法更稳。")

    doc.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
