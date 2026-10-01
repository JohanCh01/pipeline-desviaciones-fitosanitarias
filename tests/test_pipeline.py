from datetime import date

import pandas as pd
import pytest

from pipeline.categorizacion import filtrar_asignacion
from pipeline.cruce import cruzar_desagregado
from pipeline.evaluacion import evaluar_desviaciones, evaluar_indicador
from pipeline.texto import estandarizar_campo, normalizar_texto, raiz_numerica


# ---------- texto ----------
@pytest.mark.parametrize("entrada,esperado", [
    ("CAMPO 04A", "C4A"), ("CAMPO 05", "C5"), ("C05", "C5"), ("c12b", "C12B"),
])
def test_estandarizar_campo(entrada, esperado):
    assert estandarizar_campo(entrada) == esperado


def test_normalizar_texto_quita_tildes_y_enie():
    assert normalizar_texto(" Peña  Álvarez ") == "PENA ALVAREZ"


def test_raiz_numerica():
    assert raiz_numerica("C1A") == raiz_numerica("C01") == "1"


# ---------- evaluación ----------
CFG_POSTURAS = {"umbral": 0.02, "banda": {"hasta": 0.033, "categoria": 2}}


def test_sin_desviacion_si_no_supera_umbral():
    assert evaluar_indicador(0.02, CFG_POSTURAS, "POSTURAS") is None


def test_banda_asigna_su_categoria():
    r = evaluar_indicador(0.025, CFG_POSTURAS, "POSTURAS")
    assert r["categoria"] == 2 and r["motivo"] == "POSTURAS 2-3.3%"


def test_sobre_la_banda_es_categoria_6():
    r = evaluar_indicador(0.05, CFG_POSTURAS, "POSTURAS")
    assert r["categoria"] == 6 and r["motivo"] == "POSTURAS > 3.3%"


def test_elige_indicador_con_mayor_exceso():
    df = pd.DataFrame([{"PROVEEDOR": "X", "CAMPO": "C1", "Larva": 0.12,
                        "Suma Posturas": 0.0, "Suma de picados": 0.30}])
    cfg = {"LARVA": {"umbral": 0.1}, "POSTURAS": {"umbral": 0.02}, "PICADOS": {"umbral": 0.1}}
    res = evaluar_desviaciones(df, cfg, date(2026, 9, 15), date(2026, 9, 15))
    assert res.iloc[0]["Motivo"] == "PICADOS > 10%"


# ---------- cruce ----------
def _recepcion(filas):
    df = pd.DataFrame(filas, columns=["Proveedor", "Campo_std"])
    df["_proveedor_norm"] = df["Proveedor"].apply(normalizar_texto)
    return df


def test_campo_generico_se_reemplaza_por_variantes():
    desv = pd.DataFrame([{"Proveedor": "PEÑA", "Campo": "C1", "Categoria": "CAT6",
                          "Motivo": "m", "Inicio": "", "Fin": ""}])
    recep = _recepcion([("PENA", "C1A"), ("PENA", "C1B")])
    res = cruzar_desagregado(desv, recep, log=lambda *_: None)
    assert list(res["Campo"]) == ["C1A", "C1B"]


def test_campo_exacto_se_mantiene_y_suma_variantes():
    desv = pd.DataFrame([{"Proveedor": "A", "Campo": "C2", "Categoria": "CAT6",
                          "Motivo": "m", "Inicio": "", "Fin": ""}])
    recep = _recepcion([("A", "C2"), ("A", "C2B"), ("A", "C3")])
    res = cruzar_desagregado(desv, recep, log=lambda *_: None)
    assert list(res["Campo"]) == ["C2", "C2B"]


# ---------- categorización ----------
def test_vigencia_reciente_en_cat6_no_se_rescata_con_una_antigua():
    df = pd.DataFrame([
        {"Proveedor": "A", "Campo": "C1", "Categoria_Vigente": "CATEGORIA 4", "Inicio Vigencia": "01/08/2026"},
        {"Proveedor": "A", "Campo": "C1", "Categoria_Vigente": "CATEGORIA 6", "Inicio Vigencia": "01/09/2026"},
    ])
    assert filtrar_asignacion(df).empty
