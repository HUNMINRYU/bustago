"""Rule-based 혼잡도 추정 — ML 폴백 + MVP 검증용.

용도:
1. ML 모델 (`ml.models.predict.predict_congestion`) 호출 실패 시 폴백
2. 시연 비상 매트릭스 R3 (fine-tune이 baseline 이하) 시 즉시 전환 가능한 백업
3. 외부 실사 평가에서 "Acc 0.9993이 합성 라벨링 결과"라는 한계에 대한 *실용적 대안*
4. Principal Engineer 진단 (2026-05-17)의 MVP 단순화 권장 반영

설계 (광주대 통학 패턴 기반):
- 평일 출근 시간대 (7~9시):    매우혼잡 (3)
- 평일 하교 시간대 (17~18시):  매우혼잡 (3)
- 평일 점심 (12~13시):         혼잡 (2)
- 평일 그 외 낮 (10~16):       보통 (1)
- 평일 저녁 (19~21):           보통 (1)
- 평일 새벽/심야 (0~5, 22~23): 여유 (0)
- 주말 종일:                   1단계씩 낮춤

본 함수는 **ML 없이 동작 가능**해야 하며 sklearn/numpy 의존 0.
"""

from __future__ import annotations

LABEL_NAMES = {0: "여유", 1: "보통", 2: "혼잡", 3: "매우혼잡"}


def _peak_level(hour: int) -> int:
    """평일 기준 시간대별 혼잡도 (0~3)."""
    if 7 <= hour <= 9:
        return 3   # 출근·통학 피크
    if 17 <= hour <= 18:
        return 3   # 하교·퇴근 피크
    if 12 <= hour <= 13:
        return 2   # 점심
    if 10 <= hour <= 16:
        return 1   # 평일 낮
    if 19 <= hour <= 21:
        return 1   # 평일 저녁
    return 0       # 새벽 / 심야


def rule_based_predict(hour: int, weekday: int = 0) -> dict:
    """광주대 통학 패턴 rule-based 혼잡도 추정.

    Args:
        hour: 0~23
        weekday: 0=월 ~ 6=일

    Returns:
        ML predict_congestion()과 동일 스키마: {level, label, probabilities, source}
    """
    if not (0 <= hour <= 23):
        raise ValueError(f"hour must be 0-23, got {hour}")
    if not (0 <= weekday <= 6):
        raise ValueError(f"weekday must be 0-6, got {weekday}")

    base = _peak_level(hour)

    # 주말은 평일보다 1단계 낮춤 (광주대 등교 없음)
    if weekday >= 5:  # 5=토, 6=일
        base = max(0, base - 1)

    # 확률 분포: 결정된 level에 0.7, 인접 level에 0.15씩
    probs = [0.0, 0.0, 0.0, 0.0]
    probs[base] = 0.7
    if base > 0:
        probs[base - 1] = 0.15
    if base < 3:
        probs[base + 1] = 0.15
    # 정규화 (반올림 오차 보정)
    total = sum(probs)
    probs = [round(p / total, 4) for p in probs]

    return {
        "level": base,
        "label": LABEL_NAMES[base],
        "probabilities": probs,
        "source": "rule_based",
    }
