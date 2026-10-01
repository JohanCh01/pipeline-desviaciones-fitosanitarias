"""
Genera datos ficticios con la misma estructura que las fuentes reales.
Todos los nombres de proveedores y valores son inventados.

Uso: python datos/generar_datos_ejemplo.py
"""

import random
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

random.seed(42)
CARPETA = Path(__file__).resolve().parent
FECHA = date(2026, 9, 15)

PROVEEDORES = {
    # nombre en monitoreo: (unidad agrícola, campos en monitoreo, campos reales en recepción)
    "AGRICOLA LOS ALAMOS": ("UA NORTE", ["C1", "C2"], ["CAMPO 01A", "CAMPO 01B", "CAMPO 02"]),
    "FUNDO SANTA ROSA EIRL": ("UA NORTE", ["C3"], ["CAMPO 03"]),
    "PEÑA VARGAS JORGE LUIS": ("UA SUR", ["C1", "C4"], ["CAMPO 01", "CAMPO 04A"]),
    "INVERSIONES EL MIRADOR SAC": ("UA SUR", ["C2"], ["CAMPO 02", "CAMPO 02B"]),
    "QUISPE HUAMAN ROSA ELENA": ("UA CENTRO", ["C5"], ["CAMPO 05"]),
    "AGROPECUARIA VALLE VERDE": ("UA CENTRO", ["C1"], ["CAMPO 01"]),
    "RAMIREZ TORRES CARLOS": ("UA NORTE", ["C6"], []),  # no cosechó ese día
}

# Valores forzados para que el ejemplo muestre todos los casos
FORZADOS = {
    ("AGRICOLA LOS ALAMOS", "C1"): {"Larva": 0.15},
    ("PEÑA VARGAS JORGE LUIS", "C4"): {"P.Heliothis": 0.015, "P.Spodoptera": 0.01},  # banda -> CAT2
    ("INVERSIONES EL MIRADOR SAC", "C2"): {"Suma de picados": 0.18},
    ("QUISPE HUAMAN ROSA ELENA", "C5"): {"P.Heliothis": 0.03, "P.Otros": 0.02},
    ("RAMIREZ TORRES CARLOS", "C6"): {"Larva": 0.12},
}


def generar_monitoreo():
    filas = []
    for dia in range(3):
        f = FECHA - timedelta(days=dia)
        for prov, (ua, campos, _) in PROVEEDORES.items():
            for c in campos:
                fila = {
                    "FECHA": f, "CLASE DE CAMPO": "TERCEROS", "PROVEEDOR": prov,
                    "UNIDAD AGRICOLA": ua, "CAMPO": c,
                    "Suma de picados": round(random.uniform(0, 0.06), 3),
                    "Larva": round(random.uniform(0, 0.05), 3),
                    "P.Heliothis": round(random.uniform(0, 0.005), 3),
                    "P.Spodoptera": round(random.uniform(0, 0.005), 3),
                    "P.Otros": round(random.uniform(0, 0.003), 3),
                }
                if f == FECHA:
                    fila.update(FORZADOS.get((prov, c), {}))
                filas.append(fila)
        filas.append({  # campo propio: debe quedar fuera por el filtro
            "FECHA": f, "CLASE DE CAMPO": "PROPIO", "PROVEEDOR": "FUNDO PROPIO",
            "UNIDAD AGRICOLA": "UA NORTE", "CAMPO": "C9", "Suma de picados": 0.5,
            "Larva": 0.5, "P.Heliothis": 0, "P.Spodoptera": 0, "P.Otros": 0,
        })
    pd.DataFrame(filas).to_excel(CARPETA / "monitoreo_ejemplo.xlsx", index=False)


def generar_recepcion():
    filas = []
    nombres_recepcion = {
        "AGRICOLA LOS ALAMOS": "AGRÍCOLA LOS ÁLAMOS SAC",  # escrito distinto en el otro sistema
        "PEÑA VARGAS JORGE LUIS": "PENA VARGAS JORGE LUIS",  # sin Ñ
    }
    for prov, (ua, _, campos_recep) in PROVEEDORES.items():
        for c in campos_recep:
            for _ in range(random.randint(1, 3)):
                hora = datetime.combine(FECHA, datetime.min.time()) + timedelta(hours=random.randint(5, 14))
                filas.append({
                    "Hora Cosecha": hora.strftime("%d/%m/%Y %H:%M"),
                    "Proveedor": nombres_recepcion.get(prov, prov),
                    "Campo": c, "Unidad Agricola": ua,
                    "Kg Recibidos": random.randint(300, 2500),
                })
    pd.DataFrame(filas).to_excel(CARPETA / "recepcion_ejemplo.xlsx", index=False)


def generar_maestro():
    filas = [
        ("AGRÍCOLA LOS ÁLAMOS SAC", "CAMPO 01A", "CATEGORIA 3", "01/09/2026", "30/09/2026", ""),
        ("AGRÍCOLA LOS ÁLAMOS SAC", "CAMPO 01B", "CATEGORIA 3", "01/09/2026", "30/09/2026", ""),
        ("AGRÍCOLA LOS ÁLAMOS SAC", "CAMPO 02", "CATEGORIA 2", "01/08/2026", "31/08/2026", "Vencida"),
        ("PEÑA VARGAS JORGE LUIS", "CAMPO 04A", "CATEGORIA 2", "01/09/2026", "30/09/2026", ""),
        ("INVERSIONES EL MIRADOR SAC", "CAMPO 02", "CATEGORIA 4", "01/09/2026", "30/09/2026", ""),
        ("INVERSIONES EL MIRADOR SAC", "CAMPO 02B", "CATEGORIA 6", "10/09/2026", "30/09/2026", "Ya en categoría 6"),
        ("QUISPE HUAMAN ROSA ELENA", "CAMPO 05", "CATEGORIA 1", "01/09/2026", "30/09/2026", ""),
        ("QUISPE HUAMAN ROSA ELENA", "CAMPO 05", "CATEGORIA 1", "15/09/2026", "15/09/2026", "Rango de un día"),
    ]
    pd.DataFrame(filas, columns=[
        "Proveedor", "Campo", "Categoria", "Inicio Vigencia", "Fin Vigencia", "Observaciones",
    ]).to_csv(CARPETA / "maestro_categorizacion_ejemplo.csv", index=False)


if __name__ == "__main__":
    generar_monitoreo()
    generar_recepcion()
    generar_maestro()
    print(f"Datos de ejemplo generados en {CARPETA}")
