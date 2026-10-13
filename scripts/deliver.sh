#!/usr/bin/env bash
# deliver.sh — 工程可迭代交付打包（仿影子羁绊交付逻辑 + 语义化版本 + 文件清单）
#
# 产出：交付/巨人血脉分镜项目_交付_<版本>_<日期时间>.zip
# 包内：顶层同名目录 / README_交付说明.md / MANIFEST_文件清单.txt / 全部工程内容
#
# 用法:
#   bash scripts/deliver.sh                      用当前版本打包（VERSION 不变）
#   bash scripts/deliver.sh patch                补号+1  (1.0.0 -> 1.0.1)
#   bash scripts/deliver.sh minor                次号+1  (1.0.0 -> 1.1.0)
#   bash scripts/deliver.sh major                主号+1  (1.0.0 -> 2.0.0)
#   bash scripts/deliver.sh v1.2.3               指定版本并写回 VERSION
#   可选: -m "本次变更说明"   --encrypt（交互式给 zip 设密码）
#
# 安全：默认排除密钥、日志、本地备份、可重建的大索引（详见 EXCLUDES）。
set -euo pipefail

# 强制 UTF-8，避免变量名紧贴中文/全角标点时吞字节
export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DELIV="$ROOT/交付"
VERSION_FILE="$DELIV/VERSION"
CHANGELOG="$DELIV/版本记录.md"
mkdir -p "$DELIV"

# ── 解析参数 ──
ACTION="keep"; NOTE=""; ENCRYPT=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    -m)         NOTE="${2:?缺 -m 内容}"; shift 2 ;;
    --encrypt)  ENCRYPT=1; shift ;;
    patch|minor|major) ACTION="$1"; shift ;;
    v[0-9]*.[0-9]*.[0-9]*) ACTION="$1"; shift ;;
    *) echo "[中止] 未识别参数: $1"; exit 1 ;;
  esac
done

# ── 计算版本 ──
CUR="$(tr -d '[:space:]' < "$VERSION_FILE")"
CUR="${CUR#v}"
X="${CUR%%.*}"; REST="${CUR#*.}"; Y="${REST%%.*}"; Z="${REST##*.}"
case "$ACTION" in
  keep)  : ;;
  patch) Z=$((Z+1)) ;;
  minor) Y=$((Y+1)); Z=0 ;;
  major) X=$((X+1)); Y=0; Z=0 ;;
  v*)    V="${ACTION#v}"; X="${V%%.*}"; R2="${V#*.}"; Y="${R2%%.*}"; Z="${R2##*.}" ;;
esac
VER="v$X.$Y.$Z"
echo "$VER" > "$VERSION_FILE"

STAMP="$(date +%Y%m%d-%H%M)"
HUMAN="$(date +%Y-%m-%d\ %H:%M)"
PKG="巨人血脉分镜项目_交付_${VER}_${STAMP}"
STAGE="$(mktemp -d)"
DEST="$STAGE/$PKG"

# ── 复制工程（排除敏感与冗余）──
echo "═══ [1/5] 收集工程内容 ═══"
rsync -a \
  --exclude='.DS_Store' \
  --exclude='.git/' \
  --exclude='.grsai_key' \
  --exclude='.lapian/index.json' \
  --exclude='logs/' \
  --exclude='【备份】/' \
  --exclude='交付/' \
  --exclude='output/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='*.zip' \
  --exclude='.xg-animate-manager/' \
  "$ROOT/" "$DEST/"

# ── 规模统计 ──
count_png() { [ -d "$DEST/$1" ] && find "$DEST/$1" -name '*.png' | wc -l | tr -d ' ' || echo 0; }
N_SCENE="$(count_png '【项目库】/场景卡')"
N_PROP="$(count_png '【项目库】/道具卡')"
N_SPECIES="$(count_png '【项目库】/异种卡')"
N_CARD="$(count_png '【项目库】/角色卡')"
N_EP="$(find "$DEST/【剧本模块】" -name '剧本_EP*.md' 2>/dev/null | wc -l | tr -d ' ')"

# ── 追加版本记录（先记录，README 才能带上）──
[ -z "$NOTE" ] && NOTE="例行交付"
cat >> "$CHANGELOG" <<EOF

## $VER · $HUMAN
- 变更：$NOTE
- 剧本：${N_EP} 集｜场景卡 ${N_SCENE}｜道具卡 ${N_PROP}｜异种卡 ${N_SPECIES}｜角色卡 ${N_CARD}
EOF

# ── 生成 README 交付说明 ──
echo "═══ [2/5] 生成 README 交付说明 ═══"
cat > "$DEST/README_交付说明.md" <<EOF
# 巨人血脉 · 分镜项目 · 交付说明

| 项 | 内容 |
|---|---|
| 交付版本 | **$VER** |
| 打包时间 | $HUMAN |
| 交付对象 | 合作伙伴（制作向） |

## 一、项目简介
《我觉醒巨人血脉，校花女友崩溃了》分镜项目。赛博灵气近未来世界观，
短剧模式（一分钟一钩子、整体三幕式）。本包含剧本、世界观、角色 / 场景 /
道具 / 异种的设定与图片、描述词、出图工具，可直接进入分镜与制作。

## 二、目录导读
| 目录 / 文件 | 用途 |
|---|---|
| \`README·项目总览.md\` | 项目总入口、进度与全量台账（先看这个） |
| \`【剧本模块】/\` | 短剧排版规范＋全季总纲＋EP 剧本（共 ${N_EP} 集） |
| \`【项目库】/\` | 角色库、场景库、描述词库、技能装备库、美术库、故事线、编剧工作台等 |
| \`【项目库】/角色卡·场景卡·道具卡·异种卡\` | 出图 / 制作的官方参考图 |
| \`【项目库】/描述词库/\` | 角色 / 场景 / 道具 / 异种高颗粒度文字（材质·颜色·布局·全息·镜头跟随） |
| \`【巨则V1.0永久备份】/\` | 第一季规则总纲 |
| \`scripts/\` | GRS 出图接口、批量出图、拉片召回等工具（不含任何密钥） |
| \`.lapian/config.json\` | 拉片库路径配置模板（拉片索引为内部可重建数据，未随包提供） |
| \`我觉醒…by山海经搬运工.txt\` | 原著全文 |
| \`《…》全书剧情梳理.md\` | 全书剧情与节点梳理 |

## 三、内容规模
- 剧本：${N_EP} 集
- 场景卡：${N_SCENE} 张｜道具卡：${N_PROP} 张｜异种卡：${N_SPECIES} 张｜角色卡：${N_CARD} 张

## 四、快速上手
\`\`\`bash
# 1) 出图前配置你自己的 GRS key（脚本不携带任何密钥）
export GRSAI_API_KEY="sk-你的key"

# 2) 出图（会自动挂角色卡 / 场景卡）
python3 scripts/grsai_image_api.py "画面描述" --card 徐琨 --ratio 16:9

# 3) 批量出图（断点续跑 / 失败重试）
python3 scripts/batch_generate.py scenes
\`\`\`
- 拉片召回（可选）：\`python3 scripts/lapian_lib.py status\`，再按需改
  \`.lapian/config.json\` 的 roots 指向你本地的拉片库；索引可用
  \`python3 scripts/lapian_lib.py index\` 重建。

## 五、如何迭代（同一套脚本）
\`\`\`bash
bash scripts/deliver.sh patch    # 小修小改 1.0.0 -> 1.0.1
bash scripts/deliver.sh minor    # 新增集/模块 1.0.0 -> 1.1.0
bash scripts/deliver.sh major    # 新一季/大改 1.0.0 -> 2.0.0
bash scripts/deliver.sh -m "本次改了什么" patch
\`\`\`
- 每次交付自动更新 \`交付/VERSION\` 并追加 \`交付/版本记录.md\`。
- 逐文件核对见包内 \`MANIFEST_文件清单.txt\`。

## 六、安全与边界
- 本包**不含 API 密钥**：GRS key 仅从环境变量或本地 \`.grsai_key\` 读取。
- 已排除：日志、本地【备份】、72MB 可重建的 \`.lapian/index.json\`、系统与缓存文件。
- 传输建议走安全渠道；如需加密压缩，用 \`--encrypt\` 交付（交互设置密码）。

---

## 附：版本历史

$(cat "$CHANGELOG")
EOF

# ── 生成 MANIFEST ──
echo "═══ [3/5] 生成文件清单 MANIFEST ═══"
( cd "$DEST" && find . -type f ! -name 'MANIFEST_文件清单.txt' \
    | sed 's|^\./||' | sort \
    | while IFS= read -r f; do printf '%12s  %s\n' "$(stat -f%z "$f")" "$f"; done \
) > "$DEST/MANIFEST_文件清单.txt"

N_FILES="$(find "$DEST" -type f | wc -l | tr -d ' ')"
SIZE="$(du -sh "$DEST" | cut -f1)"

# ── 压缩 ──
echo "═══ [4/5] 压缩打包（${N_FILES} 文件 / ${SIZE}）═══"
ZIP="$DELIV/$PKG.zip"
if [ "$ENCRYPT" -eq 1 ]; then
  echo "[加密] 请按提示连续输入两次解压密码："
  ( cd "$STAGE" && zip -r -q -X -e "$ZIP" "$PKG" )
else
  ( cd "$STAGE" && zip -r -q -X "$ZIP" "$PKG" )
fi

# ── 清理 ──
rm -rf "$STAGE"

echo "═══ [5/5] 交付完成 ═══"
echo "版本 : $VER"
echo "压缩包: $ZIP"
echo "规模 : $N_FILES 文件 / 解压后 $SIZE"
echo "校验 : unzip -l \"$ZIP\" | head"
