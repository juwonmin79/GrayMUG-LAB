FITNESS_REGISTRY = {
    "whale_link_flow": {
        "core": 0.0,
        "ward": 0.0,
        "hound": 0.0,
    }
}


def register_fitness_result(
    name: str,
    core_score: float,
    ward_score: float,
    hound_score: float,
) -> None:
    FITNESS_REGISTRY[name] = {
        "core": round(float(core_score), 4),
        "ward": round(float(ward_score), 4),
        "hound": round(float(hound_score), 4),
    }
