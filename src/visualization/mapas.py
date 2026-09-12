"""Mapa coropletico dos municipios sem dependencias geoespaciais.

A malha vem da API de malhas do IBGE (GeoJSON, qualidade minima, 3,6 MB) e e
desenhada com matplotlib a partir das coordenadas dos poligonos. Basta para um
mapa tematico de leitura executiva; nao substitui uma biblioteca geoespacial
para analise espacial.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize

MALHA = Path("data/external/ibge/malha_municipios.json")


def carregar_malha(path: Path = MALHA) -> dict[int, list[np.ndarray]]:
    """id_municipio -> lista de aneis exteriores (um por poligono)."""
    dados = json.loads(Path(path).read_text(encoding="utf-8"))
    malha: dict[int, list[np.ndarray]] = {}
    for f in dados["features"]:
        codigo = int(f["properties"]["codarea"])
        geom = f["geometry"]
        partes = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        malha[codigo] = [np.asarray(p[0]) for p in partes]
    return malha


def mapa_municipios(
    valores: dict[int, float],
    malha: dict[int, list[np.ndarray]],
    ax: plt.Axes | None = None,
    cmap: str = "RdYlGn_r",
    vmin: float | None = None,
    vmax: float | None = None,
    titulo: str = "",
    rotulo_barra: str = "",
    cor_sem_dado: str = "#e6e6e6",
) -> plt.Axes:
    """Pinta cada municipio pelo valor em `valores`; sem valor fica cinza."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))
    poligonos, cores_valores, sem_dado = [], [], []
    for codigo, aneis in malha.items():
        v = valores.get(codigo)
        for anel in aneis:
            if v is None or (isinstance(v, float) and np.isnan(v)):
                sem_dado.append(anel)
            else:
                poligonos.append(anel)
                cores_valores.append(v)
    if sem_dado:
        ax.add_collection(PolyCollection(sem_dado, facecolors=cor_sem_dado, edgecolors="none"))
    if poligonos:
        arr = np.asarray(cores_valores, dtype=float)
        norm = Normalize(
            vmin=vmin if vmin is not None else np.nanmin(arr),
            vmax=vmax if vmax is not None else np.nanmax(arr),
        )
        col = PolyCollection(poligonos, array=arr, cmap=cmap, norm=norm, edgecolors="none")
        ax.add_collection(col)
        barra = plt.colorbar(col, ax=ax, shrink=0.6, pad=0.01)
        barra.set_label(rotulo_barra)
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_axis_off()
    if titulo:
        ax.set_title(titulo)
    return ax
