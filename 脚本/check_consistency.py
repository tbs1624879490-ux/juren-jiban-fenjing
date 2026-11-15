#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分镜跨单元一致性强制校验脚本（storyboard-kb-manager 配套）
====================================================================
用途：一幕分镜创作 / 修改完成后，对该幕目录下所有「单元N」md 做一致性检核，
确保每个单元都是独立、自包含、前后一致的个体。
· 衍生系列隔离（v2.18·2026-09-27）：--only 裸幕名 key 不吞并【第X幕·15秒版】/
  【第X幕·30秒版】/【最终版】/【重置版】前缀文件——衍生系列仅当 key 点名完整
  系列名（如 --only 第七幕·15秒版）才纳入，防两版本同号单元撞号、基线互污染。

检核维度（对应用户永久铁律）：
  A. 结构完整性   每单元头部六栏齐全；每分镜六要素齐全、编号连续（硬切不写转场，仅设计转场写【转场】）
  B. 场景自包含   【场景环境】不得缺细节；材质 / 光源 / 反射 / 外景动态必须在场
     · 同场景一致  同一地点在不同单元必须「一字不差」复制（--same 指定严格组）
  C. 光源 / 天光  光源不能缺；全幕昼夜基调统一；白天单元混入夜景元素即报错
  D. 人物位置     【人物固定站位】不能缺；输出相邻单元「上一止点→下一场开场」衔接清单
     · 道具连续   关键道具（如花）逐单元持有方序列，防止「道具飞回」
  E. 人设偏离     角色禁用演法 / 错名扫描（可被角色库「已否决」小节扩展）；外放尬演表情扫描（OVERACT）
     · 构词保护   （v2.10·2026-09-23）「消杀气流/消杀光闸」里的「杀气」是消毒流程名词、非陆遥遥
                  禁用演法——命中前缀「消」（消杀）即豁免，防子串误报（仿 v2.5 黄白菊豁免）
  F. 参照空指针   禁止「参照 / 对齐 / 以…为准 / 同上 / 承接单元 / 最终版单元 / 对照单元」
  G. 转场链       单元 N 末尾指向 N+1，链不得断（v2.3 双格式：末尾「遮罩转单元N《》」或下一单元
                  铁律「开场承接…」任一存在即算链通，两者皆缺才 WARN）
  H. 道具形态     道具首次定了具体形态后，每个「在场单元」的【全局铁律】都要锁齐形态锚点、
                  一字不落复现；不得缩水（整束→一朵/单支）、不得变色变形（白瓣黄心→明黄/红玫瑰）
  I. 触发词地图   （v2.0·--index-map 开启）总索引里登记的库文件引用必须真实落地，空指针 ERROR；
                  编剧叙事方法库条目须含 规则/做法/例证/迁移 四段（缺 WARN）；
                  单元声明所属改编段时，对应意见单须存在且"已确认"（缺/未确认 WARN）
  J. 人称代词     除「台词 / OS：」行外，描述文字禁你/我/他/她、一律直写角色名（ERROR，2026-09-18）
  K. 景别内容     近景(胸部以上)出现腿脚/全身位移大动作给 WARN（特写/大特写是局部镜头不判，2026-09-18）
  L. 外部专名     （v2.1·--ban-foreign-names 开启）扫描【项目库】全部 md，外部作品角色/组织/地名/
                  术语专名一律 ERROR；"来源：斩神Sx EPxx 时间码"锚点行与专名清洗日志行自动豁免。
                  用于拉片反哺入库后的违禁词 QA（3.7 SOP 铁律"外部专名不进项目库"）。
  M. 口白脏话锁   （v2.2·2026-09-21）按台词归属（角色，演法）切分口白，陆遥遥全剧无脏话——
                  「锤子/卧槽/妈的…」命中即 ERROR；赶人只准「你少来！」「滚开！」「我说你滚啊！」
  N. 特写双人切   （v2.2·2026-09-21）特写/大特写级单镜装下两名说话人=ERROR（特写框不住两人对切）：
                  要么拆成两个分镜正反打，要么改中景/全景＋横摇运镜一镜带走
  O. 口白报菜名   （v2.2·2026-09-21·WARN）把行为动作念成台词（"两腿发抖/说话都哆嗦"类叙述）——
                  动作交给画面演，口白只留引导句（"从小就怕，你看我这腿"）
  P. 单句十五字   （v2.2·2026-09-21·WARN）口白按句切分，单句>15字提醒"一句一重点"拆短
  Q. 站位矛盾锁   （v2.4·2026-09-22）盘腿坐×头枕腿上＝物理矛盾（盘腿双腿折叠、大腿面被压住、
                  头枕不上去）——枕腿单元站位必须「一条腿平搭沙发面、一条腿盘收沙发边」，
                  或正文写明「盘着的腿顺势放开」过渡，否则 ERROR
  R. 铁律纯约束锁 （v2.5·2026-09-22）铁律只放「承接锚+单元定位+跨镜结构约束+禁忌项」四类——
                  衣着/造型锚属画面造型、统一写【人物固定站位】：铁律出现衣着词（否定语境豁免）
                  即 WARN 提示挪字段；铁律超长告警（>320 字疑似混剧情复述）；28-31 为用户锁定
                  参照模板、保持原样，两类提示均豁免
  S. 神眷冷暗锁   （v2.9·2026-09-23 用户最高指示）神眷人靠吸收负面能量取力：眼瞳光/异能光/能力UI
                  只许蓝·白·黑·红·紫冷暗五色（荧光/微光可）——金光/金瞳/金色光/圣光/亮金面板命中即
                  ERROR；唯一豁免口＝神眷转换后的神圣态（单元明写「神眷转换/神圣态/神迹」即豁免）；
                  成片（第六幕1-31/最终版/30秒版/二~五幕）不追责；否定语境照常豁免
  v2.6·2026-09-23 成片冻结区：第六幕单元1-31为已成片存量（用户拍板「目前工作服务于后续、
                  已成片单元不再修改」），铁律超长/衣着两类提示按「第六幕+单元号」系列作用域
                  豁免、不按裸单元号全局豁免——后续新单元（第六幕32+、第七幕024+）照常全查
  v2.7·2026-09-23 冻结区归桶常开：发现项所引单元号全落冻结区的移入【成片冻结区存量】、
                  不计入 ERROR/WARN 与门禁（ship.sh/pre-commit 不传 --frozen 也生效）；
                  同号冲突防护——被非冻结文件占用的单元号（如第七幕1-23）不参与裸号豁免；
                  跨区发现（引用活跃单元）照常计入；--frozen 可追加显式范围
  扫描范围 v2.2   递归扫描全部子目录（字段精简版/ 等），路径含「备份/旧版参考/TRAE项目配置库」
                  一律排除；同幕重复单元号（同号两版并存）ERROR——防旧稿污染转场链与跨单元校验
  v2.3·2026-09-21 转场链双格式：下一单元铁律「开场承接…」也算链证据——新格式单元不再全量误报
  v2.4·2026-09-22 站位矛盾锁：盘腿×枕腿物理矛盾——场景卡坐法与单元站位双重根治
  v2.5·2026-09-22 铁律纯约束锁：衣着锚禁入铁律（归【人物固定站位】）+锁定模板豁免+
                  道具禁词「黄菊/白菊」在「黄白菊/白黄菊」复合词内的子串误报豁免
  v2.6·2026-09-23 成片冻结区豁免：第六幕1-31（含28-31模板）不再回改，铁律新规只约束后续单元
  v2.7·2026-09-23 冻结区归桶常开+同号冲突防护（第七幕1-23同号不误豁免）+--frozen 追加显式范围
  v2.8·2026-09-23 冻结区归桶支持 A/B 后缀单元号（单元9A≠9），防「单元9A」误入裸号 9 的存量桶
  v2.9·2026-09-23 神眷冷暗锁：金色/圣光/亮金面板等违例词机检（眼瞳光/异能光/能力UI 冷暗五色硬锁，
                  金光(?!泽)放过材质光泽表述；否定语境豁免+神圣态唯一豁免口+成片存量跳过）——
                  第七幕预扫零命中，最终版64/79 与存量二/四幕金光表述均落豁免区，基线零漂移
  v2.10·2026-09-23 人设构词保护：「消杀气流」里的「杀气」误报豁免——命中前一字为「消」即视为
                  消毒流程名词（消杀），不算陆遥遥禁用演法；仿 v2.5 黄白菊复合词豁免先例
  v2.11·2026-09-26 扫描排除加「资料包」——SKILL 分发快照不进校验，防同号并存假报
  v2.12·2026-09-26 子镜号支持+固定镜数废除（用户裁决）：分镜 6-1/9-6-3 插入镜键为整数元组，
                  连续性按插入镜规则校验（严格递增/同级差1/父镜后首插必-1/出子镜接父级下一同级）；
                  A/B 拆分单元起始镜号不强制为1（承接父单元镜列）；删 --expect-shots——
                  镜数是时长承载评估的结果，机检不设期望镜数
  v2.13·2026-09-26 承接锚三格式开场识别（承接锚（紧接单元N末镜·变体）/跨幕焊缝/正文带号），
                  转场链45条版式误报清零；新增锚号过期校验（拆分/插单元后未更新即WARN）；
                  【全局强制铁律】视同【全局铁律】字段别名（零内容改动放行）
  v2.14·2026-09-26 昼夜判定否定感知：DAY_MARK（白天/天光/日光/阳光）命中前8字含无/禁/不/没/别/非
                  即不算白天标记——「走廊尽头无天光」「永无休止的阳光」不再把夜单元误判成白天
                  （单元24/39 天光·烟花误报清零）；rule 提取同步兼容【全局强制铁律】别名；
                  无效词②正则收紧：括号内夜景词（月亮/霓虹/烟花/窗灯/雨面/红灯笼）前必须紧跟
                  否定词才算「跨时段否定清单」——美术登记条目名（壬-02霓虹赛博…）与烟花正拍描述
                  不再误报（单元27×2/39×5/66×1 清零）

用法：
  python3 check_consistency.py "<一幕分镜目录>" [选项]
选项：
  --same a,b,c          指定这些单元号的【场景环境】必须逐字一致（严格 ERROR）
  --prop 词             追踪某道具逐单元持有方，可多次，如 --prop 洋甘菊 --prop 花
  --rolelib <目录>      角色库目录，自动读各角色 md「已否决/禁用」小节扩充禁用词
  --day / --night       强制全幕昼夜基调（默认自动判定）
  --min-scene N         场景环境最短字数，低于则 WARN（默认 80）
  --index-map <md>      v2.0：触发词调用地图路径，开启空指针/方法库四段/改编段意见单校验
  --ban-foreign-names   v2.1：开启外部作品专名扫描（库目录取 --index-map 同级或 --lib-dir）
  --lib-dir <目录>      v2.1：显式指定【项目库】根目录（供 --ban-foreign-names 扫描）
退出码：存在 ERROR 返回 1（可接提交前自检 / 钩子），仅 WARN / 通过返回 0。

纯标准库实现，不依赖第三方。
"""
import sys, os, re, glob, argparse
import json

# ---------- 规则加载（P1：词表/字典/正则全部外置 JSON，迭代规则只改 JSON 不改代码） ----------
def _load_rules():
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "规则配置", "checker规则.json")
    with open(cfg_path, encoding="utf-8") as _f:
        return json.load(_f)

_R = _load_rules()

HEAD_FIELDS = _R["head_fields"]
SHOT_FIELDS = _R["shot_fields"]

MAT_WORDS   = _R["mat_words"]
LIGHT_WORDS = _R["light_words"]
REFL_WORDS  = _R["refl_words"]
OUT_WORDS   = _R["out_words"]

NIGHT_BAN   = _R["night_ban"]
DAY_MARK    = _R["day_mark"]
NIGHT_MARK  = _R["night_mark"]

REF_PATTERN = _R["ref_pattern"]

DEFAULT_BAN = _R["default_ban"]
PERSONA_GUARD_PREFIX = _R["persona_guard_prefix"]

INVALID_DEFAULT = _R["invalid_default"]

AGE_BAN  = _R["age_ban"]
BANNED_PROP = _R["banned_prop"]
AGE_WARN_RE = re.compile(_R["age_warn_re"])

INVALID_TIME_NEG = _R["invalid_time_neg"]
INVALID_TIME_NEG_RE = re.compile(_R["invalid_time_neg_re"])
TIME_WORD = _R["time_word"]

META_INSTRUCTION = _R["meta_instruction"]
REFIMG_LOOK_REDUNDANT = _R["refimg_look_redundant"]

SPOKEN_NEG_META = re.compile(_R["spoken_neg_meta"])
HARD_CUT_RE = re.compile(_R["hard_cut_re"])

RULE_MAXLEN = _R["rule_maxlen"]
SPOKEN_MAXLEN = _R["spoken_maxlen"]

CLOTHING_ANCHOR = _R["clothing_anchor"]

LOCKED_TEMPLATE_UNITS = set(_R["locked_template_units"])
_fr = _R["frozen_filmed_range"]
FROZEN_FILMED_UNITS = set(range(_fr[0], _fr[1]))

FILMED_PREFIXES = tuple(_R["filmed_prefixes"])

COLD_DARK_GOLD_RE = re.compile(_R["cold_dark_gold_re"])

OVERACT = _R["overact"]

ROLE_PROFANITY_BAN = _R["role_profanity_ban"]

DIALOG_ATTR_RE = re.compile(_R["dialog_attr_re"])

ACTION_AS_SPEECH = _R["action_as_speech"]
SPEECH_CUE_OK = _R["speech_cue_ok"]

SCAN_EXCLUDE = _R["scan_exclude"]

NAME_FIX = _R["name_fix"]

PROP_SPEC = _R["prop_spec"]

SHOT_SIZE_NAME = {int(_k): _v for _k, _v in _R["shot_size_name"]}
_SHOT_SIZE_TERMS = [tuple(_x) for _x in _R["shot_size_terms"]]
_SHOT_SIZE_RE = re.compile("|".join(re.escape(_w) for _w, _ in sorted(_SHOT_SIZE_TERMS, key=lambda x: -len(x[0]))))
_SHOT_SIZE_LEVEL = dict(_SHOT_SIZE_TERMS)

CLOSEUP_BODY_BAN = _R["closeup_body_ban"]

PRONOUN_RE = re.compile(_R["pronoun_re"])
PRONOUN_WORD_PART = _R["pronoun_word_part"]
PRONOUN_MAX_REPORT = _R["pronoun_max_report"]

# P6：抽象/不可视化词 lint（WARN 级，冻结/锁定单元豁免）
ABSTRACT_WORDS = _R["abstract_words"]

# ---------- 判定辅助函数（规则词表已外置 ../规则配置/checker规则.json，改规则勿动此处） ----------
def is_frozen_filmed(base, u):
    return "第六幕" in base and u in FROZEN_FILMED_UNITS

def is_locked_template(base, u):
    # v2.20·2026-09-28 按幕作用域：锁定模板仅第六幕28-31——裸号全局生效会误豁免其他幕同号单元
    # （去变体顺号后幕七旧28/29迁至43/44即暴露此泄露：臃肿WARN凭空消失/现显随编号漂移）。
    return "第六幕" in base and u in LOCKED_TEMPLATE_UNITS

def dialog_segments(body):
    """把「台词 / OS：」行按（角色，演法）归属切成 [(角色, 口白, 类型)]。
    类型：inner=内心OS（不张嘴）/ off=画外音 / spoken=画内口白（画外音与口白都算说出口）。"""
    ms = list(DIALOG_ATTR_RE.finditer(body))
    out = []
    for i, m in enumerate(ms):
        seg = body[m.end(): ms[i+1].start() if i+1 < len(ms) else len(body)]
        if re.search(r"OS|内心|心声", m.group(0)):
            kind = "inner"
        elif "画外" in m.group(0):
            kind = "off"
        else:
            kind = "spoken"
        out.append((m.group(1).strip(), seg, kind))
    return out

def nolen(s): return len(re.sub(r"\s", "", s or ""))

def shot_size_chain(jb_text):
    """把「景别：满屏黑板全景→黑板主区域推近」解析成明确档位序列（按出现顺序）。
    只认景别名词，'推近/拉开/摇/移'等运镜动词不产生档位；无明确景别返回 []。"""
    if not jb_text:
        return []
    return [_SHOT_SIZE_LEVEL[m.group(0)] for m in _SHOT_SIZE_RE.finditer(jb_text)]

def negated(text, idx, span=8):
    """目标词前 span 字内是否为否定语境（无/禁/不/没/别/非）。"""
    return any(k in text[max(0, idx-span):idx] for k in ["无", "禁", "不", "没", "别", "非", "杜绝"])

def field_body(text, field):
    m = re.search(re.escape(field) + r"(.+)", text)
    return m.group(1).strip() if m else None

def split_shots(text):
    """返回 [(镜号键, 该分镜块文本)]，只把【行首】的 '分镜 N 「…」' 当分镜标题；
    头部字段行中提及的 '分镜6 POV' 之类不算块起点。
    v2.12 子镜号：'分镜 6-1'/'分镜 9-6-3' 是渲染管线插入镜约定（成片镜号不回改），
    镜号键为整数元组 ((6,1)/(9,6,3))，连续性按插入镜规则校验（见 shot_seq_errors）。
    v2.12.1 加粗头：单元30-69 起用 '**分镜 N 「…」**' markdown 加粗标题，
    行首允许 0-2 个 '*' 前缀——此前 40 个单元从未进镜头级校验（388/784 镜盲区）。
    v2.21 概览行豁免：行首是'分镜N'但整行内联罗列≥3个分镜标记的行
    （如七幕36分镜总览行·单行11个'分镜N'）是字段体概览而非镜块起点；
    阈值3——正常分镜块行的括号注记至多引用1-2个其他分镜（五幕32）。"""
    marks = []
    for m in re.finditer(r"(?m)^\s*\*{0,2}\s*分镜\s*(\d+(?:-\d+)*)", text):
        line_end = text.find("\n", m.start())
        line = text[m.start():line_end if line_end != -1 else len(text)]
        if len(re.findall(r"分镜\s*\d", line)) >= 3:
            continue
        marks.append((m.start(), tuple(int(x) for x in m.group(1).split("-"))))
    out = []
    for i,(pos,num) in enumerate(marks):
        end = marks[i+1][0] if i+1 < len(marks) else len(text)
        out.append((num, text[pos:end]))
    return out

def shot_label(k):
    """镜号键→显示串：(6,)→'6'、(6,1)→'6-1'、(9,6,3)→'9-6-3'。"""
    return "-".join(str(x) for x in k)

def shot_seq_errors(keys, variant=False):
    """镜号序列校验：严格递增；同级相邻差1；父镜后首插镜必为 -1；出子镜接父级下一同级。
    A/B 拆分单元叙事上承接父单元镜列（如 22A 自 9-1 起），起始镜号不强制为 1。"""
    errs = []
    if not keys:
        return errs
    if not variant and keys[0] != (1,):
        errs.append(f"首镜应为分镜1，实为分镜{shot_label(keys[0])}")
    for a, b in zip(keys, keys[1:]):
        if b <= a:
            errs.append(f"分镜{shot_label(a)}→{shot_label(b)} 编号回跳/重复")
        elif len(a) == len(b) and a[:-1] == b[:-1]:
            if b[-1] != a[-1] + 1:
                errs.append(f"分镜{shot_label(a)}→{shot_label(b)} 同级跳号（缺分镜{shot_label(a[:-1]+(a[-1]+1,))}）")
        elif len(b) == len(a) + 1 and b[:-1] == a:
            if b[-1] != 1:
                errs.append(f"分镜{shot_label(a)}→{shot_label(b)} 插入镜应自 -1 起（应为分镜{shot_label(a+(1,))}）")
        elif not (len(b) < len(a) and b[:-1] == a[:len(b)-1] and b[-1] == a[len(b)-1] + 1):
            errs.append(f"分镜{shot_label(a)}→{shot_label(b)} 子镜出口不连续")
    return errs

def strip_negated(text):
    """剔除被否定统辖的文本，避免把 '禁…（无A/B/月亮）' 这类禁用清单误判成违规：
    1) 删掉内含否定词的整段括号；2) 删掉 禁/严禁/杜绝/不出现/没有 引导到分句末的内容。"""
    t = re.sub(r"[（(][^（）()]*?(?:无|禁|不|没|杜绝)[^（）()]*?[）)]", "", text)
    t = re.sub(r"(?:严禁|禁止|杜绝|不出现|没有|禁用)[^；;。\n]*", "", t)
    return t

_U_SUFFIX = {"": 0.0, "A": 0.01, "B": 0.02}
# v2.8 A/B 插入单元叙事序例外注册：编号序 ≠ 叙事序时在此登记「插入在哪个裸号之后」。
# 默认 A/B 单元叙事上紧跟同号裸单元；正片（30秒版）10A《取证》是唯一已确认例外（用户拍板插 11/12 之间）。
# v2.19·2026-09-27 系列分册：衍生系列同号单元叙事位置可不同（正片 10A 插 11/12 之间、
# 15秒版 010A《背影成永恒（上）》紧跟 010），全局裸键会互踩——衍生系列用「系列名|单元号」
# 键单列、值 None＝明确无例外（紧跟裸号）；_SERIES 由 check_dir 按本批文件系列名注入。
_UNIT_INSERT_AFTER = {"10A": 11, "第七幕·15秒版|10A": None}
_SERIES = ""
# v2.20·2026-09-28 去变体顺号适配：三幕A/B/C变体并入主编号（五1-43/六1-76/七1-114连续）后，
# 拆分碎片不再带字母后缀、「拆分单元承接父单元镜列、起始镜号不强制为1」的豁免改按「幕名|新单元号」注册
# （成片镜号不回改约定）。幕六65/73/74（原64a/72a/72b）镜列自1起、无需注册；
# 15秒版仍带字母后缀、沿用 variant 判定不受影响。
SPLIT_FRAGMENT_UNITS = {
    "第七幕|10",   # 原单元7A《教官之约》自主镜6起（7拆分：1-5/6-10）
    "第七幕|20",   # 原单元13A《九号回来了》自主镜6起（13拆分：1-5/6-10）
    "第七幕|33",   # 原单元20A自主镜9起（20拆分：1-8/9-11）
    "第七幕|36",   # 原单元22A自镜9-1起（22插入镜拆分）
    "第七幕|37",   # 原单元22B自镜9-7起（22A续拆）
}

def is_split_fragment(base, u):
    m = re.match(r"【([^】]+)】", base)
    return bool(m) and f"{m.group(1)}|{int(u)}" in SPLIT_FRAGMENT_UNITS

def unit_no(path):
    m = re.search(r"单元\s*(\d+)([A-Za-z])?", os.path.basename(path))
    if not m: return 9999
    return int(m.group(1)) + _U_SUFFIX.get((m.group(2) or "").upper(), 0.03)

def fmt_u(u):
    """显示用：5.0→'5'、9.01→'9A'、14.02→'14B'。"""
    if isinstance(u, float) and u != int(u):
        return f"{int(u)}" + {0.01: "A", 0.02: "B"}.get(round(u - int(u), 2), "?")
    return str(int(u))

def story_key(u):
    """叙事序键：默认=编号序；例外按 _UNIT_INSERT_AFTER 挂到指定裸号之后（v2.19 系列分册）。"""
    n = int(u); frac = round(u - n, 2)
    if frac == 0: return float(u)
    key = fmt_u(u)
    if _SERIES:
        sk = f"{_SERIES}|{key}"
        if sk in _UNIT_INSERT_AFTER:            # 系列分册命中；值 None＝明确无例外（紧跟裸号）
            after = _UNIT_INSERT_AFTER[sk]
            return after + frac * 0.01 if after is not None else float(u)
    after = _UNIT_INSERT_AFTER.get(key)          # 正片／未注册系列回落裸键册（旧行为）
    if after is not None:
        return after + frac * 0.01
    return float(u)

def trans_key(s):
    """转场指向串→同 unit_no 体系的 float 键，供链比对。"""
    m = re.match(r"\s*(\d+)([A-Za-z])?", s or "")
    if not m: return None
    return int(m.group(1)) + _U_SUFFIX.get((m.group(2) or "").upper(), 0.03)

def load_role_bans(rolelib):
    """从角色库各 md 的「已否决/禁用/禁止出现」小节抽禁用词，合并进 DEFAULT_BAN。"""
    bans = {k:list(v) for k,v in DEFAULT_BAN.items()}
    if not rolelib or not os.path.isdir(rolelib): return bans
    for md in glob.glob(os.path.join(rolelib, "**", "*.md"), recursive=True):
        try: t = open(md, encoding="utf-8").read()
        except Exception: continue
        # 归属以文件名为准（角色库约定：文件名＝角色名，如 江游.md / 陆遥遥.md）；
        # 禁止用"角色名是否出现在正文"判定——A 角色卡正文提到 B，会把 A 的禁用词错挂到 B 名下。
        who = os.path.splitext(os.path.basename(md))[0]
        m = re.search(r"(?:已否决|禁用|禁止出现|不要出现)[^\n]*[:：]([^\n#]+)", t)
        if m:
            words = [w.strip(" 、,，。；;（）()") for w in re.split(r"[、,，/；;]", m.group(1)) if len(w.strip())>=2]
            bans.setdefault(who, []).extend(w for w in words if w)
    return bans

# ---------- I. 触发词地图引用校验（v2.0，--index-map 开启） ----------
def _resolve_lib_path(tok, lib_root):
    """把总索引里的简写/别名路径 token 解析为【项目库】下真实相对路径。
    先按域前缀映射，再用 basename 在整个库树递归兜底匹配。找到返回相对路径，找不到返回 None。"""
    p = tok.strip()
    # 显式域前缀 -> 库前缀
    for a,b in [("场景/","场景库/"),("角色/","角色库/"),("技能/","技能装备库/技能/"),
                ("美术参考/","美术库/"),("编剧工作台/","编剧工作台/")]:
        if p.startswith(a): p = b + p[len(a):]
    # 域内短路径 -> 对应库
    for root in ["主线/","配角线/","心路历程/"]:
        if p.startswith(root): p = "故事线库/"+p
    for root in ["主角/","主要配角/","次要角色/"]:
        if p.startswith(root): p = "角色库/"+p
    # 场景子域
    for root in ["巡夜司/","暗面世界/","表世界/","林墨公寓/","江游家/","通用模板/"]:
        if p.startswith(root): p = "场景库/"+p
    if p == "伏笔清单.md": p = "故事线库/伏笔清单.md"
    # 无目录的裸名 -> 技能（技能装备库/技能/）
    if "/" not in p: p = "技能装备库/技能/"+p
    cand = os.path.join(lib_root, p)
    if os.path.exists(cand): return p
    # 兜底：按 basename 在库树递归找同名文件
    base = os.path.basename(p)
    hits = []
    for root,_,files in os.walk(lib_root):
        if base in files:
            hits.append(os.path.relpath(os.path.join(root,base), lib_root))
    return hits[0] if len(hits)==1 else None

def check_index_refs(index_path, lib_root):
    """规则1（必须）：总索引登记的库文件引用存在性校验，空指针 ERROR。
    返回 (E_list, W_list, I_list)。"""
    E, W, I = [], [], []
    try: idx = open(index_path, encoding="utf-8").read()
    except Exception as e:
        E.append(f"[触发地图] 无法读取触发词地图 {index_path}：{e}")
        return E, W, I
    toks = set(re.findall(r"`([^`]+?\.md)`", idx))
    toks |= set(re.findall(r"(?:^|[\s，。；：、（(])([一-龥][一-龥/]*?\.md)", idx))
    toks = {t.strip() for t in toks}
    ok = miss = 0
    for t in sorted(toks):
        rel = _resolve_lib_path(t, lib_root)
        if rel: ok += 1
        else:
            miss += 1
            E.append(f"[触发地图] 总索引登记引用「{t}」在【项目库】下找不到对应文件（空指针）——"
                     f"要么建该库文件，要么修正总索引里的路径，禁止登记了却不落地")
    I.append(f"—— 触发词地图引用校验：共 {len(toks)} 条唯一 .md 引用，落地 {ok} 条，缺失 {miss} 条 ——")
    return E, W, I

def check_method_lib(method_lib_path):
    """规则2（评估可行）：编剧叙事方法库条目结构校验——规则名/做法/例证/迁移四段缺失 WARN。
    文件不存在给 WARN 提示待建；文件存在才逐条目校。返回 (E, W, I)。"""
    E, W, I = [], [], []
    if not os.path.exists(method_lib_path):
        W.append(f"[编剧叙事库] {os.path.basename(method_lib_path)} 尚未建立——拉片反哺的冷开场/ED钩/母题规则暂无落位，"
                 f"待任务C建库后本规则自动启用")
        return E, W, I
    try: t = open(method_lib_path, encoding="utf-8").read()
    except Exception as e:
        W.append(f"[编剧叙事库] 读取失败：{e}"); return E, W, I
    # 按 ## 条目切分（跳过文件大标题）
    entries = re.split(r"(?m)^##\s+", t)
    four = ["规则", "做法", "例证", "迁移"]
    n = 0
    for ent in entries[1:]:
        name = ent.splitlines()[0].strip() if ent.strip() else "(无题)"
        miss = [k for k in four if k not in ent]
        if miss:
            n += 1
            W.append(f"[编剧叙事库] 条目「{name[:18]}」缺四段中的 {miss}——"
                     f"每条规则应含【规则名/做法/例证(来源EP帧锚点)/迁移(怎么用到本项目)】")
    I.append(f"—— 编剧叙事方法库条目结构校验：{max(0,len(entries)-1)} 个条目 ——")
    return E, W, I

def check_adapt_segment(unit_text, unit_name, workbench_dir):
    """规则3（评估可行）：单元若声明所属改编段，校验该段意见单存在且状态为"已确认"，否则 WARN。
    未声明改编段的单元不触发（不误伤存量分镜）。"""
    W = []
    m = re.search(r"(?:所属改编段|改编段[：:])\s*第\s*(\d+)\s*段", unit_text)
    if not m: return W
    seg = m.group(1)
    if not os.path.isdir(workbench_dir):
        W.append(f"[改编段] {unit_name} 声明属第{seg}段，但编剧工作台/分段编剧意见目录不存在：{workbench_dir}")
        return W
    cands = glob.glob(os.path.join(workbench_dir, f"第{seg}段_*.md"))
    if not cands:
        W.append(f"[改编段] {unit_name} 声明属第{seg}段，但未找到分段意见单「第{seg}段_*.md」——"
                 f"按门禁应先出意见单并经用户确认")
        return W
    body = open(cands[0], encoding="utf-8").read()
    if "已确认" not in body:
        W.append(f"[改编段] {unit_name} 属第{seg}段，但意见单「{os.path.basename(cands[0])}」状态非"
                 f"「已确认」——未确认段落不得开写分镜，请先过用户门禁")
    return W

# ---------- L. 外部作品专名扫描（v2.1，--ban-foreign-names 开启，拉片反哺入库 QA） ----------
# 3.7 SOP 铁律：外部作品的角色名 / 组织名 / 地名 / 体系术语 / 专属口癖不进【项目库】，
# 只允许以"来源：斩神Sx EPxx HH:MM:SS（帧n）"锚点行举例证。词表按新拉片作品持续扩充。
FOREIGN_NAMES = [
    # 《斩神之凡尘神域》角色
    "林七夜", "赵空城", "陈牧野", "周平", "安卿鱼", "曹渊", "韩少云", "倪克斯", "沈青竹",
    "波塞冬", "丝西娜", "尤瑞艾莉", "美杜莎", "戈尔贡", "黑无常", "无常斩",
    # 组织 / 地名 / 世界观术语
    "守夜人", "古神教会", "诸神精神病院", "136小队", "沧南", "大夏", "禁墟", "至暗侵蚀",
    "天丛云剑", "阎罗殿",
    # 专属口癖 / 名场面原词
    "呓语", "唯一解", "唯一正解", "神明禁行",
]
# 豁免行：来源锚点行（来源：斩神S1 EP03 02:14）与专名清洗更新日志行允许出现专名
FOREIGN_ANCHOR_RE = re.compile(r"来源\s*[：:]?\s*斩神|来源\s*EP|专名清洗")
FOREIGN_MAX_REPORT = 40

def check_foreign_names(lib_root):
    """扫描【项目库】整树 md，外部作品专名命中即 ERROR；锚点行 / 清洗日志行豁免。
    返回 (E_list, W_list, I_list)。"""
    E, W, I = [], [], []
    total, files_hit, scanned = 0, 0, 0
    for md in sorted(glob.glob(os.path.join(lib_root, "**", "*.md"), recursive=True)):
        rel = os.path.relpath(md, lib_root)
        scanned += 1
        try: lines = open(md, encoding="utf-8").read().splitlines()
        except Exception: continue
        fhit = 0
        for ln_no, ln in enumerate(lines, 1):
            if FOREIGN_ANCHOR_RE.search(ln):
                continue
            for w in FOREIGN_NAMES:
                if w in ln:
                    total += 1; fhit += 1
                    if total <= FOREIGN_MAX_REPORT:
                        E.append(f"[外部专名] {rel}:{ln_no} 出现外部作品专名「{w}」——外部专名不进项目库，"
                                 f"请抽象成通用方法论；例证只允许写在'来源：斩神Sx EPxx 时间码'锚点行")
        if fhit: files_hit += 1
    if total > FOREIGN_MAX_REPORT:
        E.append(f"[外部专名] 另有 {total-FOREIGN_MAX_REPORT} 处未逐条列出，请全库清洗后重跑")
    I.append(f"—— 外部专名扫描：扫描 {lib_root}（{scanned} 个 md），命中 {total} 处、涉及 {files_hit} 个文件"
             f"（来源锚点行 / 专名清洗日志行已豁免）——")
    return E, W, I

def check_dir(folder, args):
    # v2.2：递归扫描全部子目录（字段精简版/ 等系列目录），排除备份/旧稿/外部模板；
    # 修复 2026-09-21 事故根因——旧版只扫根目录 *.md，字段精简版单元从未进校验，落地门假通过
    files = sorted(glob.glob(os.path.join(folder, "**", "*.md"), recursive=True), key=lambda p: story_key(unit_no(p)))
    files = [f for f in files if re.search(r"单元\s*\d+", os.path.basename(f))
             and not any(m in f for m in SCAN_EXCLUDE)]
    # 一幕一检：--only 第六幕 时只保留文件名含该关键字的单元（多关键字为「或」）
    # 衍生系列隔离（v2.18）：【第X幕·15秒版】/【第X幕·30秒版】等衍生系列文件，
    # 仅当 key 点名该完整系列名（如 --only 第七幕·15秒版）才纳入；
    # 裸幕名 key（--only 第七幕）不吞并衍生系列——否则两版本同号单元撞号、基线互污染
    def _series_of(fn: str):
        m = re.match(r"【(第[一二三四五六七八]幕·[^】]+|最终版|重置版)】", fn)
        return m.group(1) if m else None

    if getattr(args, "only", ""):
        keys = [k for k in args.only.split(",") if k.strip()]
        if keys:
            def _only_keep(f):
                base = os.path.basename(f)
                series = _series_of(base)
                if series:
                    return any(k == series or series in k for k in keys)
                return any(k in base for k in keys)
            files = [f for f in files if _only_keep(f)]
    # v2.19 系列分册注入：本批文件同属一个衍生系列时、叙事序例外按该系列分册查
    # （防正片 10A 例外误套 15秒版同号 010A）；注入后按叙事序重排文件
    global _SERIES
    _ss = {s for s in (_series_of(os.path.basename(f)) for f in files) if s}
    _SERIES = next(iter(_ss)) if len(_ss) == 1 else ""
    files.sort(key=lambda p: story_key(unit_no(p)))
    E, W, I = [], [], []   # ERROR / WARN / INFO
    # 同幕重复单元号：同号两版并存会互相污染转场链/站位/跨单元校验，旧稿必须删除
    from collections import Counter
    _dup = Counter(unit_no(f) for f in files)
    for _n, _c in sorted(_dup.items()):
        if _c > 1:
            _names = [os.path.basename(f) for f in files if unit_no(f) == _n]
            E.append(f"[结构] 单元号 {fmt_u(_n)} 在本幕有 {_c} 个文件并存：{_names}——"
                     f"同号两版会污染转场链与跨单元校验，删旧版只留当前稿")
    scenes, day_flags, tails, opens = {}, {}, {}, {}
    prop_track = {p: {} for p in args.prop}
    prev_size_tail, prev_size_unit = None, None   # 景别隔级跳：上一单元末镜末档 + 单元号（跨单元首尾校验）

    for f in files:
        u = unit_no(f); base = os.path.basename(f)
        t = open(f, encoding="utf-8").read()

        # P6 抽象/不可视化词（WARN）：逐镜查「主体动态」，命中提示改成可视动作/微表情/材质；
        # 成片冻结区/锁定模板豁免。词表可在 checker规则.json·abstract_words 直接扩充。
        if not (is_frozen_filmed(base, u) or is_locked_template(base, u)):
            for _sk, _sblock in split_shots(t):
                _dyn = field_body(_sblock, "主体动态") or ""
                for _w in ABSTRACT_WORDS:
                    if _w in _dyn:
                        W.append(f"[抽象词] 单元{fmt_u(u)} 分镜{shot_label(_sk)} 主体动态出现不可视化词「{_w}」"
                                 f"——改用可拍的动作/微表情/材质，删抽象形容")

        # J. 非台词行人称代词（永久·2026-09-18）：除「台词 / OS：」行外，描述文字一律直写角色名，
        # 禁你 / 我 / 他 / 她；台词行（含引号内口语）整行豁免。
        # v2.2 误报豁免：标题/小节头（#、>引用块、【单元 NN 标题】）与「」『』"" 引号内直接引语不算描述
        # v2.8 台词续行豁免：台词块（「台词 / OS：」起、至空行或下一字段行止）内的续行同属台词、不扫人称
        # v2.9 书名号豁免：《…》内是单元/书名等专名引用（如《我来自火种》），不按人称代词扫描
        # v2.11 直引号豁免：ASCII 直引号 "…" 同为直接引语（对话铁律逐镜引台词处大量使用，
        # 如 分镜2"我是来救你们的…"），与弯引号一视同仁、成对才豁免（不成对的 " 不剔除）。
        _QUOTE_SPAN_RE = re.compile(r"[「『“][^」』”]*[」』”]|《[^》]*》|\"[^\"]*\"")
        _DLG_END_RE = re.compile(r"^\*{0,2}\s*(景别|拍摄角度|主体动态|环境音|光影细节)[：:]|^\*{0,2}\s*分镜|^【")
        _pn = 0
        _in_dlg = False
        for ln in t.splitlines():
            _ls = ln.strip()
            if _ls.startswith("台词 / OS：") or _ls.startswith("台词/OS："):
                _in_dlg = True
                continue
            if not _ls:
                _in_dlg = False
                continue
            if _in_dlg and not _DLG_END_RE.match(_ls):
                continue
            _in_dlg = False
            if _ls.startswith("#") or _ls.startswith(">") or _ls.startswith("（v") or re.match(r"【单元\s*\d+", _ls):
                continue
            _probe = _QUOTE_SPAN_RE.sub("", ln)
            for wp in PRONOUN_WORD_PART:
                _probe = _probe.replace(wp, "")
            _pm = PRONOUN_RE.search(_probe)
            if _pm:
                _pn += 1
                if _pn <= PRONOUN_MAX_REPORT:
                    _ctx = _probe[max(0, _pm.start()-8): _pm.start()+9].strip()
                    E.append(f"[人称代词] 单元{fmt_u(u)} 非台词行出现「{_pm.group(0)}」（…{_ctx}…）——除台词/OS行外，"
                             f"描述文字一律直写角色名（江游/陆遥遥…），禁用你/我/他/她")
        if _pn > PRONOUN_MAX_REPORT:
            E.append(f"[人称代词] 单元{fmt_u(u)} 另有 {_pn-PRONOUN_MAX_REPORT} 处非台词行人称代词未逐条列出，请全行改直写角色名")

        # A. 头部字段完整性
        for fld in HEAD_FIELDS:
            # v2.13 字段别名：24-29 起火弧重写单元用「【全局强制铁律】」，语义等同、零内容改动放行
            if fld == "【全局铁律】" and "【全局强制铁律】" in t:
                continue
            if fld not in t:
                E.append(f"[结构] {base} 缺少头部字段 {fld}")
        scene = field_body(t, "【场景环境】")
        stand = field_body(t, "【人物固定站位】")
        tone  = field_body(t, "【色调标准】")
        rule  = field_body(t, "【全局铁律】") or field_body(t, "【全局强制铁律】") or ""
        if nolen(rule) > RULE_MAXLEN and not (is_locked_template(base, u) or is_frozen_filmed(base, u)):
            W.append(f"[臃肿] 单元{fmt_u(u)} 全局铁律 {nolen(rule)} 字偏长，检查是否混入逐镜剧情复述 / 元指令（应只留跨镜硬约束）")
        # R. 铁律纯约束锁（v2.5·2026-09-22）：衣着/造型锚不进铁律——归【人物固定站位】；
        # 否定语境（禁/不/无…）豁免；锁定模板（v2.20·按幕作用域仅第六幕28-31）与成片冻结区（v2.6·第六幕1-31）豁免。
        if not (is_locked_template(base, u) or is_frozen_filmed(base, u)):
            _rule_clean = strip_negated(rule)
            for _w in CLOTHING_ANCHOR:
                _m = re.search(re.escape(_w), _rule_clean)
                if _m and not negated(_rule_clean, _m.start()):
                    W.append(f"[铁律衣着] 单元{fmt_u(u)} 【全局铁律】出现衣着/造型词「{_w}」——衣着锚属画面造型，"
                             f"应写进【人物固定站位】；铁律只留承接锚+单元定位+跨镜结构约束+禁忌项（否定式约束除外）")
                    break

        # B. 场景自包含 + 四要素 + 光源强制
        if scene is not None:
            if len(scene) < args.min_scene:
                W.append(f"[场景] 单元{fmt_u(u)} 场景环境仅{len(scene)}字，可能缺材质/光源/反射/外景细节")
            if not any(w in scene for w in LIGHT_WORDS):
                E.append(f"[光源] 单元{fmt_u(u)} 场景环境缺少任何光源描述（天光/灯/光方向），光源不得缺")
            for label, words in [("材质", MAT_WORDS), ("反射", REFL_WORDS), ("外景动态", OUT_WORDS)]:
                if not any(w in scene for w in words):
                    W.append(f"[场景] 单元{fmt_u(u)} 场景环境未见「{label}」类描述，请确认是否遗漏")
            scenes[u] = scene
        # D. 人物固定站位
        if stand is not None and len(stand) < 12:
            W.append(f"[站位] 单元{fmt_u(u)} 人物固定站位过短（{len(stand)}字），位置/朝向/道具在手可能没写清")
        # 色调冷暖
        if tone is not None and not any(w in tone for w in ["冷","暖","蓝","天光","阳光"]):
            W.append(f"[天光] 单元{fmt_u(u)} 色调标准未见冷暖/天光倾向")

        # C. 昼夜基调 + 白天混入夜景元素
        # 夕阳光/斜阳光等含「阳光」子串的暮时词先掩掉，防黄昏单元被误判成白天（v2.5）
        # v2.14：DAY_MARK 否定感知——「无天光」「永无休止的阳光」这类否定/引用语境不算白天标记
        _t_day = re.sub(r"夕阳|斜阳|残阳|落日|晚霞|暮色|黄昏", "□", t)
        is_day = any(
            any(not negated(_t_day, m.start()) for m in re.finditer(re.escape(w), _t_day))
            for w in DAY_MARK
        ) and not any(w in (rule or "") for w in ["夜晚","夜景"])
        if args.day: is_day = True
        if args.night: is_day = False
        day_flags[u] = is_day
        t_clean = strip_negated(t)   # 去掉「禁…（无A/B/C）」这类否定清单后再判违规
        if is_day:
            for bad in NIGHT_BAN:
                for m in re.finditer(bad, t_clean):
                    if not negated(t_clean, m.start()):
                        E.append(f"[天光] 单元{fmt_u(u)} 为白天却出现夜景元素「{bad}」（非否定句），昼夜不一致")

        # E. 人设禁用词 / F. 参照空指针 / 错名（否定清单已剔除，再叠加前位否定豁免）
        bans = load_role_bans(args.rolelib) if args.rolelib else DEFAULT_BAN
        for who, words in bans.items():
            for w in words:
                for m in re.finditer(re.escape(w), t_clean):
                    if not negated(t_clean, m.start()):
                        # 构词保护（v2.10）：「消杀气流」≠眼神杀气，命中前缀在保护表内即豁免
                        if any(g == t_clean[m.start()-len(g):m.start()]
                               for g in PERSONA_GUARD_PREFIX.get(w, []) if m.start() >= len(g)):
                            continue
                        E.append(f"[人设] 单元{fmt_u(u)} 出现 {who} 的禁用演法/特征「{w}」，人设偏离")
        # 无效词①：默认不存在的特征，连「无黑眼圈」这类否定声明都判错、直接删
        for w in INVALID_DEFAULT:
            for _ in re.finditer(re.escape(w), t):
                E.append(f"[无效词] 单元{fmt_u(u)} 出现「{w}」——人物本就默认没有，不写'无{w}'这类不产生画面的废话，整词删除")
        # 无效词②：跨时段否定清单 / 固定套话，时段唯一、只写当时天光
        for w in INVALID_TIME_NEG:
            for _ in re.finditer(re.escape(w), t):
                E.append(f"[无效词] 单元{fmt_u(u)} 出现「{w}」——一个单元时段唯一，直接写当时天光，不罗列被禁的其他时段元素")
        for m in INVALID_TIME_NEG_RE.finditer(t):
            E.append(f"[无效词] 单元{fmt_u(u)} 出现跨时段否定清单「{m.group(0)[:16]}…」，删掉、只写当前时段天光")
        # 单单元时段互斥：场景/色调里不得同时落在不同时段
        zones = {TIME_WORD[w] for w in TIME_WORD if w in ((scene or "") + (tone or ""))}
        if len(zones) >= 2:
            W.append(f"[天光] 单元{fmt_u(u)} 场景/色调同时含多个时段{sorted(zones)}，一个单元只能是早/午/晚之一")
        # 元指令落文件＝错：这些是管创作者怎么写的，不是给即梦的画面/声音约束，内化即可
        for w in META_INSTRUCTION:
            for _ in re.finditer(re.escape(w), t):
                E.append(f"[元指令] 单元{fmt_u(u)} 出现「{w}」——只约束创作者、不产生画面，不该写进分镜词，删除并内化执行")
        # 用户口语否定（不要描述/别写/不许出现）99%是说给创作者的，禁止原样抄进分镜词
        for m in SPOKEN_NEG_META.finditer(t):
            E.append(f"[元指令] 单元{fmt_u(u)} 出现口语否定「{m.group(0)}」——这是说给创作者的，先动脑判断、内化为正向可见结果，禁止把否定原话抄进分镜词")
        # 硬切不写【转场】行（默认直接切）；只有遮罩/叠化等设计转场才保留【转场】
        for m in HARD_CUT_RE.finditer(t):
            E.append(f"[转场] 单元{fmt_u(u)}「{m.group(0)[:22]}…」是硬切，硬切不单独写【转场】行，整行删除")
        # 尬演外放表情：笑要克制（嘴角微翘/眼底欣喜/浅笑），禁咧嘴龇牙傻乐、情绪猛起猛落（否定式豁免）
        _seen_oa = set()
        for m in re.finditer("|".join(map(re.escape, sorted(OVERACT, key=len, reverse=True))), t_clean):
            w = m.group(0)
            if w in _seen_oa or negated(t_clean, m.start()): continue
            _seen_oa.add(w)
            E.append(f"[尬演] 单元{fmt_u(u)} 出现外放夸张表情「{w}」——笑只到嘴角微翘/眼底欣喜/浅笑(微微一笑)，"
                     f"不咧嘴龇牙傻乐、情绪不猛起猛落；暖光柔和漫下、不'叮'地突然打亮")
        for ref in REF_PATTERN:
            for m in re.finditer(re.escape(ref), t):
                E.append(f"[参照] 单元{fmt_u(u)} 出现空指针表述「{ref}」——要参照就把原文整段复制进本单元，不许只甩参照")
        # 「对齐」指针式用法单独判：邻域带 单元/《/最终版 才算空指针，物理对齐（把花对齐摆正）豁免
        for m in re.finditer(r"对齐", t):
            _win = t[max(0, m.start()-10):m.end()+10]
            if any(k in _win for k in ["单元", "《", "最终版"]):
                E.append(f"[参照] 单元{fmt_u(u)} 出现空指针表述「对齐」——要参照就把原文整段复制进本单元，不许只甩参照")
        # 人设年龄锁：主角团/有戏份配角均 19+ 已毕业成年人，禁「高中生/未成年」，泛称用「学生」（否定式豁免）
        for w in AGE_BAN:
            for m in re.finditer(re.escape(w), t_clean):
                if negated(t_clean, m.start()): continue
                E.append(f"[年龄锁] 单元{fmt_u(u)} 出现「{w}」——主角团及有戏份配角均为19岁以上、已毕业的成年人，泛称统一用「学生」，不得称高中生/未成年")
        for m in AGE_WARN_RE.finditer(t):
            W.append(f"[年龄锁] 单元{fmt_u(u)} 出现裸「高中」——主角团已毕业一年、是成年人，请确认是否应改为「学生/老同学」（纯世界观背景提及除外）")
        # 永久禁用道具：烟糖等用户永久否决的道具，任何分镜单元出现即 ERROR
        for w in BANNED_PROP:
            if w in t:
                E.append(f"[禁用道具] 单元{fmt_u(u)} 出现「{w}」——用户永久否决、任何分镜都不出现，整词删除并改用其他反应/动作")
        # 影瞳 UI 定稿（2026-09-07：按时间线取最新＝第五幕紫色水墨版，禁止回退早期红色版本）
        # 外框=断续猩红科技线+墨黑水晕+猩红光点（合法）；微距螺旋/电流、扫描线/框、血条、锁定框=紫色水墨。下列为"早期红UI回退词"，命中即 ERROR
        UI_ROLLBACK = ["红色螺旋", "正红光点", "红色电流", "红电粒子", "猩红血条", "猩红3D血条",
                       "猩红 3D 血条", "红色血液光纹", "红色锁定框", "淡红锁定框", "红黑扫描框", "红框锁"]
        _ui_bad = [w for w in UI_ROLLBACK if w in t]
        if _ui_bad:
            E.append(f"[影瞳UI] 单元{fmt_u(u)} 出现早期红色UI回退词{_ui_bad}——影瞳已按第五幕最新定稿：微距紫螺旋+紫电流，POV外框猩红科技线+墨黑晕+猩红光点，扫描线/扫描框/血条/锁定框为紫色水墨（哑光灰底+紫色填充+黑毛笔字），请改紫")
        # S. 神眷冷暗锁（v2.9·2026-09-23 用户最高指示·ERROR）：神眷人靠吸收负面能量取力，视觉必须冷暗——
        # 眼瞳光/异能光/能力UI 只许蓝·白·黑·红·紫冷暗五色（荧光/微光可），禁金色禁圣光界面禁亮金面板；
        # 唯一豁免口＝神眷转换后的神圣态（单元明写「神眷转换/神圣态/神迹」即视为神圣态场景）；
        # 成片不追责：第六幕1-31 冻结区 + 过审成片前缀（最终版/30秒版/二~五幕）全跳过；否定语境照常豁免。
        if not (is_frozen_filmed(base, u) or any(p in base for p in FILMED_PREFIXES)):
            if not any(k in t for k in ("神眷转换", "神圣态", "神迹")):
                _seen_gold = set()
                for _m in COLD_DARK_GOLD_RE.finditer(t_clean):
                    if negated(t_clean, _m.start()) or _m.group(0) in _seen_gold:
                        continue
                    _seen_gold.add(_m.group(0))
                    E.append(f"[神眷冷暗] 单元{fmt_u(u)} 出现「{_m.group(0)}」——神眷人靠吸收负面能量取力，"
                             f"眼瞳光/异能光/能力UI只许蓝·白·黑·红·紫冷暗五色（荧光/微光可），禁金色禁圣光界面，"
                             f"神圣光辉仅限神眷转换后的神圣态——本处改用紫焰光柱/猩红光点/冷白微光/暗紫呼吸等冷暗光效")
        # 影瞳开启铁律（WARN 启发式）：江游出现认真/异常信号却通篇无开瞳/微距/POV，提醒人工确认（认熟人/日常可不开）
        # v2.14 收窄：红光须带眼/瞳语境（警灯红光·戒指暗红光·频闪红光等环境敌色不误报）；
        # 「锁定」限目光/视线锁定（图鉴锁定·形态锁定·P7-17形态锁等术语不误报）；
        # 「日常→异常→灾变」斩神三段式术语链先掩掉；信号词紧邻遥遥名的归遥遥（「遥遥·瞳孔收缩」）
        if "江游" in t:
            _t_sig = re.sub(r"日常[→＞>\s]*异常[→＞>\s]*灾变", "□", t_clean)
            _eye_sig = ["警觉", "凝神", "瞳孔收缩", "目光一凝", "目光凝实", "追踪", "异常",
                        "眼底红光", "瞳孔红光", "眼中红光", "眼里红光", "双眼红光", "双瞳红光",
                        "目光锁定", "视线锁定"]
            _eye_key = ["影瞳", "第一视角", "第一人称", "POV", "微距", "紫色螺旋", "科技扫描边框"]
            _hit = []
            for w in _eye_sig:
                for m in re.finditer(re.escape(w), _t_sig):
                    _win = _t_sig[max(0, m.start()-8):m.start()]
                    if "遥遥" in _win or "阿婆" in _win:
                        continue
                    _hit.append(w)
                    break
            if _hit and not any(k in t_clean for k in _eye_key):
                W.append(f"[影瞳] 单元{fmt_u(u)} 出现江游认真/异常信号{sorted(set(_hit))[:3]}，但通篇未见影瞳开启/微距/第一视角POV+UI，请确认是否应开影瞳（认熟人、日常对话可不开）")
        # 角色有参考图（江游暗影形态）：只写主体指称+身上动态特效，不堆叠外观本体描述
        if "暗影形态" in t_clean:
            _red = [w for w in REFIMG_LOOK_REDUNDANT if w in t_clean]
            if len(_red) >= 2:
                W.append(f"[参考图] 单元{fmt_u(u)} 暗影形态堆叠外观描述{sorted(set(_red))[:4]}——该形态有官方参考图，"
                         f"分镜只写「江游（暗影形态）」+身上动态特效（暗紫黑雾/能量粒子/触须），不描述剪影/裹身/面容/轮廓边")
        # 追踪/尾随语境：目标(如九号/游灵)只给远端局部/流光，不罗列其图鉴形态外观
        if any(k in t_clean for k in ["尾随", "追踪", "跟踪", "远远"]) and any(k in t_clean for k in ["九号", "游灵"]):
            _form = [w for w in ["蚯蚓", "蝌蚪", "两柄大刀", "双目猩红", "黑色纹路"] if w in t_clean]
            if _form:
                W.append(f"[追踪镜头] 单元{fmt_u(u)} 尾随语境却罗列目标形态{sorted(set(_form))}——目标有图鉴/参考图，"
                         f"追踪时只给远端局部(一只脚/半个身子)或一道流光、长距离尾随，不描述外观、不并排跑")
        # 守门人形象锁（第七幕）：不穿保安/安保制服
        for w in ["保安服", "安保服"]:
            if w in t_clean:
                W.append(f"[形象锁] 单元{fmt_u(u)} 出现「{w}」——守门人是黑西装墨镜、皮肤黝黑、肌肉壮硕、耳戴对讲机耳麦的壮汉，不穿保安/安保制服")
        for right, wrongs in NAME_FIX.items():
            for w in set(wrongs):
                if w == right: continue
                if w in t:
                    W.append(f"[正名] 单元{fmt_u(u)} 出现「{w}」，正名应为「{right}」，请统一")

        # A. 分镜六要素 + 编号连续 + 转场
        shots = split_shots(t)
        size_pairs = []   # [(分镜号, 景别档位序列, 景别字段原文)]，供景别隔级跳校验
        if not shots:
            E.append(f"[结构] 单元{fmt_u(u)} 未解析到任何分镜")
        for _se in shot_seq_errors([k for k, _ in shots], variant=(u != int(u)) or is_split_fragment(base, u)):
            E.append(f"[结构] 单元{fmt_u(u)} 镜号序列不连续：{_se}")
        for num, block in shots:
            _sl = shot_label(num)
            for sf in SHOT_FIELDS:
                if sf not in block:
                    E.append(f"[结构] 单元{fmt_u(u)} 分镜{_sl} 缺要素「{sf.rstrip('：')}」")
            # 注：不再强制每镜有【转场】——硬切默认直接切、不写；仅设计转场才出现【转场】行
            ms = re.search(r"台词 / OS：(.+)", block)
            if ms:  # 只算真正“说出口”的话：去演法括号；／后标注 OS/内心/心声 的段不张嘴、不计口白
                _segs = re.split(r"／", ms.group(1))
                _kept = [re.sub(r"（[^）]*）", "", s) for s in _segs if not re.search(r"OS|内心|心声", s)]
                spoken = "".join(_kept).replace("无", "")
                if nolen(spoken) > SPOKEN_MAXLEN:
                    W.append(f"[烫嘴] 单元{fmt_u(u)} 分镜{_sl} 实际口白 {nolen(spoken)} 字偏长，一镜一句、句间留停顿，考虑拆镜")
            # 第一视角铁律（永久·2026-09-07）：POV＝角色双眼所见，画面里不得出现该角色自己的脸/表情/完整正身
            # （镜子/水面/玻璃等明确反射面除外）；要演本人表情必须切到下一客观分镜。
            _jb = re.search(r"景别：(.+)", block); _pa = re.search(r"拍摄角度：(.+)", block)
            _chain = shot_size_chain(_jb.group(1) if _jb else "")
            size_pairs.append((num, _chain, _jb.group(1) if _jb else ""))
            # M 口白脏话锁 / N 特写双人切 / O 口白报菜名 / P 单句十五字（v2.2·2026-09-21）
            if ms:
                _vis_speakers = []
                for _who, _seg, _kind in dialog_segments(ms.group(1)):
                    if _kind == "spoken" and _who not in _vis_speakers and len(_who) >= 2:
                        _vis_speakers.append(_who)
                    # M. 角色口白脏话锁（全剧适用，内心OS同样不许带脏字）
                    for _w in ROLE_PROFANITY_BAN.get(_who, []):
                        if _w in _seg:
                            E.append(f"[口白脏话] 单元{fmt_u(u)} 分镜{_sl} {_who}的口白出现「{_w}」——"
                                     f"{_who}全剧无脏话，赶人只准「你少来！」「滚开！」「我说你滚啊！」，"
                                     f"原著粗口改写时一律替换、不得照搬")
                    if _kind == "inner":
                        continue
                    _seg_clean = re.sub(r"（[^（）]*）", "", _seg)
                    # O. 口白报菜名：行为动作念成台词（画面演，口白只留引导句）
                    for _pat in ACTION_AS_SPEECH:
                        if _pat in _seg_clean and not any(_c in _seg_clean for _c in SPEECH_CUE_OK):
                            W.append(f"[报菜名] 单元{fmt_u(u)} 分镜{_sl} {_who}口白「…{_pat}…」把行为动作念成了台词——"
                                     f"动作交给画面演（主体动态里真抖两下），口白只留引导句（如'从小就怕，你看我这腿'）")
                            break
                    # P. 单句十五字：一句一重点，超长提醒拆短
                    for _sent in re.split(r"[。！？!?]", _seg_clean):
                        _s = _sent.strip("，、；：,;: ")
                        if nolen(_s) > 15:
                            W.append(f"[单句字数] 单元{fmt_u(u)} 分镜{_sl} {_who}口白单句 {nolen(_s)} 字偏长"
                                     f"（「{_s[:18]}…」）——一句一重点、每句不超15字，长句拆成两连短句")
                            break
                # N. 特写双人切：特写/大特写级单镜装下两名画内说话人（画外音不算）
                if _chain and _chain[0] >= 5 and len(_vis_speakers) >= 2:
                    _move = ((_jb.group(1) if _jb else "") + " " + (_pa.group(1) if _pa else ""))
                    if re.search(r"摇|移|拉|推|环绕|一镜", _move):
                        W.append(f"[特写双人] 单元{fmt_u(u)} 分镜{_sl} 特写级镜头{_vis_speakers}两人对切且写了运镜——"
                                 f"确认横摇/拉镜是否真的把两人收进同一画框；装不下就拆两个分镜正反打")
                    else:
                        E.append(f"[特写双人] 单元{fmt_u(u)} 分镜{_sl} 特写级镜头装下两名说话人{_vis_speakers}——"
                                 f"特写框不住两人对切：要么拆成两个分镜正反打，要么改中景/全景＋横摇运镜一镜带走"
                                 f"（运镜不算硬切、不判跳级）")
            # 景别-内容匹配（WARN 启发式）：近景＝胸部以上，框不下腿脚 / 全身位移大动作；
            # 特写 / 大特写是局部镜头不判（手 / 眼 / 脚局部微距都合法），中景 / 全景能带全身也不判。
            if _chain and _chain[0] == 4:
                for _w in CLOSEUP_BODY_BAN:
                    if _w in block:
                        W.append(f"[景别内容] 单元{fmt_u(u)} 分镜{_sl} 是近景(胸部以上)却出现「{_w}」等腿脚/全身大动作——"
                                 f"近景框不下，改中景/全景，或把动作收到胸上(手/臂/肩/表情)；若本就拍局部，请把景别改标特写")
                        break
            _view = ((_jb and _jb.group(1)) or "") + ((_pa and _pa.group(1)) or "")
            _is_pov = re.search(r"POV|第一人称|第一视角|主观视角", _view)
            _cut_back = re.search(r"转场切回|切回客观|拉开成近景|拉开成中景|成近景|客观镜头", block)
            if _is_pov and not _cut_back:
                _refl = re.search(r"镜子|镜面|反射|倒影|水面|玻璃映|反光里", block)
                # 本人脸/表情：POV持有者（江游等）+ 面部词；别人的脸不算。
                # 「先客观拍本人、再直切进POV」的镜头里，紧邻切入标记（直切/直抽/一沉/褪灰白…）
                # 的脸句属切入前的客观拍、合法（v2.5）——只挂真正落在POV段内的脸。
                for _fm in re.finditer(r"(江游|自己|本人|主角).{0,10}(脸|面容|表情|神色|目瞪口呆|咧嘴|嘴角|笑|瞪大|眯眼)|(自己|本人)的?(脸|表情|面容|神色)", block):
                    _win = block[max(0, _fm.start()-25):_fm.end()+25]
                    if _refl or re.search(r"直切|直抽|一沉|骤沉|抽空|褪灰白|褪色|切进记忆|进记忆|转入记忆", _win):
                        continue
                    E.append(f"[第一视角] 单元{fmt_u(u)} 分镜{_sl} 是POV主观镜头却出现本人的脸/表情——POV看不到自己的脸（反射面除外），把本人反应切到下一个客观分镜（微距/近景）")
                    break
            # 异种利刃＝肢体异化（永久·2026-09-07）：游灵/九号/阿飘的刃长在前臂上，禁止写成手持兵器；
            # 出现「前臂/前肢/异化/骨刃/臂刃/长出/肢体」等肢体刃表述即豁免。
            if re.search(r"游灵|九号|阿飘", block) and re.search(r"(拿|握|持|提|举|攥).{0,4}(大刀|双刃|刀刃|刀)|两柄大刀|一柄大刀|手持.{0,3}刀", block):
                if not re.search(r"前臂|前肢|异化|骨刃|臂刃|刃长|长出|肢体|与.{0,3}(手臂|肢).{0,3}连成", block):
                    E.append(f"[异种形态] 单元{fmt_u(u)} 分镜{_sl} 把游灵/九号的刃写成手持兵器——其利刃是前臂异化长出的骨刃（肢体即刃），改成'抬起前臂骨刃'，不得拿/握/举刀")
        # 景别隔级跳铁则：相邻分镜（硬切点）档位差必须 >=2，禁同档/相邻档；跨单元首尾同样；转不过去插空镜/道具大特写
        _valid_pairs = [(n, c) for n, c, _ in size_pairs if c]
        if _valid_pairs:
            # 跨单元（v2.8 改链证据判相邻）：上一处理单元的【转场】明确指向本单元才判——
            # A/B 插入结构下「编号连续 u-1」不可靠（9→9A→10），以叙事链为准；链断则跳过防误报
            _prev_linked = prev_size_unit is not None and tails.get(prev_size_unit) is not None \
                and trans_key(tails[prev_size_unit][0]) == u
            if _prev_linked and abs(prev_size_tail - _valid_pairs[0][1][0]) <= 1:
                E.append(f"[景别跳档·跨单元] 单元{fmt_u(prev_size_unit)}末镜（{SHOT_SIZE_NAME[prev_size_tail]}）→单元{fmt_u(u)}首镜"
                         f"（{SHOT_SIZE_NAME[_valid_pairs[0][1][0]]}）是同档/相邻档硬切——跨单元首尾也必须隔级(档位差≥2)，"
                         f"改首镜景别，或在开场插空镜/道具大特写过渡")
            # 单元内相邻分镜：上一镜末档 → 下一镜首档
            for k in range(1, len(_valid_pairs)):
                pn, pc = _valid_pairs[k-1]; cn, cc = _valid_pairs[k]
                a, b = pc[-1], cc[0]
                if abs(a - b) <= 1:
                    E.append(f"[景别跳档] 单元{fmt_u(u)} 分镜{shot_label(pn)}（{SHOT_SIZE_NAME[a]}）→分镜{shot_label(cn)}（{SHOT_SIZE_NAME[b]}）"
                             f"是同档/相邻档硬切，等于在同一张画上缩放＝跳切穿帮——相邻镜头景别必须隔级(档位差≥2)："
                             f"中景只接特写/大特写/远景，全景只接近景/大特写，特写只接中景/全景/远景；转不过去就在中间插空镜或道具大特写")
            # 分镜内：景别链明写硬切/快切/切换且档位相邻才 WARN（推/拉/摇/移/环绕等连续运镜不判）
            for n, c, jb in size_pairs:
                if len(c) >= 2 and re.search(r"硬切|快切|切换|切回|跳切", jb):
                    for a, b in zip(c, c[1:]):
                        if abs(a - b) <= 1:
                            W.append(f"[景别跳档] 单元{fmt_u(u)} 分镜{shot_label(n)} 景别链「{jb.strip()}」内含同/邻档硬切，请确认是否隔级；若为推/拉连续运镜可忽略")
                            break
            prev_size_tail = _valid_pairs[-1][1][-1]
            prev_size_unit = u
        # Q. 站位矛盾锁（v2.4·2026-09-22）：头枕腿上/扶平躺到腿上＝大腿面必须放平可枕；
        # 盘腿坐（双腿折叠、膝盖朝上）枕不上去——要么站位改「一条腿平搭沙发面」，
        # 要么正文写明「盘着的腿顺势放开」过渡动作；两全其无＝ERROR。
        _zw_m = re.search(r"【人物固定站位】(.+?)(?=\n分镜|\n【|\Z)", t, re.S)
        _zw_txt = (_zw_m.group(1) if _zw_m else "") + rule
        _pillow = re.search(r"枕[^，。；\n]{0,10}腿上|平躺到[^，。；\n]{0,10}腿上", t)
        if _pillow and re.search(r"盘腿坐|盘腿收脚|盘着腿", _zw_txt):
            if not re.search(r"顺势放开|腿.{0,4}放开|放平的腿|腿平搭", _zw_txt):
                E.append(f"[站位矛盾] 单元{fmt_u(u)} 站位「盘腿坐」却要「{_pillow.group(0)}」——盘腿双腿折叠、"
                         f"大腿面被压住、头枕不上去；先补过渡（盘着的腿顺势放开、一条腿平搭沙发面），"
                         f"或站位改「一条腿平搭沙发面、一条腿盘收沙发边、头枕平搭的腿上」")
        # G. 末转场指向 & 衔接信息（v2.8：支持 A/B 后缀「转单元9A《…》」）
        last_trans = re.findall(r"遮罩转单元\s*(\d+[A-Za-z]?)《([^》]*)》", t)
        tails[u] = last_trans[-1] if last_trans else None
        # v2.13 开场承接三格式：①【全局铁律】开场… ②**承接锚（紧接单元 N 末镜…）**（头括号带号）
        # ③**承接锚（变体描述）**：0NN末…（号在正文）；跨幕焊缝（幕7.61·2026-09-28幕结构重切后为幕内承接）视为合法开场。
        om = re.search(r"【全局铁律】开场([^；;。]+)", t)
        if om:
            opens[u] = om.group(1)[:24]
        else:
            am = re.search(r"承接锚（([^）]*)）\*\*：?([^；。\n]{0,50})", t)
            if am:
                head_txt, body_txt = am.group(1), am.group(2)
                if re.search(r"幕\s*\d", head_txt + body_txt):
                    opens[u] = "(跨幕焊缝承接)"
                else:
                    ref = re.search(r"(?:单元\s*)?0?(\d{1,3})\s*([A-Z])?\s*末", head_txt + " " + body_txt)
                    opens[u] = f"(承接单元{ref.group(1)}{ref.group(2) or ''}末镜)" if ref else "(承接锚·未标单元号)"
            else:
                opens[u] = "(未见「开场…」)"

        # H. 道具形态跨单元一致：在场单元铁律锁齐形态锚点、不得缩水 / 变样 / 变色（否定式豁免）
        for pname, spec in PROP_SPEC.items():
            if any(m in t for m in spec["mention"]):
                for a in spec["anchors"]:
                    if a not in rule:
                        E.append(f"[道具形态] 单元{fmt_u(u)} 道具「{pname}」在场，但【全局铁律】没锁形态锚点「{a}」"
                                 f"——道具首次定了什么样、后面一字不落复现，请把完整形态（数量/颜色/品类/标签）写进铁律")
                # 场花豁免：林墨门前「黄白菊/黄、白菊/白黄菊」是祭奠菊花、不是洋甘菊束本身——
                # 掩掉复合词再扫禁词，防「黄菊/白菊」子串误报（v2.5·2026-09-22）
                _ban_text = re.sub(r"黄[、，,]?白菊|白[、，,]?黄菊", "□", t_clean)
                # 数量词（一朵/一枝…）只在邻域真出现 菊/花束/洋甘菊 时才算道具缩水——
                # 「相框角搭着一朵素花」类无关量词豁免（v2.5）
                _QTY_BAN = {"一朵", "一枝", "单支", "单只"}
                for bad in spec["ban"]:
                    for m in re.finditer(re.escape(bad), _ban_text):
                        if not negated(_ban_text, m.start()):
                            if bad in _QTY_BAN and not re.search(r"洋甘菊|雏菊|花束|菊",
                                                                 _ban_text[max(0, m.start()-9):m.end()+9].replace(bad, "", 1)):
                                continue
                            E.append(f"[道具形态] 单元{fmt_u(u)} 道具「{pname}」出现矛盾/缩水形态「{bad}」"
                                     f"——须与首次定义一致（整束、白瓣黄心小雏菊状、底部素白纸签），不得变一朵/单支、不得变色")

        # 道具持有方追踪
        for p in prop_track:
            holder = []
            for m in re.finditer(p, t):
                seg = t[max(0,m.start()-24):m.start()+24]
                if any(x in seg for x in ["陆遥遥","她"]) and any(x in seg for x in ["手上","怀里","抱","腰后","接"]):
                    holder.append("陆")
                elif any(x in seg for x in ["江游","他"]) and any(x in seg for x in ["手上","拎","攥","递","腰后","买"]):
                    holder.append("江")
            prop_track[p][u] = "/".join(sorted(set(holder))) or "?"

        # I. 改编段↔意见单确认状态（仅 --index-map 开启时；未声明改编段的存量单元不触发）
        if getattr(args, "index_map", ""):
            W.extend(check_adapt_segment(t, base, args.workbench_dir))

    # B-严格：--same 指定的同场景组必须逐字一致
    if args.same:
        grp = [trans_key(x) for x in args.same.split(",") if x.strip()]
        base_u = grp[0]
        for u in grp[1:]:
            if scenes.get(base_u) is not None and scenes.get(u) is not None and scenes[u] != scenes[base_u]:
                E.append(f"[场景一致] 单元{fmt_u(u)} 与单元{fmt_u(base_u)} 是同一场景，但【场景环境】未一字一致"
                         f"（{len(scenes[u])}字 vs {len(scenes[base_u])}字），请整段复制对齐")
    # B-启发：同地点锚点但正文不同 -> WARN
    anchor = {}
    for u,s in scenes.items():
        key = tuple(k for k in ["大堂","胶囊电梯","轿厢","通道","街道","窄巷","小区入口"] if k in s)
        anchor.setdefault(key, []).append(u)
    for key, us in anchor.items():
        if key and len(us) > 1:
            bodies = {u: scenes[u] for u in us}
            if len(set(bodies.values())) > 1:
                W.append(f"[场景一致] 单元{us} 锚点同为{key} 但场景描述不一致；若确为同地点请用 --same {','.join(map(str,us))} 强制逐字一致")

    # C. 全幕昼夜基调统一
    days = set(day_flags.values())
    if len(days) > 1:
        W.append(f"[天光] 全幕昼夜基调不统一：白天单元{[fmt_u(u) for u,v in day_flags.items() if v]} / 疑似夜晚单元{[fmt_u(u) for u,v in day_flags.items() if not v]}，请确认是否为有意昼夜转场")

    # G. 转场链 + D. 相邻衔接清单（v2.3·2026-09-21）：双格式链——旧格式「遮罩转单元N《》」结尾
    # 或 新格式下一单元铁律「开场承接…」均可作链证据；两者皆缺才算断链。防新格式单元全量误报。
    # v2.8：ordered 按 story_key（叙事序）排，A/B 插入单元与 10A 例外（插 11 后）才能对上链
    ordered = sorted(tails, key=story_key)
    for i,u in enumerate(ordered[:-1]):
        nxt = ordered[i+1]
        _next_opens = opens.get(nxt) and opens[nxt] != "(未见「开场…」)"
        # v2.13：承接锚带了单元号的，校验号是否真指向前一单元（防拆分/插单元后锚号过期）
        _om = re.match(r"\(承接单元(\d{1,3})([A-Z]?)末镜\)", opens.get(nxt, "") or "")
        if _om:
            _ref_u = int(_om.group(1)) + _U_SUFFIX.get((_om.group(2) or "").upper(),
                                                       0.03 if _om.group(2) else 0.0)
            if round(_ref_u, 2) != round(float(u), 2):
                W.append(f"[转场链] 单元{fmt_u(nxt)} 承接锚指向单元{_om.group(1)}{_om.group(2) or ''}，"
                         f"但实际前一单元是{fmt_u(u)}——锚号过期（拆分/插单元后未更新），请改锚")
        if tails[u] is None:
            if not _next_opens:
                W.append(f"[转场链] 单元{fmt_u(u)} 末尾未指向下一单元且单元{fmt_u(nxt)} 未见开场承接（应转单元{fmt_u(nxt)}，"
                         f"或下一单元铁律写「开场承接上一单元末镜——…」）")
        elif trans_key(tails[u][0]) != nxt:
            E.append(f"[转场链] 单元{fmt_u(u)} 末尾指向单元{tails[u][0]}《{tails[u][1]}》，但下一文件是单元{fmt_u(nxt)}，断链/错号")
    present = set(ordered)
    for u in ordered:   # 转场目标单元在本幕根本不存在（含末单元悬空指向）也算断链
        if tails[u] and trans_key(tails[u][0]) not in present:
            W.append(f"[转场链] 单元{fmt_u(u)} 转场指向单元{tails[u][0]}《{tails[u][1]}》，但本幕无此单元文件，悬空/断链")
    I.append("—— 相邻衔接人工核对（上一止点 → 下一场开场）——")
    for i,u in enumerate(ordered[:-1]):
        nxt = ordered[i+1]
        I.append(f"  单元{fmt_u(u)} 止 → 单元{fmt_u(nxt)} 开场：{opens.get(nxt,'')}")
    # 道具持有方序列
    for p, track in prop_track.items():
        seq = " → ".join(f"U{u}:{track[u]}" for u in sorted(track))
        I.append(f"道具「{p}」持有方序列：{seq}（江=江游 / 陆=陆遥遥 / ?=未判定，核对别飞回）")

    # I. 触发词地图引用校验（规则1 空指针 ERROR）+ 编剧叙事库条目结构（规则2 WARN）
    if getattr(args, "index_map", ""):
        lib_root = os.path.dirname(os.path.abspath(args.index_map))
        e1, w1, i1 = check_index_refs(args.index_map, lib_root)
        E.extend(e1); W.extend(w1); I.extend(i1)
        # 规则2：编剧叙事方法库条目结构（默认推 lib_root/分镜参考库/编剧叙事与钩子方法库.md）
        ml = getattr(args, "method_lib", "") or os.path.join(lib_root, "分镜参考库", "编剧叙事与钩子方法库.md")
        e2, w2, i2 = check_method_lib(ml)
        E.extend(e2); W.extend(w2); I.extend(i2)

    # L. 外部作品专名扫描（v2.1，--ban-foreign-names 开启；库目录取 --lib-dir 或 --index-map 同级）
    if getattr(args, "ban_foreign_names", False):
        lib_root = getattr(args, "lib_dir", "") or (
            os.path.dirname(os.path.abspath(args.index_map)) if getattr(args, "index_map", "") else "")
        if lib_root and os.path.isdir(lib_root):
            e3, w3, i3 = check_foreign_names(lib_root)
            E.extend(e3); W.extend(w3); I.extend(i3)
        else:
            E.append("[外部专名] --ban-foreign-names 需用 --lib-dir 指定【项目库】根目录，或同时传 --index-map 自动推断")

    # v2.7 成片冻结区归桶（常开）：用户拍板「已成片单元不再修改」——发现项所引单元号全部
    # 落在冻结区的移入存量桶，不计入 ERROR/WARN 与门禁（ship.sh / pre-commit 不传 --frozen
    # 也生效）；跨区发现（如31末→32首）引用了活跃单元、照常计入，只约束改得动的一侧；
    # 引用不到单元号的发现（库文件类）不受影响。--frozen 仍可追加显式范围。
    FE, FW = [], []
    _fz = set(FROZEN_FILMED_UNITS)
    # 同号冲突防护：单元号若同时被非冻结文件占用（如第七幕单元1-23），裸号不可豁免，
    # 否则第七幕单元5的报错会被误当第六幕单元5的存量收进桶
    for _f in files:
        _u = unit_no(_f)
        if _u in _fz and not is_frozen_filmed(os.path.basename(_f), _u):
            _fz.discard(_u)
    if getattr(args, "frozen", ""):
        for _p in args.frozen.split(","):
            _p = _p.strip()
            if not _p:
                continue
            if "-" in _p:
                _a, _b = _p.split("-", 1)
                _fz.update(range(int(_a), int(_b) + 1))
            else:
                _fz.add(int(_p))
    if _fz:
        # v2.8：提取带 A/B 后缀的单元号（9A≠9），与同体系 float 键比对，防「单元9A」误入裸号 9 的桶
        _fz_re = re.compile(r"单元\s*\[([\d\s,，、A-Za-z]+)\]|单元\s*(\d+[A-Za-z]?)")
        def _units_in(x):
            _ns = []
            for _m in _fz_re.finditer(x):
                if _m.group(1):
                    _ns += [trans_key(_n) for _n in re.findall(r"\d+[A-Za-z]?", _m.group(1))]
                elif _m.group(2):
                    _ns.append(trans_key(_m.group(2)))
            return _ns
        def _all_frozen(x):
            _ns = _units_in(x)
            return bool(_ns) and all(_n in _fz for _n in _ns)
        FE = [x for x in E if _all_frozen(x)]; E = [x for x in E if not _all_frozen(x)]
        FW = [x for x in W if _all_frozen(x)]; W = [x for x in W if not _all_frozen(x)]

    # ---------- 输出 ----------
    print("="*64)
    print(f"跨单元一致性检核报告：{folder}")
    print(f"单元数 {len(files)}，分镜总数 {sum(len(split_shots(open(f,encoding='utf-8').read())) for f in files)}")
    print("="*64)
    for tag, arr in [("ERROR", E), ("WARN", W)]:
        if arr:
            print(f"\n【{tag}】{len(arr)} 条")
            for x in arr: print("  "+x)
    if FE or FW:
        print(f"\n【成片冻结区存量】ERROR {len(FE)} 条 / WARN {len(FW)} 条（第六幕单元1-31已成片、"
              f"不再回改，不计入上方结果与门禁；--frozen 追加的范围同桶）")
    for x in I: print(x)
    print("\n" + "-"*64)
    print(f"结果：ERROR {len(E)} 条，WARN {len(W)} 条 →", "全部通过 ✅" if not E else "存在必须修复项 ❌")
    return 1 if E else 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="一幕分镜所在目录（多幕混放时用 --only 指定一幕）")
    ap.add_argument("--only", default="", help="只校验文件名含该关键字的单元，一幕一检；多关键字逗号分隔为或，如 第六幕")
    ap.add_argument("--same", default="", help="同场景须逐字一致的单元号，逗号分隔，如 2,3,4,5,6")
    ap.add_argument("--prop", action="append", default=[], help="追踪道具，可多次")
    ap.add_argument("--rolelib", default="", help="角色库目录")
    ap.add_argument("--day", action="store_true"); ap.add_argument("--night", action="store_true")
    ap.add_argument("--min-scene", type=int, default=80)
    # v2.12：删 --expect-shots——用户裁决(2026-09-26)废除一切固定镜数，镜数是承载评估的结果、机检不设期望值
    ap.add_argument("--index-map", default="", help="v2.0：触发词调用地图 md 路径；传入后开启引用路径存在性校验(空指针ERROR)、编剧叙事库条目结构WARN、改编段意见单WARN")
    ap.add_argument("--method-lib", default="", help="v2.0：编剧叙事与钩子方法库 md 路径；默认从 --index-map 同目录推 分镜参考库/编剧叙事与钩子方法库.md")
    ap.add_argument("--workbench-dir", default="", help="v2.0：编剧工作台/分段编剧意见 目录；默认从 --index-map 同目录推 编剧工作台/分段编剧意见")
    ap.add_argument("--ban-foreign-names", action="store_true", help="v2.1：扫描【项目库】外部作品专名（拉片反哺入库QA），命中 ERROR；锚点行/清洗日志豁免")
    ap.add_argument("--lib-dir", default="", help="v2.1：【项目库】根目录，供 --ban-foreign-names 扫描；不传则取 --index-map 同级目录")
    ap.add_argument("--frozen", default="", help="v2.6：成片冻结区单元号（如 1-31 或 1,2,3）；相关发现项移入存量桶，不计入 ERROR/WARN 与门禁")
    a = ap.parse_args()
    # 未显式传 workbench-dir 时，若给了 index-map 则自动推断
    if not a.workbench_dir and a.index_map:
        a.workbench_dir = os.path.join(os.path.dirname(os.path.abspath(a.index_map)), "编剧工作台", "分段编剧意见")
    if not os.path.isdir(a.folder):
        print("目录不存在：", a.folder); sys.exit(2)
    sys.exit(check_dir(a.folder, a))

if __name__ == "__main__":
    main()
