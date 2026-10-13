#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lapian_lib.py · 拉片公共库接入（纯标准库，零依赖）

把外接卷《拉片工作区》的成片拉片笔记切块、建成语义索引，供本项目随时召回，
不复制源文件；外接卷未挂载时给出明确提示。

用法:
  python3 scripts/lapian_lib.py status                 挂载/索引状态
  python3 scripts/lapian_lib.py index [--rebuild]      扫描笔记→切块→建索引
  python3 scripts/lapian_lib.py search "<创作需求>" [-n 8] [--work 咒术回战]
      语义召回（字符 unigram+bigram 余弦），输出 作品/文件/块标题/命中片段
  python3 scripts/lapian_lib.py grep "<专有名词>"       关键词精确命中
"""
import argparse, json, math, os, re, sys
from collections import Counter
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CFG_PATH = os.path.join(ROOT, ".lapian", "config.json")

# ---------- 配置 ----------
def load_cfg():
    with open(CFG_PATH, encoding="utf-8") as f:
        return json.load(f)

def resolve_root(cfg):
    for r in cfg["roots"]:
        if os.path.isdir(r):
            return r
    return None

def index_path(cfg):
    return os.path.join(ROOT, cfg["index_file"])

# ---------- 语义向量（与影子 studio.py 同款：unigram+bigram） ----------
def vectorize(text):
    t = re.sub(r"\s+", "", text or "")
    v = Counter()
    for ch in t:
        v[ch] += 1.0
    for i in range(len(t) - 1):
        v[t[i:i+2]] += 1.5
    norm = math.sqrt(sum(c * c for c in v.values())) or 1.0
    return {g: c / norm for g, c in v.items()}

def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return round(sum(c * b.get(g, 0.0) for g, c in a.items()), 4)

# ---------- 扫描 + 切块 ----------
def iter_note_files(cfg, base):
    excl_dirs = set(cfg["exclude_dirs"])
    excl_top = set(cfg["exclude_top"])
    for top in sorted(os.listdir(base)):
        p_top = os.path.join(base, top)
        if not os.path.isdir(p_top) or top.startswith((".", "_")) or top in excl_top:
            continue
        for dp, dns, fns in os.walk(p_top):
            dns[:] = [d for d in dns if d not in excl_dirs and not d.startswith(".")]
            for fn in sorted(fns):
                if fn.endswith(".md") and not fn.startswith("."):
                    yield os.path.join(dp, fn)

def split_chunks(text, max_lines):
    """按 markdown 标题切块；超过 max_lines 的块按行再切。"""
    lines = text.splitlines()
    blocks, buf, head = [], [], ""
    def flush():
        nonlocal buf, head
        body = [l for l in buf]
        if any(x.strip() for x in body):
            blocks.append((head, body))
        buf = []
    for ln in lines:
        if re.match(r"^#{1,4}\s", ln):
            flush()
            head = ln.lstrip("#").strip()
        buf.append(ln)
        if len(buf) >= max_lines and re.match(r"^\|", ln) is None:
            # 长块硬切，并保留一个接续标题
            flush()
            head = (head + "（续）") if head else ""
    flush()
    return blocks

def build_index(cfg, rebuild=False):
    base = resolve_root(cfg)
    if not base:
        print("✗ 未找到拉片公共库（外接卷《共用》似乎未挂载）。")
        print("  已探测:\n   " + "\n   ".join(cfg["roots"]))
        return 1
    ip = index_path(cfg)
    if os.path.exists(ip) and not rebuild:
        print("索引已存在，加 --rebuild 可重建。")
        return 0

    chunks = []
    files = 0
    for path in iter_note_files(cfg, base):
        files += 1
        work = os.path.relpath(path, base).split(os.sep)[0]
        rel = os.path.relpath(path, base)
        with open(path, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        title = ""
        m = re.search(r"^#\s+(.+)$", text, re.M)
        if m:
            title = m.group(1).strip()
        for head, body in split_chunks(text, cfg["chunk_max_lines"]):
            snippet = "\n".join(body).strip()
            if len(snippet) < 12:
                continue
            chunks.append({
                "work": work,
                "file": rel,
                "doc": title,
                "head": head,
                "text": snippet[:1200],
                "vec": vectorize(head + "\n" + snippet),
            })
    os.makedirs(os.path.dirname(ip), exist_ok=True)
    with open(ip, "w", encoding="utf-8") as f:
        json.dump({
            "_meta": {"root": base, "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
                      "files": files, "chunks": len(chunks)},
            "chunks": chunks,
        }, f, ensure_ascii=False)
    print(f"✓ 索引完成：{files} 篇笔记 → {len(chunks)} 个语义块")
    print(f"  源: {base}")
    print(f"  缓存: {os.path.relpath(ip)}")
    return 0

# ---------- 加载索引 ----------
def load_index(cfg):
    ip = index_path(cfg)
    if not os.path.exists(ip):
        return None
    with open(ip, encoding="utf-8") as f:
        return json.load(f)

def compact(text, n=240):
    t = re.sub(r"\n{2,}", "\n", text).strip()
    return t if len(t) <= n else t[:n] + " …"

def cmd_search(cfg, query, n, work):
    data = load_index(cfg)
    if not data:
        print("索引不存在，先运行: python3 scripts/lapian_lib.py index")
        return 1
    qv = vectorize(query)
    scored = []
    for i, c in enumerate(data["chunks"]):
        if work and c["work"] != work:
            continue
        scored.append((cosine(qv, c["vec"]), i))
    scored.sort(reverse=True)
    print(f"查询：{query}\n源库：{data['_meta']['root']}\n")
    for rank, (score, i) in enumerate(scored[:n], 1):
        c = data["chunks"][i]
        print(f"── TOP{rank}  相似度 {score} ──")
        print(f"作品：{c['work']}｜文件：{c['file']}")
        if c["head"]:
            print(f"段落：{c['head']}")
        print(compact(c["text"]))
        print()
    return 0

def cmd_grep(cfg, keyword, n):
    data = load_index(cfg)
    if not data:
        print("索引不存在，先运行: python3 scripts/lapian_lib.py index")
        return 1
    hits = 0
    for c in data["chunks"]:
        if keyword in c["text"] or keyword in c["head"]:
            hits += 1
            print(f"[{c['work']}] {c['file']}｜{c['head']}")
            for ln in c["text"].splitlines():
                if keyword in ln:
                    print("   " + compact(ln, 160))
            print()
            if hits >= n:
                break
    print(f"共 {hits} 块命中“{keyword}”")
    return 0

def cmd_status(cfg):
    base = resolve_root(cfg)
    print("=== 拉片公共库状态 ===")
    if base:
        print(f"✓ 已挂载：{base}")
    else:
        print("✗ 未挂载（外接卷《共用》未连接）。探测路径：")
        for r in cfg["roots"]:
            print("   -", r)
    ip = index_path(cfg)
    if os.path.exists(ip):
        data = load_index(cfg)
        m = data["_meta"]
        print(f"✓ 索引：{m['chunks']} 块 / {m['files']} 篇，建于 {m['built']}")
        if base and m.get("root") != base:
            print("  注意：当前挂载根与建索引时不同，建议 --rebuild")
    else:
        print("· 尚无索引，运行 python3 scripts/lapian_lib.py index 建立。")
    return 0

def main():
    ap = argparse.ArgumentParser(description="拉片公共库接入（纯标准库）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p_idx = sub.add_parser("index"); p_idx.add_argument("--rebuild", action="store_true")
    p_s = sub.add_parser("search")
    p_s.add_argument("query"); p_s.add_argument("-n", type=int, default=8)
    p_s.add_argument("--work", default=None, help="限定作品目录名")
    p_g = sub.add_parser("grep")
    p_g.add_argument("keyword"); p_g.add_argument("-n", type=int, default=12)
    args = ap.parse_args()

    cfg = load_cfg()
    if args.cmd == "status":
        sys.exit(cmd_status(cfg))
    elif args.cmd == "index":
        sys.exit(build_index(cfg, args.rebuild))
    elif args.cmd == "search":
        sys.exit(cmd_search(cfg, args.query, args.n, args.work))
    elif args.cmd == "grep":
        sys.exit(cmd_grep(cfg, args.keyword, args.n))

if __name__ == "__main__":
    main()
