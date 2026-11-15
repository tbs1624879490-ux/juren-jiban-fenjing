#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_idle_shots.py —— 空镜·薄镜·可合并信号 查重器（2026-10-11 意见75）
====================================================================
用户口径：第一个单元空两秒、第二个还空两秒、第三个照样空两秒——
说明信息量缺失，前后单元要考虑并合。本脚本把这件事变成机器检测：
  【E】空镜镜清单   —— 正文自述"空镜/纯空镜/无人"的镜（列出＋验转场功能）
  【A】静帧开场链   —— 连续 ≥3 单元以静态画面接续开场＝节奏停滞
  【B】双薄接缝     —— 相邻单元的末镜/首镜都薄（<40字）或空镜＝可合并信号（ERROR）
  【C】大远景挤占比 —— 单元内大远景镜占比过高＝空旷定调挤占时长（WARN）
  【D】环境描述雷同 —— 相邻单元【场景环境】段高度相似＝复制粘贴嫌疑（WARN）

规则外置：../规则配置/S2核销规则.json（R18_info_density 复用同一密度底线）。
退出码：存在 B 类（ERROR）返回 1；否则 0。纯标准库实现。

用法：
  python3 check_idle_shots.py "<分镜目录>"
"""
import sys, os, re, json, glob

def load_cfg(cfg_path=None):
    if cfg_path:
        with open(cfg_path, encoding="utf-8") as f:
            return json.load(f)
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "规则配置", "S2核销规则.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)

CFG = None   # main() 里按 --config 或默认路径加载（支持多项目：脚本通用、配置项目化）

STATIC_WORDS = ["僵住", "僵在", "定住", "凝固", "定格", "尬凝",
                "钉在原地", "钉住", "一动不动", "静止", "谁都没先开口"]
EMPTY_WORDS = ["空镜", "纯空镜", "无人", "只有环境"]
TRANSIT_WORDS = ["转场", "泛白", "回忆", "切回", "蒙太奇", "闪回"]

def field_line(block, field):
    m = re.search(r"^[-\s]*" + re.escape(field) + r"[：:](.+)$", block, re.M)
    return m.group(1).strip() if m else ""

def unit_files(folder):
    rx = re.compile(CFG["unit_fn_re"])
    active = set(CFG["active_units"])
    out = []
    for f in sorted(glob.glob(os.path.join(folder, "S2_单元*.md"))):
        m = rx.match(os.path.basename(f))
        if m and int(m.group(1)) in active:
            out.append((int(m.group(1)), f))
    out.sort(key=lambda x: x[0])
    return out

def parse_unit(path):
    """-> dict(no, body, notes, scenes=[(镜号, 景别, 主体动态)], env)"""
    text = open(path, encoding="utf-8").read()
    m = re.search(CFG["separator_re"], text, re.M)
    body = text[:m.start()] if m else text
    notes = text[m.start():] if m else ""
    marks = [(mm.start(), int(mm.group(1)))
             for mm in re.finditer(CFG["shot_title_re"], body)]
    shots = []
    for i, (pos, num) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        blk = body[pos:end]
        shots.append({
            "no": num,
            "jingbie": field_line(blk, "景别"),
            "dyn": field_line(blk, "主体动态"),
        })
    env = ""
    me = re.search(r"【场景环境】\n(.*?)(?=\n【人物固定站位】|\Z)", body, re.S)
    if me:
        env = me.group(1).strip()
    # 承接行（备注区）取静态判断用
    mc = re.search(r"承接[：:](.+)$", notes, re.M)
    hook = mc.group(1).strip() if mc else ""
    return {"no": int(re.search(r"单元(\d+)", path).group(1)),
            "path": path, "shots": shots, "env": env, "hook": hook}

def grams(s, n=3):
    s = re.sub(r"\s", "", s)
    return set(s[i:i + n] for i in range(max(0, len(s) - n + 1)))

def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def is_static(s):
    return any(w in s for w in STATIC_WORDS)

def main():
    global CFG, MIN_CHARS
    args = [a for a in sys.argv[1:] if a != "--config"]
    cfg_path = ""
    if "--config" in sys.argv[1:]:
        i = sys.argv.index("--config")
        cfg_path = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        args = [a for j, a in enumerate(sys.argv[1:]) if a != "--config" and j != i]
    if cfg_path:
        CFG = load_cfg(cfg_path)
    else:
        CFG = load_cfg(None)
    MIN_CHARS = CFG.get("R18_info_density", {}).get("min_chars", 40)
    folder = args[0]
    units = [parse_unit(p) for _, p in unit_files(folder)]
    units = [u for u in units if u["shots"]]
    E, W = [], []

    print("=" * 64)
    print("空镜·薄镜·可合并信号 查重：%s（共 %d 个升级单元）" % (folder, len(units)))
    print("=" * 64)

    # 【E】空镜镜清单
    print("\n【E｜空镜镜清单】")
    empties = []
    for u in units:
        for s in u["shots"]:
            text_one = s["dyn"] + " " + s["jingbie"]
            if any(w in text_one for w in EMPTY_WORDS):
                ok = any(w in s["dyn"] for w in TRANSIT_WORDS)
                empties.append((u["no"], s["no"], ok))
                print("  U%03d 镜%d 空镜（%s）——%s"
                      % (u["no"], s["no"],
                         "带转场功能 ✔" if ok else "⚠ 无转场功能词、纯氛围占秒",
                         s["dyn"][:40]))
    if not empties:
        print("  无")

    # 【A】静帧开场链（连续 ≥3 单元：承接行或首镜主体动态为静态）
    print("\n【A｜静帧开场链（连续≥3单元静态接续）】")
    chains, cur = [], []
    for u in units:
        first = u["shots"][0]
        if is_static(u["hook"]) or is_static(first["dyn"]):
            cur.append(u["no"])
        else:
            if len(cur) >= 3:
                chains.append(cur)
            cur = []
    if len(cur) >= 3:
        chains.append(cur)
    for ch in chains:
        W.append("A 静帧开场链 U%03d→U%03d（%d 连）" % (ch[0], ch[-1], len(ch)))
        print("  U%03d→U%03d 连续 %d 个单元以静态画面接续开场——节奏停滞："
              "考虑中间单元改动势开场、或前后并合" % (ch[0], ch[-1], len(ch)))
    if not chains:
        print("  无")

    # 【B】双薄接缝（ERROR 级：可合并信号）
    print("\n【B｜双薄接缝（相邻单元缝合处双薄＝可合并信号）】")
    def thin(s):
        return len(s["dyn"]) < MIN_CHARS or any(
            w in s["dyn"] + s["jingbie"] for w in EMPTY_WORDS)
    hit_b = False
    for a, b in zip(units, units[1:]):
        ta, tb = thin(a["shots"][-1]), thin(b["shots"][0])
        if ta and tb:
            hit_b = True
            E.append("B 接缝双薄 U%03d镜%d — U%03d镜%d"
                     % (a["no"], a["shots"][-1]["no"], b["no"], b["shots"][0]["no"]))
            print("  U%03d 末镜（%d字）— U%03d 首镜（%d字）：两镜都薄——"
                  "缝合处信息空转，两单元内容可考虑并合"
                  % (a["no"], len(a["shots"][-1]["dyn"]),
                     b["no"], len(b["shots"][0]["dyn"])))
    if not hit_b:
        print("  无")

    # 【C】大远景挤占比（WARN）
    print("\n【C｜大远景挤占比（单元内大远景镜 ≥ 半数）】")
    hit_c = False
    for u in units:
        far = sum(1 for s in u["shots"] if "大远景" in s["jingbie"])
        if len(u["shots"]) >= 3 and far >= (len(u["shots"]) + 1) // 2:
            hit_c = True
            W.append("C U%03d 大远景 %d/%d 镜" % (u["no"], far, len(u["shots"])))
            print("  U%03d：%d/%d 镜是大远景——空旷定调挤占时长，考虑换中近景实拍细节"
                  % (u["no"], far, len(u["shots"])))
    if not hit_c:
        print("  无")

    # 【D】场景环境雷同（WARN：3-gram Jaccard > 0.55）
    print("\n【D｜场景环境雷同（相邻单元 3-gram 相似度 > 0.55）】")
    hit_d = False
    for a, b in zip(units, units[1:]):
        sim = jaccard(grams(a["env"]), grams(b["env"]))
        if sim > 0.55:
            hit_d = True
            W.append("D U%03d—U%03d 环境相似度 %.2f" % (a["no"], b["no"], sim))
            print("  U%03d—U%03d 场景环境相似度 %.2f——同场景可接受，"
                  "但检查是否整段复制（同景应换观察位/加入单元新物件）"
                  % (a["no"], b["no"], sim))
    if not hit_d:
        print("  无")

    print("\n" + "-" * 64)
    print("结果：ERROR %d 条（B类可合并信号）、WARN %d 条（A/C/D类提示）→ %s"
          % (len(E), len(W), "全部通过 ✅" if not E else "存在缝合处空转，需处理 ❌"))
    return 1 if E else 0

if __name__ == "__main__":
    sys.exit(main())
