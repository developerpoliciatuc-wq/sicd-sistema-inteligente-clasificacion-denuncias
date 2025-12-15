from types import SimpleNamespace

from src.services import gemini_service


class _DummyModel:
    def __init__(self, *_args, **_kwargs):
        pass

    def generate_content(self, _prompt: str):
        return SimpleNamespace(text='OK {"fecha":"2025-12-15","comisaria_detectada":"Cria 1","tipo_delito":"ROBO","modalidad_delito":"ROBO_ARREBATO"}')


def test_clasificar_denuncia_parses_json(monkeypatch):
    monkeypatch.setattr(gemini_service.genai, "GenerativeModel", _DummyModel)

    res = gemini_service.clasificar_denuncia("texto", model_name="dummy")

    assert res.denuncia is not None
    assert res.denuncia.fecha == "2025-12-15"
    assert res.denuncia.comisaria_detectada == "Cria 1"
    assert res.denuncia.tipo_delito == "ROBO"
    assert res.denuncia.modalidad_delito == "ROBO_ARREBATO"


class _DummyModelBad:
    def __init__(self, *_args, **_kwargs):
        pass

    def generate_content(self, _prompt: str):
        return SimpleNamespace(text="no-json")


def test_clasificar_denuncia_invalid_json_returns_none(monkeypatch):
    monkeypatch.setattr(gemini_service.genai, "GenerativeModel", _DummyModelBad)

    res = gemini_service.clasificar_denuncia("texto", model_name="dummy")

    assert res.denuncia is None


def test_load_modalidades_returns_valid_structure():
    """Verifica que las modalidades se cargan correctamente desde el JSON."""
    # Limpiar cache
    gemini_service._MODALIDADES_CACHE = None
    
    data = gemini_service._load_modalidades()
    
    assert "tipos_delito" in data
    assert "modalidades" in data
    assert "HURTO" in data["tipos_delito"]
    assert "ROBO" in data["tipos_delito"]
    assert "ESTAFA" in data["tipos_delito"]
    assert "PORTACION_ARMA_FUEGO" in data["tipos_delito"]
    
    # Verificar algunas modalidades específicas
    assert "HURTO_PUNGA" in data["modalidades"]["HURTO"]
    assert "ROBO_ARREBATO" in data["modalidades"]["ROBO"]
    assert "ESTAFA_TELEFONICA" in data["modalidades"]["ESTAFA"]


def test_build_prompt_modalidades_contains_definitions():
    """Verifica que el prompt incluye las definiciones de modalidades."""
    # Limpiar cache
    gemini_service._MODALIDADES_CACHE = None
    
    prompt_text = gemini_service._build_prompt_modalidades()
    
    assert "HURTO" in prompt_text
    assert "ROBO" in prompt_text
    assert "ESTAFA" in prompt_text
    assert "HURTO_PUNGA" in prompt_text
    assert "vía pública" in prompt_text.lower() or "via publica" in prompt_text.lower()

