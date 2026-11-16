#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
满镜令机检器（check_fullshot.py）——20261116王导令逐场自检工具
====================================================================
六项检查（对齐满镜令六条·王导20261116怒令）：
  1. 镜数≥5（只能多不能少）
  2. 配秒总和＝15.0s（余量≤1.0s，容差0.05）
  3. 隔级链零同档·相邻差≥2（远1/全2/中3/近4/特5/大特6）
  4. 对照区逐字全等（对源剧本行号区间逐行比对）
  5. 代词0（正文域她/他/它；台词行、「」引文域、对照区、▲行豁免）
  6. 禁词0（手机/快门/摄录）
另查：九字段齐备（出场人物/入镜承接/景别/拍摄角度/主体动态/台词/环境音/光影细节/出镜末态/转场）、
      【转场】条数＝镜数。

用法：
  python3 check_fullshot.py <分镜文件...>
  python3 check_fullshot.py --scene 分镜目录/  （目录内全部S1_单元*.md）
退出码：存在违规返回 1；否则 0。纯标准库实现。
"""
import sys, os, re

DANG = ["手机", "快门", "摄录"]
LEVEL = {
    "大远景": 1, "远景": 1, "远1": 1,
    "全景": 2, "全2": 2,
    "中景": 3, "中3": 3,
    "近景": 4, "近4": 4,
    "特写": 5, "特5": 5,
    "大特写": 6, "大特": 6, "大特6": 6,
}
FIELDS = ["出场人物", "入镜承接", "景别", "拍摄角度", "主体动态", "台词 / OS",
          "环境音", "光影细节", "出镜末态", "【转场】"]

def parse_level(jingbie_line):
    """从景别行提取档位数字"""
    m = re.search(r"景别：(.+?)(?:（|$)", jingbie_line)
    if not m:
        m = re.search(r"景别：(\S+)", jingbie_line)
    if not m:
        return None
    name = m.group(1).strip()
    for k, v in LEVEL.items():
        if name.startswith(k):
            return v
    # 兜底：档位数字直接写在中括号或行内
    m2 = re.search(r"[（(]?[档]?([1-6])[）)．.、]?", jingbie_line)
    if m2:
        return int(m2.group(1))
    return None

def check_file(path, script_path=None):
    errs, warns = [], []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    head = lines[0] if lines else ""

    # —— 1/2. 镜数与配秒（header：N镜＝a/b/...＝Xs＋余量Ys）——
    m = re.search(r"(\d+)镜＝([0-9./]+)＝([0-9.]+)s＋余量([0-9.]+)s", head)
    if not m:
        errs.append("header缺少满镜令镜秒账（格式：N镜＝a/b/...＝Xs＋余量Ys）")
        n_shots_hdr, secs, total, yl = None, [], None, None
    else:
        n_shots_hdr = int(m.group(1))
        secs = [float(x) for x in m.group(2).split("/")]
        total, yl = float(m.group(3)), float(m.group(4))
        if n_shots_hdr < 5:
            errs.append(f"镜数{n_shots_hdr}<5（满镜令：只能多不能少）")
        if len(secs) != n_shots_hdr:
            errs.append(f"header秒数{n_shots_hdr}段与镜数{len(secs)}不符")
        s = sum(secs)
        if abs(s - total) > 0.05:
            errs.append(f"秒账打架：header总和{s}≠标称{total}")
        if total < 13.95:
            errs.append(f"配秒{total}s<14s（满镜令：配满15s）")
        if abs(total + yl - 15.0) > 0.06:
            errs.append(f"15秒账不平：{total}＋余量{yl}≠15.0")

    # —— 分镜块解析 ——
    blocks = re.split(r"\n(?=分镜\d+「)", text)
    blocks = [b for b in blocks if re.match(r"分镜\d+「", b)]
    n_real = len(blocks)
    if n_shots_hdr is not None and n_real != n_shots_hdr:
        errs.append(f"实文分镜数{n_real}≠header镜数{n_shots_hdr}")

    # —— 3. 隔级链（黑场为收口拍·跨黑场豁免先例） ——
    chain = []
    for b in blocks:
        lv = None
        for ln in b.split("\n"):
            if ln.startswith("景别："):
                lv = "黑" if ln.startswith("景别：黑场") else parse_level(ln)
                break
        chain.append(lv)
    nums = [(i, v) for i, v in enumerate(chain) if isinstance(v, int)]
    if any(v is None or v == "黑" for v in chain):
        # 仅允许黑场为末镜收口；其余解析失败仍报错
        for i, v in enumerate(chain):
            if v is None:
                errs.append(f"隔级链解析失败：镜{i+1}档无法识别")
        if "黑" in chain and chain.index("黑") != len(chain) - 1:
            errs.append("黑场拍不在末镜（收口位）")
    for k in range(len(nums) - 1):
        i1, v1 = nums[k]
        i2, v2 = nums[k + 1]
        # 相邻才查差值；隔黑场跳过（跨黑场豁免）
        if i2 == i1 + 1 and abs(v2 - v1) < 2:
            errs.append(f"隔级违规：镜{i1+1}档{v1}→镜{i2+1}档{v2}（差{abs(v2-v1)}<2）")

    # —— 九字段＋转场数（只数正文提示词域·制作备注为非画面文本不计数） ——
    for i, b in enumerate(blocks, 1):
        for fld in FIELDS:
            if fld not in b:
                errs.append(f"镜{i}缺字段：{fld}")
    prompt_part = text.split("【剧本原文对照】")[0]
    n_zc = len(re.findall(r"【转场】", prompt_part))
    if n_shots_hdr is not None and n_zc != n_shots_hdr:
        errs.append(f"【转场】{n_zc}条≠镜数{n_shots_hdr}")

    # —— 4. 对照区逐字 ——
    m2 = re.search(r"【剧本原文对照】（五密终版L(\d+)-(\d+)[^）]*）\n(.*?)(?=\n\n【制作备注】|\Z)", text, re.S)
    if not m2:
        errs.append("缺【剧本原文对照】节或行号头")
    else:
        a, b_ = int(m2.group(1)), int(m2.group(2))
        claim = [ln for ln in m2.group(3).split("\n") if ln.strip()]
        if script_path and os.path.exists(script_path):
            with open(script_path, encoding="utf-8") as f:
                src = f.read().split("\n")
            expect = [src[i-1] for i in range(a, b_+1) if i-1 < len(src) and src[i-1].strip()]
            if len(claim) != len(expect):
                errs.append(f"对照区行数{len(claim)}≠源文L{a}-{b_}行数{len(expect)}")
            else:
                for k, (c, e) in enumerate(zip(claim, expect)):
                    if c.strip() != e.strip():
                        errs.append(f"对照区第{k+1}行被改写：\n  件:{c}\n  源:{e}")
        else:
            warns.append("未提供源剧本路径，对照区只查结构不查逐字")

    # —— 5/6. 代词0＋禁词（只查正文提示词域·对照区与制作备注豁免） ——
    body = prompt_part
    keep = []
    for ln in body.split("\n"):
        if ln.startswith("台词 / OS："):
            keep.append(ln.split("：", 1)[0] + "：")  # 台词行豁免（保留字段名）
            continue
        keep.append(ln)
    body2 = "\n".join(keep)
    body2 = re.sub(r"「[^」]*」", "", body2)   # 「」引文域豁免
    body2 = re.sub(r"【[^】]*】", "", body2)   # 结构域豁免
    for p in ["她", "他", "它"]:
        for mm in re.finditer(p, body2):
            ctx = body2[max(0, mm.start()-12):mm.start()+12].replace("\n", "·")
            errs.append(f"正文域代词「{p}」：…{ctx}…")

    for w in DANG:
        if w in body2:  # 台词行与「」引文域豁免（禁词只查正文域·与代词0同口径）
            errs.append(f"禁词命中：{w}")

    return errs, warns

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    script = "前10集剧本_终版_五密_20261014.md"
    files = []
    for a in args:
        if os.path.isdir(a):
            for fn in sorted(os.listdir(a)):
                if re.match(r"S1_单元\d+_.+\.md$", fn):
                    files.append(os.path.join(a, fn))
        else:
            files.append(a)
    if not files:
        print("用法：check_fullshot.py <文件|目录>..."); return 2
    bad = 0
    for fp in files:
        errs, warns = check_file(fp, script)
        tag = "✗" if errs else "✓"
        print(f"{tag} {os.path.basename(fp)}  ({len(errs)}违规/{len(warns)}提示)")
        for e in errs:
            print(f"    · {e}")
        for w in warns:
            print(f"    △ {w}")
        bad += len(errs)
    print(f"\n总计：{len(files)}件·{bad}违规")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
