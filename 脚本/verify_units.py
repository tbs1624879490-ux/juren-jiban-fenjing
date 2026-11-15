#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S2 分镜核销器（verify_units.py）
====================================================================
目的：把 2026-10-09 U001/U002 复盘的 13 类错误变成机器拦截项，
让"凭记忆整文件重写导致元素静默丢失"在交付前被拦下。

规则外置：../规则配置/S2核销规则.json —— 调规则只改 JSON。
门控：active_units 列出的单元才全量核销；未升级的旧单元仅统计、不判错。

用法：
  python3 verify_units.py verify "<分镜目录>" [--unit 1,2] [--fixture]
  python3 verify_units.py brief <单元号>

退出码：存在 ERROR 返回 1；否则 0。
纯标准库实现。
"""
import sys, os, re, json, argparse, glob

def load_cfg(cfg_path=None):
    if cfg_path:
        with open(cfg_path, encoding="utf-8") as f:
            return json.load(f)
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "规则配置", "S2核销规则.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)

CFG = None   # main() 里按 --config 或默认路径加载（支持多项目：脚本通用、配置项目化）

# ---------- 解析 ----------
def split_body_notes(text):
    """按分隔线（==== 或 【制作备注】）切成 正文 / 备注。"""
    m = re.search(CFG["separator_re"], text, re.M)
    if m:
        return text[:m.start()], text[m.start():]
    return text, ""

def get_shots(body):
    """正文 -> [(镜号:int, 块文本)]。"""
    marks = [(m.start(), int(m.group(1)))
             for m in re.finditer(CFG["shot_title_re"], body)]
    out = []
    for i, (pos, num) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        out.append((num, body[pos:end]))
    return out

def field_line(block, field):
    m = re.search(r"^[-\s]*" + re.escape(field) + r"[：:](.+)$",
                  block, re.M)
    return m.group(1).strip() if m else ""

def unit_files(folder):
    rx = re.compile(CFG["unit_fn_re"])
    out = []
    for f in sorted(glob.glob(os.path.join(folder, "**", "*.md"), recursive=True)):
        m = rx.match(os.path.basename(f))
        if m:
            out.append((int(m.group(1)), f))
    out.sort(key=lambda x: x[0])
    return out

# ---------- 核销 ----------
def verify_unit(unit, path):
    errs = []   # [(规则, 说明)]
    text = open(path, encoding="utf-8").read()
    body, notes = split_body_notes(text)
    shots = get_shots(body)

    def E(tag, detail): errs.append((tag, detail))

    shadow_world = not any(mk in body for mk in CFG["skip_world_markers"])

    # R1 暗面禁光词
    if shadow_world:
        hit = [w for w in CFG["R1_dark_banned_words"]["words"] if w in body]
        if hit:
            E("R1", "暗面正文出现表世界光源词 %s——%s" % (hit, CFG["R1_dark_banned_words"]["msg"]))

    # R2 器物死光
    if shadow_world:
        hit = [w for w in CFG["R2_dead_light_words"]["words"] if w in body]
        if hit:
            E("R2", "暗面正文出现器物发光词 %s——%s" % (hit, CFG["R2_dead_light_words"]["msg"]))

    # R3 建模外观词
    hit = [w for w in CFG["R3_appearance_phrases"]["phrases"] if w in body]
    if hit:
        E("R3", "正文出现外观定义词 %s——%s" % (hit, CFG["R3_appearance_phrases"]["msg"]))

    # R4 变身因果
    tf = CFG["R4_transformation"]
    cu = tf["complete_unit"]; abw = tf["ability_words"]
    if unit < cu:
        hit = [w for w in abw if w in body]
        if hit:
            E("R4", "变身完成前（U%03d）出现能力词 %s——%s" % (unit, hit, tf["msg"]))
    elif unit == cu and shots:
        for num, block in shots[:-1]:   # 末镜之外不允许能力词
            hit = [w for w in abw if w in block]
            if hit:
                E("R4", "分镜%d 变身尚未走完却出现能力词 %s——%s" % (num, hit, tf["msg"]))

    # R5 姿态
    r5 = CFG["R5_posture"]
    hit = [w for w in r5["banned"] if w in body]
    if hit:
        E("R5", "正文出现错误姿态词 %s——%s" % (hit, r5["msg"]))
    if any(t in body for t in r5["aerial_triggers"]) and not any(
            w in body for w in r5["aerial_require_any"]):
        E("R5", "空中单元缺姿态锚点（应有 %s 之一）——%s"
          % (r5["aerial_require_any"], r5["msg"]))

    # R6 动作链完整
    chain = CFG["R6_required_chains"].get(str(unit))
    if chain:
        miss = [w for w in chain["must_all"] if w not in body]
        if miss:
            E("R6", "单元必含动作链缺失 %s（须全部出现：%s）——动作单元被内容填满，过程一拍不许断"
              % (miss, chain["must_all"]))

    # R7 摆荡物理（trigger 为空＝本项目无此类能力，跳过；防 "" 恒命中误报）
    r7 = CFG["R7_swing_physics"]
    if r7.get("trigger") and r7["trigger"] in body and not any(w in body for w in r7["require_any"]):
        E("R7", "出现「%s」却缺摆荡物理锚点（应有 %s 之一）——%s"
          % (r7["trigger"], r7["require_any"], r7["msg"]))

    # R8 前景遮罩
    if chain and not any(w in body for w in CFG["R8_foreground_mask"]["require_any"]):
        E("R8", "高速动作单元缺前景遮罩（应有 %s 之一）——%s"
          % (CFG["R8_foreground_mask"]["require_any"],
             CFG["R8_foreground_mask"]["msg"]))

    # R9 UI 视角锁（逐分镜）
    r9 = CFG["R9_ui_view_lock"]
    for num, block in shots:
        ui_hit = [w for w in r9["ui_words"] if w in block]
        if not ui_hit:
            continue
        header = field_line(block, "景别") + " " + field_line(block, "拍摄角度")
        if not any(mk in header for mk in r9["pov_markers"]):
            E("R9", "分镜%d 含 UI 元素 %s，但景别/拍摄角度未声明第一视角（标记词：%s）——%s"
              % (num, ui_hit, r9["pov_markers"], r9["msg"]))

    # R10 UI 版本
    hit = [w for w in CFG["R10_ui_version"]["banned"] if w in body]
    if hit:
        E("R10", "正文出现已废止 UI 版本词 %s——%s" % (hit, CFG["R10_ui_version"]["msg"]))

    # R11 元信息分区
    hit = [w for w in CFG["R11_meta_separation"]["words"] if w in body]
    if hit:
        E("R11", "正文（分隔线以上）出现元信息词 %s——%s"
          % (hit, CFG["R11_meta_separation"]["msg"]))

    # R12 批注分区
    hit = [w for w in CFG["R12_annotation_separation"]["words"] if w in body]
    if hit:
        E("R12", "正文出现解释性批注 %s——%s"
          % (hit, CFG["R12_annotation_separation"]["msg"]))

    # R13 写作规矩泄漏
    hit = [w for w in CFG["R13_writing_rules_leak"]["words"] if w in body]
    if hit:
        E("R13", "正文出现给创作者看的写作规矩 %s——%s"
          % (hit, CFG["R13_writing_rules_leak"]["msg"]))

    # R14 丝连续：空中动作分镜块必须见丝（仅配置单元）
    r14 = CFG["R14_silk_continuity"]
    if unit in r14["apply_units"]:
        for num, block in shots:
            if any(t in block for t in r14["aerial_triggers"]) and \
                    r14["require_word"] not in block and not \
                    any(x in block for x in r14.get("exempt_if_any", [])):
                E("R14", "分镜%d 含空中动作却不见影丝——%s"
                  % (num, r14["msg"]))

    # R15 武戏运镜（2026-10-10 用户拍板）：运动镜头为默认、定机位为特例
    r15 = CFG.get("R15_wuxia_camera")
    if r15 and shots:
        mtype = re.search(r"类型：([^\n]+)", text)
        is_wuxia = bool(mtype) and any(
            t in mtype.group(1) for t in r15["wuxia_type_markers"])
        if is_wuxia:
            still = []
            for num, block in shots:
                ang = field_line(block, "拍摄角度")
                dyn = field_line(block, "主体动态")
                if any(w in ang for w in r15["movement_words"]):
                    continue
                if any(w in ang + dyn for w in r15["fixed_exempt_words"]):
                    continue   # 定机位特例：冲击帧/骤静/收势定格/UI结算
                still.append(num)
            if len(still) > len(shots) // 2:
                E("R15", "武戏单元定机位镜 %s 超半数——%s"
                  % (still, r15["msg"]))

    # R16 工作流史泄漏（2026-10-11 用户裁决）：意见编号/拍板记录只进台账，不进单元文件正文
    r16 = CFG.get("R16_workflow_history_leak")
    if r16:
        hits = sorted({mm.group(0) for pat in r16["patterns"]
                       for mm in re.finditer(pat, body)})
        if hits:
            E("R16", "正文出现工作流史词 %s——%s" % (hits, r16["msg"]))

    # R17 时长填满（2026-10-11 意见74）：15秒档空余≥2秒即拦
    r17 = CFG.get("R17_duration_fill")
    if r17:
        m = re.search(r"时长：≈(\d+(?:\.\d+)?)s\s*/\s*" + str(r17["slot"]) + r"s", text)
        if m:
            idle = r17["slot"] - float(m.group(1))
            if idle >= r17["max_idle"]:
                E("R17", "时长 ≈%ss、%ds 档空余 %.1fs 未填满——%s"
                  % (m.group(1), r17["slot"], idle, r17["msg"]))

    # R18 信息密度（2026-10-11 意见75）：主体动态过短＝信息量缺失
    r18 = CFG.get("R18_info_density")
    if r18:
        for num, block in shots:
            dyn = field_line(block, "主体动态")
            if not dyn:
                E("R18", "分镜%d 缺主体动态字段——%s" % (num, r18["msg"]))
            elif len(dyn) < r18["min_chars"]:
                E("R18", "分镜%d 主体动态仅 %d 字、低于密度底线 %d 字——%s"
                  % (num, len(dyn), r18["min_chars"], r18["msg"]))

    # R19 拉片锚点引用（2026-10-12 P2-⑪）：正文含拉片特征词→备注库挂载须引用公共拉片库
    r19 = CFG.get("R19_lapian_ref")
    if r19:
        hit_words = sorted(w for w in r19["triggers"] if w in body)
        if hit_words:
            has_ref = r19["require_marker"] in notes and r19["ref_format"] in notes
            if not has_ref:
                E("R19", "正文命中拉片特征 %s，备注库挂载未见公共拉片库引用（须含「%s」）——%s"
                  % (hit_words, r19["ref_format"], r19["msg"]))

    # R20 外部游戏专名禁入（2026-10-19 王导拍板）：摆摊拉片只借视觉手法，抽卡/转盘类符号零入镜
    r20 = CFG.get("R20_external_game_terms")
    if r20:
        hit = sorted({w for w in r20["words"] if w in body})
        if hit:
            E("R20", "正文出现外部游戏化专名 %s——%s" % (hit, r20["msg"]))

    return errs

# ---------- ask：交付前逐项自问 ----------
def load_ask_cfg(cfg_path=None):
    if cfg_path:
        # 约定：核销规则与自检问题同目录、命名成对（XX核销规则.json ↔ XX自检问题.json）
        p = cfg_path.replace("核销规则", "自检问题")
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "规则配置", "S2自检问题.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def _shot_index_map(body):
    """正文 -> {镜号: (块起点, 终点)}，用于定位违禁词所在镜。"""
    shots = get_shots(body)
    out = {}
    for num, block in shots:
        start = body.find(block)
        out[num] = (start, start + len(block))
    return out

def cmd_ask(args):
    ask = load_ask_cfg(getattr(args, "config", "") or None)
    path = args.file
    if not os.path.isfile(path):
        print("文件不存在：", path); return 2
    text = open(path, encoding="utf-8").read()
    body, _notes = split_body_notes(text)
    shots = get_shots(body)
    real_nos = {num for num, _ in shots}
    idx_map = _shot_index_map(body)

    # 启用本次要问的项（manual 的 applies_if_contains 按正文过滤）
    enabled = []
    for chk in ask["checks"]:
        cond = chk.get("applies_if_contains")
        if cond and not any(w in body for w in cond):
            continue
        # 否定语境豁免：如“不拉影丝”，本单元不靠丝、该项不适用
        if any(neg in body for neg in chk.get("skip_if_negated", [])):
            continue
        enabled.append(chk)

    evidences = {}   # id -> 证据
    total = len(enabled)
    print("=" * 64)
    print("交付前自问：%s（共 %d 项，一项不过即中断、改完从第1项重来）"
          % (os.path.basename(path), total))
    print("=" * 64)

    def fail(chk, detail):
        print("\n✗【%s】%s" % (chk["area"], detail))
        print("  → %s" % chk["fail_hint"])
        print("中断于第 %d/%d 项。修正文件后，重新执行：ask \"%s\"（从第1项自问）"
              % (enabled.index(chk) + 1, total, path))
        return 1

    for i, chk in enumerate(enabled, 1):
        print("\n【自问 %d/%d｜%s】%s" % (i, total, chk["area"], chk["q"]))

        if chk["mode"] == "auto_grep":
            hits = []
            for w in chk["banned"]:
                pos = body.find(w)
                if pos != -1:
                    in_shot = next((n for n, (s, e) in idx_map.items()
                                   if s <= pos < e), None)
                    hits.append((w, in_shot))
            if hits:
                detail = "；".join("「%s」%s" %
                        (w, ("镜%d" % n) if n else "(头部)") for w, n in hits)
                return fail(chk, detail)
            print("  ✓ 未出现")
            continue

        # manual：读一行证据，校验引用的镜号全部真实存在
        print("  证据：%s" % chk["evidence_hint"])
        line = sys.stdin.readline()
        ev = line.strip()
        if len(ev) < 4:
            return fail(chk, "未提供有效证据（空）")
        cited = {int(x) for x in re.findall(ask["evidence_shot_regex"], ev)}
        if not cited:
            return fail(chk, "证据必须引用本文件真实镜号（如 镜2）")
        fake = sorted(cited - real_nos)
        if fake:
            return fail(chk, "证据引用了不存在的镜号 %s、本文件真实镜号为 %s"
                        % (fake, sorted(real_nos)))
        evidences[chk["id"]] = ev
        print("  ✓ %s" % ev)

    # 全部通过：追加自检日志
    from datetime import datetime
    log_p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", os.path.basename(ask["log_path"]))
    rec = {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           "file": os.path.basename(path),
           "passed": True,
           "auto": [c["id"] for c in enabled if c["mode"] == "auto_grep"],
           "manual": {str(k): v for k, v in evidences.items()}}
    with open(log_p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print("\n" + "=" * 64)
    print("自问全部通过（%d 项），已记入 %s，可交付。"
          % (total, os.path.basename(log_p)))
    return 0

# ---------- brief：动笔前必读清单 ----------
def brief(unit):
    c = CFG
    cu = c["R4_transformation"]["complete_unit"]
    form = "普通形态（变身前）" if unit < cu else "暗影形态（变身后）"
    ui = "红黑口径（常态）" if unit < cu else "全紫：四角紫雾＋紫血条＋紫扫描框，无科技线框"
    chain = c["R6_required_chains"].get(str(unit))
    a = c["brief_assets"]
    print("=" * 60)
    print("单元 U%03d 动笔前必读清单" % unit)
    print("=" * 60)
    print("1. 持久清单（single source of truth）：")
    print("   %s" % a["persistent"])
    print("2. 场景词条：%s" % a["scene_doc"])
    print("3. 角色词条：%s" % a["char_doc"])
    lap = a.get("public_lapian")
    if lap:
        print("3b. 公共拉片库（视觉参考·五库闸门之一，原料过蒸馏五步）：%s" % lap)
    print("4. 本单元角色状态：%s" % form)
    print("5. 本单元 UI 配色：%s" % ui)
    if chain:
        print("6. 必含动作链（全部出现）：%s" % chain["must_all"])
        print("7. 前景遮罩：%s" % c["R8_foreground_mask"]["require_any"])
    print("-" * 60)
    print("写完执行：python3 【规则中枢】/scripts/verify_units.py verify "
          "\"3_分镜正片/S2/正片_新S2_20261008\" --unit %d" % unit)

# ---------- 入口 ----------
def cmd_verify(args):
    files = unit_files(args.folder)
    only = {int(x) for x in args.unit.split(",") if x.strip()} if args.unit else None
    active = set(CFG["active_units"])

    total_err = 0
    checked, pending = 0, 0
    tags_fired = set()
    for unit, path in files:
        if only is not None and unit not in only:
            continue
        if not args.fixture and unit not in active:
            pending += 1
            continue
        checked += 1
        errs = verify_unit(unit, path)
        if errs:
            print("\n【U%03d｜%s】%d 条 ERROR"
                  % (unit, os.path.basename(path), len(errs)))
            for tag, detail in errs:
                tags_fired.add(tag)
                print("  [%s] %s" % (tag, detail))
            total_err += len(errs)

    print("\n" + "-" * 60)
    if only is None and not args.fixture:
        print("核销单元 %d 个；待升级旧单元 %d 个（升级后把编号加进 "
              "S2核销规则.json·active_units）" % (checked, pending))
    print("结果：ERROR %d 条 → %s"
          % (total_err, "全部通过 ✅" if total_err == 0 else "存在必须修复项 ❌"))
    return 1 if total_err else 0

def main():
    global CFG
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        p.add_argument("--config", default="",
                       help="项目规则 JSON 路径（缺省回退脚本旁 ../规则配置/S2核销规则.json）")

    pv = sub.add_parser("verify")
    pv.add_argument("folder")
    pv.add_argument("--unit", default="")
    pv.add_argument("--fixture", action="store_true",
                    help="测试用：忽略 active_units 门控")
    add_common(pv)

    pb = sub.add_parser("brief")
    pb.add_argument("unit", type=int)
    add_common(pb)

    pa = sub.add_parser("ask", help="交付前逐项自问")
    pa.add_argument("file")
    add_common(pa)

    a = ap.parse_args()
    CFG = load_cfg(a.config or None)
    if a.cmd == "verify":
        sys.exit(cmd_verify(a))
    if a.cmd == "brief":
        brief(a.unit)
    if a.cmd == "ask":
        sys.exit(cmd_ask(a))

if __name__ == "__main__":
    main()
