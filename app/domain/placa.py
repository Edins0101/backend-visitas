import re
from typing import Optional, Iterable


_PLACA_RE = re.compile(r"\b([A-Z0-9]{3})-?([A-Z0-9]{3,4})\b")


def extraer_placa(texto: str) -> Optional[str]:
    match = _PLACA_RE.search(_normalizar(texto))
    if not match:
        return None
    letras = _normalizar(match.group(1))
    numeros = _normalizar(match.group(2))
    letras = "".join(_DIGIT_TO_LETTER.get(ch, ch) for ch in letras)
    numeros = "".join(_LETTER_TO_DIGIT.get(ch, ch) for ch in numeros)
    if len(numeros) < 3:
        return None
    return f"{letras}-{numeros}"


def extraer_placa_en_lineas(lineas: Iterable[str]) -> Optional[str]:
    for linea in lineas:
        placa = extraer_placa(linea)
        if placa:
            return placa
    return None


def _normalizar(texto: str) -> str:
    return texto.upper().replace(" ", "")


_DIGIT_TO_LETTER = {
    "0": "O",
    "1": "I",
    "2": "Z",
    "5": "S",
    "6": "G",
    "8": "B",
    "9": "G",
}

_LETTER_TO_DIGIT = {
    "O": "0",
    "I": "1",
    "Z": "2",
    "S": "5",
    "B": "8",
    "G": "6",
    "T": "7",
}
