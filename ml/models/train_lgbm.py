"""
BUSTAGO - LightGBM 혼잡도 예측 모델 학습
Feature DataFrame(train_features.csv)으로 LightGBM 모델을 학습하고 RF와 성능을 비교한다.

회의 근거: RF 대비 학습 속도 15배 향상 및 오차 감소 효과 (2026-05-07 회의)

모델: LGBMClassifier(n_estimators=300, max_depth=6, learning_rate=0.05)
라벨: 0(여유), 1(보통), 2(혼잡), 3(매우혼잡)

Usage:
    python train_lgbm.py
    python train_lgbm.py --compare   # RF와 나란히 비교
"""

import argparse
import os
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import cross_val_score, train_test_split

try:
    from lightgbm import LGBMClassifier
except ImportError:
    raise ImportError("LightGBM 미설치. pip install lightgbm")

FEATURE_COLS = [
    "hour", "weekday",
    "weather", "temperature",
    "prev_boarding", "prev_alighting",
    "route_count",
]
LABEL_COL = "label"
LABEL_NAMES = {0: "여유", 1: "보통", 2: "혼잡", 3: "매우혼잡"}


def load_features(features_path: str) -> pd.DataFrame:
    if not os.path.exists(features_path):
        raise FileNotFoundError(f"Feature 파일 없음: {features_path}")
    df = pd.read_csv(features_path, encoding="utf-8-sig")
    print(f"[데이터] {len(df):,}건 로드")
    print(f"  라벨 분포:\n{df[LABEL_COL].value_counts().sort_index().to_string()}")
    return df


def train_lgbm(df: pd.DataFrame, test_size: float = 0.2):
    available = [c for c in FEATURE_COLS if c in df.columns]
    X = df[available].values
    y = df[LABEL_COL].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    print(f"\n[분할] Train: {len(X_train):,}건, Test: {len(X_test):,}건")

    t0 = time.time()
    model = LGBMClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbose=-1,
    )
    model.fit(X_train, y_train)
    elapsed = time.time() - t0
    print(f"[학습] LightGBM 완료 ({elapsed:.2f}s)")

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1_macro = f1_score(y_test, y_pred, average="macro", zero_division=0)
    f1_weighted = f1_score(y_test, y_pred, average="weighted", zero_division=0)

    print(f"\n[평가] Test Set:")
    print(f"  Accuracy:      {acc:.4f}")
    print(f"  F1 (macro):    {f1_macro:.4f}")
    print(f"  F1 (weighted): {f1_weighted:.4f}")

    target_names = [LABEL_NAMES.get(i, str(i)) for i in sorted(np.unique(y))]
    print(f"\n{classification_report(y_test, y_pred, target_names=target_names, zero_division=0)}")

    cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
    print(f"[교차검증] 5-Fold Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    importance = pd.Series(model.feature_importances_, index=available).sort_values(ascending=False)
    print(f"\n[Feature Importance]")
    for feat, imp in importance.items():
        print(f"  {feat:>20}: {imp:.0f}")

    metrics = {
        "accuracy": round(acc, 4),
        "f1_macro": round(f1_macro, 4),
        "f1_weighted": round(f1_weighted, 4),
        "cv_mean": round(cv_scores.mean(), 4),
        "cv_std": round(cv_scores.std(), 4),
        "train_time_sec": round(elapsed, 2),
        "feature_cols": available,
    }
    return model, metrics


def compare_with_rf(df: pd.DataFrame):
    """RF vs LightGBM 성능 비교표 출력."""
    from sklearn.ensemble import RandomForestClassifier

    available = [c for c in FEATURE_COLS if c in df.columns]
    X = df[available].values
    y = df[LABEL_COL].values
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # RF
    t0 = time.time()
    rf = RandomForestClassifier(n_estimators=10, max_depth=10, min_samples_leaf=5,
                                max_features="sqrt", random_state=42)
    rf.fit(X_train, y_train)
    rf_time = time.time() - t0
    rf_acc = accuracy_score(y_test, rf.predict(X_test))
    rf_f1 = f1_score(y_test, rf.predict(X_test), average="macro", zero_division=0)

    # LightGBM
    t0 = time.time()
    lgbm = LGBMClassifier(n_estimators=300, max_depth=6, learning_rate=0.05,
                          num_leaves=31, subsample=0.8, colsample_bytree=0.8,
                          random_state=42, verbose=-1)
    lgbm.fit(X_train, y_train)
    lgbm_time = time.time() - t0
    lgbm_acc = accuracy_score(y_test, lgbm.predict(X_test))
    lgbm_f1 = f1_score(y_test, lgbm.predict(X_test), average="macro", zero_division=0)

    print("\n" + "=" * 52)
    print(f"{'모델':<18} {'Accuracy':>10} {'F1(macro)':>10} {'학습시간':>10}")
    print("-" * 52)
    print(f"{'RandomForest':<18} {rf_acc:>10.4f} {rf_f1:>10.4f} {rf_time:>9.2f}s")
    print(f"{'LightGBM':<18} {lgbm_acc:>10.4f} {lgbm_f1:>10.4f} {lgbm_time:>9.2f}s")
    print("=" * 52)


def save_model(model, model_path: str):
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    size_kb = os.path.getsize(model_path) / 1024
    print(f"\n[저장] {model_path} ({size_kb:.0f} KB)")


def main():
    parser = argparse.ArgumentParser(description="BUSTAGO LightGBM 혼잡도 모델 학습")
    parser.add_argument("--compare", action="store_true", help="RF와 성능 비교 출력")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, "..", "..")
    features_path = os.path.join(project_root, "data", "features", "train_features.csv")
    model_path = os.path.join(script_dir, "lgbm_model.pkl")

    print("=" * 50)
    print("BUSTAGO LightGBM 모델 학습")
    print("=" * 50)

    df = load_features(features_path)

    if args.compare:
        print("\n[비교] RandomForest vs LightGBM")
        compare_with_rf(df)
        print()

    model, metrics = train_lgbm(df)
    save_model(model, model_path)

    print(f"\n{'='*50}")
    print(f"학습 완료")
    print(f"  Accuracy:   {metrics['accuracy']}")
    print(f"  F1 (macro): {metrics['f1_macro']}")
    print(f"  CV Mean:    {metrics['cv_mean']} (+/- {metrics['cv_std']})")
    print(f"  학습 시간:  {metrics['train_time_sec']}s")
    print(f"  모델 경로:  {os.path.abspath(model_path)}")
    print(f"{'='*50}")

    return model, metrics


if __name__ == "__main__":
    model, metrics = main()
