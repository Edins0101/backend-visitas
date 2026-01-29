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


def extraer_cedula_etiquetada(lineas: List[str]) -> Optional[str]:
    normalizadas = [_normalizar(linea) for linea in lineas]
    for linea in normalizadas:
        if "NUI" in linea or "DOCUMENTO" in linea or "DOC." in linea:
            cedula = extraer_cedula(linea)
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
        if "APELLIDOS" in linea or "NOMBRES" in linea:
            posible = _colectar_nombres(normalizadas, idx + 1)
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
