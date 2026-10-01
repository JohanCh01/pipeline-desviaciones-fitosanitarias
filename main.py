"""
Pipeline de detección de desviaciones fitosanitarias.

Uso:
    python main.py                       # usa los datos de ejemplo y la fecha de config.json
    python main.py --fecha 15/09/2026    # otra fecha
    python main.py --drive               # descarga el monitoreo desde Google Drive
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from pipeline.categorizacion import (
    cargar_maestro, construir_tabla_final, filtrar_asignacion, validar_categorizacion,
)
from pipeline.cruce import agregar_fecha_y_unidad, cargar_recepcion, cruzar_desagregado
from pipeline.evaluacion import cargar_monitoreo, evaluar_desviaciones, filtrar
from pipeline.reporte import guardar_reporte

BASE = Path(__file__).resolve().parent

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("pipeline").info


def _fecha(texto: str):
    return datetime.strptime(texto, "%d/%m/%Y").date()


def ejecutar(cfg: dict, fecha, usar_drive: bool = False) -> Path:
    rutas = {k: BASE / v for k, v in cfg["rutas"].items()}

    # ---------- Fase 1: monitoreo ----------
    if usar_drive:
        from pipeline.fuentes import descargar_de_drive
        rutas["monitoreo"] = descargar_de_drive(BASE / "descargas" / "monitoreo.xlsx", log=log)

    df = cargar_monitoreo(rutas["monitoreo"], cfg.get("correcciones_proveedor"))
    log(f"Monitoreo: {len(df)} filas leídas")

    df_dia = filtrar(df, fecha, cfg["clase_campo"])
    log(f"Filtro fecha {fecha:%d/%m/%Y} + clase '{cfg['clase_campo']}': {len(df_dia)} filas")

    inicio = fin = _fecha(cfg["vigencia"]["inicio"]) if cfg["vigencia"].get("inicio") else fecha
    if cfg["vigencia"].get("fin"):
        fin = _fecha(cfg["vigencia"]["fin"])

    df_desv = evaluar_desviaciones(df_dia, cfg["indicadores"], inicio, fin)
    log(f"Desviaciones detectadas: {len(df_desv)}")

    if df_desv.empty:
        log("Sin desviaciones para esta fecha. Fin del proceso.")
        return guardar_reporte(rutas["salida"], {"Desviaciones": df_desv})

    # ---------- Fase 2: cruce con recepción ----------
    df_recep = cargar_recepcion(rutas["recepcion"], fecha)
    log(f"Recepción del día: {len(df_recep)} filas")
    df_cruce = agregar_fecha_y_unidad(cruzar_desagregado(df_desv, df_recep, log=log), df_recep)
    log(f"Cruce desagregado: {len(df_desv)} -> {len(df_cruce)} filas")

    # ---------- Fase 3: categorización vigente ----------
    maestro = cargar_maestro(rutas["maestro_categorizacion"])
    df_cat = validar_categorizacion(df_cruce, maestro, fecha)
    df_asig = filtrar_asignacion(df_cat)
    tabla = construir_tabla_final(df_asig)
    log(f"Campos a categorizar: {len(tabla)}")

    pendientes = tabla[tabla["STATUS"] != "CATEGORIZADO"]
    for _, f in pendientes.iterrows():
        log(f"[REVISAR] {f['PROVEEDOR']} - {f['CAMPO']} ({f['STATUS']})")

    # ---------- Fase 4: reporte ----------
    ruta = guardar_reporte(rutas["salida"], {
        "Desviaciones": df_desv,
        "Recepcion_Cruce": df_cruce,
        "Categorizacion": df_cat,
        "Asignacion": df_asig,
        "Tabla_Final": tabla,
    })
    log(f"Reporte generado: {ruta}")
    return ruta


def main():
    parser = argparse.ArgumentParser(description="Detección de desviaciones fitosanitarias")
    parser.add_argument("--fecha", help="Fecha a evaluar (dd/mm/aaaa)")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--drive", action="store_true", help="Descargar monitoreo desde Google Drive")
    args = parser.parse_args()

    cfg = json.loads((BASE / args.config).read_text(encoding="utf-8"))
    fecha = _fecha(args.fecha or cfg["fecha"])
    ejecutar(cfg, fecha, usar_drive=args.drive)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        logging.exception(f"Error: {e}")
        sys.exit(1)
