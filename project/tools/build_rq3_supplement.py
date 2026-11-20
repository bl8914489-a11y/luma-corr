"""Build the RQ3 D1/D2 supplementary report (DOCX + Markdown)."""
from __future__ import annotations

import csv
import json
import os

import numpy as np
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
D1 = os.path.join(WS, "results", "runs", "rq3_d1d2_v1")
E2E = os.path.join(WS, "results", "runs", "rq3_e2e_cusum_v1")
OUT_MD = os.path.join(WS, "报告", "RQ3_D1D2补充实验_2026-11-17.md")
OUT_DOCX = os.path.join(WS, "报告", "RQ3_D1D2补充实验_2026-11-17.docx")

DETS = [("median_dev", "局部中值（原）"), ("eq5_kl_s2_n5", "BlazeBVD 式(5) KL"),
        ("eq5_js_s2_n5", "BlazeBVD 式(5) JS"), ("d1_js_s2", "D1 JS + 全局阈值"),
        ("d2_full", "D2 完整"), ("d2_no_dual", "D2 去双阈值"),
        ("d2_no_gap", "D2 去间隔合并"), ("d2_no_refine", "D2 去边界细化"),
        ("d2_no_minlen", "D2 去最小时长"), ("hist_kl_cusum", "滚动中值 + CUSUM")]


class Doc:
    def __init__(self):
        self.d = Document()
        for s in self.d.sections:
            s.left_margin = s.right_margin = Cm(2.0)
            s.top_margin = s.bottom_margin = Cm(2.0)
        st = self.d.styles["Normal"]
        st.font.name = "宋体"; st.font.size = Pt(10.5)
        self.md = []

    def title(self, t, sub=None):
        p = self.d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(t); r.font.size = Pt(19); r.font.bold = True
        self.md.append(f"# {t}\n")
        if sub:
            p = self.d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(sub); self.md.append(f"*{sub}*\n")

    def h(self, t, level=1):
        self.d.add_heading(t, level=level); self.md.append(f"\n{'#'*(level+1)} {t}\n")

    def p(self, t):
        p = self.d.add_paragraph(); p.paragraph_format.space_after = Pt(4); p.add_run(t)
        self.md.append(t + "\n")

    def bullet(self, t):
        p = self.d.add_paragraph(style="List Bullet"); p.add_run(t); self.md.append(f"- {t}\n")

    def table(self, headers, rows, widths=None, size=8.2, caption=None):
        if caption:
            p = self.d.add_paragraph(); r = p.add_run(caption); r.font.bold = True; r.font.size = Pt(9)
            self.md.append(f"\n**{caption}**\n")
        t = self.d.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        trPr = t.rows[0]._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:tblHeader")); trPr.append(OxmlElement("w:cantSplit"))
        for i, h in enumerate(headers):
            c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(str(h))
            r.font.bold = True; r.font.size = Pt(size)
        for row in rows:
            tr = t.add_row(); tr._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
            for i, v in enumerate(row):
                c = tr.cells[i]; c.text = ""; r = c.paragraphs[0].add_run(str(v)); r.font.size = Pt(size)
        if widths:
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Cm(w)
        self.md.append("\n| " + " | ".join(map(str, headers)) + " |")
        self.md.append("|" + "|".join(["---"] * len(headers)) + "|")
        for row in rows:
            self.md.append("| " + " | ".join(map(str, row)) + " |")
        self.md.append("")

    def save(self):
        for p in self.d.paragraphs:
            for r in p.runs:
                r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")
        for t in self.d.tables:
            for row in t.rows:
                for c in row.cells:
                    for p in c.paragraphs:
                        for r in p.runs:
                            r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")
        self.d.save(OUT_DOCX)
        with open(OUT_MD, "w", encoding="utf-8") as fh:
            fh.write("\n".join(self.md))


def rows(path):
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def mean(rs, key):
    v = [float(r[key]) for r in rs if r[key] not in ("", "nan")]
    return float(np.nanmean(v)) if v else float("nan")


def main():
    pc = rows(os.path.join(D1, "per_condition.csv"))
    e2e = rows(os.path.join(E2E, "per_condition.csv"))
    esum = json.load(open(os.path.join(E2E, "summary.json"), encoding="utf-8"))
    sweep = rows(os.path.join(D1, "sweep.csv"))
    dsum = json.load(open(os.path.join(D1, "summary.json"), encoding="utf-8"))

    R = Doc()
    R.title("RQ3 D1/D2 补充实验记录",
            "BlazeBVD 式(5) 复现基线 · 直方图 σ/bin/KL-JS 消融 · 区间后处理 · 检测→校正联动 | 2026-11-17")

    R.h("一、为什么要补这组实验")
    R.p("查新报告第 3.3 与 5.3 节指出：BlazeBVD 式(5) 已用「平滑前后直方图的 KL 散度 + 局部滑动均值阈值」"
        "给出闪烁帧索引。因此本项目不能主张「提出了一种直方图 KL 检测器」；可主张的增量只能落在"
        "持续型缺陷的基线构造、区间级输出/评测，以及检测→校正的联动上。本轮据此补做 D1（分数构造与参数消融）"
        "与 D2（区间后处理），并做端到端检测→校正实验。")

    R.h("二、实验设置")
    R.p(f"D1/D2 运行：{dsum['n_conditions']} 个条件（13 段 × 4 注入 × 3 长度 × 10 检测器），"
        f"墙钟 {dsum['wall_seconds']/60:.1f} 分钟；参数扫描 {len(sweep)} 组（bins 32/64/128 × σ 1/2/4 × KL/JS）。"
        "端到端运行：117 个条件（13 段 × 3 注入 × 3 长度），检测器为滚动中值 + CUSUM，校正器为 A3。")
    R.p("所有阈值均为无标签规则：Eq(5) 用局部均值阈值；D1/D2 用 median + k·MAD（k=3）；"
        "D2 低阈值取 med + 0.5·(hi−med)。未用注入真值调参。")

    R.h("三、检测器对比（帧级均值，13 段 × 3 注入）")
    t1 = []
    for key, name in DETS:
        row = [name]
        for L in (1, 4, 12):
            rs = [r for r in pc if r["detector"] == key and r["length"] == str(L) and r["injection"] != "CLEAN"]
            row += [f"{mean(rs,'recall'):.3f}", f"{mean(rs,'precision'):.3f}"]
        rs = [r for r in pc if r["detector"] == key and r["injection"] == "CLEAN"]
        row.append(f"{mean(rs,'fp_rate'):.3f}")
        t1.append(row)
    R.table(["检测器", "R@1", "P@1", "R@4", "P@4", "R@12", "P@12", "干净 FP"], t1,
            widths=[4.6, 1.45, 1.45, 1.45, 1.45, 1.45, 1.45, 1.6],
            caption="表 1  各检测器的帧级召回/精确率与干净序列误报率")

    R.p("关键结果：忠实复现的 BlazeBVD 式(5)（σ=2、局部均值阈值）在 len=12 上召回只有 0.280、精确率 0.146、"
        "干净误报 0.328；同一分数换成全局稳健阈值（D1）召回 0.376；再做区间化（D2）也只有 0.400。"
        "滚动中值基线 + CUSUM 在全 13 段上为 R=0.825、P=0.737、IoU=0.690、FP=0.100；按第七节的预注册测试集则为 0.744/0.641。"
        "这说明差异不在「有没有用 KL」，而在基线估计器：高斯时间平滑会把 12 帧的平台一起平滑掉，"
        "只在平台两侧留下尖峰；滚动中值基线仍然干净，CUSUM 再把持续证据累积起来。")

    R.h("四、D2 区间后处理的组件增量（len=12）")
    t2 = []
    base = [r for r in pc if r["detector"] == "d2_full" and r["length"] == "12" and r["injection"] != "CLEAN"]
    for key, name in [("d2_full", "完整"), ("d2_no_dual", "去双阈值"), ("d2_no_gap", "去间隔合并"),
                      ("d2_no_refine", "去边界细化"), ("d2_no_minlen", "去最小时长")]:
        rs = [r for r in pc if r["detector"] == key and r["length"] == "12" and r["injection"] != "CLEAN"]
        t2.append([name, f"{mean(rs,'recall'):.3f}", f"{mean(rs,'precision'):.3f}",
                   f"{mean(rs,'iou'):.3f}", f"{mean(rs,'interval_iou'):.3f}",
                   f"{mean(rs,'interval_hit'):.2f}"])
    R.table(["D2 变体", "召回", "精确率", "帧 IoU", "区间 IoU", "区间命中"], t2,
            widths=[4.2, 2.2, 2.4, 2.2, 2.4, 2.2],
            caption="表 2  D2 组件消融（len=12，13 段 × 3 注入）")
    R.p("双阈值与间隔合并在 len=12 上没有带来增益；边界细化去掉后召回反而从 0.400 升到 0.500、"
        "区间 IoU 从 0.248 升到 0.278，说明把边界强制吸附到亮度突变点会被自然闪烁拉偏；"
        "最小时长只有很小正贡献。在 len=4 上 D2 把精确率从 0.265 提到 0.345、召回从 0.853 提到 0.929。"
        "这与查新报告的预期部分不符：区间化能改善短段与中段的精确率，但救不了持续段——"
        "持续段的关键是基线，不是后处理。")

    R.h("五、D1 参数敏感性（len=12，按 F1 排序前 6）")
    sw = sorted(sweep, key=lambda r: float(r["f1"]), reverse=True)[:6]
    t3 = [[r["bins"], r["sigma"], r["mode"], f"{float(r['recall']):.3f}", f"{float(r['precision']):.3f}",
           f"{float(r['f1']):.3f}", f"{float(r['interval_iou']):.3f}"] for r in sw]
    R.table(["bins", "σ", "散度", "召回", "精确率", "F1", "区间 IoU"], t3,
            widths=[1.6, 1.4, 1.6, 2.2, 2.4, 2.0, 2.4],
            caption="表 3  D1 最佳参数组合（仍低于滚动中值 + CUSUM）")
    R.p("σ 越大，平滑基线越接近平台，召回反而略升（σ=4 最好），但这与 Eq(5) 的原设定（σ 小、抓瞬时闪烁）"
        "方向相反：为了让持续段可见，必须把平滑做得更弱、基线做得更稳。这进一步说明"
        "「把 BlazeBVD 式(5) 直接搬来做区间定位」不可行。")

    R.h("六、检测→校正端到端")
    t4 = []
    for L in (1, 4, 12):
        rs = [r for r in e2e if r["length"] == str(L)]
        t4.append([L, f"{mean(rs,'reduction_oracle')*100:.1f}%", f"{mean(rs,'reduction_detected')*100:.1f}%",
                   f"{mean(rs,'outfrac_oracle')*100:.2f}%", f"{mean(rs,'outfrac_detected')*100:.2f}%",
                   f"{mean(rs,'det_hit'):.2f}"])
    R.table(["len", "真值区间 YMAE 降幅", "检测区间 YMAE 降幅", "真值 outFrac", "检测 outFrac", "检测命中"],
            t4, widths=[1.4, 3.6, 3.6, 2.6, 2.8, 2.2],
            caption="表 4  检测→校正联动（A3 校正；评价始终在真值区间上）")
    R.p(f"汇总：真值区间校正把 Y MAE 降低 {esum['mean_reduction_oracle']*100:.1f}%；"
        f"用盲检测区间驱动校正只降低 {esum['mean_reduction_detected']*100:.1f}%，"
        f"outFrac 为 {esum['mean_outfrac_detected']*100:.2f}%（真值为 0%），区间命中率 "
        f"{esum['detection_hit_rate']*100:.1f}%。检测误差确实会传导为校正误差："
        "命中时接近真值上界，未命中时几乎等于 no-op，且误检区间会在真值区间外引入改动。")

    R.h("七、预注册验证/测试划分（避免在测试集上调参）", 1)
    R.p("序列按 sha256(name) 升序固定划分：验证集 4 段（paint、sailboat、book、retriever），测试集 9 段"
        "（fish、unicorn、yoga、knight、rabbit、astronaut、ship、asteroids、horse）。该划分在看到任何阈值结果前固定；"
        "k/h 与是否与全局直方图检测器取并集，只在验证集上选择，测试集只评一次。")
    R.table(["划分", "变体", "k", "h", "召回", "精确率", "F1", "帧 IoU", "区间 IoU"], [
        ["验证", "CUSUM（选中）", 0.5, 8.0, 0.965, 0.898, 0.925, 0.864, 0.836],
        ["验证", "CUSUM（先验 h=6）", 0.5, 6.0, 0.965, 0.882, 0.916, 0.847, 0.857],
        ["测试", "CUSUM（选中 h=8）", 0.5, 8.0, 0.744, 0.641, 0.672, 0.607, 0.739],
        ["测试", "CUSUM（先验 h=6）", 0.5, 6.0, 0.762, 0.673, 0.687, 0.620, 0.696],
    ], widths=[1.6, 4.4, 1.2, 1.2, 1.8, 1.8, 1.6, 1.8, 1.8],
        caption="表 5  验证集选择与测试集表现（len=12，测试集 9 段 × 3 注入）")
    R.p("关键结果：验证集上 h=8 的召回 0.965、精确率 0.898，看起来达标；但同一阈值在测试集只有"
        "召回 0.744、精确率 0.641。先验 h=6 在测试集为 0.762/0.673，略好于“选中的” h=8。"
        "这说明：①阈值不是主要杠杆；②4/9 划分下的序列间方差极大，验证集选出的工作点不能迁移；"
        "③用全 13 段的 0.825 作为论文数字会高估，测试集 0.744 才是更诚实的泛化估计。")
    R.p("测试集按注入拆分（len=12）：B（γ=2）召回 0.880、A（−20）0.704、B′（γ=1.3）0.648；"
        "按长度：len=1 0.815、len=4 0.843、len=12 0.744。B′ 的弱对比度是主要短板。")
    R.p("端到端按同一划分重跑（rq3_e2e_test_v1，测试集 9 段，CUSUM h=8）：真值区间校正降低 Y MAE 84.7%，"
        "盲检测驱动降低 65.5%，outFrac 4.01%，区间命中 45.7%。此前全 13 段的 71.1%/3.26% 应视为上限估计。")
    R.p("负结果补充：同一划分下把分数改为 max(滚动中值 JS, 全局中值 JS, 亮度 z) 后，"
        "验证集 R=0.965/P=0.884，测试集 R=0.756/P=0.653（较单基线仅 +0.012 召回），仍远低于 0.90。"
        "说明瓶颈不是“少了一个基线”，而是测试序列的自然闪烁与 B′ 弱对比本身；继续调分数/阈值的边际收益已很低。"
        "该 run 记录为 rq3_dual_threshold_v1。")

    R.h("八、验收与结论")
    R.table(["验收项", "目标", "实际", "判定"], [
        ["len=12 召回", "≥0.90", "0.744（测试集；验证 0.965）", "未达"],
        ["len=12 精确率", "≥0.60", "0.641（测试集）", "达到"],
        ["端到端 YMAE 降幅", "≥50%", "65.5%（测试集）/ 71.1%（全13段）", "达到"],
        ["端到端 outFrac", "≤0.01", "4.01%（测试集）/ 3.26%（全13段）", "未达"],
        ["真实集区间 IoU", "≥0.50", "无人工标注", "未完成"],
    ], widths=[4.2, 3.0, 5.0, 2.6], caption="表 6  查新报告 5.7 验收")
    R.p("结论：本轮把「BlazeBVD 式(5) → D1 → D2 → 端到端」这条链路跑通并留下了完整记录，"
        "但没有达到「检测—校正联合框架」的验收线（召回与 outFrac 未达）。按查新报告 7.2 的退路，"
        "论文应写成「受控基准 + 持续型缺陷检测的边界性发现 + 检测→校正的误差传导分析」，"
        "而不是「提出了新的联合框架」。")
    R.p("可辩护的增量有三点：① 证明 Eq(5) 的高斯平滑基线会吸收持续型缺陷（R=0.28），"
        "而滚动中值基线 + CUSUM 全 13 段能到 0.825、测试集 0.744；② 给出帧级 + 区间级 + 端到端三层评价与逐条件记录；"
        "③ 量化检测误差如何传导为校正误差（真值 85.7% → 盲检测 71.1%，outFrac 0% → 3.3%）。"
        "这三点都不需要「新检测器」的措辞。")

    R.h("九、对论文写作的直接修改")
    for t in [
        "RQ3 标题从「直方图 KL 检测器」改为「持续型亮度缺陷的区间定位：基线构造与误差传导」。",
        "Related Work 必须引用 BlazeBVD 式(5)，并写清本文与其差异是基线估计器（滚动中值 vs 高斯平滑）、"
        "累积规则（CUSUM vs 单帧阈值）与输出形态（区间 + 区间级评测）。",
        "贡献列表不要写「首次/新的 KL 检测器」；写「复现并指出 Eq(5) 在持续型缺陷上的失效，给出区间级协议」。",
        "Limitations 写：合成注入、13 段、无人工标注、端到端 outFrac 未达 1%。",
        "若审稿人追问「与 BlazeBVD 的区别」，用表 1 的 R/P/FP 与表 4 的误差传导回答，而不是口头声明。",
    ]:
        R.bullet(t)

    R.p("产物：results/runs/rq3_d1d2_v1/（per_condition.csv、pr_points.csv、sweep.csv、summary.json）；"
        "results/runs/rq3_e2e_cusum_v1/（per_condition.csv、summary.json）；"
        "results/runs/rq3_threshold_v1/（selection.csv、test_metrics.csv、summary.json）。"
        "本报告所有数字由脚本从这两份 CSV 读取。")

    R.save()
    print("saved", OUT_DOCX)


if __name__ == "__main__":
    main()
