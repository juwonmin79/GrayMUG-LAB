from __future__ import annotations

import os
import sys
from typing import Dict


if __package__ is None or __package__ == "":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.calibration.signal_calibrator import calibrate_signals
from research.fitness.fitness_pipeline import run_fitness_pipeline
from research.targeting.target_pipeline import run_target_pipeline


def run_calibration_pipeline(
    mode: str = "BTC_ACCUMULATION",
    top_n: int = 3,
) -> Dict:
    target_payload = run_target_pipeline(mode=mode, top_n=top_n)
    fitness_report = run_fitness_pipeline(mode=mode, top_n=top_n)
    return calibrate_signals(target_payload, fitness_report)


def main() -> None:
    payload = run_calibration_pipeline(mode="BTC_ACCUMULATION", top_n=3)
    by_engine = {signal["engine"]: signal for signal in payload["signals"]}

    print("GRAYMUG LAB SIGNAL CALIBRATION")
    for engine in ["CORE", "WARD", "HOUND"]:
        signal = by_engine[engine]
        print(engine)
        print(f"signal_strength: {signal['signal_strength']:.2f}")
        print(f"confidence: {signal['confidence']:.2f}")
        print(f"max_influence: {signal['max_influence']:.2f}")
        print(f"final_weight: {signal['final_weight']:.2f}")


if __name__ == "__main__":
    main()
