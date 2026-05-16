#!/usr/bin/env bash
#
# BUSTAGO 시연일 영상 녹화 스크립트
# =================================
# Phase 2 (시연 당일 5/21)에 사용. counter.py 추론과 별도 트랙으로 raw mp4를 보관해
# Phase 3 (자체 데이터 가공)의 입력으로 활용한다.
#
# 동작:
#   - /dev/video0 (USB 웹캠 또는 CSI 카메라) 입력
#   - libx264 ultrafast 인코딩 (CPU 부담 최소)
#   - 외장 SSD에 1차 저장 + 로컬 백업 디렉토리에 2차 백업 (rsync, 종료 시)
#   - 종료 사유와 동의 시간대 정보를 동일 stem .meta.json 로그로 기록
#
# 사용:
#   hardware/record_demo.sh                 # 1시간 녹화, 외장 SSD 기본 경로
#   hardware/record_demo.sh --duration 1800 # 30분
#   hardware/record_demo.sh --output /path/to/file.mp4
#   hardware/record_demo.sh --dry-run       # 명령만 출력
#   hardware/record_demo.sh --help
#
# 동의 시간대 마킹: Ctrl-C로 종료 후 stem.meta.json에 사용자가 직접 시간대 기록.
#
set -euo pipefail

# ---------- 기본값 ----------
DEFAULT_DURATION=3600
DEFAULT_CAMERA="/dev/video0"
DEFAULT_RESOLUTION="1280x720"
DEFAULT_FPS=15

USER_NAME="${USER:-$(whoami)}"
DEFAULT_SSD_DIR="/media/${USER_NAME}/BUSTAGO_DATA/raw_videos"
DEFAULT_BACKUP_DIR="${HOME}/PC_BACKUP/raw_videos"

DEFAULT_STATION="INS01"

# ---------- 파라미터 ----------
DURATION="${DURATION:-$DEFAULT_DURATION}"
CAMERA="${CAMERA:-$DEFAULT_CAMERA}"
RESOLUTION="${RESOLUTION:-$DEFAULT_RESOLUTION}"
FPS="${FPS:-$DEFAULT_FPS}"
STATION="${STATION:-$DEFAULT_STATION}"
OUTPUT=""
DRY_RUN=0

usage() {
    cat <<EOF
BUSTAGO 시연일 영상 녹화

Usage:
  $(basename "$0") [options]

Options:
  --duration N       녹화 길이 초 (기본 ${DEFAULT_DURATION}=1시간)
  --camera DEV       카메라 디바이스 (기본 ${DEFAULT_CAMERA})
  --resolution WxH   해상도 (기본 ${DEFAULT_RESOLUTION})
  --fps N            프레임율 (기본 ${DEFAULT_FPS})
  --station ID       정류장 ID, 파일명에 들어감 (기본 ${DEFAULT_STATION})
  --output PATH      출력 mp4 경로 (기본 ${DEFAULT_SSD_DIR}/<날짜>_demo_<STATION>.mp4)
  --dry-run          실제 녹화 없이 명령만 출력
  --help             이 메시지

Examples:
  $(basename "$0") --duration 1800 --station INS01
  $(basename "$0") --camera /dev/video1 --resolution 1920x1080
  $(basename "$0") --dry-run

종료 시 동의 시간대를 <output>.meta.json에 기록하면 Phase 3 라벨링에 참고됨.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --duration)   DURATION="$2"; shift 2 ;;
        --camera)     CAMERA="$2"; shift 2 ;;
        --resolution) RESOLUTION="$2"; shift 2 ;;
        --fps)        FPS="$2"; shift 2 ;;
        --station)    STATION="$2"; shift 2 ;;
        --output)     OUTPUT="$2"; shift 2 ;;
        --dry-run)    DRY_RUN=1; shift ;;
        --help|-h)    usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

# 출력 경로 결정
TODAY="$(date +%Y-%m-%d)"
if [[ -z "$OUTPUT" ]]; then
    OUTPUT="${DEFAULT_SSD_DIR}/${TODAY}_demo_${STATION}.mp4"
fi
OUT_DIR="$(dirname "$OUTPUT")"
STEM="${OUTPUT%.mp4}"
META="${STEM}.meta.json"

# ---------- pre-flight 체크 ----------
preflight() {
    local fail=0

    if ! command -v ffmpeg >/dev/null 2>&1; then
        echo "[ERR] ffmpeg가 설치되지 않았습니다. apt install ffmpeg" >&2
        fail=1
    fi

    if [[ ! -e "$CAMERA" ]]; then
        echo "[ERR] 카메라 디바이스 없음: $CAMERA" >&2
        fail=1
    fi

    if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
        echo "[ERR] 출력 디렉토리 생성 실패: $OUT_DIR" >&2
        fail=1
    fi

    # 디스크 여유 확인 (최소 5GB)
    local avail_kb
    avail_kb=$(df -k "$OUT_DIR" 2>/dev/null | awk 'NR==2 {print $4}')
    if [[ -n "$avail_kb" && "$avail_kb" -lt $((5*1024*1024)) ]]; then
        echo "[WARN] 출력 디렉토리 여유 < 5GB ($((avail_kb/1024))MB). 계속 진행." >&2
    fi

    return $fail
}

# ---------- 메타 로그 작성 ----------
write_meta() {
    local exit_reason="$1"
    local started="$2"
    local ended="$3"

    cat > "$META" <<EOF
{
  "video": "$(basename "$OUTPUT")",
  "station_id": "${STATION}",
  "camera": "${CAMERA}",
  "resolution": "${RESOLUTION}",
  "fps": ${FPS},
  "duration_requested_sec": ${DURATION},
  "started_at": "${started}",
  "ended_at": "${ended}",
  "exit_reason": "${exit_reason}",
  "consent_windows": [
    {"start": "기입", "end": "기입", "note": "동의받은 시간대를 사람이 채움"}
  ],
  "operator": "${USER_NAME}",
  "notes": ""
}
EOF
    echo "[meta] $META 작성. 동의 시간대를 직접 편집하세요." >&2
}

# ---------- 종료 시 백업 ----------
finalize() {
    local reason="$1"
    local end_ts="$(date -Iseconds)"

    if [[ -f "$OUTPUT" ]]; then
        echo "[done] $OUTPUT ($(du -h "$OUTPUT" | cut -f1)) — reason: $reason" >&2
        write_meta "$reason" "$START_TS" "$end_ts"

        # 백업 시도 (실패해도 메인 영상은 남아 있음)
        if mkdir -p "$DEFAULT_BACKUP_DIR" 2>/dev/null; then
            if command -v rsync >/dev/null 2>&1; then
                echo "[backup] rsync → $DEFAULT_BACKUP_DIR/" >&2
                rsync -ah --progress "$OUTPUT" "$META" "$DEFAULT_BACKUP_DIR/" || \
                    echo "[WARN] 백업 rsync 실패. 수동으로 복사 필요." >&2
            else
                cp -v "$OUTPUT" "$META" "$DEFAULT_BACKUP_DIR/" 2>/dev/null || \
                    echo "[WARN] 백업 cp 실패." >&2
            fi
        fi
    else
        echo "[ERR] 출력 파일이 생성되지 않음: $OUTPUT" >&2
    fi
}

trap 'finalize "interrupted"; exit 0' INT TERM

# ---------- 실행 ----------
FFMPEG_CMD=(
    ffmpeg
    -hide_banner -loglevel info
    -f v4l2
    -framerate "$FPS"
    -video_size "$RESOLUTION"
    -i "$CAMERA"
    -t "$DURATION"
    -c:v libx264 -preset ultrafast -pix_fmt yuv420p
    -y
    "$OUTPUT"
)

if (( DRY_RUN )); then
    echo "[dry-run] 명령:"
    printf '  %q ' "${FFMPEG_CMD[@]}"; echo
    echo "[dry-run] 출력: $OUTPUT"
    echo "[dry-run] 메타: $META"
    echo "[dry-run] 백업 대상: $DEFAULT_BACKUP_DIR"
    exit 0
fi

if ! preflight; then
    echo "[ERR] pre-flight 실패. 위 항목 해결 후 재시도." >&2
    exit 1
fi

START_TS="$(date -Iseconds)"
echo "[start] $(basename "$OUTPUT") — ${DURATION}s @ ${RESOLUTION} ${FPS}fps from ${CAMERA}" >&2
echo "[start] Ctrl-C로 조기 종료 가능 (지금까지 녹화분은 보존됨)" >&2

if "${FFMPEG_CMD[@]}"; then
    finalize "completed"
else
    RC=$?
    finalize "ffmpeg-exit-${RC}"
    exit "$RC"
fi
