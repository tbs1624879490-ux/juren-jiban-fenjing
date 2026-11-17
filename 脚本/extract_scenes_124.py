#!/usr/bin/env python3
"""extract_scenes_124.py — 从《剧本.md》(124集底本)确定性提取场头/集头/钩子数据
v2·2026-11-17：①人物/地点/钩列全量不截断②连场检测放宽(A档全等/前缀·B档主地名候选)③幕界检测按场号N切换④集列=场号N取整
输出：分场档案表数据(markdown)。底本零改动·只读提取。承王导令「对应每一幕继续分场」
"""
import re, sys

SRC = '0、分场分幕和剧本/剧本.md'

def main():
    lines = open(SRC, encoding='utf-8').read().split('\n')
    episodes = []
    scenes = []
    hooks = []
    eds = []

    ep_re = re.compile(r'^### 第 (\d+) 集（(.*)）')
    sc_re = re.compile(r'^#### 第(\d+)集 (\S+) (\S+) (.*)$')
    io_re = re.compile(r'^(内/外|外/内|内|外)\s*(.*)$')

    for i, raw in enumerate(lines, 1):
        ln = i
        s = raw.strip()
        m = ep_re.match(s)
        if m:
            episodes.append({'n': int(m.group(1)), 'tag': m.group(2), 'ln': ln})
            continue
        m = sc_re.match(s)
        if m:
            ep_head, scene_no, tod, rest = m.groups()
            m2 = io_re.match(rest)
            if m2:
                io, rest2 = m2.group(1), m2.group(2)
            else:
                io, rest2 = '多场景', rest
            cast = ''
            place = rest2
            if '，人物：' in rest2:
                place, cast = rest2.rsplit('，人物：', 1)
            half = '.' in scene_no.split('-', 1)[0]
            scenes.append({'ep_head': int(ep_head), 'scene_no': scene_no,
                           'tod': tod, 'io': io, 'place': place.strip(),
                           'cast': cast.strip(), 'ln': ln, 'half': half})
            continue
        if s.startswith('▶ 下集钩'):
            hooks.append({'ln': ln, 'text': s})
        elif 'ED钉' in s and s.startswith('*'):
            eds.append({'ln': ln, 'text': s})

    def scene_of(ln):
        cur = None
        for sc in scenes:
            if sc['ln'] < ln:
                cur = sc
            else:
                break
        return cur

    def sn_n(scene_no):
        return float(scene_no.rsplit('-', 1)[0])

    def act_of(n):
        return 1 if n <= 32 else (2 if n <= 86 else 3)

    for sc in scenes:
        sc['hook'] = ''
    for h in hooks:
        sc = scene_of(h['ln'])
        if sc:
            sc['hook'] = h['text'].replace('▶ 下集钩：', '').strip()
    for sc in scenes:
        sc['ed'] = any(abs(e['ln'] - sc['ln']) < 40 and e['ln'] > sc['ln'] for e in eds)

    # 连场检测：A档=地点全等或一方为另一方前缀；B档=「→」前主地名相等（候选·跳时/转场待复核）
    def main_place(p):
        return p.split('→')[0].strip().rstrip('·，, ')

    links_a, links_b = [], []
    for a, b in zip(scenes, scenes[1:]):
        pa, pb = a['place'], b['place']
        if not pa or not pb or pa == '多场景' or pb == '多场景':
            continue
        if pa == pb:
            links_a.append((a['scene_no'], b['scene_no'], pa))
        elif pa.startswith(pb) or pb.startswith(pa):
            links_a.append((a['scene_no'], b['scene_no'], pa if len(pa) < len(pb) else pb))
        elif main_place(pa) and main_place(pa) == main_place(pb):
            links_b.append((a['scene_no'], b['scene_no'], main_place(pa)))

    # 幕界检测：场号N跨32/33·86/87
    bounds = []
    for a, b in zip(scenes, scenes[1:]):
        na, nb = sn_n(a['scene_no']), sn_n(b['scene_no'])
        if na <= 32 < nb:
            bounds.append(('幕一|幕二', a['scene_no'], b['scene_no']))
        if na <= 86 < nb:
            bounds.append(('幕二|幕三', a['scene_no'], b['scene_no']))

    out = []
    out.append('# 底本确定性提取·场档案（extract_scenes_124.py v2·20261117）')
    out.append('')
    out.append(f'统计：集头行{len(episodes)}（唯一集号{len(set(e["n"] for e in episodes))}）·场{len(scenes)}'
               f'（插场半集{sum(1 for s in scenes if s["half"])}个）·下集钩{len(hooks)}·ED钉{len(eds)}'
               f'·连场A档{len(links_a)}对·B档候选{len(links_b)}对')
    out.append('')
    out.append('## 一、场档案总表（幕｜集｜分场号｜底本场号｜时段｜内外｜地点｜人物｜集尾钩｜ED钉）')
    out.append('')
    out.append('| 幕 | 集 | 分场号 | 底本场号 | 时段 | 内外 | 地点 | 人物 | 集尾钩（全句） | ED |')
    out.append('|---|---|---|---|---|---|---|---|---|---|')
    # 字母分场号：按底本场号N分组·场序M映射a/b/c…（半集N如70.5独立成组）
    from collections import OrderedDict
    groups = OrderedDict()
    for sc in scenes:
        key = sc['scene_no'].rsplit('-', 1)[0]
        groups.setdefault(key, []).append(sc)
    letter_of = {}
    for key, grp in groups.items():
        for idx, sc in enumerate(grp):
            letter_of[sc['scene_no']] = key + chr(ord('a') + idx)
    for sc in scenes:
        n = int(sn_n(sc['scene_no']))
        act = act_of(sn_n(sc['scene_no']))
        out.append(f'| {act} | {n} | {letter_of[sc["scene_no"]]} | {sc["scene_no"]} | '
                   f'{sc["tod"]} | {sc["io"]} | {sc["place"]} | {sc["cast"]} | {sc["hook"]} | {"✔" if sc["ed"] else ""} |')
    out.append('')
    out.append('## 二、同地点连场（A档·全等/前缀）')
    out.append('')
    for a_no, b_no, pl in links_a:
        out.append(f'- {a_no} → {b_no}：{pl}')
    out.append('')
    out.append('## 三、连场候选（B档·主地名同·跳时/转场待复核）')
    out.append('')
    for a_no, b_no, pl in links_b:
        out.append(f'- {a_no} → {b_no}：{pl}')
    out.append('')
    out.append('## 四、幕界交界场（场号N跨幕）')
    out.append('')
    for tag, a_no, b_no in bounds:
        out.append(f'- {tag}：{a_no} → {b_no}')
    out.append('')
    out.append('## 五、ED钉行')
    out.append('')
    for e in eds:
        out.append(f'- L{e["ln"]}：{e["text"][:60]}')

    print('\n'.join(out))

if __name__ == '__main__':
    main()
