from types import SimpleNamespace

from src.services import gemini_service


class _DummyModel:
    def __init__(self, *_args, **_kwargs):
        pass

    def generate_content(self, _prompt: str):
        return SimpleNamespace(text='OK {"fecha":"2025-12-15","comisaria_detectada":"Cria 1","tipo_delito":"ROBO"}')


def test_clasificar_denuncia_parses_json(monkeypatch):
    monkeypatch.setattr(gemini_service.genai, "GenerativeModel", _DummyModel)

    res = gemini_service.clasificar_denuncia("texto", model_name="dummy")

    assert res.denuncia is not None
    assert res.denuncia.fecha == "2025-12-15"
    assert res.denuncia.comisaria_detectada == "Cria 1"
    assert res.denuncia.tipo_delito == "ROBO"


class _DummyModelBad:
    def __init__(self, *_args, **_kwargs):
        pass

    def generate_content(self, _prompt: str):
        return SimpleNamespace(text="no-json")


def test_clasificar_denuncia_invalid_json_returns_none(monkeypatch):
    monkeypatch.setattr(gemini_service.genai, "GenerativeModel", _DummyModelBad)

    res = gemini_service.clasificar_denuncia("texto", model_name="dummy")

    assert res.denuncia is None
