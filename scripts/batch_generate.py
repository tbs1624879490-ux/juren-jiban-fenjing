# -*- coding: utf-8 -*-
"""批量出图驱动：按 batch_jobs.ALL 顺序生成并归档。
- 断点续跑：目标文件已存在则跳过
- 失败自动重试（默认 2 次）
- 实时写日志 logs/batch_generate.log
用法:
  python3 scripts/batch_generate.py            # 跑全部
  python3 scripts/batch_generate.py scenes     # 仅场景
  python3 scripts/batch_generate.py props      # 道具+异种
"""
import os, sys, time, datetime, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grsai_image_api as g
from batch_jobs import SCENES, PROPS, SPECIES, STYLE_SUFFIX

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGDIR = os.path.join(ROOT, "logs")
os.makedirs(LOGDIR, exist_ok=True)
LOG = os.path.join(LOGDIR, "batch_generate.log")

def log(msg):
    line = f"[{datetime.datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_one(job, retries=2):
    sub, name, ratio, desc = job
    save_dir = os.path.join(ROOT, "【项目库】", sub)
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, name)
    if os.path.exists(path):
        log(f"SKIP {name}（已存在）")
        return "skip"
    prompt = f"{desc}，{STYLE_SUFFIX}" if sub == "场景卡" else desc
    for attempt in range(1, retries + 2):
        try:
            res = g.generate_and_wait(prompt, model=g.DEFAULT_MODEL,
                                      aspect_ratio=ratio, verbose=False,
                                      max_wait=240)
            status = res.get("status")
            if status == "succeeded" and res.get("results"):
                url = res["results"][0]["url"]
                g.download_image(url, path)
                log(f"DONE {name} <- {url}")
                return "done"
            log(f"WARN {name} status={status} attempt={attempt}")
        except Exception as e:
            log(f"WARN {name} 异常 attempt={attempt}: {e}")
        time.sleep(3)
    log(f"FAIL {name}")
    return "fail"

def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    jobs = {"scenes": SCENES, "props": PROPS + SPECIES,
            "all": SCENES + PROPS + SPECIES}[which]
    # 可选索引范围：start end（1 起，含两端），用于前台分批
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    end = int(sys.argv[3]) if len(sys.argv) > 3 else len(jobs)
    batch = jobs[start - 1:end]
    log(f"==== 批量开始 which={which} 范围={start}-{end} 本批 {len(batch)} 张 ====")
    counts = {"done": 0, "skip": 0, "fail": 0}
    for job in batch:
        log(f"[{start + counts['done'] + counts['skip'] + counts['fail']}/{len(jobs)}] {job[1]}")
        counts[run_one(job)] += 1
    log(f"==== 批量结束 完成={counts['done']} 跳过={counts['skip']} 失败={counts['fail']} ====")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("致命异常:\n" + traceback.format_exc())
        raise
