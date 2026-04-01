"""
BUSTAGO - 통합 데이터 수집 파이프라인
3개 수집기(boarding, weather, congestion) + Feature 구축 실행

Usage:
    python pipeline.py              # 전체 파이프라인
    python pipeline.py --step weather  # 특정 단계만 실행
"""

import asyncio
import os
import sys
import argparse
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..", "..")
sys.path.insert(0, project_root)

from ml.data_collection.collect_boarding import main as collect_boarding
from ml.data_collection.collect_weather import main as collect_weather
from ml.data_collection.collect_congestion import main as collect_congestion
from ml.preprocessing.build_features import main as build_features


STEP_META = {
    "boarding": {
        "index": 1,
        "title": "승하차 데이터 수집",
        "error": "승하차 수집 실패",
        "func": collect_boarding,
    },
    "weather": {
        "index": 2,
        "title": "기상 데이터 수집",
        "error": "기상 수집 실패",
        "func": collect_weather,
    },
    "congestion": {
        "index": 3,
        "title": "차내혼잡도 수집",
        "error": "혼잡도 수집 실패",
        "func": collect_congestion,
    },
    "features": {
        "index": 4,
        "title": "Feature DataFrame 구축",
        "error": "Feature 구축 실패",
        "func": build_features,
    },
}


def _print_step_header(step_name):
    meta = STEP_META[step_name]
    print(f"\n{'='*50}")
    print(f"[Step {meta['index']}/4] {meta['title']}")
    print(f"{'='*50}")


async def _run_collector(step_name):
    _print_step_header(step_name)
    return await asyncio.to_thread(STEP_META[step_name]["func"])


def _record_step_result(results, step_name, result):
    if isinstance(result, Exception):
        print(f"  [ERROR] {STEP_META[step_name]['error']}: {result}")
        results[step_name] = 0
        return

    results[step_name] = len(result) if result is not None else 0
    print(f"  결과: {results[step_name]:,}건")


async def _run_pipeline_async(steps=None):
    """
    전체 파이프라인 실행

    steps: None이면 전체 실행, ['boarding', 'weather', 'congestion', 'features'] 중 선택
    """
    all_steps = ["boarding", "weather", "congestion", "features"]
    if steps is None:
        steps = all_steps

    start_time = datetime.now()
    print(f"{'='*60}")
    print(f"BUSTAGO 데이터 파이프라인 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"실행 단계: {', '.join(steps)}")
    print(f"{'='*60}\n")

    results = {}

    collector_steps = [step for step in ["boarding", "weather", "congestion"] if step in steps]
    if collector_steps:
        collector_results = await asyncio.gather(
            *[_run_collector(step) for step in collector_steps],
            return_exceptions=True,
        )
        for step_name, result in zip(collector_steps, collector_results):
            _record_step_result(results, step_name, result)

    # Step 4: Feature DataFrame 구축
    if "features" in steps:
        _print_step_header("features")
        try:
            df_features = await asyncio.to_thread(build_features)
            _record_step_result(results, "features", df_features)
        except Exception as e:
            _record_step_result(results, "features", e)

    # 요약
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    print(f"\n{'='*60}")
    print(f"파이프라인 완료: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"소요 시간: {elapsed:.1f}초")
    print(f"\n수집 결과 요약:")
    for step, count in results.items():
        status = "OK" if count > 0 else "EMPTY"
        print(f"  {step:>12}: {count:>8,}건  [{status}]")
    print(f"{'='*60}")

    return results


def run_pipeline(steps=None):
    return asyncio.run(_run_pipeline_async(steps=steps))


def main():
    parser = argparse.ArgumentParser(description="BUSTAGO 데이터 수집 파이프라인")
    parser.add_argument(
        "--step",
        choices=["boarding", "weather", "congestion", "features"],
        help="특정 단계만 실행",
    )
    args = parser.parse_args()

    if args.step:
        return run_pipeline(steps=[args.step])
    else:
        return run_pipeline()


if __name__ == "__main__":
    main()
