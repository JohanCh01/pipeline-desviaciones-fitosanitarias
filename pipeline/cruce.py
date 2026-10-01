"""Fase 2: cruce de desviaciones con el reporte de recepción de materia prima.

El monitoreo registra el campo de forma general ('C1'), mientras que la
recepción lo trae desglosado ('CAMPO 01A', 'CAMPO 01B'). Este módulo
reconcilia ambas fuentes.
"""

from datetime import date

import pandas as pd

from .texto import coincide_flexible, estandarizar_campo, normalizar_texto, raiz_numerica


def cargar_recepcion(ruta, fecha: date) -> pd.DataFrame:
    """Lee la recepción, valida columnas y filtra por fecha de cosecha."""
    df = pd.read_excel(ruta)
    requeridas = {"Hora Cosecha", "Proveedor", "Campo"}
    if not requeridas.issubset(df.columns):
        raise ValueError(f"Faltan columnas en recepción: {requeridas - set(df.columns)}")

    df["Hora Cosecha"] = pd.to_datetime(df["Hora Cosecha"], errors="coerce", dayfirst=True)
    df["_fecha_cosecha"] = df["Hora Cosecha"].dt.date
    df = df[df["_fecha_cosecha"] == fecha].copy()
    df["Campo_std"] = df["Campo"].apply(estandarizar_campo)
    df["_proveedor_norm"] = df["Proveedor"].apply(normalizar_texto)
    return df


def _campos_de_proveedor(campos_por_proveedor: dict, proveedor_norm: str) -> set:
    if proveedor_norm in campos_por_proveedor:
        return set(campos_por_proveedor[proveedor_norm])
    encontrados = set()
    for clave, campos in campos_por_proveedor.items():
        if coincide_flexible(clave, proveedor_norm):
            encontrados.update(campos)
    return encontrados


def nombres_similares(proveedor_norm: str, candidatos, maximo: int = 3) -> list:
    """Nombres que comparten palabras: ayuda a detectar errores de tipeo entre sistemas."""
    objetivo = set(proveedor_norm.split())
    puntaje = [(len(objetivo & set(c.split())), c) for c in candidatos]
    puntaje = [p for p in puntaje if p[0] > 0]
    puntaje.sort(key=lambda x: (-x[0], x[1]))
    return [c for _, c in puntaje[:maximo]]


def cruzar_desagregado(df_desv: pd.DataFrame, df_recep: pd.DataFrame, log=print) -> pd.DataFrame:
    """Reemplaza campos genéricos por sus variantes reales cuando corresponde.

    - Si el campo exacto existe en recepción: se mantiene y se agregan sus variantes.
    - Si no existe pero hay variantes con la misma raíz: se reemplaza por ellas.
    - Si no hay coincidencias: la fila queda igual y se registra un aviso.
    """
    if df_desv.empty:
        return df_desv.copy()

    campos_por_proveedor = (
        df_recep.groupby("_proveedor_norm")["Campo_std"]
        .apply(lambda s: {x for x in s if x})
        .to_dict()
    )
    proveedores_recep = set(campos_por_proveedor)

    filas = []
    avisados = set()
    for _, fila in df_desv.iterrows():
        prov = normalizar_texto(fila["Proveedor"])
        campo = estandarizar_campo(fila["Campo"])
        campos_recep = _campos_de_proveedor(campos_por_proveedor, prov)

        if not campos_recep and prov not in avisados:
            avisados.add(prov)
            similares = nombres_similares(prov, proveedores_recep)
            if similares:
                log(f"[AVISO] '{fila['Proveedor']}' sin coincidencia; nombres parecidos: {similares}")
            else:
                log(f"[AVISO] '{fila['Proveedor']}' no aparece en recepción para esa fecha")

        variantes = sorted(
            c for c in campos_recep if c != campo and raiz_numerica(c) == raiz_numerica(campo)
        )
        exacto = campo in campos_recep

        campos_finales = ([campo] if exacto or not variantes else []) + (variantes if variantes else [])
        for c in campos_finales:
            nueva = fila.to_dict()
            nueva["Campo"] = c
            filas.append(nueva)

    return pd.DataFrame(filas, columns=df_desv.columns)


def agregar_fecha_y_unidad(df: pd.DataFrame, df_recep: pd.DataFrame) -> pd.DataFrame:
    """Agrega 'Fecha Cosecha' y 'Unidad Agricola' buscando por Proveedor + Campo."""
    if df is None or df.empty:
        return df
    df = df.copy()

    lookup = {}
    for _, r in df_recep.iterrows():
        clave = (r["_proveedor_norm"], r["Campo_std"])
        lookup.setdefault(clave, (r["_fecha_cosecha"], r.get("Unidad Agricola", "")))

    fechas, unidades = [], []
    for _, fila in df.iterrows():
        prov = normalizar_texto(fila["Proveedor"])
        campo = estandarizar_campo(fila["Campo"])
        dato = lookup.get((prov, campo))
        if dato is None:
            dato = next(
                (v for (p, c), v in lookup.items() if c == campo and coincide_flexible(p, prov)),
                None,
            )
        fechas.append(dato[0].strftime("%d/%m/%Y") if dato else "")
        unidades.append(dato[1] if dato else "")

    df.insert(0, "Unidad Agricola", unidades)
    df.insert(0, "Fecha Cosecha", fechas)
    return df
