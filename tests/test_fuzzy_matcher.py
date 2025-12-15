from src.services.comisarias_repo import ComisariaRef
from src.services.fuzzy_matcher import match_comisaria


def test_match_comisaria_finds_best_match():
    refs = [
        ComisariaRef(region="R1", nombre="Cria 1 Capital"),
        ComisariaRef(region="R2", nombre="Cria 2 Yerba Buena"),
    ]

    match = match_comisaria("Comisaría 1 - Capital", refs, threshold=60)

    assert match is not None
    assert match.region == "R1"
    assert match.comisaria == "Cria 1 Capital"
    assert match.score >= 60
