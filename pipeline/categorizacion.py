"""Fase 3: validación contra el maestro de categorización vigente.

En el proceso original esta información se consultaba en un sistema web
interno. En esta versión pública se lee desde un CSV con la misma
estructura (proveedor, campo, categoría, vigencia).
"""

from datetime import date

import pandas as pd

from .texto import estandarizar_campo, normalizar_texto

CATEGORIAS_EXCLUIDAS = {"CATEGORIA 5", "CATEGORIA 6", "CATEGORIA 7"}


def cargar_maestro(ruta) -> pd.DataFrame:
    df = pd.read_csv(ruta).fillna({"Observaciones": ""})
    df["_prov"] = df["Proveedor"].apply(normalizar_texto)
    df["_campo"] = df["Campo"].apply(estandarizar_campo)
    df["Inicio Vigencia"] = pd.to_datetime(df["Inicio Vigencia"], dayfirst=True).dt.date
    df["Fin Vigencia"] = pd.to_datetime(df["Fin Vigencia"], dayfirst=True).dt.date
    return df


def validar_categorizacion(df_desv: pd.DataFrame, maestro: pd.DataFrame, fecha: date) -> pd.DataFrame:
    """Cruza cada Proveedor + Campo con las vigencias que cubren `fecha`.

    Se ignoran vigencias de un solo día. Si no hay vigencia válida, se
    distingue entre 'SIN CATEGORÍA' (el campo existe pero está vencido) y
    'SIN REGISTRO' (el campo nunca fue categorizado).
    """
    columnas = [
        "Fecha Cosecha", "Unidad Agricola", "Proveedor", "Campo", "Motivo",
        "Categoria_Desviacion", "Categoria_Vigente", "Inicio Vigencia",
        "Fin Vigencia", "Observaciones", "Inicio", "Fin",
    ]
    filas = []
    for _, d in df_desv.iterrows():
        prov, campo = normalizar_texto(d["Proveedor"]), estandarizar_campo(d["Campo"])
        registros = maestro[(maestro["_prov"] == prov) & (maestro["_campo"] == campo)]
        vigentes = registros[
            (registros["Inicio Vigencia"] != registros["Fin Vigencia"])
            & (registros["Inicio Vigencia"] <= fecha)
            & (registros["Fin Vigencia"] >= fecha)
        ]

        base = {
            "Fecha Cosecha": d.get("Fecha Cosecha", ""),
            "Unidad Agricola": d.get("Unidad Agricola", ""),
            "Proveedor": d["Proveedor"],
            "Campo": campo,
            "Motivo": d["Motivo"],
            "Categoria_Desviacion": d["Categoria"],
            "Inicio": d["Inicio"],
            "Fin": d["Fin"],
        }

        if vigentes.empty:
            obs = "SIN CATEGORÍA" if not registros.empty else "SIN REGISTRO"
            filas.append({**base, "Categoria_Vigente": "", "Inicio Vigencia": "",
                          "Fin Vigencia": "", "Observaciones": obs})
            continue

        for _, v in vigentes.iterrows():
            filas.append({
                **base,
                "Categoria_Vigente": v["Categoria"],
                "Inicio Vigencia": v["Inicio Vigencia"].strftime("%d/%m/%Y"),
                "Fin Vigencia": v["Fin Vigencia"].strftime("%d/%m/%Y"),
                "Observaciones": v.get("Observaciones", "") or "",
            })

    return pd.DataFrame(filas, columns=columnas)


def filtrar_asignacion(df_cat: pd.DataFrame) -> pd.DataFrame:
    """Se queda con la vigencia más reciente por Proveedor + Campo y luego
    excluye las que ya están en categorías 5, 6 o 7.

    El orden importa: si se excluyera primero, una vigencia antigua podría
    'rescatar' a un campo cuya vigencia actual ya es categoría 5/6.
    """
    if df_cat is None or df_cat.empty:
        return df_cat
    df = df_cat.copy()
    df["_inicio_dt"] = pd.to_datetime(df["Inicio Vigencia"], format="%d/%m/%Y", errors="coerce")
    df = (
        df.sort_values("_inicio_dt", ascending=False, na_position="last")
        .drop_duplicates(subset=["Proveedor", "Campo"], keep="first")
        .drop(columns="_inicio_dt")
    )
    excluir = df["Categoria_Vigente"].astype(str).str.upper().str.strip().isin(CATEGORIAS_EXCLUIDAS)
    return df[~excluir].sort_values("Proveedor", kind="stable").reset_index(drop=True)


def estado(categoria_vigente, observacion) -> str:
    cat = str(categoria_vigente).strip()
    if cat and cat.lower() != "nan":
        return "CATEGORIZADO"
    return "SIN CATEGORÍA" if str(observacion).strip().upper() == "SIN CATEGORÍA" else "SIN REGISTRO"


def construir_tabla_final(df_asig: pd.DataFrame) -> pd.DataFrame:
    """Tabla resumen lista para compartir."""
    return pd.DataFrame({
        "FECHA COSECHA": df_asig["Fecha Cosecha"].values,
        "UNIDAD AGRICOLA": df_asig["Unidad Agricola"].values,
        "PROVEEDOR": df_asig["Proveedor"].values,
        "CAMPO": df_asig["Campo"].values,
        "CATEGORÍA": df_asig["Categoria_Desviacion"].values,
        "MOTIVO": df_asig["Motivo"].values,
        "INICIO": df_asig["Inicio"].values,
        "FIN": df_asig["Fin"].values,
        "STATUS": [estado(c, o) for c, o in zip(df_asig["Categoria_Vigente"], df_asig["Observaciones"])],
    })
