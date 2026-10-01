"""Fase 1: carga, limpieza y evaluación de desviaciones del monitoreo."""

from datetime import date

import pandas as pd

COLUMNAS_BASE = [
    "FECHA", "CLASE DE CAMPO", "PROVEEDOR", "UNIDAD AGRICOLA", "CAMPO",
    "Suma de picados", "Larva",
]
COLUMNAS_POSTURAS = ["P.Heliothis", "P.Spodoptera", "P.Otros"]

# Indicador -> (columna en el dataframe, nombre que aparece en el motivo)
INDICADORES = {
    "LARVA": ("Larva", "LARVA"),
    "POSTURAS": ("Suma Posturas", "POSTURAS"),
    "PICADOS": ("Suma de picados", "PICADOS"),
}


def cargar_monitoreo(ruta, correcciones_proveedor=None) -> pd.DataFrame:
    """Lee el Excel de monitoreo, valida columnas y calcula 'Suma Posturas'."""
    df = pd.read_excel(ruta)

    faltantes = [c for c in COLUMNAS_BASE + COLUMNAS_POSTURAS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en el archivo de monitoreo: {faltantes}")

    df = df[COLUMNAS_BASE + COLUMNAS_POSTURAS].copy()

    if correcciones_proveedor:
        mapa = {k.upper().strip(): v for k, v in correcciones_proveedor.items()}
        df["PROVEEDOR"] = df["PROVEEDOR"].apply(lambda n: mapa.get(str(n).upper().strip(), n))

    df["Suma Posturas"] = df[COLUMNAS_POSTURAS].sum(axis=1)
    df["FECHA"] = pd.to_datetime(df["FECHA"], dayfirst=True).dt.date
    return df.drop(columns=COLUMNAS_POSTURAS)


def filtrar(df: pd.DataFrame, fecha: date, clase_campo: str = "TERCEROS") -> pd.DataFrame:
    """Filtra por fecha y clase de campo."""
    mask = (df["FECHA"] == fecha) & (
        df["CLASE DE CAMPO"].astype(str).str.upper().str.strip() == clase_campo
    )
    return df[mask].copy()


def _pct(valor: float, con_signo: bool = True) -> str:
    pct = round(valor * 100, 4)
    texto = str(int(pct)) if pct == int(pct) else f"{pct:.1f}"
    return f"{texto}%" if con_signo else texto


def evaluar_indicador(valor: float, cfg: dict, nombre: str):
    """Evalúa un valor contra su umbral (y banda opcional).

    - valor <= umbral                       -> sin desviación (None)
    - umbral < valor <= banda (si existe)   -> categoría de la banda
    - valor > banda o sin banda             -> categoría 6
    """
    if not cfg.get("activo", True):
        return None
    valor = round(float(valor), 3)
    umbral = cfg["umbral"]
    if valor <= umbral:
        return None

    banda = cfg.get("banda")
    if banda and valor <= banda["hasta"]:
        return {
            "categoria": banda["categoria"],
            "motivo": f"{nombre} {_pct(umbral, False)}-{_pct(banda['hasta'])}",
            "exceso": valor - umbral,
        }
    limite = banda["hasta"] if banda else umbral
    return {"categoria": 6, "motivo": f"{nombre} > {_pct(limite)}", "exceso": valor - umbral}


def evaluar_desviaciones(df: pd.DataFrame, cfg_indicadores: dict, inicio: date, fin: date) -> pd.DataFrame:
    """Devuelve una fila por registro desviado, con el indicador de mayor exceso."""
    filas = []
    for _, row in df.iterrows():
        candidatos = []
        for clave, (columna, nombre) in INDICADORES.items():
            r = evaluar_indicador(row[columna], cfg_indicadores[clave], nombre)
            if r:
                candidatos.append(r)
        if not candidatos:
            continue
        peor = max(candidatos, key=lambda d: d["exceso"])
        filas.append({
            "Proveedor": row["PROVEEDOR"],
            "Campo": row["CAMPO"],
            "Categoria": f"CAT{peor['categoria']}",
            "Motivo": peor["motivo"],
            "Inicio": inicio.strftime("%d/%m/%Y"),
            "Fin": fin.strftime("%d/%m/%Y"),
        })
    return pd.DataFrame(filas, columns=["Proveedor", "Campo", "Categoria", "Motivo", "Inicio", "Fin"])
