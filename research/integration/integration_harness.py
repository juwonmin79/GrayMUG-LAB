from __future__ import annotations

import os
import sys


if __package__ is None or __package__ == "":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.integration.simulator_payload import build_simulator_payload


def main() -> None:
    payload = build_simulator_payload(mode="BTC_ACCUMULATION", top_n=3)
    core = payload["core"]
    ward = payload["ward"]
    hound = payload["hound"]

    top_symbol = hound["tracked_symbols"][0] if hound["tracked_symbols"] else "NONE"
    top_rank = top_symbol.split("/")[0] if top_symbol != "NONE" else "NONE"

    print("====================================")
    print("GRAYMUG ENGINE HARNESS")
    print("MODE")
    print(core["mode"])
    print("CORE")
    print("BTC Focus" if core["btc_accumulation"] else core["mode"])
    print("WARD")
    print(ward["risk_level"])
    print("HOUND")
    for symbol in hound["tracked_symbols"]:
        print(symbol)
    print("LEAD LINE")
    print(f"Top Rank = {top_rank}")
    print("====================================")


if __name__ == "__main__":
    main()
