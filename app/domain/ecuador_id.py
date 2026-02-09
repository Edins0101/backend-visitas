import re
import unicodedata
from typing import Optional, List, Tuple


def validar_cedula(cedula: str) -> bool:
    if len(cedula) != 10 or not cedula.isdigit():
        return False

    provincia = int(cedula[0:2])
    if provincia < 1 or provincia > 24:
        return False

    tercer = int(cedula[2])
    if tercer < 0 or tercer > 5:
        return False

    total = 0
    for idx in range(9):
        digito = int(cedula[idx])
        if idx % 2 == 0:
            digito *= 2
            if digito > 9:
                digito -= 9
        total += digito

    verificador = (10 - (total % 10)) % 10
    return verificador == int(cedula[9])


def extraer_cedula(texto: str) -> Optional[str]:
    digits = _solo_digitos(texto)
    if len(digits) < 10:
        return None

    for i in range(len(digits) - 9):
        candidato = digits[i : i + 10]
        if validar_cedula(candidato):
            return candidato
    return None


def extraer_cedula_patron(texto: str) -> Optional[str]:
    # Prefer patterns with a visible separator (e.g., 095155304-9)
    for match in re.finditer(r"(\d{9})\D{1,3}(\d)", texto):
        candidato = match.group(1) + match.group(2)
        if validar_cedula(candidato):
            return candidato
    # Fallback to contiguous 10 digits in the raw text
    for match in re.finditer(r"(\d{10})", texto):
        candidato = match.group(1)
        if validar_cedula(candidato):
            return candidato
    return None


def extraer_cedula_etiquetada(lineas: List[str]) -> Optional[str]:
    normalizadas = [_normalizar(linea) for linea in lineas]
    for idx, linea in enumerate(normalizadas):
        if _linea_tiene_etiqueta(linea):
            cedula = extraer_cedula(linea)
            if cedula:
                return cedula
            for siguiente in normalizadas[idx + 1 : idx + 3]:
                cedula = extraer_cedula(siguiente)
                if cedula:
                    return cedula
    return None


def extraer_nombres(lineas: List[str]) -> Optional[str]:
    normalizadas = [_normalizar(linea) for linea in lineas]
    for idx, linea in enumerate(normalizadas):
        if "APELLIDOS" in linea and "NOMBRES" in linea:
            nombre_en_linea = _extraer_despues_marcador(linea, "APELLIDOS Y NOMBRES")
            if nombre_en_linea:
                return _limpiar_nombres(nombre_en_linea)
            return _limpiar_nombres(_colectar_nombres(normalizadas, idx + 1))
        if "APELLIDOS" in linea:
            apellidos = _colectar_hasta(normalizadas, idx + 1, {"NOMBRES"})
            nombres = None
            for j in range(idx + 1, min(len(normalizadas), idx + 6)):
                if "NOMBRES" in normalizadas[j]:
                    nombres = _colectar_hasta(normalizadas, j + 1, _PALABRAS_CORTE)
                    break
            combinado = " ".join([p for p in [apellidos, nombres] if p])
            if combinado:
                return _limpiar_nombres(combinado)
        if "NOMBRES" in linea:
            posible = _colectar_hasta(normalizadas, idx + 1, _PALABRAS_CORTE)
            if posible:
                return _limpiar_nombres(posible)
    return None


def _colectar_nombres(normalizadas: List[str], start: int) -> Optional[str]:
    nombres = []
    for linea in normalizadas[start : start + 3]:
        if _es_linea_nombre(linea):
            nombres.append(linea.strip())
        elif nombres:
            break
    if nombres:
        return " ".join(nombres)
    return None


def _colectar_hasta(normalizadas: List[str], start: int, cortes: set[str]) -> Optional[str]:
    nombres = []
    for linea in normalizadas[start:]:
        if any(palabra in linea for palabra in cortes):
            break
        if _es_linea_nombre(linea):
            nombres.append(linea.strip())
        elif nombres:
            break
    if nombres:
        return " ".join(nombres)
    return None


def _es_linea_nombre(linea: str) -> bool:
    if not linea or len(linea.strip()) < 3:
        return False
    if any(palabra in linea for palabra in _PALABRAS_CORTE):
        return False
    letras = sum(1 for ch in linea if ch.isalpha() or ch == " ")
    return letras / max(len(linea), 1) >= 0.6


def _extraer_despues_marcador(linea: str, marcador: str) -> Optional[str]:
    if marcador in linea:
        extra = linea.split(marcador, 1)[1].strip()
        return extra or None
    return None


def _solo_digitos(texto: str) -> str:
    return "".join(ch for ch in texto if ch.isdigit())


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
    return texto.upper()


def _linea_tiene_etiqueta(linea: str) -> bool:
    if not linea:
        return False
    tokens = []
    token = []
    for ch in linea:
        if ch.isalnum():
            token.append(ch)
        else:
            if token:
                tokens.append("".join(token))
                token = []
    if token:
        tokens.append("".join(token))
    etiquetas = {"NUI", "DOCUMENTO", "DOC", "NO", "NRO", "NUM", "NUMERO"}
    return any(t in etiquetas for t in tokens)


_PALABRAS_CORTE = {
    "CEDULA",
    "CIUDADANIA",
    "REPUBLICA",
    "ECUADOR",
    "NACIONALIDAD",
    "SEXO",
    "ESTADO",
    "CIVIL",
    "LUGAR",
    "NACIMIENTO",
    "FECHA",
    "DOCUMENTO",
    "NUI",
    "FIRMA",
    "CONDICION",
}


def _limpiar_nombres(texto: Optional[str]) -> Optional[str]:
    if not texto:
        return None
    tokens = [t for t in texto.split() if t not in _PALABRAS_NOMBRES]
    if not tokens:
        return None
    return " ".join(tokens).strip()


_PALABRAS_NOMBRES = {
    "APELLIDOS",
    "NOMBRES",
    "Y",
}
