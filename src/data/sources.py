"""Catalogo das fontes de dados do projeto.

Todas as fontes sao publicas e baixadas sem credencial. As do Inep vem por HTTP
porque o servidor download.inep.gov.br publica uma cadeia de certificado
incompleta e a verificacao TLS falha em ambientes limpos; a integridade e
garantida pelo MD5 que o proprio Inep distribui dentro dos zips e, para os demais
arquivos, pelo SHA-256 registrado em data/manifest.json na primeira execucao.

A tabela abaixo resume o que cada fonte alimenta:

    indicador   resultados e metas do Indicador Crianca Alfabetizada (municipio e UF)
    microdados  avaliacao da alfabetizacao no grao de aluno (2024 e 2025)
    inse        nivel socioeconomico dos alunos por municipio (2023)
    censo       indicadores do Censo Escolar por municipio (formacao docente,
                alunos por turma, distorcao idade-serie, docentes com superior,
                rendimento)
    ideb        IDEB dos anos iniciais por municipio, serie 2005-2025
    ibge        populacao, area, densidade (Censo 2022) e PIB municipal (SIDRA)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

RAW_DIR = Path("data/raw")
EXTERNAL_DIR = Path("data/external")

INEP_ALFA = "http://download.inep.gov.br/avaliacao_da_alfabetizacao"
INEP_ALFABETIZA = "http://download.inep.gov.br/alfabetiza_brasil"
INEP_ABERTOS = "http://download.inep.gov.br/dados_abertos"
INEP_INDIC = "http://download.inep.gov.br/informacoes_estatisticas/indicadores_educacionais"
INEP_IDEB = "http://download.inep.gov.br/ideb/resultados"
SIDRA = "https://apisidra.ibge.gov.br/values"


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    dest: Path
    group: str
    year: int
    description: str
    kind: str = "file"  # file | zip | json


def _s(name, url, dest, group, year, description, kind="file") -> Source:
    return Source(name, url, Path(dest), group, year, description, kind)


SOURCES: tuple[Source, ...] = (
    # Indicador Crianca Alfabetizada: resultados e metas (formato largo, metas 2024-2030)
    _s("ica_municipios_2023", f"{INEP_ALFA}/resultados_e_metas_municipios.xlsx",
       RAW_DIR / "inep/ica_municipios_2023.xlsx", "indicador", 2023,
       "Resultado 2023 e metas por municipio (rede municipal)"),
    _s("ica_municipios_2024", f"{INEP_ALFABETIZA}/resultados_e_metas_municipios_2024.xlsx",
       RAW_DIR / "inep/ica_municipios_2024.xlsx", "indicador", 2024,
       "Resultados 2023 e 2024 e metas por municipio (rede municipal)"),
    _s("ica_municipios_2025", f"{INEP_ALFA}/resultados/resultados_e_metas_municipios_2025_3.xlsx",
       RAW_DIR / "inep/ica_municipios_2025.xlsx", "indicador", 2025,
       "Resultados 2023 a 2025 e metas por municipio (rede municipal)"),
    _s("ica_ufs_2023", f"{INEP_ALFA}/resultados_e_metas_ufs.xlsx",
       RAW_DIR / "inep/ica_ufs_2023.xlsx", "indicador", 2023,
       "Resultado 2023, Saeb 2019 e 2021 e metas por UF e Brasil"),
    _s("ica_ufs_2024", f"{INEP_ALFABETIZA}/resultados_e_metas_ufs_2024_2.xlsx",
       RAW_DIR / "inep/ica_ufs_2024.xlsx", "indicador", 2024,
       "Resultados 2023 e 2024 e metas por UF e Brasil"),
    _s("ica_ufs_2025", f"{INEP_ALFA}/resultados/resultados_e_metas_ufs_2025_v1.xlsx",
       RAW_DIR / "inep/ica_ufs_2025.xlsx", "indicador", 2025,
       "Resultados 2023 a 2025 e metas por UF e Brasil"),
    # Microdados no grao de aluno
    _s("microdados_2024", f"{INEP_ABERTOS}/microdados_avaliacao_da_alfabetizacao_2024.zip",
       RAW_DIR / "inep/microdados_2024.zip", "microdados", 2024,
       "Microdados da avaliacao da alfabetizacao 2024 (TS_ALUNO, TS_MUNICIPIO, TS_ESTADO)", "zip"),
    _s("microdados_2025", f"{INEP_ABERTOS}/microdados_AEEB_2025.zip",
       RAW_DIR / "inep/microdados_2025.zip", "microdados", 2025,
       "Microdados da avaliacao da alfabetizacao 2025", "zip"),
    # Nivel socioeconomico
    _s("inse_2023", f"{INEP_INDIC}/2023/nivel_socioeconomico/INSE_2023_municipios.xlsx",
       EXTERNAL_DIR / "inep/inse_2023_municipios.xlsx", "inse", 2023,
       "Indicador de Nivel Socioeconomico dos alunos por municipio, rede e localizacao"),
    # Indicadores do Censo Escolar por municipio
    *[
        _s(f"{code.lower()}_{year}", f"{INEP_INDIC}/{year}/{code}_{year}_MUNICIPIOS.zip",
           EXTERNAL_DIR / f"inep/{code.lower()}_{year}.zip", "censo", year, desc, "zip")
        for year in (2024, 2025)
        for code, desc in (
            ("AFD", "Adequacao da formacao docente por municipio"),
            ("ATU", "Media de alunos por turma por municipio"),
            ("TDI", "Taxa de distorcao idade-serie por municipio"),
            ("DSU", "Percentual de docentes com curso superior por municipio"),
        )
    ],
    *[
        _s(f"rend_{year}", f"{INEP_INDIC}/{year}/tx_rend_municipios_{year}.zip",
           EXTERNAL_DIR / f"inep/rend_{year}.zip", "censo", year,
           "Taxas de aprovacao, reprovacao e abandono por municipio", "zip")
        for year in (2023, 2024)
    ],
    # IDEB anos iniciais, serie historica
    _s("ideb_anos_iniciais", f"{INEP_IDEB}/divulgacao_anos_iniciais_municipios_2025.zip",
       EXTERNAL_DIR / "inep/ideb_anos_iniciais.zip", "ideb", 2025,
       "IDEB dos anos iniciais por municipio e rede, 2005 a 2025", "zip"),
    # IBGE via API SIDRA (n6 = todos os municipios)
    _s("ibge_censo_2022", f"{SIDRA}/t/4714/n6/all/v/93,6318,614/p/2022",
       EXTERNAL_DIR / "ibge/censo_2022.json", "ibge", 2022,
       "Populacao residente, area e densidade demografica (Censo 2022)", "json"),
    _s("ibge_pib", f"{SIDRA}/t/5938/n6/all/v/37,516,520,528,6574/p/2021",
       EXTERNAL_DIR / "ibge/pib_municipal.json", "ibge", 2021,
       "PIB e participacao dos setores no valor adicionado (2021, ultima edicao com o "
       "detalhamento setorial divulgado)", "json"),
)


def get_source(name: str) -> Source:
    for source in SOURCES:
        if source.name == name:
            return source
    raise KeyError(f"Fonte desconhecida: {name}")


def by_group(group: str) -> list[Source]:
    return [s for s in SOURCES if s.group == group]
