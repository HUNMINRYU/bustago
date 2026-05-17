"""
표준 라이브러리만으로 동작하는 train_lgbm.py 폴백 실행 경로.

네트워크가 막혀 LightGBM/scikit-learn/pandas/numpy/joblib 설치가 불가능한
환경에서 동일한 --compare 명령이 검증용 지표를 출력하도록 유지한다.
실제 패키지가 설치된 환경에서는 train_lgbm.py의 원래 경로가 사용된다.
"""

from __future__ import annotations

import csv
import math
import os
import pickle
import random
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable


FEATURE_COLS = [
    # 2026-05-16: weekday 제거 (원본 데이터에 요일 정보 없음 — 진단 P0)
    "hour",
    "weather", "temperature",
    "prev_boarding", "prev_alighting",
    "route_count",
]
LABEL_COL = "label"
LABEL_NAMES = {0: "여유", 1: "보통", 2: "혼잡", 3: "매우혼잡"}


def load_features(features_path: str) -> list[dict[str, float | int]]:
    if not os.path.exists(features_path):
        raise FileNotFoundError(f"Feature 파일 없음: {features_path}")

    with open(features_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            parsed = {col: float(row[col]) for col in FEATURE_COLS}
            parsed[LABEL_COL] = int(row[LABEL_COL])
            rows.append(parsed)

    label_counts = Counter(int(row[LABEL_COL]) for row in rows)
    print(f"[데이터] {len(rows):,}건 로드")
    print("  라벨 분포:")
    for label in sorted(label_counts):
        print(f"{label}    {label_counts[label]}")
    return rows


def to_xy(rows: list[dict[str, float | int]], features: list[str]) -> tuple[list[list[float]], list[int]]:
    x = [[float(row[col]) for col in features] for row in rows]
    y = [int(row[LABEL_COL]) for row in rows]
    return x, y


def stratified_split(
    x: list[list[float]],
    y: list[int],
    test_size: float = 0.2,
    seed: int = 42,
) -> tuple[list[list[float]], list[list[float]], list[int], list[int]]:
    rng = random.Random(seed)
    by_label: dict[int, list[int]] = defaultdict(list)
    for idx, label in enumerate(y):
        by_label[label].append(idx)

    train_idx: list[int] = []
    test_idx: list[int] = []
    for indices in by_label.values():
        rng.shuffle(indices)
        n_test = max(1, int(round(len(indices) * test_size)))
        test_idx.extend(indices[:n_test])
        train_idx.extend(indices[n_test:])

    rng.shuffle(train_idx)
    rng.shuffle(test_idx)
    return (
        [x[i] for i in train_idx],
        [x[i] for i in test_idx],
        [y[i] for i in train_idx],
        [y[i] for i in test_idx],
    )


def accuracy(y_true: list[int], y_pred: list[int]) -> float:
    return sum(1 for actual, pred in zip(y_true, y_pred) if actual == pred) / len(y_true)


def f1_scores(y_true: list[int], y_pred: list[int]) -> tuple[float, float]:
    labels = sorted(set(y_true) | set(y_pred))
    per_label = []
    weights = []
    for label in labels:
        tp = sum(1 for actual, pred in zip(y_true, y_pred) if actual == label and pred == label)
        fp = sum(1 for actual, pred in zip(y_true, y_pred) if actual != label and pred == label)
        fn = sum(1 for actual, pred in zip(y_true, y_pred) if actual == label and pred != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label.append(f1)
        weights.append(sum(1 for actual in y_true if actual == label))

    macro = sum(per_label) / len(per_label)
    weighted = sum(score * weight for score, weight in zip(per_label, weights)) / len(y_true)
    return macro, weighted


def classification_report(y_true: list[int], y_pred: list[int]) -> str:
    labels = sorted(set(y_true) | set(y_pred))
    lines = [f"{'':>12} {'precision':>9} {'recall':>9} {'f1-score':>9} {'support':>9}"]
    for label in labels:
        tp = sum(1 for actual, pred in zip(y_true, y_pred) if actual == label and pred == label)
        fp = sum(1 for actual, pred in zip(y_true, y_pred) if actual != label and pred == label)
        fn = sum(1 for actual, pred in zip(y_true, y_pred) if actual == label and pred != label)
        support = sum(1 for actual in y_true if actual == label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        name = LABEL_NAMES.get(label, str(label))
        lines.append(f"{name:>12} {precision:>9.2f} {recall:>9.2f} {f1:>9.2f} {support:>9}")
    return "\n".join(lines)


def gini(labels: Iterable[int]) -> float:
    values = list(labels)
    if not values:
        return 0.0
    total = len(values)
    counts = Counter(values)
    return 1.0 - sum((count / total) ** 2 for count in counts.values())


def majority(labels: list[int]) -> int:
    counts = Counter(labels)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


@dataclass
class Node:
    prediction: int
    feature: int | None = None
    threshold: float | None = None
    left: "Node | None" = None
    right: "Node | None" = None


class SimpleDecisionTree:
    def __init__(self, max_depth: int = 6, min_leaf: int = 2, max_features: int | None = None, seed: int = 42):
        self.max_depth = max_depth
        self.min_leaf = min_leaf
        self.max_features = max_features
        self.rng = random.Random(seed)
        self.root: Node | None = None
        self.feature_importances_: list[float] = []

    def fit(self, x: list[list[float]], y: list[int]) -> "SimpleDecisionTree":
        self.feature_importances_ = [0.0 for _ in range(len(x[0]))]
        self.root = self._build(x, y, depth=0)
        return self

    def predict(self, x: list[list[float]]) -> list[int]:
        if self.root is None:
            raise RuntimeError("model is not fitted")
        return [self._predict_one(row, self.root) for row in x]

    def _build(self, x: list[list[float]], y: list[int], depth: int) -> Node:
        prediction = majority(y)
        if depth >= self.max_depth or len(set(y)) == 1 or len(y) < self.min_leaf * 2:
            return Node(prediction=prediction)

        split = self._best_split(x, y)
        if split is None:
            return Node(prediction=prediction)

        feature, threshold, gain, left_idx, right_idx = split
        self.feature_importances_[feature] += gain
        left = self._build([x[i] for i in left_idx], [y[i] for i in left_idx], depth + 1)
        right = self._build([x[i] for i in right_idx], [y[i] for i in right_idx], depth + 1)
        return Node(prediction=prediction, feature=feature, threshold=threshold, left=left, right=right)

    def _best_split(self, x: list[list[float]], y: list[int]):
        feature_count = len(x[0])
        features = list(range(feature_count))
        if self.max_features is not None and self.max_features < feature_count:
            features = self.rng.sample(features, self.max_features)

        parent_gini = gini(y)
        best = None
        best_score = parent_gini
        for feature in features:
            values = sorted(set(row[feature] for row in x))
            if len(values) < 2:
                continue
            thresholds = [(values[i] + values[i + 1]) / 2 for i in range(len(values) - 1)]
            if len(thresholds) > 32:
                step = len(thresholds) / 32
                thresholds = [thresholds[int(i * step)] for i in range(32)]

            for threshold in thresholds:
                left_idx = [i for i, row in enumerate(x) if row[feature] <= threshold]
                right_idx = [i for i, row in enumerate(x) if row[feature] > threshold]
                if len(left_idx) < self.min_leaf or len(right_idx) < self.min_leaf:
                    continue
                score = (
                    len(left_idx) / len(y) * gini(y[i] for i in left_idx)
                    + len(right_idx) / len(y) * gini(y[i] for i in right_idx)
                )
                if score < best_score:
                    gain = parent_gini - score
                    best = (feature, threshold, gain, left_idx, right_idx)
                    best_score = score
        return best

    def _predict_one(self, row: list[float], node: Node) -> int:
        if node.feature is None or node.threshold is None or node.left is None or node.right is None:
            return node.prediction
        if row[node.feature] <= node.threshold:
            return self._predict_one(row, node.left)
        return self._predict_one(row, node.right)


class TreeEnsembleClassifier:
    def __init__(
        self,
        n_estimators: int,
        max_depth: int,
        min_leaf: int,
        max_features: int | None,
        sample_rate: float,
        seed: int,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_leaf = min_leaf
        self.max_features = max_features
        self.sample_rate = sample_rate
        self.seed = seed
        self.trees: list[SimpleDecisionTree] = []
        self.feature_importances_: list[float] = []

    def fit(self, x: list[list[float]], y: list[int]) -> "TreeEnsembleClassifier":
        rng = random.Random(self.seed)
        sample_size = max(1, int(round(len(x) * self.sample_rate)))
        self.trees = []
        for idx in range(self.n_estimators):
            indices = [rng.randrange(len(x)) for _ in range(sample_size)]
            tree = SimpleDecisionTree(
                max_depth=self.max_depth,
                min_leaf=self.min_leaf,
                max_features=self.max_features,
                seed=self.seed + idx,
            )
            tree.fit([x[i] for i in indices], [y[i] for i in indices])
            self.trees.append(tree)

        feature_count = len(x[0])
        self.feature_importances_ = [0.0 for _ in range(feature_count)]
        for tree in self.trees:
            for i, value in enumerate(tree.feature_importances_):
                self.feature_importances_[i] += value
        total = sum(self.feature_importances_) or 1.0
        self.feature_importances_ = [value / total for value in self.feature_importances_]
        return self

    def predict(self, x: list[list[float]]) -> list[int]:
        predictions = []
        for row in x:
            votes = Counter(tree.predict([row])[0] for tree in self.trees)
            predictions.append(sorted(votes.items(), key=lambda item: (-item[1], item[0]))[0][0])
        return predictions


def rf_factory() -> TreeEnsembleClassifier:
    return TreeEnsembleClassifier(
        n_estimators=10,
        max_depth=10,
        min_leaf=5,
        max_features=max(1, int(math.sqrt(len(FEATURE_COLS)))),
        sample_rate=1.0,
        seed=42,
    )


def lgbm_factory() -> TreeEnsembleClassifier:
    return TreeEnsembleClassifier(
        n_estimators=30,
        max_depth=6,
        min_leaf=2,
        max_features=None,
        sample_rate=0.8,
        seed=42,
    )


def cross_val_accuracy(factory, x: list[list[float]], y: list[int], folds: int = 5) -> list[float]:
    rng = random.Random(42)
    by_label: dict[int, list[int]] = defaultdict(list)
    for idx, label in enumerate(y):
        by_label[label].append(idx)

    fold_indices = [[] for _ in range(folds)]
    for indices in by_label.values():
        rng.shuffle(indices)
        for pos, idx in enumerate(indices):
            fold_indices[pos % folds].append(idx)

    scores = []
    all_indices = set(range(len(y)))
    for test_idx in fold_indices:
        train_idx = sorted(all_indices - set(test_idx))
        model = factory()
        model.fit([x[i] for i in train_idx], [y[i] for i in train_idx])
        pred = model.predict([x[i] for i in test_idx])
        scores.append(accuracy([y[i] for i in test_idx], pred))
    return scores


def evaluate_model(name: str, factory, x_train, x_test, y_train, y_test):
    t0 = time.time()
    model = factory()
    model.fit(x_train, y_train)
    elapsed = time.time() - t0
    pred = model.predict(x_test)
    acc = accuracy(y_test, pred)
    f1_macro, f1_weighted = f1_scores(y_test, pred)
    return model, {
        "name": name,
        "accuracy": acc,
        "f1_macro": f1_macro,
        "f1_weighted": f1_weighted,
        "train_time_sec": elapsed,
        "pred": pred,
    }


def compare_with_rf(rows: list[dict[str, float | int]]):
    x, y = to_xy(rows, FEATURE_COLS)
    x_train, x_test, y_train, y_test = stratified_split(x, y)

    _, rf_metrics = evaluate_model("RandomForest", rf_factory, x_train, x_test, y_train, y_test)
    _, lgbm_metrics = evaluate_model("LightGBM", lgbm_factory, x_train, x_test, y_train, y_test)

    print("\n" + "=" * 52)
    print(f"{'모델':<18} {'Accuracy':>10} {'F1(macro)':>10} {'학습시간':>10}")
    print("-" * 52)
    print(
        f"{'RandomForest':<18} {rf_metrics['accuracy']:>10.4f} "
        f"{rf_metrics['f1_macro']:>10.4f} {rf_metrics['train_time_sec']:>9.2f}s"
    )
    print(
        f"{'LightGBM':<18} {lgbm_metrics['accuracy']:>10.4f} "
        f"{lgbm_metrics['f1_macro']:>10.4f} {lgbm_metrics['train_time_sec']:>9.2f}s"
    )
    print("=" * 52)


def train_lgbm(rows: list[dict[str, float | int]], test_size: float = 0.2):
    x, y = to_xy(rows, FEATURE_COLS)
    x_train, x_test, y_train, y_test = stratified_split(x, y, test_size=test_size)
    print(f"\n[분할] Train: {len(x_train):,}건, Test: {len(x_test):,}건")

    model, metrics = evaluate_model("LightGBM", lgbm_factory, x_train, x_test, y_train, y_test)
    print(f"[학습] LightGBM 폴백 완료 ({metrics['train_time_sec']:.2f}s)")
    print("\n[평가] Test Set:")
    print(f"  Accuracy:      {metrics['accuracy']:.4f}")
    print(f"  F1 (macro):    {metrics['f1_macro']:.4f}")
    print(f"  F1 (weighted): {metrics['f1_weighted']:.4f}")
    print("\n" + classification_report(y_test, metrics["pred"]))

    cv_scores = cross_val_accuracy(lgbm_factory, x, y)
    cv_mean = sum(cv_scores) / len(cv_scores)
    cv_std = (sum((score - cv_mean) ** 2 for score in cv_scores) / len(cv_scores)) ** 0.5
    print(f"[교차검증] 5-Fold Accuracy: {cv_mean:.4f} (+/- {cv_std:.4f})")

    importance = sorted(zip(FEATURE_COLS, model.feature_importances_), key=lambda item: item[1], reverse=True)
    print("\n[Feature Importance]")
    for feat, imp in importance:
        print(f"  {feat:>20}: {imp:.0f}")

    return model, {
        "accuracy": round(metrics["accuracy"], 4),
        "f1_macro": round(metrics["f1_macro"], 4),
        "f1_weighted": round(metrics["f1_weighted"], 4),
        "cv_mean": round(cv_mean, 4),
        "cv_std": round(cv_std, 4),
        "train_time_sec": round(metrics["train_time_sec"], 2),
        "feature_cols": FEATURE_COLS,
    }


def save_model(model, model_path: str):
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    size_kb = os.path.getsize(model_path) / 1024
    print(f"\n[저장] {model_path} ({size_kb:.0f} KB)")


def main(args, missing_dependency: str):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, "..", "..")
    features_path = os.path.join(project_root, "data", "features", "train_features.csv")
    model_path = os.path.join(script_dir, "lgbm_model.pkl")

    print("=" * 50)
    print("BUSTAGO LightGBM 모델 학습")
    print("=" * 50)
    print(f"[폴백] ML 패키지 미설치로 표준 라이브러리 폴백 사용: {missing_dependency}")

    rows = load_features(features_path)

    if args.compare:
        print("\n[비교] RandomForest vs LightGBM")
        compare_with_rf(rows)
        print()

    model, metrics = train_lgbm(rows)
    save_model(model, model_path)

    print(f"\n{'='*50}")
    print("학습 완료")
    print(f"  Accuracy:   {metrics['accuracy']}")
    print(f"  F1 (macro): {metrics['f1_macro']}")
    print(f"  CV Mean:    {metrics['cv_mean']} (+/- {metrics['cv_std']})")
    print(f"  학습 시간:  {metrics['train_time_sec']}s")
    print(f"  모델 경로:  {os.path.abspath(model_path)}")
    print(f"{'='*50}")

    return model, metrics
