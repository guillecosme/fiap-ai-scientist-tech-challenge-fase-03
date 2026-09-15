# Dicionário de dados

Tabelas da camada Gold (`data/gold/`) e das bases analíticas (`data/processed/`). A Gold segue o contrato definido na Fase 2 (mesmos nomes de tabela e de campo), agora alimentada pelas fontes reais do Inep, e ganha a tabela `fato_aluno`. As chaves são consistentes entre as tabelas: `id_municipio` (código IBGE de 7 dígitos), `sigla_uf`, `ano`.

## Camada Gold

### dim_municipio
Um registro por município presente em qualquer planilha de resultados ou nos microdados (5.570).

| Campo | Tipo | Descrição |
|---|---|---|
| id_municipio | int | Código IBGE de 7 dígitos |
| nome_municipio | string | Nome do município |
| sigla_uf | string | Sigla da UF |
| id_uf | int | Código IBGE da UF (dois primeiros dígitos do município) |
| nome_uf | string | Nome da UF |
| nome_regiao | string | Grande região (Norte, Nordeste, Sudeste, Sul, Centro-Oeste) |

### fato_aluno
Grão aluno. Todos os estudantes do 2º ano listados pelas redes na avaliação estadual, presentes ou não (4,34 milhões em 2024 e 2025).

| Campo | Tipo | Descrição |
|---|---|---|
| ano | int | Ano da avaliação |
| sigla_uf | category | UF da escola |
| id_aluno | int | Identificador anônimo do aluno (não persiste entre anos) |
| id_escola | int (nulo permitido) | Código mascarado da escola, consistente dentro do ano |
| rede | category | Dependência administrativa: estadual, municipal, privada |
| id_municipio | int (nulo permitido) | Município da escola |
| presente | int | 1 se compareceu à prova de língua portuguesa |
| preencheu | int | 1 se a prova foi preenchida |
| peso | float | Peso amostral do aluno (nulo para ausentes) |
| proficiencia | float | Proficiência em língua portuguesa na escala Saeb (nulo para ausentes) |
| alfabetizado | int | 1 se proficiência >= 743; 0 caso contrário (inclusive ausentes) |

Regra de uso: o universo do indicador são os avaliados (`presente == 1 e preencheu == 1`). Ausentes não entram no denominador do percentual oficial.

### fato_alfabetizacao
Grão ano x município x rede, calculado a partir de `fato_aluno` reproduzindo o cálculo oficial (média ponderada pelo peso amostral). Diferença média para o número publicado pelo Inep: 0,02 ponto percentual.

| Campo | Tipo | Descrição |
|---|---|---|
| ano, id_municipio, nome_municipio, sigla_uf, id_uf, nome_regiao | | chaves e atributos da dimensão |
| rede | string | estadual, municipal ou privada |
| qtd_avaliados | int | Alunos presentes com prova preenchida |
| qtd_alfabetizados | int | Avaliados com proficiência >= 743 |
| media_proficiencia | float | Média ponderada da proficiência |
| indicador_pct | float | Percentual ponderado de alfabetizados (cálculo oficial) |
| indicador_pct_bruto | float | Percentual sem ponderação, para referência |
| meta_municipio | float | Meta do município no ano (a meta é definida para a rede municipal) |
| atingiu_meta | boolean | indicador_pct >= meta_municipio |
| gap_meta_pp | float | indicador_pct - meta_municipio, em pontos percentuais |

### indicador_municipio
Série oficial da rede municipal, 2023 a 2025, como publicada pelo Inep, comparada à meta. É a tabela usada pelo modelo de risco municipal.

| Campo | Tipo | Descrição |
|---|---|---|
| ano, id_municipio, nome_municipio, sigla_uf, id_uf, nome_uf, nome_regiao | | chaves e atributos |
| qtd_avaliados, qtd_alfabetizados, media_proficiencia | | volumes dos microdados (2024 e 2025; nulos em 2023) |
| indicador_pct | float | Percentual de alunos alfabetizados. Em 2023 vem da planilha de divulgação; em 2024 e 2025 vem do agregado exato dos microdados (TS_MUNICIPIO), porque a planilha de 2025 arredonda para inteiros |
| nivel | int | Nível de alfabetização do município (0 a 5), como divulgado |
| participacao_pct | float | Percentual de participação dos alunos na prova |
| meta_municipio | float | Meta do ano (não há meta para 2023, ano de linha de base) |
| atingiu_meta | boolean | indicador_pct >= meta_municipio |
| gap_meta_pp | float | Distância para a meta em pontos percentuais |

### metas_municipio
Metas anuais por município, 2024 a 2030, em formato longo (`id_municipio`, `ano`, `meta_pct`). A trajetória de cada município vem inteira da planilha mais recente em que está completa (alguns municípios tiveram a meta repactuada), com a precisão das planilhas anteriores quando os valores coincidem depois do arredondamento. Meta igual a zero na fonte é tratada como ausente.

### evolucao_temporal
Série por município com `indicador_ano_anterior` e `variacao_pp`.

### comparacao_meta_uf
Indicador por UF e Brasil (`sigla_uf = BR`) contra a meta estadual. A coluna `fonte` separa o indicador (2023 a 2025) do Saeb 2019 e 2021, incluídos como referência histórica.

### metas_uf
Metas anuais por UF e Brasil, 2024 a 2030.

## Campos derivados

- **indicador_pct**: soma dos pesos dos alfabetizados dividida pela soma dos pesos dos avaliados, vezes 100.
- **atingiu_meta**: verdadeiro quando `indicador_pct >= meta`.
- **gap_meta_pp**: `indicador_pct - meta`, em pontos percentuais; negativo significa abaixo da meta.
- **nome_regiao**: derivado do primeiro dígito do código da UF.

## Bases analíticas

As bases analíticas saem de `make abt` (`src/data/abt.py`):

- `abt_municipio.parquet`: uma linha por município e ano-alvo (2024 e 2025 com alvo; 2026 para projeção), 16.575 linhas e 60 colunas: chaves e nomes, histórico do indicador, meta e salto, blocos de contexto, colunas `ref_*` com o ano de referência de cada bloco, e os alvos `indicador_t`, `atingiu_meta_t` e `gap_meta_t`;
- `abt_aluno.parquet`: uma linha por aluno avaliado, com `ano`, chaves, `rede`, `peso`, `proficiencia`, `alfabetizado` e as duas variáveis de escola; o contexto municipal é juntado por `carregar_abt_aluno` a partir da ABT de município do mesmo ano.

A regra de alinhamento temporal (que edição de cada fonte entra em cada ano-alvo) está em `docs/metodologia.md`, seção 2, e é verificada em `tests/test_abt.py`.

## Variáveis dos modelos

As listas abaixo são as que `src/preprocessing/features.py` entrega aos pipelines: 42 variáveis no modelo do aluno (A), 39 no modelo de município (M) e 15 nos perfis territoriais (P). Depois do preprocessamento (one-hot da UF e da rede, indicadores de ausência do histórico) o modelo de município trabalha com 66 colunas e o do aluno com 72. O ano de referência segue a regra de alinhamento temporal da seção anterior (t é o ano-alvo; a prova é aplicada em outubro e novembro de t).

| Bloco | Variáveis | Transformação |
|---|---:|---|
| histórico do indicador | 3 | mediana + indicador de ausência + z-score |
| escola | 2 | mediana + z-score (log1p nos alunos avaliados) |
| Censo Escolar | 10 | mediana + z-score |
| rendimento escolar | 5 | mediana + z-score |
| IDEB | 6 | mediana + z-score |
| socioeconômico | 5 | mediana + z-score (log1p nos alunos com INSE) |
| território | 4 | mediana + log1p + z-score (capital sem log) |
| renda | 5 | mediana + z-score (log1p no PIB per capita) |
| categórica | 2 | one-hot |

| Variável | Rótulo de negócio | Bloco | Fonte | Ano de referência | Transformação | Modelos |
|---|---|---|---|---|---|---|
| `indicador_t1` | % alfabetizados no ano anterior | histórico do indicador | Inep, resultados e metas do indicador | t-1 | mediana + indicador de ausência + z-score | A M P |
| `participacao_t1` | Participação na prova no ano anterior (%) | histórico do indicador | Inep, resultados e metas do indicador | t-1 | mediana + indicador de ausência + z-score | A M P |
| `salto_necessario` | Salto necessário para a meta (p.p.) | histórico do indicador | Inep, resultados e metas do indicador | meta de t menos indicador de t-1 | mediana + indicador de ausência + z-score | A M |
| `escola_qtd_avaliados` | Alunos avaliados na escola | escola | Inep, microdados do indicador | t (dia da prova) | mediana + log1p + z-score | A |
| `escola_taxa_presenca` | Presença na prova na escola (%) | escola | Inep, microdados do indicador | t (dia da prova) | mediana + z-score | A |
| `afd_ai_grupo1_pct` | Docentes com formação adequada, anos iniciais (%) | Censo Escolar | Inep, Censo Escolar | t (referência em maio) | mediana + z-score | A M P |
| `afd_ai_grupo5_pct` | Docentes sem licenciatura, anos iniciais (%) | Censo Escolar | Inep, Censo Escolar | t (referência em maio) | mediana + z-score | A M |
| `afd_inf_grupo1_pct` | Docentes com formação adequada, educação infantil (%) | Censo Escolar | Inep, Censo Escolar | t (referência em maio) | mediana + z-score | A M |
| `alunos_por_turma_ai` | Alunos por turma, anos iniciais | Censo Escolar | Inep, Censo Escolar | t (referência em maio) | mediana + z-score | A M |
| `alunos_por_turma_2ano` | Alunos por turma no 2o ano | Censo Escolar | Inep, Censo Escolar | t (referência em maio) | mediana + z-score | A M P |
| `alunos_por_turma_pre` | Alunos por turma na pré-escola | Censo Escolar | Inep, Censo Escolar | t (referência em maio) | mediana + z-score | A M |
| `distorcao_ai_pct` | Distorção idade-série, anos iniciais (%) | Censo Escolar | Inep, Censo Escolar | t (referência em maio) | mediana + z-score | A M P |
| `distorcao_2ano_pct` | Distorção idade-série no 2o ano (%) | Censo Escolar | Inep, Censo Escolar | t (referência em maio) | mediana + z-score | A M |
| `docentes_superior_ai_pct` | Docentes com curso superior, anos iniciais (%) | Censo Escolar | Inep, Censo Escolar | t (referência em maio) | mediana + z-score | A M P |
| `docentes_superior_inf_pct` | Docentes com curso superior, educação infantil (%) | Censo Escolar | Inep, Censo Escolar | t (referência em maio) | mediana + z-score | A M |
| `aprovacao_ai_pct` | Taxa de aprovação, anos iniciais (%) | rendimento escolar | Inep, rendimento escolar | t-1 | mediana + z-score | A M |
| `aprovacao_1ano_pct` | Taxa de aprovação no 1o ano (%) | rendimento escolar | Inep, rendimento escolar | t-1 | mediana + z-score | A M |
| `aprovacao_2ano_pct` | Taxa de aprovação no 2o ano (%) | rendimento escolar | Inep, rendimento escolar | t-1 | mediana + z-score | A M |
| `reprovacao_ai_pct` | Taxa de reprovação, anos iniciais (%) | rendimento escolar | Inep, rendimento escolar | t-1 | mediana + z-score | A M P |
| `abandono_ai_pct` | Taxa de abandono, anos iniciais (%) | rendimento escolar | Inep, rendimento escolar | t-1 | mediana + z-score | A M P |
| `ideb_ultimo` | IDEB anos iniciais (última edição) | IDEB | Inep, IDEB anos iniciais | última edição até t-1 | mediana + z-score | A M P |
| `ideb_nota_lp_ultimo` | Nota de português no Saeb 5o ano (última edição) | IDEB | Inep, IDEB anos iniciais | última edição até t-1 | mediana + z-score | A M |
| `ideb_rendimento_ultimo` | Indicador de rendimento do IDEB (última edição) | IDEB | Inep, IDEB anos iniciais | última edição até t-1 | mediana + z-score | A M |
| `ideb_anterior` | IDEB anos iniciais (edição anterior) | IDEB | Inep, IDEB anos iniciais | última edição até t-1 | mediana + z-score | A M |
| `ideb_variacao` | Variação do IDEB entre edições | IDEB | Inep, IDEB anos iniciais | última edição até t-1 | mediana + z-score | A M |
| `ideb_tendencia` | Tendência do IDEB (pontos por edição) | IDEB | Inep, IDEB anos iniciais | última edição até t-1 | mediana + z-score | A M P |
| `inse_qtd_alunos` | Alunos com INSE calculado | socioeconômico | Inep, INSE 2023 | 2023 (estático) | mediana + log1p + z-score | A M |
| `inse_medio` | Nível socioeconômico médio dos alunos (INSE) | socioeconômico | Inep, INSE 2023 | 2023 (estático) | mediana + z-score | A M P |
| `pct_alunos_rural` | Alunos em escolas rurais (%) | socioeconômico | Inep, INSE 2023 | 2023 (estático) | mediana + z-score | A M P |
| `inse_pct_nivel_baixo` | Alunos nos níveis socioeconômicos baixos (%) | socioeconômico | Inep, INSE 2023 | 2023 (estático) | mediana + z-score | A M |
| `inse_pct_nivel_alto` | Alunos nos níveis socioeconômicos altos (%) | socioeconômico | Inep, INSE 2023 | 2023 (estático) | mediana + z-score | A M |
| `populacao` | População (Censo 2022) | território | IBGE, Censo 2022 e localidades | 2022 (estático) | mediana + log1p + z-score | A M P |
| `area_km2` | Área (km²) | território | IBGE, Censo 2022 e localidades | 2022 (estático) | mediana + log1p + z-score | A M |
| `densidade_hab_km2` | Densidade demográfica (hab/km2) | território | IBGE, Censo 2022 e localidades | 2022 (estático) | mediana + log1p + z-score | A M |
| `capital` | Capital de UF | território | IBGE, Censo 2022 e localidades | 2022 (estático) | mediana + z-score | A M |
| `pib_per_capita` | PIB per capita (R$) | renda | IBGE, PIB dos municípios 2021 | 2021 (estático) | mediana + log1p + z-score | A M P |
| `pct_vab_agro` | Peso da agropecuária na economia (%) | renda | IBGE, PIB dos municípios 2021 | 2021 (estático) | mediana + z-score | A M P |
| `pct_vab_industria` | Peso da indústria na economia (%) | renda | IBGE, PIB dos municípios 2021 | 2021 (estático) | mediana + z-score | A M |
| `pct_vab_adm_publica` | Peso da administração pública na economia (%) | renda | IBGE, PIB dos municípios 2021 | 2021 (estático) | mediana + z-score | A M |
| `pct_vab_servicos` | Peso dos serviços na economia (%) | renda | IBGE, PIB dos municípios 2021 | 2021 (estático) | mediana + z-score | A M |
| `rede` | Rede de ensino | categórica | Inep, microdados (rede) e IBGE (UF) | t | one-hot | A |
| `sigla_uf` | UF | categórica | Inep, microdados (rede) e IBGE (UF) | t | one-hot | A M |

Colunas da ABT de município que ficam fora dos modelos, e por quê:

| Coluna | Motivo |
|---|---|
| `indicador_t`, `atingiu_meta_t`, `gap_meta_t` | são o alvo (nível, meta atingida, distância) |
| `nivel_t1`, `meta_t` | redundantes com `indicador_t1` e `salto_necessario` (decisão D16) |
| `indicador_t2`, `variacao_t1`, `meta_t1`, `gap_meta_t1` | só existem a partir do ano-alvo 2025 (o indicador começa em 2023); entrariam como defasagem dupla quando houver mais anos |
| `pib_mil_reais`, `log_populacao` | redundantes com `pib_per_capita` e `populacao` (o log é aplicado no pipeline) |
| `nome_municipio`, `nome_uf`, `nome_regiao`, `id_uf` | identificação; a região fica fora por decisão D9 (a UF a contém) |
| `ref_censo_escolar`, `ref_rendimento`, `ref_ideb`, `ano_pib` | metadados do alinhamento temporal, usados nas checagens do notebook 01 |

Na ABT de aluno, `proficiencia` define o alvo e nunca entra como variável; `peso` é o peso amostral do Inep, usado no ajuste e nas métricas; `id_aluno`, `id_escola` e `id_municipio` são chaves; `id_escola` é um código mascarado pelo Inep, consistente só dentro do ano, e por isso as variáveis de escola são calculadas dentro do mesmo ano e nenhuma variável liga escolas entre anos.

