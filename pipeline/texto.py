"""Utilidades de normalización de texto y códigos de campo."""

import re
import unicodedata

import pandas as pd


def normalizar_texto(texto) -> str:
    """Mayúsculas, sin tildes, Ñ -> N y espacios colapsados.

    Permite comparar nombres que vienen escritos distinto entre sistemas
    (por ejemplo 'PEÑA ROJAS' y 'PENA  ROJAS').
    """
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return ""
    texto = str(texto).upper().strip().replace("Ñ", "N")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.split())


def estandarizar_campo(valor):
    """'CAMPO 04A' -> 'C4A' ; 'CAMPO 05' -> 'C5' ; 'C05' -> 'C5'."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    texto = str(valor).strip().upper()
    match = re.match(r"^(?:CAMPO\s*|C)0*(\d+)\s*([A-Z]*)$", texto)
    if match:
        numero, letras = match.groups()
        return f"C{numero}{letras}"
    return texto.replace(" ", "")


def raiz_numerica(campo_std):
    """'C1A' -> '1' ; 'C04' -> '4'. Agrupa variantes de un mismo campo."""
    if not campo_std:
        return campo_std
    match = re.match(r"^C0*(\d+)[A-Z]*$", str(campo_std).upper().strip())
    return match.group(1) if match else campo_std


def coincide_flexible(a: str, b: str) -> bool:
    """True si un nombre normalizado contiene al otro (palabras extra al final/inicio)."""
    if not a or not b:
        return False
    return a == b or a in b or b in a
