"""Build the literature-use report (DOCX + Markdown) from the curated library.

Reads the workbook, the DOI-fetch status and the fetched BibTeX metadata, then
writes a citation map, a section-by-section skeleton, the missing-classics list
and the entries that should not be used as-is.
"""
from __future__ import annotations

import csv
import json
import os

import openpyxl
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
XLSX = os.path.join(WS, "data", "literature", "文献基线库_精选(1).xlsx")
STATUS = os.path.join(WS, "报告", "refs", "doi_fetch_status.csv")
OUT_MD = os.path.join(WS, "报告", "文献库使用建议_2026-11-17.md")
OUT_DOCX = os.path.join(WS, "报告", "文献库使用建议_2026-11-17.docx")
SELECTED_CSV = os.path.join(WS, "报告", "refs", "selected_core.csv")

# (序号, 优先级, 建议位置, 用途)
SELECTED = [
    (9, "必引", "Related Work 2.1；Baselines", "BlazeBVD：BVD SOTA、STE 直方图思想、B1 对照"),
    (11, "必引", "Related Work 2.1；Data", "All-In-One 神经滤波；VideoDM/Meta 数据来源"),
    (7, "支撑", "Related Work 2.1", "DiffSynth：T2V 迭代去闪烁"),
    (26, "支撑", "Related Work 2.1", "局部对比度去闪烁稳定化（与本课题最接近的经典局部方法）"),
    (32, "背景", "Related Work 2.1", "老电影强度闪烁校正（问题源头）"),
    (14, "背景", "Related Work 2.1", "后处理自适应滤波去闪烁"),
    (17, "背景", "Related Work 2.1", "时序重建优化去闪烁"),
    (10, "背景", "Related Work 2.1", "无监督去闪烁+去斑（可选）"),
    (3, "背景", "Related Work 2.1", "RIFLE：latent diffusion 去 flicker-banding（2025 预印本，可选）"),
    (47, "必引", "Related Work 2.2", "视频曝光校正：大规模真实数据集与方法（TPAMI 2026）"),
    (52, "必引", "Related Work 2.2；Limitations", "OSMamba：B5 曝光校正 SOTA"),
    (57, "必引", "Related Work 2.2；Limitations", "ECMamba：B4 曝光校正 SOTA"),
    (67, "必引", "Related Work 2.2", "DUAL：双光照估计曝光校正经典"),
    (59, "支撑", "Related Work 2.2", "动态场景曝光校正"),
    (69, "必引", "Related Work 2.2；Discussion", "时序一致区域级视频曝光校正：最接近“局部视频校正”的工作"),
    (71, "支撑", "Related Work 2.2", "CMOS 视频时序曝光不一致校正"),
    (72, "支撑", "Related Work 2.2", "无监督视频曝光校正"),
    (43, "支撑", "Related Work 2.2", "Practical exposure correction via compensation"),
    (54, "必引", "Method 3.2；Discussion", "AGCSNet：gamma + 饱和度校正，支撑削波/饱和论述"),
    (58, "背景", "Related Work 2.2", "区域感知曝光一致性（可选）"),
    (60, "背景", "Related Work 2.2", "Transformer 曝光校正（可选）"),
    (33, "必引", "Introduction；Related Work 2.3", "T2V 时空一致性综述（2026）"),
    (35, "支撑", "Related Work 2.3", "神经渲染/视频生成时序一致性综述"),
    (42, "必引", "Related Work 2.3", "Blind video temporal consistency 经典"),
    (41, "支撑", "Related Work 2.3", "GAN 视频生成自监督时序一致"),
    (38, "支撑", "Related Work 2.3", "扩散视频编辑的时序一致适配器"),
    (40, "必引", "Related Work 2.3", "低光视频增强中的时序一致性（亮度场景最接近）"),
    (39, "背景", "Related Work 2.3", "T2V 时序一致性增强（预印本，可选）"),
    (34, "背景", "Related Work 2.3", "动画 T2V 时序一致（可选）"),
    (94, "必引", "Related Work 2.4", "HDR 视频时序一致局部 tone mapping"),
    (93, "支撑", "Related Work 2.4", "K-means 时序一致 tone mapping"),
    (95, "必引", "Metrics", "Tone mapping 算子评测：指标选择依据"),
    (13, "支撑", "Related Work 2.4", "HDR 视频无闪烁 tone mapping"),
    (96, "背景", "Related Work 2.4", "Ldr2Hdr（只引期刊版；#97 为重复会议版）"),
    (79, "必引", "Metrics；RQ3", "IHCM 光照直方图一致性指标（本课题直方图距离依据）"),
    (18, "必引", "Introduction；Metrics", "局部闪烁的时序视觉掩蔽：闪烁感知指标依据"),
    (27, "支撑", "RQ3", "H.264 闪烁伪影测量"),
    (28, "背景", "RQ3", "周期 I 帧闪烁测量（可选）"),
    (19, "支撑", "RQ3", "神经网络闪烁检测"),
    (98, "支撑", "RQ3；Discussion", "AI 生成视频时序伪影检测（2026）"),
    (83, "必引", "Method 3.2", "Gamma 校正与亮度保持（A7）"),
    (86, "支撑", "Method 3.2", "直方图均衡（A6 背景）"),
    (89, "支撑", "Method 3.2", "自适应亮度校正（A9 背景；只引期刊版，#90 重复）"),
    (81, "支撑", "Method 3.2", "视频亮度稳定化算法与评测（A9 背景）"),
]

EXCLUDED = [
    ("21", "anon2018variational", "无 DOI（HAL），无法核验版本与页码；如必须引用需手工补全"),
    ("31", "anon2005novel", "无 DOI、中文期刊英文版，元数据不完整；建议弃用"),
    ("99", "anon2020comprehensive", "无 DOI、类型“其他”，且与主题关联弱；建议弃用"),
    ("96 / 97", "rempel2007ldr2hdr / …b", "同一 Ldr2Hdr 工作的期刊版与会议版；只保留 #96"),
    ("89 / 90", "yang2008algorithm / …b", "同一自适应亮度工作的期刊版与会议版；只保留 #89"),
    ("46", "zhang2026dimeplus", "IEEE DataPort 数据集 DOI，应作为 dataset 引用而非方法论文"),
    ("1 / 2", "qu2026takes / zhou2026vdfp", "2026 预印本、C 级、引用数极低；只可作“最新进展”一句，不作依据"),
    ("4 / 8 / 16 / 24 / 25", "—", "事件相机/反射去除/MJPEG/高速摄影，与本课题关联弱；背景即可"),
    ("74–78", "—", "光照编辑、取证、光照扩散等，属背景，不进入 Related Work 主体"),
]

CLASSICS = [
    ("wang2004image", "10.1109/TIP.2003.819861", "SSIM 原始论文：PSNR/SSIM 指标的必引来源"),
    ("zuiderveld1994contrast", "10.1016/B978-0-12-336156-1.50061-6", "CLAHE 原始章节：A6 的必引来源"),
    ("tomasi1998bilateral", "10.1109/ICCV.1998.710815", "双边滤波原始论文：A8 的必引来源"),
    ("kalman1960new", "10.1115/1.3662552", "Kalman 滤波原始论文：A9 的必引来源"),
    ("wilcoxon1945individual", "10.2307/3001968", "Wilcoxon 符号秩检验：统计节必引"),
    ("efron1979bootstrap", "10.1214/aos/1176344552", "Bootstrap：簇自助区间必引"),
    ("delon2006movie", "10.1109/tip.2005.860328", "STE 原始论文：A5/BlazeBVD 前处理的必引来源"),
]


def pct(n, d):
    return f"{100.0*n/d:.1f}%"


class Doc:
    def __init__(self):
        self.d = Document()
        sec = self.d.sections[0]
        sec.left_margin = sec.right_margin = Cm(2.0)
        sec.top_margin = sec.bottom_margin = Cm(2.0)
        st = self.d.styles["Normal"]
        st.font.name = "宋体"
        st.font.size = Pt(10.5)
        self.md = []

    def title(self, text, sub=None):
        p = self.d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text); r.font.size = Pt(19); r.font.bold = True
        r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")
        self.md.append(f"# {text}\n")
        if sub:
            p = self.d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(sub); r.font.size = Pt(10.5); r.font.color.rgb = None
            self.md.append(f"*{sub}*\n")

    def h(self, text, level=1):
        self.d.add_heading(text, level=level)
        self.md.append(f"\n{'#'*(level+1)} {text}\n")

    def p(self, text):
        p = self.d.add_paragraph(); p.paragraph_format.space_after = Pt(4)
        p.add_run(text)
        self.md.append(text + "\n")

    def bullet(self, text):
        p = self.d.add_paragraph(style="List Bullet"); p.add_run(text)
        self.md.append(f"- {text}\n")

    def table(self, headers, rows, widths=None, size=8.3, caption=None):
        if caption:
            p = self.d.add_paragraph(); r = p.add_run(caption); r.font.bold = True; r.font.size = Pt(9)
            self.md.append(f"\n**{caption}**\n")
        t = self.d.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        trPr = t.rows[0]._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:tblHeader")); trPr.append(OxmlElement("w:cantSplit"))
        for i, h in enumerate(headers):
            c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(str(h)); r.font.bold = True; r.font.size = Pt(size)
        for row in rows:
            tr = t.add_row()
            tr._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
            cells = tr.cells
            for i, v in enumerate(row):
                cells[i].text = ""; r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(size)
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
        def ea(run):
            run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")
        for p in self.d.paragraphs:
            for r in p.runs:
                ea(r)
        for t in self.d.tables:
            for row in t.rows:
                for c in row.cells:
                    for p in c.paragraphs:
                        for r in p.runs:
                            ea(r)
        self.d.save(OUT_DOCX)
        with open(OUT_MD, "w", encoding="utf-8") as fh:
            fh.write("\n".join(self.md))


def main():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    ws = wb["精选基线库"]
    rows = list(ws.iter_rows(values_only=True))
    hdr = rows[0]
    data = {int(r[0]): dict(zip(hdr, r)) for r in rows[1:] if r[0] is not None}
    status = {int(r["序号"]): r for r in csv.DictReader(open(STATUS, encoding="utf-8-sig"))}

    themes = {}
    grades = {}
    for d in data.values():
        themes[d["主题"]] = themes.get(d["主题"], 0) + 1
        grades[d["可复现等级"]] = grades.get(d["可复现等级"], 0) + 1
    ok = sum(1 for s in status.values() if s["fetch_status"] == "ok")

    R = Doc()
    R.title("文献基线库（精选 99）使用建议与引用骨架",
            "面向《文生视频缺陷时间区间局部亮度校正》SCI 三区投稿 | 2026-11-17")

    R.h("一、结论先行")
    R.p(f"该库共 99 条，覆盖视频去闪烁、时序一致性、曝光校正、亮度/光照、色调映射、质量评测六个主题；"
        f"其中 {ok} 条 DOI 可解析并已导出结构化元数据，3 条无 DOI。对本课题最有价值的是三类："
        "①盲去闪烁（BlazeBVD、All-In-One、DiffSynth）提供 SOTA 定位与 B1/B2 对照依据；"
        "②曝光校正中的“视频/时序一致/区域级”分支（TPAMI 2026 视频曝光、OSMamba、ECMamba、ICME 2015 区域级视频曝光）"
        "是“局部视频亮度校正”最直接的近邻；③亮度/光照主题中的 IHCM 指标与闪烁时序掩蔽文献，"
        "正好为本课题的直方图距离和闪烁指标提供依据。")
    R.p("但库中有两个明显缺口：一是方法学经典（SSIM、CLAHE、双边滤波、Kalman、Wilcoxon、Bootstrap、STE 原文）"
        "全部缺失；二是三条无 DOI 记录（#21、#31、#99）与两组重复版本（#96/#97、#89/#90）需要处理。"
        "本报告已补 7 条经典并导出合并 BibTeX。")

    R.h("二、库的构成")
    R.table(["主题", "篇数", "占比"], [[k, v, pct(v, 99)] for k, v in themes.items()],
            widths=[6.0, 2.0, 2.0], caption="表 1  主题分布")
    R.table(["可复现等级", "篇数", "说明"], [
        ["A", grades.get("A", 0), "元数据/复现线索最完整，优先引用"],
        ["B", grades.get("B", 0), "可用，需核对页码/版本"],
        ["C", grades.get("C", 0), "预印本或元数据较弱，只作背景/最新进展"],
    ], widths=[3.0, 2.0, 9.0], caption="表 2  可复现等级分布（等级来自原表，不代表引用优先级）")
    R.p(f"DOI 状态：{ok}/99 成功解析（doi.org content negotiation），3 条无 DOI。"
        "全部 96 条已抓取作者、题名、会议/期刊、年份等字段并生成 BibTeX。")

    R.h("三、推荐使用的核心文献（按论文位置）")
    sel_rows = []
    for idx, pri, section, use in SELECTED:
        s = status.get(idx, {})
        d = data[idx]
        sel_rows.append([idx, s.get("cite_key", ""), d["年份"], pri, section, use, d["可复现等级"]])
    R.table(["#", "BibTeX key", "年", "优先级", "位置", "用途", "级"], sel_rows,
            widths=[0.8, 4.8, 0.9, 1.15, 2.9, 5.7, 0.55], size=7.8,
            caption=f"表 3  推荐的 {len(sel_rows)} 条核心文献（键名与合并 BibTeX 一致）")

    R.h("四、逐节引用骨架")
    R.p("下面给出可直接改写成英文段落的引用骨架。方括号内为 BibTeX key，均已存在于合并 BibTeX。")

    R.h("4.1 Introduction", 2)
    R.p("T2V 生成的时序一致性仍是主要失效模式，亮度闪烁在生成视频与真实视频中都被列为显著伪影"
        "[yin2026survey; choi2018video]。盲去闪烁方法以整段视频为单位重建亮度"
        "[qiu2024blazebvd; lei2023blind; duan2024diffsynth]，而实际编辑/修复流程往往已经知道缺陷区间，"
        "此时“只改区间、不动区间外”的局部写回是否足够、边界代价多大，缺少系统量化。"
        "本文以可复现的受控注入回答这一问题，并把检测—校正联合起来。")

    R.h("4.2 Related Work — Blind video deflickering", 2)
    R.p("经典路线从老电影强度闪烁校正 [vanroosmalen1999correction]、局部对比度稳定化 [delon2010stabilization]、"
        "尺度-时间均衡（STE）[delon2006movie] 到自适应后处理 [gandam2021efficient]、时序重建 [li2019video]。"
        "深度路线以 All-In-One 的 flawed-atlas 神经滤波 [lei2023blind]、BlazeBVD 的直方图辅助 STE [qiu2024blazebvd]、"
        "DiffSynth 的迭代去闪烁 [duan2024diffsynth] 为代表。共同点是全局处理整段视频；"
        "本文关心的“区间内重建 + 区间外保持 + 边界分解”并非它们的优化目标。")

    R.h("4.3 Related Work — Exposure and brightness correction", 2)
    R.p("图像曝光校正从 DUAL 双光照估计 [zhang2019dual] 发展到区域感知 [liu2024region]、"
        "Transformer [li2023fearless]、CLIP 引导 [huang2025clip] 与扩散先验 [li2026high]；"
        "视频曝光校正强调时序一致与动态场景 [dong2015temporally; vo2012temporal; petrova2009unsupervised; "
        "zhang2026learning]，最新 SOTA 为 OSMamba [li2025osmamba] 与 ECMamba [dong2024ecmamba]。"
        "与本课题最接近的是区域级、时序一致的视频曝光校正 [dong2015temporally] 与 CMOS 时序曝光不一致校正 [vo2012temporal]；"
        "本文的差异是把缺陷区间视为已知、把边界误差拆成“估计器偏差/区间外改动”两列，并给出逐帧配对统计。")

    R.h("4.4 Related Work — Temporal consistency in T2V", 2)
    R.p("T2V 时序一致性已有系统综述 [yin2026survey; einabadi2026survey]；经典盲时序一致 [bonneel2015blind]、"
        "自监督 GAN 视频生成 [chu2020learning]、扩散视频编辑适配器 [song2025efficient] 与低光视频时序一致 [zhang2021learning]"
        " 分别覆盖不同失效模式。本文的受控注入实验可视为对这一谱系的“已知区间”压力测试。")

    R.h("4.5 Related Work — Tone mapping and quality metrics", 2)
    R.p("HDR 视频的时序一致 tone mapping [aydin2014temporally; oskarsson2016temporally] 与 flicker-free tone mapping "
        "[mujtaba2022efficient] 说明亮度映射必须联合时间维考虑；tone mapping 评测 [eilertsen2013evaluation] 为指标选择提供依据。"
        "质量侧采用 SSIM [wang2004image]、IHCM 直方图一致性 [chen2024illumination] 与局部闪烁的时序视觉掩蔽 [choi2018video]。")

    R.h("4.6 Method — 注入、基线与指标", 2)
    R.p("注入采用码值域 gamma 变换 [srekhi2023gamma]，并显式记录注入/校正两阶段的削波比例，"
        "以区分“注入饱和”与“校正饱和”；饱和度校正文献 [kim2025agcsnet] 支撑这一诊断。"
        "基线对应关系：A5↔STE [delon2006movie; qiu2024blazebvd]，A6↔CLAHE [zuiderveld1994contrast]，"
        "A7↔gamma [srekhi2023gamma]，A8↔双边滤波 [tomasi1998bilateral]，A9↔Kalman [kalman1960new] 与亮度稳定化 [bilozerskyi2023new; yang2008algorithm]。"
        "指标：SSIM [wang2004image]、IHCM [chen2024illumination]、闪烁时序掩蔽 [choi2018video]；"
        "统计：Wilcoxon [wilcoxon1945individual] 与 bootstrap [efron1979bootstrap]。")

    R.h("4.7 RQ3 — Detection", 2)
    R.p("闪烁检测与测量已有 H.264 周期 I 帧测量 [lim2010measurement]、早期闪烁测量 [yang2008effective] 与神经网络检测 [patel2018effective]；"
        "AI 生成视频的时序伪影检测 [d2026temporal] 说明该问题在 T2V 场景仍活跃。"
        "本文把“帧 vs 局部中值”升级为“帧直方图 vs 滚动中值直方图”的 KL/JS 散度，并用 CUSUM 累积持续证据；"
        "该库中未见将这一组合用于“已知区间局部亮度缺陷定位”的工作，但不能据此断言首创，投稿前需补检索引证。")

    R.h("4.8 Discussion / Limitations", 2)
    R.p("未运行的深度对照应引用其公开结果而非本机数字：BlazeBVD [qiu2024blazebvd]、All-In-One [lei2023blind]、"
        "OSMamba [li2025osmamba]、ECMamba [dong2024ecmamba]。最接近的局部视频校正工作 [dong2015temporally; vo2012temporal]"
        " 应在 Discussion 中明确比较维度（是否已知区间、是否逐帧统计、是否报告区间外保持）。")

    R.h("五、必须补充的 7 条经典文献")
    add_rows = [[i + 1, k, doi, why] for i, (k, doi, why) in enumerate(CLASSICS)]
    R.table(["#", "BibTeX key", "DOI", "为什么必须补"], add_rows,
            widths=[0.8, 4.0, 5.6, 6.0], caption="表 4  库中缺失的方法学经典（已导出到 refs/core_additions.bib）")
    R.p("这 7 条不是“锦上添花”：SSIM/CLAHE/双边/Kalman/Wilcoxon/Bootstrap 是本课题方法与统计的直接来源，"
        "STE 原文是 A5 与 BlazeBVD 前处理的根引用。缺它们会让方法节看起来没有出处。")

    R.h("六、不建议直接使用或需要处理的条目")
    ex_rows = [[a, b, c] for a, b, c in EXCLUDED]
    R.table(["#", "key", "处理建议"], ex_rows, widths=[2.2, 5.6, 8.0],
            caption="表 5  无 DOI、重复版本与低相关条目")
    R.p("另外，#23（thesis.fr DOI）虽可解析，但 DOI 形态异常、页码信息弱，引用前需核对原论文；"
        "#1/#2 是 2026 年预印本，只能作为“最新进展”一句，不能当作方法依据。")

    R.h("七、BibTeX 文件与使用")
    R.p("已生成三个文件（均在 报告/ 目录）：")
    R.bullet("参考文献_精选99_2026-11-17.bib —— 原库 99 条，96 条为 doi.org 抓取的完整元数据，3 条标记为 no DOI。")
    R.bullet("refs/core_additions.bib —— 上表 7 条经典。")
    R.bullet("参考文献_合并_2026-11-17.bib —— 106 条合并版，论文直接使用这一个即可。")
    R.p("键名规则为“第一作者姓 + 年份 + 标题首个实词”（如 qiu2024blazebvd、lei2023blind、chen2024illumination）；"
        "重复工作自动加后缀 b（如 rempel2007ldr2hdrb），但正文只引其中一个版本。"
        "示例：\\cite{qiu2024blazebvd,lei2023blind,delon2006movie}。")
    R.p("注意：BibTeX 的标题/作者来自 DOI 注册元数据，个别会议名可能是全称或大小写不规范；"
        "投稿前请按目标期刊格式统一（Springer 的 sn-jnl / splncs 样式对 booktitle 的缩写较敏感）。")

    R.h("八、对论文写作的三条具体建议")
    R.bullet("定位：不要把它写成“又一个去闪烁网络”。库中 BlazeBVD/All-In-One/OSMamba/ECMamba 已占据 SOTA 生态；"
             "本课题的差异化是“已知区间的局部写回 + 边界分解 + 可复现审计 + 检测—校正联合”，这与库中 #69/#71 的"
             "区域级视频曝光校正最接近，应在 Related Work 中主动比较。")
    R.bullet("指标：直方图距离必须引 IHCM [chen2024illumination]，闪烁指标必须引时序掩蔽 [choi2018video]；"
             "否则审稿人会问“为什么用这个指标”。")
    R.bullet("诚实边界：库中没有“已知区间局部亮度缺陷”的直接 benchmark；本文的注入协议是自建的。"
             "Related Work 末尾应明确“不存在可直接对比的公开协议”，这也是贡献之一（可复现协议），而不是掩饰。")

    R.p("附：本报告的所有计数来自 data/literature/文献基线库_精选(1).xlsx（SHA-256 "
        "06B02A3F…3933）与 报告/refs/doi_fetch_status.csv；引用键与 参考文献_合并_2026-11-17.bib 一一对应。")

    R.save()

    # selected core csv
    with open(SELECTED_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["序号", "cite_key", "年份", "优先级", "建议位置", "用途", "可复现等级", "主题", "标题", "DOI"])
        for idx, pri, section, use in SELECTED:
            d = data[idx]; s = status.get(idx, {})
            w.writerow([idx, s.get("cite_key", ""), d["年份"], pri, section, use,
                        d["可复现等级"], d["主题"], d["标题"], d["DOI"]])
    print("saved", OUT_DOCX, "selected", len(SELECTED))


if __name__ == "__main__":
    main()
