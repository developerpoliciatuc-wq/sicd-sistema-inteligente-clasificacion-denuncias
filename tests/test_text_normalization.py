from src.utils.text_normalization import normalize_text


def test_normalize_text_basic():
    assert normalize_text("  Comisaría 1° - Capital  ") == "cria 1 capital"


def test_normalize_text_subcria_variants():
    assert normalize_text("Sub. Cria. 2") == "sub cria 2"
    assert normalize_text("subcria 2") == "sub cria 2"
