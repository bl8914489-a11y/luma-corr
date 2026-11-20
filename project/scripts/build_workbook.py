"""Build the result workbook (XLSX) from the generated CSV tables."""
from __future__ import annotations

import csv
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
SRC = os.path.join(WS, "results", "tables", "final")
OUT = os.path.join(WS, "报告", "实验结果表_2026-11-17.xlsx")

HEAD_FILL = PatternFill("solid", fgColor="1F3864")
HEAD_FONT = Font(bold=True, color="FFFFFF", size=10, name="微软雅黑")
BODY_FONT = Font(size=9.5, name="微软雅黑")
TITLE_FONT = Font(bold=True, size=14, name="微软雅黑")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def read(name):
    path = os.path.join(SRC, name)
    if not os.path.exists(path):
        return [], []
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    return rows[0], rows[1:]


def add_sheet(wb, title, csv_name, widths=None, note=None):
    headers, rows = read(csv_name)
    sh = wb.create_sheet(title)
    r0 = 1
    if note:
        sh.cell(row=1, column=1, value=note).font = Font(italic=True, size=9, color="595959",
                                                         name="微软雅黑")
        sh.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(len(headers), 2))
        r0 = 3
    if not headers:
        sh.cell(row=r0, column=1, value="(no data)")
        return sh
    for j, h in enumerate(headers, 1):
        c = sh.cell(row=r0, column=j, value=h)
        c.fill, c.font, c.border = HEAD_FILL, HEAD_FONT, BORDER
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for i, row in enumerate(rows, r0 + 1):
        for j, v in enumerate(row, 1):
            try:
                num = float(v)
                val = int(num) if num.is_integer() and abs(num) < 1e15 and "." not in v else num
            except (TypeError, ValueError):
                val = v
            c = sh.cell(row=i, column=j, value=val)
            c.font, c.border = BODY_FONT, BORDER
            c.alignment = Alignment(vertical="center", wrap_text=False)
    sh.freeze_panes = sh.cell(row=r0 + 1, column=1)
    for j in range(1, len(headers) + 1):
        width = (widths[j - 1] if widths and j - 1 < len(widths) else 14)
        sh.column_dimensions[get_column_letter(j)].width = width
    sh.row_dimensions[r0].height = 32
    return sh


def main():
    wb = Workbook()
    wb.remove(wb.active)

    # ---- 说明 ----
    sh = wb.create_sheet("说明")
    sh.column_dimensions["A"].width = 26
    sh.column_dimensions["B"].width = 110
    sh["A1"] = "文生视频缺陷时间区间局部亮度校正 — 实验结果表"
    sh["A1"].font = TITLE_FONT
    sh.merge_cells("A1:B1")
    man = json.load(open(os.path.join(WS, "results", "runs", "tierA_matrix_v1", "run_manifest.json"),
                         encoding="utf-8"))
    summ = json.load(open(os.path.join(WS, "results", "runs", "tierA_matrix_v1", "summary.json"),
                          encoding="utf-8"))
    env = man["environment"]
    lines = [
        ("生成时间", "2026-11-17"),
        ("数据", "Blind-Video-Deflickering-Dataset / VideoDM / Meta，13 段 × 76 帧 × 512×512，CC BY 4.0"),
        ("归档 SHA-256", "737252c0aa5f3a73972bec126c7edfe0ec7e19798dce6bc63eb4becd3ae0626e"),
        ("矩阵", f"{summ['n_conditions']} 个条件；{summ['n_per_frame_rows']} 行逐帧指标；"
                 f"墙钟 {summ['wall_seconds']/60:.1f} 分钟"),
        ("配置哈希", man["config_sha256"]),
        ("代码树哈希", man["code_tree_sha256"]),
        ("环境", f"Python {env['python']} / NumPy {env['numpy']} / Pillow {env['pillow']} / CPU {env['cpu_count']}"),
        ("GPU", "NVIDIA RTX 5060 Laptop 8GB（驱动 577.03）存在；无 PyTorch/CUDA 运行时与权重"),
        ("FFmpeg", "未安装、未调用；无任何 FFmpeg 性能声明"),
        ("All-In-One / B1–B5", "NOT_RUN（BLOCKED_NO_CUDA_NOT_RUN）；不报告对比数字"),
        ("指标定义", "Y=BT.601 亮度；Y MAE 为区间内逐帧空间平均绝对误差；"
                     "outFrac=区间外任一通道变化的像素比例；边界=区间两侧亮度跳变误差之和"),
        ("统计", "逐帧 Wilcoxon（描述性）+ 13 视频簇精确符号翻转/Wilcoxon + 簇自助 95% 区间 + rank-biserial"),
        ("校验", "validate_run.py 抽样 12 条件独立重算 PASS（12/12）；单元测试 25 项通过"),
        ("注意", "真实 T2V 人工标注未完成；15 段目标未达（子集仅 13 段）；详见报告第十一节"),
    ]
    for i, (k, v) in enumerate(lines, 3):
        a = sh.cell(row=i, column=1, value=k)
        b = sh.cell(row=i, column=2, value=v)
        a.font = Font(bold=True, size=10, name="微软雅黑")
        b.font = Font(size=9.5, name="微软雅黑")
        b.alignment = Alignment(wrap_text=True, vertical="top")
        a.alignment = Alignment(vertical="top")

    add_sheet(wb, "RQ1_区间内", "T1_rq1_interval.csv",
              widths=[8, 7, 7, 22, 18, 11, 15, 9, 9, 9],
              note="开发集 3 段（sailboat/book/horse）Y MAE 与 13 段均值；PSNR/SSIM/削波为 13 段均值。")
    add_sheet(wb, "RQ2_保持性", "T2_rq2_preservation.csv",
              widths=[8, 7, 7, 28, 16, 15, 14, 14, 14],
              note="局部（A2/A3）与全序列（A4）写回；边界误差拆为估计器偏差与外帧跳变。")
    add_sheet(wb, "RQ3_检测", "T3_rq3_detection.csv",
              widths=[18, 8, 10, 11, 10, 9, 13],
              note="13 段 × 3 注入均值；干净序列误报率见报告表 5 下方文字。")
    add_sheet(wb, "消融_上下文k", "T4_ablation_context.csv",
              widths=[8, 7, 12, 12, 12, 11, 9],
              note="k=1/3/5；YMAE 与边界均为 13 段均值。")
    add_sheet(wb, "消融_削波", "T4_ablation_clip.csv",
              widths=[8, 7, 10, 12, 12, 11, 9],
              note="硬裁剪 vs tanh 肩部（阈值 235）。")
    add_sheet(wb, "统计_配对", "T5_stats_A3_vs_baselines.csv",
              widths=[8, 7, 10, 14, 22, 10, 12, 11],
              note="负中位差表示 A3 的 Y MAE 更低；p_holm 为 81 个视频级比较的 Holm 校正。")

    # detection ablation (not in final CSV): build from run
    det_path = os.path.join(WS, "results", "runs", "ablation_detection_v1", "per_condition.csv")
    if os.path.exists(det_path):
        rows = list(csv.DictReader(open(det_path, encoding="utf-8")))
        sh = wb.create_sheet("消融_检测器")
        headers = ["检测器", "R@1", "R@4", "R@12", "P@1", "P@4", "P@12", "干净FP"]
        for j, h in enumerate(headers, 1):
            c = sh.cell(row=1, column=j, value=h)
            c.fill, c.font, c.border = HEAD_FILL, HEAD_FONT, BORDER
            c.alignment = Alignment(horizontal="center")
        dets = ["median_dev", "hist_kl_global", "cusum_k025_h3", "cusum_k05_h4", "cusum_k05_h6", "cusum_nosmooth"]
        for i, d in enumerate(dets, 2):
            vals = [d]
            for L in (1, 4, 12):
                rr = [r for r in rows if r["detector"] == d and r["injection"] != "CLEAN" and int(r["length"]) == L]
                vals.append(round(sum(float(x["recall"]) for x in rr) / len(rr), 3))
            for L in (1, 4, 12):
                rr = [r for r in rows if r["detector"] == d and r["injection"] != "CLEAN" and int(r["length"]) == L]
                vals.append(round(sum(float(x["precision"]) for x in rr) / len(rr), 3))
            rc = [r for r in rows if r["detector"] == d and r["injection"] == "CLEAN"]
            vals.append(round(sum(float(x["fp_rate"]) for x in rc) / len(rc), 3))
            for j, v in enumerate(vals, 1):
                c = sh.cell(row=i, column=j, value=v)
                c.font, c.border = BODY_FONT, BORDER
        widths = [20, 8, 8, 8, 8, 8, 8, 9]
        for j, w in enumerate(widths, 1):
            sh.column_dimensions[get_column_letter(j)].width = w
        sh.freeze_panes = "A2"

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wb.save(OUT)
    print("saved", OUT, "sheets", wb.sheetnames)


if __name__ == "__main__":
    main()
