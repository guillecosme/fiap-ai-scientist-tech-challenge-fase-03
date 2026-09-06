"""Estilo unico dos graficos e exportacao para images/.

Paleta sobria, uma cor de destaque para a classe de interesse (nao alfabetizado
ou municipio em risco) e um cinza para o restante. Todos os graficos dos
notebooks passam por `salvar`, que grava o PNG com o mesmo nome em images/.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns

IMAGES_DIR = Path("images")

AZUL = "#1f4e79"
LARANJA = "#d9822b"
CINZA = "#8c8c8c"
VERDE = "#3b7a57"
VERMELHO = "#b23a48"
PALETA = [AZUL, LARANJA, VERDE, VERMELHO, CINZA, "#6c5b7b"]

CORES_REGIAO = {
    "Norte": "#3b7a57",
    "Nordeste": "#d9822b",
    "Centro-Oeste": "#6c5b7b",
    "Sudeste": "#1f4e79",
    "Sul": "#8c8c8c",
}


def aplicar_estilo() -> None:
    sns.set_theme(style="whitegrid", context="notebook", palette=PALETA)
    mpl.rcParams.update(
        {
            "figure.figsize": (10, 5.5),
            "figure.dpi": 110,
            "savefig.dpi": 150,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "font.family": "DejaVu Sans",
        }
    )


def salvar(fig: plt.Figure, nome: str, images_dir: Path = IMAGES_DIR) -> Path:
    """Grava a figura em images/<nome>.png com layout ajustado."""
    images_dir.mkdir(parents=True, exist_ok=True)
    destino = images_dir / f"{nome}.png"
    fig.tight_layout()
    fig.savefig(destino, bbox_inches="tight")
    return destino


def fmt_pct(ax: plt.Axes, eixo: str = "x") -> None:
    """Formata o eixo como percentual inteiro."""
    formatter = mpl.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%")
    (ax.xaxis if eixo == "x" else ax.yaxis).set_major_formatter(formatter)
