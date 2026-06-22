from __future__ import annotations

import inspect
import os
import unittest

try:
    import production_interface
    from production_interface import (
        PRODUCTION_INTERFACE_VERSION,
        build_production_interface_response,
        enforce_non_trade_output,
        evaluate_case,
        evaluate_cases,
        evaluate_production_payload,
        validate_production_interface_input,
    )
    from test_accumulation_features import _bel_base_candles, _distribution_candles, _signals
except ImportError:
    from . import production_interface
    from .production_interface import (
        PRODUCTION_INTERFACE_VERSION,
        build_production_interface_response,
        enforce_non_trade_output,
        evaluate_case,
        evaluate_cases,
        evaluate_production_payload,
        validate_production_interface_input,
    )
    from .test_accumulation_features import _bel_base_candles, _distribution_candles, _signals


class ProductionInterfaceTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "true"

    def test_batch_processing_preserves_case_ids(self) -> None:
        results = evaluate_cases([_case("case-1", "BELUSDT"), _case("case-2", "ACTUSDT", act=True)])
        response = build_production_interface_response(results)

        self.assertEqual(response["interface_version"], PRODUCTION_INTERFACE_VERSION)
        self.assertEqual(response["mode"], "shadow")
        self.assertEqual([row["case_id"] for row in response["results"]], ["case-1", "case-2"])
        self.assertFalse(response["is_trade_command"])
        self.assertTrue(all(row["is_trade_command"] is False for row in response["results"]))

    def test_case_output_is_compatible_with_library_interface(self) -> None:
        result = evaluate_case(_case("case-1", "BELUSDT"))

        self.assertEqual(result["case_id"], "case-1")
        self.assertEqual(result["symbol"], "BELUSDT")
        self.assertEqual(result["entry_bias"], "neutral")
        self.assertIn(result["source_interface_version"], {"hellhound_library_interface_v1", None})
        self.assertFalse(result["is_trade_command"])

    def test_non_trade_output_is_forced_recursively(self) -> None:
        payload = {
            "is_trade_command": True,
            "entry_bias": "long",
            "nested": {"is_trade_command": True},
            "items": [{"is_trade_command": True}],
        }

        sanitized = enforce_non_trade_output(payload)

        self.assertFalse(sanitized["is_trade_command"])
        self.assertEqual(sanitized["entry_bias"], "neutral")
        self.assertFalse(sanitized["nested"]["is_trade_command"])
        self.assertFalse(sanitized["items"][0]["is_trade_command"])

    def test_malformed_case_returns_fail_safe_rejectable_result(self) -> None:
        result = evaluate_case({"case_id": "bad-case"})

        self.assertEqual(result["case_id"], "bad-case")
        self.assertEqual(result["promotion_status"], "WATCH")
        self.assertEqual(result["advisory"], "WATCH_NEUTRAL")
        self.assertFalse(result["is_trade_command"])
        self.assertIn("error", result)

    def test_empty_cases_are_valid_and_return_empty_results(self) -> None:
        payload = {
            "interface_version": PRODUCTION_INTERFACE_VERSION,
            "mode": "shadow",
            "cases": [],
        }

        validation = validate_production_interface_input(payload)
        response = evaluate_production_payload(payload)

        self.assertTrue(validation["valid"])
        self.assertEqual(response["results"], [])
        self.assertFalse(response["is_trade_command"])

    def test_bad_payload_rejects_with_non_trade_response(self) -> None:
        response = evaluate_production_payload({"mode": "live", "cases": "bad"})

        self.assertEqual(response["results"][0]["advisory"], "WATCH_NEUTRAL")
        self.assertFalse(response["is_trade_command"])
        self.assertFalse(response["results"][0]["is_trade_command"])

    def test_mixed_batch_keeps_valid_case_and_rejects_bad_case(self) -> None:
        payload = {
            "interface_version": PRODUCTION_INTERFACE_VERSION,
            "mode": "shadow",
            "cases": [_case("case-1", "BELUSDT"), {"case_id": "bad-case"}],
        }

        response = evaluate_production_payload(payload)

        self.assertEqual(len(response["results"]), 2)
        self.assertEqual(response["results"][0]["case_id"], "case-1")
        self.assertEqual(response["results"][0]["symbol"], "BELUSDT")
        self.assertEqual(response["results"][1]["case_id"], "bad-case")
        self.assertIn("error", response["results"][1])
        self.assertTrue(all(row["is_trade_command"] is False for row in response["results"]))

    def test_snapshot_candles_are_passed_to_existing_library_interface(self) -> None:
        case = _case("case-1", "BELUSDT")
        case["snapshot"] = {"candles_by_timeframe": _candles_by_timeframe()}

        result = evaluate_case(case)

        self.assertEqual(result["case_id"], "case-1")
        self.assertFalse(result["is_trade_command"])
        self.assertNotIn(
            "Pre-spike features are placeholders because no candle snapshot was provided.",
            result["reasons"],
        )

    def test_disabled_library_decision_returns_signal_based_advisory(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "false"
        result = evaluate_case(
            {
                "case_id": "case-fallback",
                "symbol": "BELUSDT",
                "decision_enabled": False,
                "signal": {
                    "symbol": "BELUSDT",
                    "price": 1.23,
                    "rsi": 58,
                    "volume_ratio": 2.8,
                    "rs_value": 1.08,
                    "rs_rising": True,
                    "fng": 55,
                    "passes_entry": True,
                    "is_whale": False,
                    "reasons": [],
                    "spike_type": "volume",
                    "volume_spike": True,
                    "taker_buy_ratio": 0.64,
                },
            }
        )

        self.assertEqual(result["structure_type"], "BEL")
        self.assertEqual(result["promotion_status"], "PROMOTE")
        self.assertEqual(result["advisory"], "WATCH_STRONG")
        self.assertGreater(result["hellhound_score"], 0.0)
        self.assertEqual(result["entry_bias"], "neutral")
        self.assertFalse(result["is_trade_command"])

    def test_production_interface_source_has_no_binance_or_db_mutation_endpoint(self) -> None:
        source = inspect.getsource(production_interface)

        self.assertNotIn("Binance", source)
        self.assertNotIn("create_order", source)
        self.assertNotIn(".delete(", source)
        self.assertNotIn(".update(", source)


def _case(case_id: str, symbol: str, *, act: bool = False) -> dict[str, object]:
    return {
        "case_id": case_id,
        "symbol": symbol,
        "signal": _signals(symbol, 1)[0],
        "snapshot": {"symbol": symbol, "source": "unit-test"},
        "shadow_signals": _signals(symbol, 40),
        "historical_candles": _distribution_candles() if act else _bel_base_candles(),
    }


def _candles_by_timeframe() -> dict[str, list[dict[str, float]]]:
    candles = []
    price = 1.0
    for index in range(24):
        price += 0.002
        candles.append(
            {
                "open": price,
                "high": price * 1.01,
                "low": price * 0.995,
                "close": price * 1.003,
                "volume": 1000 + index * 25,
                "btc_close": 50000 + index * 10,
            }
        )
    return {"15m": candles}


if __name__ == "__main__":
    unittest.main()
