"""
BUSTAGO - Random Forest 혼잡도 예측 모델 학습
Feature DataFrame(train_features.csv)으로 모델을 학습하고 평가한다.

모델: RandomForestClassifier(n_estimators=100, max_depth=10, min_samples_leaf=5, max_features=sqrt)
- 2026-05-16 진단 §6 P1 반영: n_estimators 10 → 100 (일반 권장치)
라벨: 0(여유), 1(보통), 2(혼잡), 3(매우혼잡)

Usage:
    python train_rf.py
"""

import pandas as pd
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import classification_report, accuracy_score, f1_score

# Feature 컬럼 순서 (build_features.py 기준)
# 2026-05-16: weekday 제거 (진단 P0)
# 2026-05-17: weather/temperature 제거 (단순화 C — 외부 의존 제거)
FEATURE_COLS = [
    "hour",
    "prev_boarding", "prev_alighting",
    "route_count",
]

LABEL_COL = "label"

LABEL_NAMES = {0: "여유", 1: "보통", 2: "혼잡", 3: "매우혼잡"}


def load_features(features_path: str) -> pd.DataFrame:
    """학습용 Feature CSV를 로드한다."""
    if not os.path.exists(features_path):
        raise FileNotFoundError(f"Feature 파일 없음: {features_path}")

    df = pd.read_csv(features_path, encoding="utf-8-sig")
    print(f"[데이터] {len(df):,}건 로드")
    print(f"  컬럼: {list(df.columns)}")
    print(f"  라벨 분포:\n{df[LABEL_COL].value_counts().sort_index().to_string()}")
    return df


def train_model(df: pd.DataFrame, test_size: float = 0.2):
    """
    Random Forest 모델 학습 및 평가

    Returns:
        model: 학습된 RandomForestClassifier
        metrics: dict (accuracy, f1_macro, f1_weighted, cv_scores)
    """
    # Feature / Label 분리
    available_features = [c for c in FEATURE_COLS if c in df.columns]
    X = df[available_features].values
    y = df[LABEL_COL].values

    if len(X) < 100:
        print(f"[WARNING] 학습 데이터 부족: {len(X)}건 (최소 100건 권장)")

    # Train / Test 분할
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    print(f"\n[분할] Train: {len(X_train):,}건, Test: {len(X_test):,}건")

    # 모델 학습 (2026-05-16: n_estimators 10→100, 진단 P1)
    n_features = len(available_features)
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_leaf=5,
        max_features="sqrt",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    print(f"[학습] RandomForest(n_estimators=100, max_depth=10, min_samples_leaf=5, "
          f"max_features=sqrt, {n_features} features) 학습 완료")

    # 예측 및 평가
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1_macro = f1_score(y_test, y_pred, average="macro", zero_division=0)
    f1_weighted = f1_score(y_test, y_pred, average="weighted", zero_division=0)

    print(f"\n[평가] Test Set:")
    print(f"  Accuracy:    {acc:.4f}")
    print(f"  F1 (macro):  {f1_macro:.4f}")
    print(f"  F1 (weighted): {f1_weighted:.4f}")

    # Classification Report
    target_names = [LABEL_NAMES.get(i, str(i)) for i in sorted(np.unique(y))]
    print(f"\n{classification_report(y_test, y_pred, target_names=target_names, zero_division=0)}")

    # 교차검증 (5-fold)
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
    print(f"[교차검증] 5-Fold Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    print(f"  개별: {[f'{s:.4f}' for s in cv_scores]}")

    # Feature Importance
    importance = pd.Series(model.feature_importances_, index=available_features)
    importance = importance.sort_values(ascending=False)
    print(f"\n[Feature Importance]")
    for feat, imp in importance.items():
        print(f"  {feat:>20}: {imp:.4f}")

    metrics = {
        "accuracy": round(acc, 4),
        "f1_macro": round(f1_macro, 4),
        "f1_weighted": round(f1_weighted, 4),
        "cv_mean": round(cv_scores.mean(), 4),
        "cv_std": round(cv_scores.std(), 4),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "feature_cols": available_features,
    }

    return model, metrics


def save_model(model, model_path: str):
    """모델을 joblib으로 저장한다."""
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    size_mb = os.path.getsize(model_path) / (1024 * 1024)
    print(f"\n[저장] {model_path} ({size_mb:.1f} MB)")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, "..", "..")

    features_path = os.path.join(project_root, "data", "features", "train_features.csv")
    model_path = os.path.join(script_dir, "rf_model.pkl")

    print(f"{'='*50}")
    print(f"BUSTAGO Random Forest 모델 학습")
    print(f"{'='*50}\n")

    # 1. 데이터 로드
    df = load_features(features_path)

    # 2. 모델 학습 및 평가
    model, metrics = train_model(df)

    # 3. 모델 저장
    save_model(model, model_path)

    # 4. 결과 요약
    print(f"\n{'='*50}")
    print(f"학습 완료")
    print(f"  Accuracy: {metrics['accuracy']}")
    print(f"  F1 (macro): {metrics['f1_macro']}")
    print(f"  CV Mean Accuracy: {metrics['cv_mean']} (+/- {metrics['cv_std']})")
    print(f"  모델 경로: {os.path.abspath(model_path)}")
    print(f"{'='*50}")

    return model, metrics


if __name__ == "__main__":
    model, metrics = main()
