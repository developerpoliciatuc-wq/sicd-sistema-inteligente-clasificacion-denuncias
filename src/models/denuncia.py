from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List


# =============================================================================
# CONSTANTES - Franjas Horarias
# =============================================================================
FRANJAS_HORARIAS = {
    "MADRUGADA_(00:00-04:59)": (0, 4),
    "MANANA_(05:00-08:59)": (5, 8),
    "VESPERTINA_(09:00-12:59)": (9, 12),
    "SIESTA_(13:00-16:59)": (13, 16),
    "TARDE_(17:00-19:59)": (17, 19),
    "NOCHE_(20:00-23:59)": (20, 23),
}

NO_CONSTA = "NO CONSTA"


def calcular_franja_horaria(hora: Optional[str]) -> str:
    """
    Calcula la franja horaria a partir de una hora en formato HH:MM.
    Retorna '#NO_CONSTA' si la hora no está disponible o es inválida.
    """
    if not hora:
        return "#NO_CONSTA"
    
    try:
        # Parsear hora en formato HH:MM o HH:MM:SS
        partes = hora.strip().split(":")
        hora_int = int(partes[0])
        
        for franja, (inicio, fin) in FRANJAS_HORARIAS.items():
            if inicio <= hora_int <= fin:
                return franja
        
        return "#NO_CONSTA"
    except (ValueError, IndexError):
        return "#NO_CONSTA"


def derivar_mes_dia(fecha: Optional[str]) -> tuple[str, str]:
    """
    Deriva el mes y día de la semana a partir de una fecha AAAA-MM-DD.
    Retorna (mes, dia) o (NO_CONSTA, NO_CONSTA) si no es posible.
    """
    if not fecha:
        return NO_CONSTA, NO_CONSTA
    
    try:
        from datetime import datetime
        
        # Intentar parsear fecha
        dt = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                dt = datetime.strptime(fecha.strip(), fmt)
                break
            except ValueError:
                continue
        
        if not dt:
            return NO_CONSTA, NO_CONSTA
        
        meses = [
            "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
            "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
        ]
        dias = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO"]
        
        mes = meses[dt.month - 1]
        dia = dias[dt.weekday()]
        
        return mes, dia
    except Exception:
        return NO_CONSTA, NO_CONSTA


# =============================================================================
# DATACLASSES - Datos de ubicación
# =============================================================================
@dataclass(frozen=True)
class DireccionHecho:
    """Datos de ubicación extraídos del relato del hecho."""
    calle_principal: Optional[str] = None
    calle_secundaria: Optional[str] = None  # Para intersecciones
    numero: Optional[str] = None
    barrio: Optional[str] = None
    localidad: Optional[str] = None
    referencia: Optional[str] = None
    
    def to_query(self) -> str:
        """Construye una query para geocodificación."""
        parts = []
        if self.calle_principal:
            if self.numero:
                parts.append(f"{self.calle_principal} {self.numero}")
            elif self.calle_secundaria:
                parts.append(f"{self.calle_principal} y {self.calle_secundaria}")
            else:
                parts.append(self.calle_principal)
        if self.barrio:
            parts.append(self.barrio)
        if self.localidad:
            parts.append(self.localidad)
        else:
            parts.append("Tucumán")
        parts.append("Argentina")
        return ", ".join(parts)


@dataclass(frozen=True)
class Coordenadas:
    """Coordenadas geográficas del lugar del hecho."""
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    precision: Optional[str] = None  # "exacta", "aproximada", "barrio", "localidad"
    fuente: Optional[str] = None  # "nominatim", "manual", etc.


# =============================================================================
# DATACLASSES - Datos de personas
# =============================================================================
@dataclass(frozen=True)
class DatosPersona:
    """Datos de una persona involucrada (víctima, denunciante o causante)."""
    apellido_nombre: Optional[str] = None
    sexo: Optional[str] = None  # MASCULINO, FEMENINO, NO CONSTA
    edad: Optional[str] = None
    dni: Optional[str] = None
    direccion: Optional[str] = None
    # Campos adicionales para causante
    alias: Optional[str] = None
    descripcion: Optional[str] = None
    situacion: Optional[str] = None  # APREHENDIDO, PROFUGO, IDENTIFICADO, etc.


# =============================================================================
# DATACLASSES - Objetos involucrados
# =============================================================================
@dataclass(frozen=True)
class DatosVehiculo:
    """Datos de vehículos utilizados en el hecho."""
    tipo: Optional[str] = None  # MOTO, AUTO, BICICLETA, etc.
    descripcion: Optional[str] = None


@dataclass(frozen=True)
class DatosArma:
    """Datos de armas utilizadas en el hecho."""
    tipo: Optional[str] = None  # ARMA DE FUEGO, ARMA BLANCA, etc.
    detalle: Optional[str] = None


@dataclass(frozen=True)
class ElementoSustraido:
    """Datos del elemento sustraído."""
    tipo: Optional[str] = None  # CELULAR, DINERO, CARTERA, etc.
    detalle: Optional[str] = None


# =============================================================================
# DATACLASS PRINCIPAL - Denuncia Clasificada
# =============================================================================
@dataclass(frozen=True)
class DenunciaClasificada:
    """Modelo completo de una denuncia clasificada por IA."""
    
    # --- Campos de identificación ---
    fecha: Optional[str] = None
    numero_sumario: Optional[str] = None  # Nº de imagen/sumario/fecha memorandum
    
    # --- Campos institucionales ---
    comisaria_detectada: Optional[str] = None
    jurisdiccion: Optional[str] = None
    
    # --- Clasificación del delito ---
    tipo_delito: Optional[str] = None
    modalidad_delito: Optional[str] = None
    
    # --- Temporalidad ---
    hora: Optional[str] = None  # Formato HH:MM
    franja_horaria: Optional[str] = None  # Calculado automáticamente
    mes: Optional[str] = None  # Derivado de fecha
    dia_semana: Optional[str] = None  # Derivado de fecha
    
    # --- Ubicación del hecho ---
    lugar: Optional[str] = None  # VIA PUBLICA, DOMICILIO, COMERCIO, etc.
    detalle_lugar: Optional[str] = None
    
    # --- Reseña ---
    breve_resena: Optional[str] = None  # Máximo 254 caracteres
    
    # --- Datos de personas ---
    victima: Optional[DatosPersona] = None
    denunciante: Optional[DatosPersona] = None
    vinculo_denunciante_victima: Optional[str] = None
    causante: Optional[DatosPersona] = None
    
    # --- Objetos involucrados ---
    vehiculo: Optional[DatosVehiculo] = None
    arma: Optional[DatosArma] = None
    elemento_sustraido: Optional[ElementoSustraido] = None
    
    # --- Campos de procesamiento interno ---
    region_asignada: Optional[str] = None
    comisaria_asignada: Optional[str] = None
    score_match: Optional[float] = None
    motivo_revision: Optional[str] = None
    requiere_revision_manual: bool = False
    
    # --- Campos de georreferenciación ---
    direccion_hecho: Optional[DireccionHecho] = None
    coordenadas: Optional[Coordenadas] = None
