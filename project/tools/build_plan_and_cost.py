"""Build the 15-day schedule and the cost ledger (XLSX + Markdown)."""
from __future__ import annotations

import csv
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
OUT_DIR = os.path.join(WS, "项目计划")
os.makedirs(OUT_DIR, exist_ok=True)
XLSX = os.path.join(OUT_DIR, "项目时间表与成本台账_2026-11-17.xlsx")
MD = os.path.join(OUT_DIR, "时间表与成本_2026-11-17.md")

HEAD_FILL = PatternFill("solid", fgColor="1F3864")
HEAD_FONT = Font(bold=True, color="FFFFFF", size=10, name="微软雅黑")
BODY = Font(size=9.5, name="微软雅黑")
TITLE = Font(bold=True, size=14, name="微软雅黑")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def sheet(wb, title, headers, rows, widths, note=None):
    sh = wb.create_sheet(title)
    r0 = 1
    if note:
        sh.cell(row=1, column=1, value=note).font = Font(italic=True, size=9, color="595959", name="微软雅黑")
        sh.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        r0 = 3
    for j, h in enumerate(headers, 1):
        c = sh.cell(row=r0, column=j, value=h)
        c.fill, c.font, c.border = HEAD_FILL, HEAD_FONT, BORDER
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for i, row in enumerate(rows, r0 + 1):
        for j, v in enumerate(row, 1):
            c = sh.cell(row=i, column=j, value=v)
            c.font, c.border = BODY, BORDER
            c.alignment = Alignment(vertical="top", wrap_text=True)
    for j, w in enumerate(widths, 1):
        sh.column_dimensions[get_column_letter(j)].width = w
    sh.freeze_panes = sh.cell(row=r0 + 1, column=1)
    sh.row_dimensions[r0].height = 30
    return sh


SCHEDULE = [
    ("2026-11-17", "周二", "P1 收尾", "双基线负结果、RQ3 定位；B2 All-In-One 14 案例；日志/成本；可视化", "补充报告、B2 报告、日志、可视化", 9, "今日完成", "已完成"),
    ("2026-11-18", "周三", "P1 收尾", "冻结全部数字；复现包（README/env/一键脚本/校验）", "复现包 v1", 6, "G1 数字冻结", "待做"),
    ("2026-11-19", "周四", "P1 收尾", "RQ1/RQ2/RQ3 图表定稿；Methods 骨架", "图表 + Methods 提纲", 6, "—", "待做"),
    ("2026-11-20", "周五", "P2 写作", "GPU 门控：本地装 torch 试 B2；失败则写 limitations", "GPU 决策记录", 4, "G2 GPU 决策", "待做"),
    ("2026-11-21", "周六", "P2 写作", "Related Work 全文（106 条库 + 划界表）", "RW 初稿", 8, "—", "待做"),
    ("2026-11-22", "周日", "P2 写作", "Methods 全文（注入/基线/指标/检测/统计）", "Methods 初稿", 8, "G3 标注决策", "待做"),
    ("2026-11-23", "周一", "P2 写作", "Experiments 全文（RQ1/RQ2/RQ3 表）", "Experiments 初稿", 8, "—", "待做"),
    ("2026-11-24", "周二", "P2 写作", "Discussion / Limitations / Conclusion", "全文 v0", 6, "—", "待做"),
    ("2026-11-25", "周三", "P3 审阅", "全文 v1 交导师；图 3-5 张", "投稿稿 v1", 6, "G4 导师审阅", "待做"),
    ("2026-11-26", "周四", "P3 审阅", "按意见修改；语言润色第一轮", "v1.1", 6, "—", "待做"),
    ("2026-11-27", "周五", "P3 审阅", "复现包最终校验；补充材料", "复现包 v2", 5, "—", "待做"),
    ("2026-11-28", "周六", "P3 审阅", "全文 v2；参考文献格式（Springer SIVP）", "v2", 6, "—", "待做"),
    ("2026-11-29", "周日", "P3 审阅", "内部终审；数字/表格/图一致性", "v2.1", 5, "G5 内容冻结", "待做"),
    ("2026-11-30", "周一", "P4 投稿", "排版、Cover Letter、Highlights", "投稿包", 4, "—", "待做"),
    ("2026-12-01", "周二", "P4 投稿", "作者/基金/声明/元数据；PDF 校验", "最终 PDF", 4, "—", "待做"),
    ("2026-12-02", "周三", "P4 投稿", "Editorial Manager 提交；保存回执", "提交回执", 2, "G6 提交", "待做"),
]

GATES = [
    ("G1", "2026-11-18", "数字冻结", "所有表数字来自 run 产物；之后只允许改表述，不重新调参。", "补充报告/日志/主报告哈希"),
    ("G2", "2026-11-20", "GPU 决策", "本地 8GB 已跑通 B2；无需远程。B1 代码未公开，B3–B5 不跑只引用。", "B2 运行日志 + 权重 SHA"),
    ("G3", "2026-11-22", "真实标注决策", "两名标注者能否到位；不能则真实集标为未完成，只用 CLEAN 假阳性探针。", "标注协议或未完成声明"),
    ("G4", "2026-11-25", "导师审阅", "全文 v1 必须包含 RQ3 负结果与 tested-split 数字。", "导师意见"),
    ("G5", "2026-11-29", "内容冻结", "只改语言与格式；不再加实验。", "v2.1 哈希"),
    ("G6", "2026-12-02", "提交", "目标刊 Signal, Image and Video Processing（备选 IET IP）。", "投稿回执"),
]

GPU_OPTIONS = [
    ("不租（当前建议）", "—", 0, 0.0, 0.0, "剩余工作全 CPU；B1 代码未公开、B2 本地 8GB 可试；权重/工具链才是瓶颈", "先不占用机器"),
    ("RTX 4090 24GB", "24 GB", 4, 2.5, 10.0, "仅 B2 推理 5 段 × 76 帧（若本地 8GB OOM）", "G2 触发才开"),
    ("RTX 4090 24GB", "24 GB", 8, 2.5, 20.0, "B2 全量 + 参数调试", "G2 触发才开"),
    ("A100 40GB", "40 GB", 8, 6.0, 48.0, "B1/B2 大 batch 或 512×512 全帧", "非必要"),
]


def main():
    # measured compute from run summaries
    runs_dir = os.path.join(WS, "results", "runs")
    total_s = 0.0
    n_runs = 0
    for name in os.listdir(runs_dir):
        s = read_json(os.path.join(runs_dir, name, "summary.json"))
        if s and "wall_seconds" in s:
            total_s += float(s["wall_seconds"])
            n_runs += 1
    cpu_h = total_s / 3600.0 + 0.5  # + report/data prep estimate
    kwh = cpu_h * 0.065  # 65 W package under NumPy load
    gpu_h = 17.16        # B2: 117 cases x (stage1 ~8.8 min + stage2 12 s)
    gpu_kwh = gpu_h * 0.085
    price = 0.60
    local_cost = (kwh + gpu_kwh) * price

    wb = Workbook()
    wb.remove(wb.active)

    sh = wb.create_sheet("说明")
    sh.column_dimensions["A"].width = 24
    sh.column_dimensions["B"].width = 105
    sh["A1"] = "项目时间表与成本台账"
    sh["A1"].font = TITLE
    lines = [
        ("生成时间", "2026-11-17 18:55 (+08:00)"),
        ("目标", "2026-12-02 提交 SCI 三区（首选 Signal, Image and Video Processing）"),
        ("剩余", "15 天（含今天）"),
        ("算力现状", "本地 RTX 5060 Laptop 8GB；无 PyTorch/CUDA 运行时；无 FFmpeg；远程 GPU 暂不需要"),
        ("数据现状", "VideoDM/Meta 13 段 × 76 帧 × 512×512；逐帧 SHA-256；测试 37 项全过"),
        ("实验现状", "Tier A 1170 条件 + RQ3 D1/D2 1300 条件 + 端到端 234 条件 + 阈值选择 2 组"),
        ("关键结论", "RQ3 预注册测试集 len12 召回 0.744（验证 0.965），0.90 未达；按边界性发现写"),
        ("钱的口径", "本表只核算可测的本地算力与公开报价；LLM/平台账单未暴露，不能编造，以平台账单为准"),
        ("远程 GPU", "先不要开机器；11/20 G2 门控再决定。若开：24GB VRAM、50GB 磁盘、CUDA 12.8、4–8 小时"),
    ]
    for i, (k, v) in enumerate(lines, 3):
        sh.cell(row=i, column=1, value=k).font = Font(bold=True, size=10, name="微软雅黑")
        c = sh.cell(row=i, column=2, value=v)
        c.font = BODY
        c.alignment = Alignment(wrap_text=True, vertical="top")

    sheet(wb, "时间表", ["日期", "星期", "阶段", "任务", "交付物", "预计工时(h)", "门控/依赖", "状态"],
          SCHEDULE, [12, 6, 10, 40, 24, 10, 14, 8],
          note="15 天倒排；P1 收尾 → P2 写作 → P3 审阅 → P4 投稿。工时按个人全职估算。")
    sheet(wb, "里程碑与门控", ["编号", "日期", "门控", "通过标准", "证据"], GATES,
          [6, 12, 16, 60, 30], note="门控未过时的退路见补充报告与查新报告 7.2。")

    sheet(wb, "算力成本(实测)", ["项目", "数值", "单位", "说明"], [
        ["纳入统计的 run 数", n_runs, "个", "有 summary.json 的运行目录"],
        ["运行墙钟合计", round(total_s / 3600.0, 2), "小时", "所有 run 的 wall_seconds 之和"],
        ["含数据/报告准备", round(cpu_h, 2), "小时", "上项 + 0.5 h 估算"],
        ["CPU 功率假设", 65, "W", "NumPy 单线程负载的整机 package 估计，非实测"],
        ["耗电", round(kwh, 3), "kWh", "cpu_h × 0.065 kW"],
        ["电价假设", price, "元/kWh", "居民电价估计，按本地账单为准"],
        ["本地电费", round(local_cost, 2), "元", "耗电 × 电价"],
        ["GPU 小时（B2）", gpu_h, "小时", "All-In-One 14 案例：stage1 约 8.7 min/案例 + stage2 11 s"],
        ["GPU 耗电", round(gpu_kwh, 3), "kWh", "按 85 W 估算（RTX 5060 Laptop 推理）"],
        ["云存储/流量", 0.0, "元", "数据在本地；HF 下载未计费"],
    ], [26, 16, 12, 60], note="本地算力成本为估算，误差主要来自功率假设；不含设备折旧。")

    sheet(wb, "远程GPU报价(估算)", ["方案", "显存", "小时", "单价(元/h)", "小计(元)", "用途", "何时开"],
          [list(x) for x in GPU_OPTIONS], [22, 10, 8, 12, 12, 55, 20],
          note="单价为 2026 年中国区租赁市场参考价，非实际账单；开机前以服务商报价为准。")

    sheet(wb, "成本汇总", ["类别", "金额(元)", "口径"], [
        ["本地电费（已发生）", round(local_cost, 2), "CPU 65W + GPU 85W × 实测小时 × 0.6 元/kWh（估算）"],
        ["远程 GPU（已发生）", 0.0, "未开机器"],
        ["远程 GPU（预算上限）", 50.0, "建议上限：4090 约 20 h 或 A100 约 8 h"],
        ["LLM/平台费（已发生）", "未知", "Harness 未暴露 token 账单；以平台账单为准，不估算"],
        ["数据/存储", 0.0, "本地；HF 下载免费"],
        ["合计（不含 LLM）", round(local_cost, 2), "已发生 + 0 云算力"],
    ], [26, 16, 60], note="不要用估算数字冒充账单；若需要，我可以按实际 token 用量另做一张换算表。")

    idx = os.path.join(WS, "实验记录", "runs_index.csv")
    if os.path.exists(idx):
        rows = list(csv.DictReader(open(idx, encoding="utf-8-sig")))
        sheet(wb, "今日运行日志", ["run_id", "类型", "状态", "条件数", "墙钟(s)", "配置哈希", "校验", "备注"],
              [[r["run_id"], r["kind"], r["status"], r["n_conditions"], r["wall_seconds"],
                r["config_sha256"][:12], r["validation"], r["note"]] for r in rows],
              [26, 20, 10, 10, 12, 14, 8, 70],
              note="来自 实验记录/runs_index.csv；完整日志见 实验记录/实验日志_2026-11-17.md。")

    wb.save(XLSX)

    # markdown
    md = []
    md.append("# 项目时间表与成本台账（2026-11-17）\n")
    md.append(f"- 目标：2026-12-02 提交 SCI 三区（首选 Signal, Image and Video Processing）")
    md.append(f"- 剩余：15 天（含今天）")
    md.append(f"- 本地算力：{n_runs} 个 run，墙钟 {total_s/3600:.2f} h；含准备约 {cpu_h:.2f} h；电费约 ¥{local_cost:.2f}")
    md.append(f"- 远程 GPU：**现在不需要**；11/20 G2 门控再决定")
    md.append(f"- LLM/平台费：本会话未暴露账单，**不编造**，以平台为准\n")
    md.append("## 15 天时间表\n")
    md.append("| 日期 | 星期 | 阶段 | 任务 | 交付物 | 工时 | 门控 | 状态 |")
    md.append("|---|---|---|---|---|---:|---|---|")
    for r in SCHEDULE:
        md.append("| " + " | ".join(str(x) for x in r) + " |")
    md.append("\n## 门控\n")
    md.append("| 编号 | 日期 | 门控 | 通过标准 | 证据 |")
    md.append("|---|---|---|---|---|")
    for r in GATES:
        md.append("| " + " | ".join(str(x) for x in r) + " |")
    md.append("\n## 远程 GPU：先不要开\n")
    md.append("当前瓶颈不是显存，而是 **PyTorch/CUDA 运行时 + 权重**：")
    md.append("- B1 BlazeBVD 的官方代码在公开渠道仍标注为待发布，租卡也跑不了；")
    md.append("- B2 All-In-One 代码与权重可获取，本地 8GB 在 512×512、batch=1 下有机会跑通；先本地装 torch 试。")
    md.append("- 若 11/20 本地试跑失败（OOM 或权重拿不到），再开远程：**24GB VRAM、50GB 磁盘、CUDA 12.8、4–8 小时**，预算 ¥20–50。")
    md.append("- 现在开机器会空转计费，建议等到 G2。\n")
    md.append("## 成本\n")
    md.append("| 类别 | 金额 | 口径 |")
    md.append("|---|---:|---|")
    md.append(f"| 本地电费（已发生） | ¥{local_cost:.2f} | 65W × {cpu_h:.2f}h × ¥0.6/kWh（估算） |")
    md.append("| 远程 GPU（已发生） | ¥0 | 未开机器 |")
    md.append("| 远程 GPU（建议上限） | ¥50 | 4090 约 20h 或 A100 约 8h |")
    md.append("| LLM/平台费 | 未知 | 以平台账单为准 |")
    md.append("\n> 注：电费是估算；不要把它当发票。")
    with open(MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print("saved", XLSX, "runs", n_runs, "cpu_h", round(cpu_h, 2), "local_cost", round(local_cost, 2))


if __name__ == "__main__":
    main()
