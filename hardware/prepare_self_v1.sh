#!/usr/bin/env bash
#
# BUSTAGO Phase 3 데이터 가공 오케스트레이션
# =========================================
# Phase 3-1 (프레임 추출) → 3-2 (auto-label) → 3-3 (얼굴 비식별 옵션) → 3-4 (8:2 split)
# 까지를 1회 실행으로 수행. 각 단계는 idempotent — 결과물이 이미 있으면 skip.
#
# 사용:
#   hardware/prepare_self_v1.sh                                    # 기본 (raw_videos/ → self_v1/)
#   hardware/prepare_self_v1.sh --raw /path/to/raw_videos --interval 2 --val-ratio 0.2
#   hardware/prepare_self_v1.sh --anonymize                        # 얼굴 비식별 추가
#   hardware/prepare_self_v1.sh --skip-autolabel                   # autolabel은 따로 (yolo11x 없을 때)
#   hardware/prepare_self_v1.sh --dry-run                          # 명령만 출력
#
# 산출:
#   datasets/bustago_person/self_v1/
#   ├── raw_videos/*.mp4              # (입력, 이미 존재)
#   ├── frames/<video>_*.jpg          # 3-1
#   ├── labels_auto/<video>_*.txt     # 3-2 (auto-label 원본)
#   ├── frames_anon/<video>_*.jpg     # 3-3 (--anonymize 시)
#   ├── images/train/                 # 3-4 split (검수는 사람이 별도)
#   ├── images/val/
#   ├── labels/train/
#   └── labels/val/
#
# 영상 단위 grouping: 한 영상의 모든 프레임은 train 또는 val 한쪽에만 들어감 (data leak 방지).

set -euo pipefail

# ---------- 기본값 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DEFAULT_BASE="${PROJECT_ROOT}/datasets/bustago_person/self_v1"
DEFAULT_INTERVAL=2.0
DEFAULT_VAL_RATIO=0.2
DEFAULT_YOLO_MODEL="yolo11x.pt"
DEFAULT_CONF=0.25

BASE_DIR="${BASE_DIR:-$DEFAULT_BASE}"
RAW_DIR=""
INTERVAL="${INTERVAL:-$DEFAULT_INTERVAL}"
VAL_RATIO="${VAL_RATIO:-$DEFAULT_VAL_RATIO}"
YOLO_MODEL="${YOLO_MODEL:-$DEFAULT_YOLO_MODEL}"
CONF="${CONF:-$DEFAULT_CONF}"
ANONYMIZE=0
SKIP_AUTOLABEL=0
DRY_RUN=0
SEED=42

usage() {
    cat <<EOF
BUSTAGO Phase 3 자체 데이터 가공 (Phase 3-1 ~ 3-4)

Usage:
  $(basename "$0") [options]

Options:
  --raw DIR        입력 raw_videos 디렉토리 (기본: <base>/raw_videos)
  --base DIR       self_v1 기준 디렉토리 (기본: ${DEFAULT_BASE})
  --interval N     프레임 추출 간격 초 (기본: ${DEFAULT_INTERVAL})
  --val-ratio R    검증 분할 비율, 영상 단위 (기본: ${DEFAULT_VAL_RATIO})
  --model PATH     auto-label에 사용할 YOLO 모델 (기본: ${DEFAULT_YOLO_MODEL})
  --conf N         auto-label confidence threshold (기본: ${DEFAULT_CONF})
  --anonymize      Phase 3-3: 얼굴 비식별 처리 (frames → frames_anon)
  --skip-autolabel auto-label 건너뜀 (yolo11x 미설치 환경)
  --seed N         split 재현성 (기본: 42)
  --dry-run        실제 실행 없이 명령만 출력
  --help           이 메시지

Examples:
  # 기본 (autolabel 포함, anonymize 생략)
  $(basename "$0")

  # 익명화 포함
  $(basename "$0") --anonymize

  # autolabel 건너뛰고 프레임 추출 + split만
  $(basename "$0") --skip-autolabel

  # 7:3 split
  $(basename "$0") --val-ratio 0.3
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --raw)             RAW_DIR="$2"; shift 2 ;;
        --base)            BASE_DIR="$2"; shift 2 ;;
        --interval)        INTERVAL="$2"; shift 2 ;;
        --val-ratio)       VAL_RATIO="$2"; shift 2 ;;
        --model)           YOLO_MODEL="$2"; shift 2 ;;
        --conf)            CONF="$2"; shift 2 ;;
        --anonymize)       ANONYMIZE=1; shift ;;
        --skip-autolabel)  SKIP_AUTOLABEL=1; shift ;;
        --seed)            SEED="$2"; shift 2 ;;
        --dry-run)         DRY_RUN=1; shift ;;
        --help|-h)         usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

# 경로 결정
[[ -z "$RAW_DIR" ]] && RAW_DIR="${BASE_DIR}/raw_videos"
FRAMES_DIR="${BASE_DIR}/frames"
FRAMES_ANON_DIR="${BASE_DIR}/frames_anon"
LABELS_AUTO_DIR="${BASE_DIR}/labels_auto"
IMG_TRAIN_DIR="${BASE_DIR}/images/train"
IMG_VAL_DIR="${BASE_DIR}/images/val"
LBL_TRAIN_DIR="${BASE_DIR}/labels/train"
LBL_VAL_DIR="${BASE_DIR}/labels/val"

# Python 인터프리터 (.venv 우선)
PYTHON="${PROJECT_ROOT}/.venv/bin/python"
[[ ! -x "$PYTHON" ]] && PYTHON="python3"

run() {
    if (( DRY_RUN )); then
        echo "[dry-run] $*"
    else
        echo "[run] $*" >&2
        "$@"
    fi
}

# ---------- pre-flight ----------
preflight() {
    local fail=0
    if [[ ! -d "$RAW_DIR" ]]; then
        echo "[ERR] raw_videos 디렉토리 없음: $RAW_DIR" >&2
        echo "    record_demo.sh로 시연 영상부터 녹화하세요." >&2
        fail=1
    else
        local n_mp4
        n_mp4=$(find "$RAW_DIR" -maxdepth 1 -name "*.mp4" 2>/dev/null | wc -l)
        if (( n_mp4 == 0 )); then
            echo "[ERR] $RAW_DIR 에 .mp4 파일이 없음" >&2
            fail=1
        else
            echo "[ok] raw_videos: $n_mp4 mp4 file(s)" >&2
        fi
    fi

    if [[ ! -x "$PYTHON" && "$PYTHON" != "python3" ]]; then
        echo "[ERR] Python 실행 파일 없음: $PYTHON" >&2
        fail=1
    fi

    for script in sample_frames.py autolabel.py anonymize_faces.py; do
        if [[ ! -f "$SCRIPT_DIR/$script" ]]; then
            echo "[ERR] 필요 스크립트 누락: $SCRIPT_DIR/$script" >&2
            fail=1
        fi
    done

    return $fail
}

# ---------- Phase 3-1: 프레임 추출 ----------
phase_3_1() {
    echo "" >&2
    echo "=== Phase 3-1: 프레임 추출 ===" >&2
    local existing
    existing=$(find "$FRAMES_DIR" -maxdepth 1 -name "*.jpg" 2>/dev/null | wc -l)
    if (( existing > 0 )) && [[ $DRY_RUN -eq 0 ]]; then
        echo "[skip] frames/ 에 이미 ${existing}장 존재. 강제 재추출하려면 디렉토리 삭제 후 재실행." >&2
        return 0
    fi

    while IFS= read -r video; do
        [[ -z "$video" ]] && continue
        run "$PYTHON" "$SCRIPT_DIR/sample_frames.py" \
            --video "$video" --out "$FRAMES_DIR" --interval "$INTERVAL"
    done < <(find "$RAW_DIR" -maxdepth 1 -name "*.mp4" | sort)
}

# ---------- Phase 3-2: auto-label ----------
phase_3_2() {
    echo "" >&2
    echo "=== Phase 3-2: auto-label (${YOLO_MODEL}) ===" >&2
    if (( SKIP_AUTOLABEL )); then
        echo "[skip] --skip-autolabel 지정. labels_auto는 사람이 다른 도구(Roboflow 등)로 생성." >&2
        return 0
    fi
    local frame_count
    frame_count=$(find "$FRAMES_DIR" -maxdepth 1 -name "*.jpg" 2>/dev/null | wc -l)
    if (( frame_count == 0 )) && [[ $DRY_RUN -eq 0 ]]; then
        echo "[skip] frames/ 비어있음 — Phase 3-1 결과 확인" >&2
        return 0
    fi
    local label_count
    label_count=$(find "$LABELS_AUTO_DIR" -maxdepth 1 -name "*.txt" 2>/dev/null | wc -l)
    if (( label_count >= frame_count )) && [[ $DRY_RUN -eq 0 ]]; then
        echo "[skip] labels_auto/ 에 ${label_count}장. frames와 같거나 많음." >&2
        return 0
    fi

    run "$PYTHON" "$SCRIPT_DIR/autolabel.py" \
        --images "$FRAMES_DIR" --labels "$LABELS_AUTO_DIR" \
        --model "$YOLO_MODEL" --conf "$CONF" --classes 0
}

# ---------- Phase 3-3: 얼굴 비식별 (옵션) ----------
phase_3_3() {
    if (( ! ANONYMIZE )); then
        return 0
    fi
    echo "" >&2
    echo "=== Phase 3-3: 얼굴 비식별 ===" >&2
    local existing
    existing=$(find "$FRAMES_ANON_DIR" -maxdepth 1 -name "*.jpg" 2>/dev/null | wc -l)
    if (( existing > 0 )) && [[ $DRY_RUN -eq 0 ]]; then
        echo "[skip] frames_anon/ 에 이미 ${existing}장. 강제 재처리하려면 디렉토리 삭제." >&2
        return 0
    fi
    run "$PYTHON" "$SCRIPT_DIR/anonymize_faces.py" \
        --input "$FRAMES_DIR" --output "$FRAMES_ANON_DIR" --method blur
}

# ---------- Phase 3-4: 8:2 split (영상 단위 grouping) ----------
phase_3_4() {
    echo "" >&2
    echo "=== Phase 3-4: 8:2 split (영상 단위, seed=${SEED}) ===" >&2
    local existing_train
    existing_train=$(find "$IMG_TRAIN_DIR" -maxdepth 1 -name "*.jpg" 2>/dev/null | wc -l)
    if (( existing_train > 0 )) && [[ $DRY_RUN -eq 0 ]]; then
        echo "[skip] images/train/ 에 이미 ${existing_train}장. 재분할하려면 images/ labels/ 삭제." >&2
        return 0
    fi

    local src_frames="$FRAMES_DIR"
    (( ANONYMIZE )) && src_frames="$FRAMES_ANON_DIR"

    # 영상 단위 grouping은 Python에서 처리 — sample_frames.py가 파일명을
    # <video_stem>_<idx>.jpg로 생성하므로 첫 underscore 앞이 video_stem.
    if (( DRY_RUN )); then
        echo "[dry-run] split: $src_frames + $LABELS_AUTO_DIR → train/val (영상 단위)"
        return 0
    fi

    "$PYTHON" - <<PYEOF
import random, shutil, sys
from pathlib import Path
from collections import defaultdict

src_frames = Path("$src_frames")
labels_auto = Path("$LABELS_AUTO_DIR")
img_train = Path("$IMG_TRAIN_DIR")
img_val = Path("$IMG_VAL_DIR")
lbl_train = Path("$LBL_TRAIN_DIR")
lbl_val = Path("$LBL_VAL_DIR")
val_ratio = float("$VAL_RATIO")
seed = int("$SEED")

for d in (img_train, img_val, lbl_train, lbl_val):
    d.mkdir(parents=True, exist_ok=True)

# 영상 단위 grouping — 파일명 <video_stem>_<6-digit-idx>.jpg
groups = defaultdict(list)
for img in sorted(src_frames.glob("*.jpg")):
    stem = img.stem
    # 끝의 _\d+ 패턴 제거하여 video_stem 추출
    video_stem = stem.rsplit("_", 1)[0]
    groups[video_stem].append(img)

if not groups:
    print("[ERR] frames가 없음", file=sys.stderr)
    sys.exit(1)

video_stems = sorted(groups.keys())
rng = random.Random(seed)
rng.shuffle(video_stems)
n_val = max(1, int(round(len(video_stems) * val_ratio)))
val_stems = set(video_stems[:n_val])
train_stems = set(video_stems[n_val:])

print(f"[split] videos={len(video_stems)} train={len(train_stems)} val={len(val_stems)} (val_ratio={val_ratio})")

n_t = n_v = 0
n_t_lbl = n_v_lbl = 0
for stem, imgs in groups.items():
    is_val = stem in val_stems
    img_dst = img_val if is_val else img_train
    lbl_dst = lbl_val if is_val else lbl_train
    for img in imgs:
        shutil.copy2(img, img_dst / img.name)
        if is_val: n_v += 1
        else: n_t += 1
        lbl = labels_auto / (img.stem + ".txt")
        if lbl.exists():
            shutil.copy2(lbl, lbl_dst / lbl.name)
            if is_val: n_v_lbl += 1
            else: n_t_lbl += 1

print(f"[split] train images={n_t} labels={n_t_lbl}")
print(f"[split] val   images={n_v} labels={n_v_lbl}")
PYEOF
}

# ---------- 메인 ----------
main() {
    echo "=== BUSTAGO Phase 3 prepare_self_v1 ==="
    echo "raw:        $RAW_DIR"
    echo "base:       $BASE_DIR"
    echo "interval:   $INTERVAL sec"
    echo "val_ratio:  $VAL_RATIO (영상 단위 grouping)"
    echo "autolabel:  $( ((SKIP_AUTOLABEL)) && echo skip || echo enabled )"
    echo "anonymize:  $( ((ANONYMIZE)) && echo enabled || echo skip )"
    echo "seed:       $SEED"
    [[ $DRY_RUN -eq 1 ]] && echo "dry-run:    YES"

    if ! preflight; then
        if (( DRY_RUN )); then
            echo "[dry-run] pre-flight 실패 (위 메시지 참고). 계속 진행하여 명령만 시뮬레이션." >&2
        else
            echo "[ERR] pre-flight 실패. 위 항목 해결 후 재시도." >&2
            exit 1
        fi
    fi

    phase_3_1
    phase_3_2
    phase_3_3
    phase_3_4

    echo ""
    echo "=== 완료. 다음 단계: ==="
    echo "1. 사람 검수 (Roboflow 또는 LabelImg)로 ${LBL_TRAIN_DIR} / ${LBL_VAL_DIR} 확인·수정"
    echo "2. hardware/configs/bustago_person_self.yaml 생성 (path: ${BASE_DIR})"
    echo "3. python hardware/train_yolo.py --data hardware/configs/bustago_person_self.yaml \\"
    echo "                                 --model yolo11n.pt --name self_v1_finetune"
}

main
