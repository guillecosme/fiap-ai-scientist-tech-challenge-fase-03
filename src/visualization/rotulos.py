"""Rotulos de negocio para as variaveis do projeto.

Os graficos e as tabelas de interpretabilidade usam estes nomes no lugar dos
identificadores tecnicos, para que um gestor entenda o que cada variavel mede
sem consultar o dicionario de dados.
"""

from __future__ import annotations

ROTULOS: dict[str, str] = {
    # alvo e historico do indicador
    "alfabetizado": "Aluno alfabetizado",
    "indicador_t": "% alfabetizados no ano",
    "atingiu_meta_t": "Atingiu a meta do ano",
    "gap_meta_t": "Distancia para a meta (p.p.)",
    "indicador_t1": "% alfabetizados no ano anterior",
    "indicador_t2": "% alfabetizados dois anos antes",
    "nivel_t1": "Nivel de alfabetizacao no ano anterior (0 a 5)",
    "participacao_t1": "Participacao na prova no ano anterior (%)",
    "variacao_t1": "Variacao do indicador no ano anterior (p.p.)",
    "meta_t1": "Meta do ano anterior (%)",
    "gap_meta_t1": "Distancia para a meta no ano anterior (p.p.)",
    "meta_t": "Meta do ano (%)",
    "salto_necessario": "Salto necessario para a meta (p.p.)",
    # censo escolar
    "afd_ai_grupo1_pct": "Docentes com formacao adequada, anos iniciais (%)",
    "afd_ai_grupo5_pct": "Docentes sem licenciatura, anos iniciais (%)",
    "afd_inf_grupo1_pct": "Docentes com formacao adequada, educacao infantil (%)",
    "alunos_por_turma_ai": "Alunos por turma, anos iniciais",
    "alunos_por_turma_2ano": "Alunos por turma no 2o ano",
    "alunos_por_turma_pre": "Alunos por turma na pre-escola",
    "distorcao_ai_pct": "Distorcao idade-serie, anos iniciais (%)",
    "distorcao_2ano_pct": "Distorcao idade-serie no 2o ano (%)",
    "docentes_superior_ai_pct": "Docentes com curso superior, anos iniciais (%)",
    "docentes_superior_inf_pct": "Docentes com curso superior, educacao infantil (%)",
    "aprovacao_ai_pct": "Taxa de aprovacao, anos iniciais (%)",
    "aprovacao_1ano_pct": "Taxa de aprovacao no 1o ano (%)",
    "aprovacao_2ano_pct": "Taxa de aprovacao no 2o ano (%)",
    "reprovacao_ai_pct": "Taxa de reprovacao, anos iniciais (%)",
    "abandono_ai_pct": "Taxa de abandono, anos iniciais (%)",
    # ideb
    "ideb_ultimo": "IDEB anos iniciais (ultima edicao)",
    "ideb_nota_lp_ultimo": "Nota de portugues no Saeb 5o ano (ultima edicao)",
    "ideb_rendimento_ultimo": "Indicador de rendimento do IDEB (ultima edicao)",
    "ideb_anterior": "IDEB anos iniciais (edicao anterior)",
    "ideb_variacao": "Variacao do IDEB entre edicoes",
    "ideb_tendencia": "Tendencia do IDEB (pontos por edicao)",
    # territorio e renda
    "populacao": "Populacao (Censo 2022)",
    "log_populacao": "Populacao (escala log)",
    "area_km2": "Area (km2)",
    "densidade_hab_km2": "Densidade demografica (hab/km2)",
    "pib_mil_reais": "PIB (mil R$)",
    "pib_per_capita": "PIB per capita (R$)",
    "pct_vab_agro": "Peso da agropecuaria na economia (%)",
    "pct_vab_industria": "Peso da industria na economia (%)",
    "pct_vab_adm_publica": "Peso da administracao publica na economia (%)",
    "pct_vab_servicos": "Peso dos servicos na economia (%)",
    "capital": "Capital de UF",
    # socioeconomico
    "inse_medio": "Nivel socioeconomico medio dos alunos (INSE)",
    "inse_qtd_alunos": "Alunos com INSE calculado",
    "pct_alunos_rural": "Alunos em escolas rurais (%)",
    "inse_pct_nivel_baixo": "Alunos nos niveis socioeconomicos baixos (%)",
    "inse_pct_nivel_alto": "Alunos nos niveis socioeconomicos altos (%)",
    # aluno e escola
    "rede": "Rede de ensino",
    "sigla_uf": "UF",
    "nome_regiao": "Regiao",
    "peso": "Peso amostral",
    "proficiencia": "Proficiencia em portugues (Saeb)",
    "escola_qtd_avaliados": "Alunos avaliados na escola",
    "escola_taxa_presenca": "Presenca na prova na escola (%)",
    "ano": "Ano da avaliacao",
    "ano_alvo": "Ano-alvo",
}


def rotulo(nome: str) -> str:
    """Rotulo de negocio da variavel; trata as colunas one-hot (prefixo=valor)."""
    if nome in ROTULOS:
        return ROTULOS[nome]
    for sep in ("=", "_"):
        base, _, valor = nome.partition(sep)
        if base in ROTULOS and valor:
            return f"{ROTULOS[base]}: {valor}"
    return nome


def rotular(nomes) -> list[str]:
    return [rotulo(n) for n in nomes]
