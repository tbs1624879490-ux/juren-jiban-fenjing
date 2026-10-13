"""
Grsai 图像生成 API 统一接入脚本 v2（本项目复刻自「影子羁绊」同款）
支持模型: gpt-image-2 / gpt-image-2.5 系列 + nano-banana 系列

接口文档:
  - gpt-image-2/2.5 生成: https://qmy27nhsd9.apifox.cn/452409160e0
  - 异步结果查询:       https://qmy27nhsd9.apifox.cn/452409577e0
  - nano-banana:        https://qmy27nhsd9.apifox.cn/452392911e0

脚本位置: 项目根/scripts/grsai_image_api.py
本地密钥: 项目根/.grsai_key（权限 600、已在 .gitignore，不进 git、不打包外传）

用法（命令行）:
  # 首次：把你自己的 key 存到本地一次（或 export GRSI_API_KEY=sk-xxxxx）
  python3 scripts/grsai_image_api.py setkey sk-xxxxx

  # 出图（分镜模板，默认 16:9）
  python3 scripts/grsai_image_api.py "画面描述" --model gpt-image-2.5 --ratio 16:9

  # 垫参考图（角色卡/场景卡，可重复多张）
  python3 scripts/grsai_image_api.py "画面描述" --image 【项目库】/角色卡/徐琨.png

  # 按卡片名自动挂参考图 + 打印性格表演要点
  python3 scripts/grsai_image_api.py "画面描述" --card 徐琨

  # 查询异步任务
  python3 scripts/grsai_image_api.py --query 14-5f3cf761-xxxx
"""

import argparse
import base64
import json
import mimetypes
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# ========== 配置 ==========

# 基础节点（二选一）
BASE_URL_GLOBAL = "https://grsaiapi.com"      # 全球节点
BASE_URL_CN = "https://grsai.dakka.com.cn"    # 国内节点

DEFAULT_BASE_URL = BASE_URL_CN

# API Key 读取优先级：命令行 --apikey ＞ 环境变量 GRSI_API_KEY ＞ 本地密钥文件
# 本地文件：项目根/.grsai_key（已在 .gitignore，不进 git、不回传、不打进给别人的包）
#   合作者只需把自己的 key 写进该文件一次（一行：sk-xxxxx），或运行：
#   python3 scripts/grsai_image_api.py setkey sk-xxxxx
def _local_key_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".grsai_key")

def _read_local_key():
    p = _local_key_path()
    if not os.path.exists(p):
        return ""
    for ln in open(p, encoding="utf-8"):
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            return ln
    return ""

API_KEY = os.environ.get("GRSI_API_KEY", "") or _read_local_key()

DEFAULT_MODEL = "gpt-image-2.5"
DEFAULT_REPLY_TYPE = "async"  # json / stream / async

# ========== 模型与参数配置 ==========

NANO_BANANA_MODELS = [
    "nano-banana", "nano-banana-fast", "nano-banana-2",
    "nano-banana-2-cl", "nano-banana-2-2k-cl", "nano-banana-2-4k-cl",
    "nano-banana-pro", "nano-banana-pro-vt", "nano-banana-pro-cl",
    "nano-banana-pro-vip", "nano-banana-pro-4k-vip",
]

GPT_IMAGE_MODELS = [
    "gpt-image-2", "gpt-image-2-vip",
    "gpt-image-2.5", "gpt-image-2.5-flare", "gpt-image-2.5-sunburst",
]

AVAILABLE_MODELS = NANO_BANANA_MODELS + GPT_IMAGE_MODELS

# 各模型允许的 quality 值（接口文档规定；取 allowed[0] 为默认值）
MODEL_QUALITY_OPTIONS: Dict[str, List[str]] = {
    "gpt-image-2": ["auto"],
    "gpt-image-2.5": ["auto"],
    "gpt-image-2-vip": ["medium"],
    "gpt-image-2.5-flare": ["low", "medium", "high"],
    "gpt-image-2.5-sunburst": ["low", "medium", "high", "xhigh", "max"],
}

# 支持 background=transparent 的模型
BACKGROUND_SUPPORTED_MODELS = {
    "gpt-image-2-vip", "gpt-image-2.5-flare", "gpt-image-2.5-sunburst",
}

# 仅支持像素值 aspectRatio（不支持比例字符串）的模型
PIXEL_ONLY_MODELS = {
    "gpt-image-2-vip", "gpt-image-2.5-flare", "gpt-image-2.5-sunburst",
}

# vip / flare / sunburst 比例 -> 1K/2K/4K 像素对照表
GPT_IMAGE_VIP_SIZE_MAP = {
    "1:1":    {"1K": "1024x1024", "2K": "2048x2048", "4K": "2880x2880"},
    "16:9":   {"1K": "1280x720",  "2K": "2048x1152", "4K": "3840x2160"},
    "9:16":   {"1K": "720x1280",  "2K": "1152x2048", "4K": "2160x3840"},
    "4:3":    {"1K": "1152x864",  "2K": "2304x1728", "4K": "3264x2448"},
    "3:4":    {"1K": "864x1152",  "2K": "1728x2304", "4K": "2448x3264"},
    "3:2":    {"1K": "1536x1024", "2K": "2048x1360", "4K": "3504x2336"},
    "2:3":    {"1K": "1024x1536", "2K": "1360x2048", "4K": "2336x3504"},
    "5:4":    {"1K": "1120x896",  "2K": "2240x1792", "4K": "3200x2560"},
    "4:5":    {"1K": "896x1120",  "2K": "1792x2240", "4K": "2560x3200"},
    "21:9":   {"1K": "1456x624",  "2K": "2912x1248", "4K": "3840x1648"},
    "9:21":   {"1K": "624x1456",  "2K": "1248x2912", "4K": "1648x3840"},
    "1:3":    {"1K": "688x2048",  "2K": None,        "4K": "1280x3840"},
    "3:1":    {"1K": "2048x688",  "2K": None,        "4K": "3840x1280"},
    "2:1":    {"1K": "1536x768",  "2K": "3072x1536", "4K": "3840x1920"},
    "1:2":    {"1K": "768x1536",  "2K": "1536x3072", "4K": "1920x3840"},
}


# ========== 参数校验与解析 ==========

def _is_nano_banana(model: str) -> bool:
    return model in NANO_BANANA_MODELS


def load_image_ref(source: str) -> str:
    """
    参考图预处理：本地路径 -> data URI base64；http(s) URL / data URI -> 原样返回
    """
    if source.startswith(("http://", "https://", "data:")):
        return source
    path = Path(source).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"参考图不存在: {source}")
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def _validate_vip_pixels(px: str) -> str:
    """校验 vip/flare/sunburst 自定义像素约束"""
    try:
        w, h = (int(v) for v in px.lower().split("x"))
    except ValueError:
        raise ValueError(f"像素格式错误: {px}（应为 如 2048x1152）")
    if max(w, h) > 3840:
        raise ValueError(f"最大边长超限: {px}（须 ≤3840px）")
    if w % 16 or h % 16:
        raise ValueError(f"两边长均须为16的倍数: {px}")
    if max(w, h) / min(w, h) > 3:
        raise ValueError(f"长短边之比超限: {px}（须 ≤3:1）")
    total = w * h
    if not (655_360 <= total <= 8_294_400):
        raise ValueError(f"总像素数超限: {px}（须 655360 ~ 8294400）")
    return px


def _resolve_aspect_ratio(
    model: str,
    ratio: Optional[str] = None,
    image_size: str = "1K",
) -> str:
    """
    根据模型解析实际传给 API 的 aspectRatio 值

    - nano-banana 系列：比例字符串（如 "16:9"）
    - gpt-image-2 / gpt-image-2.5（基础版）：比例字符串 或 1K 像素值
    - gpt-image-2-vip / 2.5-flare / 2.5-sunburst：仅像素值，按 1K/2K/4K 档位查表，
      自定义像素值须满足约束（16倍数 / ≤3840 / ≤3:1 / 总像素范围）
    """
    if ratio and "x" in ratio.lower():
        if model in PIXEL_ONLY_MODELS:
            return _validate_vip_pixels(ratio)
        return ratio

    ratio = ratio or "16:9"

    if _is_nano_banana(model):
        return ratio

    if model in ("gpt-image-2", "gpt-image-2.5"):
        return ratio

    if model in PIXEL_ONLY_MODELS:
        tier_map = GPT_IMAGE_VIP_SIZE_MAP.get(ratio)
        if not tier_map:
            raise ValueError(f"{model} 不支持比例 {ratio}（该模型仅接受像素值）")
        px = tier_map.get(image_size)
        if not px:
            raise ValueError(f"比例 {ratio} 不支持 {image_size} 档位（可选: "
                             f"{[k for k, v in tier_map.items() if v]}）")
        return px

    return ratio


def _resolve_quality(model: str, quality: Optional[str]) -> Optional[str]:
    """按模型校验 quality，不合法时自动纠正为该模型默认值并提示"""
    if model not in MODEL_QUALITY_OPTIONS:
        return None  # nano-banana 系列不支持 quality
    allowed = MODEL_QUALITY_OPTIONS[model]
    if quality is None:
        return allowed[0]
    if quality not in allowed:
        print(f"[警告] {model} 不支持 quality={quality}，"
              f"已改为 {allowed[0]}（允许: {allowed}）")
        return allowed[0]
    return quality


# ========== 核心函数 ==========

def _headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers


def _post(url: str, payload: Dict[str, Any], timeout: int = 600) -> Dict[str, Any]:
    resp = requests.post(url, headers=_headers(), json=payload, timeout=timeout)
    if resp.status_code >= 400:
        try:
            err = resp.json()
            raise RuntimeError(
                f"API {resp.status_code}: {err.get('error', resp.text)} "
                f"(id={err.get('id')}, status={err.get('status')})")
        except ValueError:
            resp.raise_for_status()
    return resp.json()


def generate_image(
    prompt: str,
    model: str = DEFAULT_MODEL,
    images: Optional[List[str]] = None,
    aspect_ratio: Optional[str] = None,
    image_size: str = "1K",
    quality: Optional[str] = None,
    background: Optional[str] = None,
    mask: Optional[str] = None,
    reply_type: str = DEFAULT_REPLY_TYPE,
    base_url: str = DEFAULT_BASE_URL,
) -> Dict[str, Any]:
    """
    提交图像生成请求

    Args:
        prompt: 提示词
        model: 模型名称
        images: 参考图列表（本地路径自动转 base64，或直接传 URL）
        aspect_ratio: 比例（如 "16:9"）或像素值（如 "2048x1152"）
        image_size: 分辨率档位 1K/2K/4K（仅 vip/flare/sunburst 生效）
        quality: 质量（按模型自动校验）
        background: "transparent"（仅 vip/flare/sunburst 支持）
        mask: 蒙版图 URL（局部重绘用）
        reply_type: json / stream / async
        base_url: 基础节点 URL

    Returns:
        API 响应 JSON（async 返回 {id, status}，json 直接返回最终结果）
    """
    url = f"{base_url}/v1/api/generate"

    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "images": [load_image_ref(s) for s in (images or [])],
        "aspectRatio": _resolve_aspect_ratio(model, aspect_ratio, image_size),
        "replyType": reply_type,
    }

    q = _resolve_quality(model, quality)
    if q:
        payload["quality"] = q

    if background:
        if background == "transparent" and model in BACKGROUND_SUPPORTED_MODELS:
            payload["background"] = background
        else:
            print(f"[警告] {model} 不支持 background={background}，已忽略")

    if mask:
        payload["mask"] = mask

    return _post(url, payload)


def query_result(task_id: str, base_url: str = DEFAULT_BASE_URL) -> Dict[str, Any]:
    """查询异步生成结果"""
    url = f"{base_url}/v1/api/result"
    resp = requests.get(url, headers=_headers(), params={"id": task_id}, timeout=60)
    if resp.status_code >= 400:
        try:
            err = resp.json()
            raise RuntimeError(f"API {resp.status_code}: {err.get('error', resp.text)}")
        except ValueError:
            resp.raise_for_status()
    return resp.json()


def generate_and_wait(
    prompt: str,
    model: str = DEFAULT_MODEL,
    images: Optional[List[str]] = None,
    aspect_ratio: Optional[str] = None,
    image_size: str = "1K",
    quality: Optional[str] = None,
    background: Optional[str] = None,
    mask: Optional[str] = None,
    base_url: str = DEFAULT_BASE_URL,
    poll_interval: int = 3,
    max_wait: int = 300,
    verbose: bool = True,
) -> Dict[str, Any]:
    """提交生成（async 模式）并轮询等待完成"""
    if verbose:
        resolved = _resolve_aspect_ratio(model, aspect_ratio, image_size)
        print(f"[提交] 模型={model} | 比例={aspect_ratio} -> {resolved} | 档位={image_size}")
        if images:
            print(f"[参考图] {len(images)} 张")
        if background:
            print(f"[背景] {background}")
        if mask:
            print(f"[蒙版] {mask}")
        print(f"[提示词] {prompt[:80]}..." if len(prompt) > 80 else f"[提示词] {prompt}")

    result = generate_image(
        prompt=prompt, model=model, images=images,
        aspect_ratio=aspect_ratio, image_size=image_size, quality=quality,
        background=background, mask=mask,
        reply_type="async", base_url=base_url,
    )

    task_id = result.get("id")
    status = result.get("status", "running")
    if verbose:
        print(f"[任务] id={task_id} 状态={status}")

    if status in ("succeeded", "failed", "violation"):
        return result

    waited = 0
    while waited < max_wait:
        time.sleep(poll_interval)
        waited += poll_interval

        result = query_result(task_id, base_url=base_url)
        status = result.get("status", "running")
        progress = result.get("progress", 0)

        if verbose:
            print(f"[进度] {status} - {progress}% (已等 {waited}s)")

        if status == "succeeded":
            if verbose and result.get("results"):
                print(f"[完成] 图片链接: {result['results'][0].get('url', '')}")
            return result
        elif status in ("failed", "violation"):
            if verbose:
                print(f"[失败] {status}: {result.get('error', '未知错误')}")
            return result

    if verbose:
        print(f"[超时] 等待 {max_wait}s 仍未完成，可稍后用 query_result('{task_id}') 查询")
    return result


def download_image(url: str, save_path: str) -> str:
    """下载生成的图片到本地"""
    resp = requests.get(url, timeout=180)
    resp.raise_for_status()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(resp.content)
    return save_path


# ========== 【项目库】卡片解析（出图三步法支撑） ==========

def _find_card_root():
    # 向上查找含【项目库】的目录：脚本位于 项目根/scripts，项目根即含【项目库】
    for _p in Path(__file__).resolve().parents:
        _cand = _p / "【项目库】"
        if _cand.is_dir():
            return _cand
    raise RuntimeError("未找到【项目库】目录（脚本父级链中均不存在）")

CARD_ROOT = _find_card_root()
CARD_TYPES = ("角色卡", "异种卡", "场景卡", "道具卡")

_SETTING_DIRS = {
    "角色卡": ("角色库/主角", "角色库/主要配角", "角色库/次要角色"),
    "异种卡": ("技能装备库/异种图鉴",),
    "场景卡": ("场景库",),
    "道具卡": ("技能装备库/装备道具",),
}


def _find_setting_doc(ctype: str, name: str) -> Optional[Path]:
    # 双造型卡（如 徐琨_出战装）回落到主词条（徐琨.md）
    candidates = [name]
    if "_" in name:
        candidates.append(name.split("_", 1)[0])
    for sub in _SETTING_DIRS.get(ctype, ()):
        d = CARD_ROOT / sub
        if not d.exists():
            continue
        for cand in candidates:
            for md in sorted(d.rglob("*.md")):
                if cand in md.stem:
                    return md
    return None


def resolve_card(name: str) -> Dict[str, Any]:
    """
    在【项目库】四卡库中按名称解析卡片（卡名即文件名，生图锚定）

    匹配顺序：文件名 stem 精确等于 name → 文件名包含 name（多形态/编号变体）
    设定文档按卡类型回查：角色卡→角色库、异种卡→异种图鉴、场景卡→场景库、道具卡→装备道具
    Returns: {"type", "folder", "images", "doc"}
    """
    for ctype in CARD_TYPES:
        base = CARD_ROOT / ctype
        if not base.exists():
            continue
        pngs = sorted(base.glob("*.png")) + sorted(base.glob("*.jpg"))
        exact = [p for p in pngs if p.stem == name]
        fuzzy = [p for p in pngs if name in p.stem]
        selected = exact or fuzzy
        if selected:
            doc = _find_setting_doc(ctype, name)
            return {
                "type": ctype,
                "folder": str(base),
                "images": [str(p) for p in selected],
                "doc": str(doc) if doc else None,
            }
    raise FileNotFoundError(f"【项目库】卡库中未找到卡片: {name}（已检索 {list(CARD_TYPES)}）")


def read_card_setting(name: str) -> str:
    """读取卡片设定文档全文（出图三步法第1步：性格分析数据源）"""
    card = resolve_card(name)
    if not card["doc"]:
        return ""
    return Path(card["doc"]).read_text(encoding="utf-8")


def extract_personality(setting_text: str) -> str:
    """从设定文档中提取「性格/表演要点」段落"""
    out: List[str] = []
    capture = False
    for line in setting_text.splitlines():
        if line.startswith("#"):
            capture = "性格" in line or "表演" in line
        elif capture and line.strip():
            out.append(line)
    return "\n".join(out)


def generate_storyboard_image(
    shot_description: str,
    scene: str = "赛博朋克都市",
    model: str = DEFAULT_MODEL,
    images: Optional[List[str]] = None,
    aspect_ratio: str = "16:9",
    image_size: str = "1K",
    quality: Optional[str] = None,
    background: Optional[str] = None,
    mask: Optional[str] = None,
    save_dir: str = "./output",
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    分镜专用生成函数 —— 自动拼接电影级分镜风格提示词

    images 传入素材图库的角色卡/场景卡本地路径可锁定人物与场景一致性
    """
    full_prompt = (
        f"{shot_description}, "
        f"{scene}背景, "
        f"3D动漫CG写实质感, 电影级光影, 8K超高清细节, "
        f"赛博朋克风格, 精细构图, 专业分镜画面"
    )

    result = generate_and_wait(
        prompt=full_prompt, model=model, images=images,
        aspect_ratio=aspect_ratio, image_size=image_size,
        quality=quality, background=background, mask=mask, verbose=True,
    )

    local_path = None
    if result.get("status") == "succeeded" and result.get("results"):
        url = result["results"][0]["url"]
        if not filename:
            filename = url.split("/")[-1]
        save_path = os.path.join(save_dir, filename)
        local_path = download_image(url, save_path)
        print(f"[已保存] {local_path}")

    return {"result": result, "local_path": local_path}


# ========== 命令行入口 ==========

def main():
    parser = argparse.ArgumentParser(
        description="Grsai 图像生成 API v2（gpt-image-2/2.5 + nano-banana）")
    parser.add_argument("prompt", nargs="?",
        help='提示词；首次可先运行：setkey sk-你的key（把你自己的密钥存到本地）')
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"模型 (默认: {DEFAULT_MODEL})")
    parser.add_argument("--ratio", default="16:9",
                        help="比例 或 像素值 如 2048x1152 (默认: 16:9)")
    parser.add_argument("--size", default="1K", choices=["1K", "2K", "4K"],
                        help="分辨率档位，仅 vip/flare/sunburst 生效 (默认: 1K)")
    parser.add_argument("--quality", default=None,
                        help="质量，按模型自动校验纠正")
    parser.add_argument("--image", action="append", default=[],
                        help="参考图（本地路径或URL），可重复传多张")
    parser.add_argument("--card", action="append", default=[],
                        help="素材图库卡片名称（如 徐琨/叶清漪），"
                             "自动挂载该卡片参考图+打印性格表演要点")
    parser.add_argument("--background", default=None, choices=["transparent"],
                        help="透明底，仅 vip/flare/sunburst 支持")
    parser.add_argument("--mask", default=None, help="蒙版图 URL（局部重绘）")
    parser.add_argument("--scene", default="赛博朋克都市",
                        help="分镜模板场景前缀 (默认: 赛博朋克都市)")
    parser.add_argument("--raw", action="store_true",
                        help="跳过分镜模板，直接使用原始提示词")
    parser.add_argument("--save", default="./output", help="保存目录 (默认: ./output)")
    parser.add_argument("--filename", default=None, help="保存文件名")
    parser.add_argument("--query", default=None, help="查询已有任务 ID 的结果")
    parser.add_argument("--global-node", action="store_true", help="使用全球节点")
    parser.add_argument("--apikey", default=None,
                        help="API Key (也可通过环境变量 GRSI_API_KEY 或本地文件 .grsai_key 设置)")
    # key_value：仅配合「setkey」用法传入你的 GRSI_API_KEY（普通出图留空）
    parser.add_argument("key_value", nargs="?", default=None,
                        help="配合 setkey 使用：你的 GRSI_API_KEY")
    args = parser.parse_args()

    # ① 密钥设置模式：grsai_image_api.py setkey sk-xxxxx
    if args.prompt == "setkey":
        key = (args.key_value or "").strip()
        if not key:
            exit("用法: grsai_image_api.py setkey sk-你的key")
        p = _local_key_path()
        with open(p, "w", encoding="utf-8") as f:
            f.write("# GRSI 本地密钥（请勿提交/外传）\n" + key + "\n")
        try:
            os.chmod(p, 0o600)
        except Exception:
            pass
        print(f"✅ 已把你的 key 写入本地：{os.path.relpath(p)}")
        print("   该文件不进 git、不回传；以后出图自动读取。")
        return

    global API_KEY
    if args.apikey:
        API_KEY = args.apikey

    base_url = BASE_URL_GLOBAL if args.global_node else DEFAULT_BASE_URL

    # 查询模式
    if args.query:
        if not API_KEY:
            print("错误: 未设置 API Key")
            exit(1)
        print(json.dumps(query_result(args.query, base_url=base_url),
                         ensure_ascii=False, indent=2))
        return

    if not args.prompt:
        parser.error("缺少提示词（或使用 --query 查询任务）")

    if not API_KEY:
        print("错误: 未设置 API Key")
        print("请设置环境变量: export GRSI_API_KEY=sk-xxxxx")
        print("或使用 --apikey 参数")
        exit(1)

    # 卡片解析（出图三步法：第1步性格分析数据 + 第2步参考图自动挂载）
    if args.card:
        for card_name in args.card:
            try:
                card = resolve_card(card_name)
            except FileNotFoundError as e:
                print(f"[错误] {e}")
                exit(1)
            print(f"[卡片] {card_name} → {card['type']}")
            for img in card["images"]:
                print(f"  参考图: {img}")
            if card["doc"]:
                setting = Path(card["doc"]).read_text(encoding="utf-8")
                personality = extract_personality(setting)
                print(f"  设定文档: {card['doc']}")
                if personality:
                    print("  --- 性格/表演要点（提示词须体现） ---")
                    for line in personality.splitlines():
                        print(f"  | {line}")
            args.image.extend(card["images"])
        print()

    if args.raw:
        result = generate_and_wait(
            prompt=args.prompt, model=args.model, images=args.image,
            aspect_ratio=args.ratio, image_size=args.size, quality=args.quality,
            background=args.background, mask=args.mask, base_url=base_url,
        )
        payload = {"result": result, "local_path": None}
        if result.get("status") == "succeeded" and result.get("results"):
            url = result["results"][0]["url"]
            fname = args.filename or url.split("/")[-1]
            payload["local_path"] = download_image(
                url, os.path.join(args.save, fname))
            print(f"[已保存] {payload['local_path']}")
    else:
        payload = generate_storyboard_image(
            shot_description=args.prompt, scene=args.scene, model=args.model,
            images=args.image, aspect_ratio=args.ratio, image_size=args.size,
            quality=args.quality, background=args.background, mask=args.mask,
            save_dir=args.save, filename=args.filename,
        )

    print("\n=== 最终结果 ===")
    print(json.dumps(payload["result"], ensure_ascii=False, indent=2))
    if payload["local_path"]:
        print(f"\n本地文件: {payload['local_path']}")


if __name__ == "__main__":
    main()
