# Predição e Inteligência Analítica para Alfabetização no Brasil

Projeto da Fase 3 do MBA em AI Scientist (FIAP / POSTECH). A camada Gold construída na Fase 2, sobre o Indicador Criança Alfabetizada, foi recomposta com dado real do Inep e do IBGE e passou a alimentar modelos de Machine Learning: um que prevê se um aluno do 2º ano será considerado alfabetizado, um que estima o risco de cada município não atingir a meta do ano seguinte, e um agrupamento de municípios em perfis. Tudo explicado com SHAP, em linguagem de gestão, e traduzido em listas de prioridade para política pública.

- Apresentação executiva: [reports/slides/alfabetizacao_predicao_fase3.pdf](reports/slides/alfabetizacao_predicao_fase3.pdf)
- Vídeo executivo (até 5 min): [reports/slides/link_do_video.txt](reports/slides/link_do_video.txt)
- Ranking de risco 2026: [reports/municipios_risco_2026.csv](reports/municipios_risco_2026.csv)

## Sumário

1. [Contexto do problema](#contexto-do-problema)
2. [Objetivo analítico](#objetivo-analítico)
3. [Descrição da base utilizada](#descrição-da-base-utilizada)
4. [Etapas de modelagem](#etapas-de-modelagem)
5. [Escolha do algoritmo](#escolha-do-algoritmo)
6. [Métricas de avaliação](#métricas-de-avaliação)
7. [Interpretação dos resultados](#interpretação-dos-resultados)
8. [Insights encontrados](#insights-encontrados)
9. [Limitações do projeto](#limitações-do-projeto)
10. [Aplicação prática para políticas públicas](#aplicação-prática-para-políticas-públicas)
11. [Possíveis evoluções futuras](#possíveis-evoluções-futuras)
12. [Estrutura do repositório](#estrutura-do-repositório)
13. [Como executar](#como-executar)
14. [Documentação técnica](#documentação-técnica)

## Contexto do problema

A alfabetização ao final do 2º ano do ensino fundamental é um dos principais marcos do desenvolvimento educacional e social. O Compromisso Nacional Criança Alfabetizada mobiliza União, estados e municípios em torno de uma meta: todas as crianças alfabetizadas na idade certa até 2030. Com a Pesquisa Alfabetiza Brasil, o Inep definiu o corte de 743 pontos na escala Saeb como o nível a partir do qual uma criança é considerada alfabetizada, e desde 2023 publica o Indicador Criança Alfabetizada por município, com metas anuais pactuadas até 2030.

O indicador diz onde estamos. Entre 2023 e 2025 o país foi de 56% para 66% de crianças alfabetizadas na rede pública, e a dispersão entre municípios é enorme: há redes com 90% e redes com 20%. O que o gestor precisa, e o indicador sozinho não dá, é antecipação: quais municípios tendem a ficar aquém da meta no ano que vem, quais fatores mais pesam, quais territórios se parecem e, portanto, onde e como agir antes que o resultado saia.

## Objetivo analítico

Construir uma pipeline completa de Machine Learning, do dado da Gold ao modelo interpretado, que responda às perguntas do desafio:

| Pergunta | Entrega | Onde |
|---|---|---|
| Um aluno será alfabetizado? | classificador no grão de aluno, com pesos amostrais e teste temporal | notebook 03, `models/modelo_aluno.joblib` |
| Quais municípios apresentam maior risco? | risco de não atingir a meta, derivado da regressão do nível do indicador, com ranking e mapa | notebook 04, `reports/municipios_risco_2026.csv` |
| Quais regiões possuem padrões semelhantes? | quatro perfis de município (K-Means, hierárquico, PCA) cruzados com o risco | notebook 05, `reports/perfis_municipios.csv` |
| Como prever quem não atinge metas futuras? | backtest 2024 para 2025 e projeção para 2026 com o modelo reajustado | notebook 04 |
| Quais fatores e variáveis mais influenciam? | SHAP global, por bloco, local e por permutação, com rótulos de negócio | notebook 06, `reports/importancia_*.csv` |

## Descrição da base utilizada

A Fase 2 entregou a Gold com o contrato de esquema, mas com indicador e metas simulados, porque o microdado só saía da Base dos Dados via BigQuery com billing. Nesta fase a Gold foi recomposta, no mesmo contrato, com as fontes que o Inep passou a publicar diretamente, e ganhou uma tabela no grão de aluno:

| Tabela da Gold | Grão | Linhas | Fonte |
|---|---|---|---|
| `dim_municipio` | município | 5.570 | planilhas do Inep e microdados |
| `fato_aluno` | aluno listado para a prova (presente ou não) | 4,34 milhões (2024 e 2025) | microdados da avaliação da alfabetização |
| `fato_alfabetizacao` | ano x município x rede | 13 mil | agregado dos microdados, reproduzindo o cálculo oficial |
| `indicador_municipio` | ano x município (rede municipal) | 16,5 mil (2023 a 2025) | planilhas de divulgação e microdados |
| `metas_municipio`, `metas_uf` | unidade x ano da meta (2024 a 2030) | 38,7 mil e 194 | planilhas de divulgação |
| `evolucao_temporal`, `comparacao_meta_uf` | marts | | derivados |

O enriquecimento vem do próprio Inep (INSE 2023; adequação da formação docente, alunos por turma, distorção idade-série, docentes com curso superior, rendimento escolar do Censo Escolar 2023 a 2025; IDEB dos anos iniciais de 2005 a 2025) e do IBGE (Censo 2022, PIB municipal 2021 com composição setorial, malha municipal). Nenhuma fonte exige credencial; os downloads são conferidos por MD5 e SHA-256.

Duas bases analíticas saem da Gold: a **ABT de município** (uma linha por município e ano-alvo: 2024 e 2025 com alvo, 2026 para projeção; 56 colunas) e a **ABT de aluno** (uma linha por aluno avaliado, 3,8 milhões, com rede, escola e o contexto municipal do mesmo ano). A regra de alinhamento temporal, que evita vazamento, é que para prever o ano t só entram variáveis conhecidas antes da prova: Censo Escolar de t, rendimento de t-1, IDEB até t-1, resultado de t-1, meta de t. Ela está codificada em `src/data/abt.py` e testada em `tests/test_abt.py`.

Dicionário completo em [docs/dicionario_de_dados.md](docs/dicionario_de_dados.md); fontes e URLs em [docs/fontes_de_dados.md](docs/fontes_de_dados.md).

## Etapas de modelagem

| Etapa | Notebook | O que faz |
|---|---|---|
| 1. Base e qualidade | [01_base_gold_e_qualidade](notebooks/01_base_gold_e_qualidade.ipynb) | descreve a Gold, mede cobertura, roda doze checagens de qualidade (chaves, faixas, corte de 743, metas, cálculo próprio x oficial) e apresenta as ABTs com as referências temporais |
| 2. EDA e hipóteses | [02_eda_e_hipoteses](notebooks/02_eda_e_hipoteses.ipynb) | catorze hipóteses testadas (Kruskal-Wallis, Spearman, qui-quadrado, decomposição de variância) e a tabela achado, hipótese, decisão de modelagem |
| 3. Modelo do aluno | [03_modelo_aluno](notebooks/03_modelo_aluno.ipynb) | pipeline integrado, busca de hiperparâmetros em amostra, ablação, curva de aprendizado, ajuste final em 1,85 milhão de alunos, limiar de operação e teste em 2025 |
| 4. Risco municipal | [04_modelo_municipio_risco](notebooks/04_modelo_municipio_risco.ipynb) | classificador direto x regressão do nível com risco derivado, backtest 2024 para 2025, projeção 2026 e ranking |
| 5. Perfis territoriais | [05_perfis_territoriais](notebooks/05_perfis_territoriais.ipynb) | K-Means com cotovelo, silhueta e Davies-Bouldin, hierárquico de Ward, PCA, perfis nomeados e matriz perfil x risco |
| 6. Interpretabilidade e aplicação | [06_interpretabilidade_e_aplicacao](notebooks/06_interpretabilidade_e_aplicacao.ipynb) | SHAP global, por bloco, dependência e local; permutação; mapas; respostas às cinco perguntas |

### O pipeline

Um único `Pipeline` do scikit-learn, com um `ColumnTransformer` de quatro ramos e o modelo no fim, ajustado sempre dentro do fold:

| Ramo | Variáveis | Tratamento |
|---|---|---|
| histórico | % alfabetizados, participação e salto necessário do ano anterior | imputação pela mediana + indicador de ausência + escalonamento |
| log | população, área, densidade, PIB per capita, alunos com INSE, alunos avaliados na escola | mediana + log1p + escalonamento |
| numéricas | Censo Escolar, rendimento, IDEB, socioeconômico, presença na escola | mediana + escalonamento |
| categóricas | UF, rede | one-hot, categorias novas ignoradas |

Os requisitos do enunciado estão cobertos assim: imputação de numéricas (mediana, ajustada no treino); transformação de numéricas (log1p e padronização) e de categóricas (one-hot); tratamento de leakage (alinhamento temporal testado, split por município, teste temporal aberto uma vez, nada ajustado antes do split); preprocessamento integrado ao modelo (o objeto persistido é o pipeline inteiro); treino e validação (busca aleatória com validação cruzada por grupos); replicabilidade e generalização (`random_state` fixo, métricas de treino x validação x teste, curva de aprendizado, backtest).

## Escolha do algoritmo

Três famílias foram comparadas em cada problema, com busca aleatória de hiperparâmetros (`RandomizedSearchCV`) e o mesmo pipeline: regressão logística com L2 (baseline linear e interpretável), Random Forest (bagging) e LightGBM (gradient boosting). Para o nível do indicador, as versões de regressão (Ridge, Random Forest, LightGBM).

- **Modelo do aluno:** o gradient boosting ficou à frente por pouco; a logística chega perto porque o sinal disponível é majoritariamente linear no contexto. Ficou o LightGBM, ajustado com pesos amostrais.
- **Modelo de município:** a decisão mais importante do projeto não foi entre famílias, e sim entre formulações. O classificador direto de "atingiu a meta" chega a AUC 0,81 na validação de 2024 e cai no teste de 2025 (0,60 nas árvores; 0,75 na logística, mais rígida), porque a regra das metas mudou entre os anos (em 2024 a meta acompanhava o resultado de 2023; em 2025 exige saltos crescentes). A regressão do nível do indicador, com o risco derivado da comparação com a meta via distribuição dos resíduos, mantém o AUC do risco em torno de 0,77 no teste temporal. Ficou a regressão com LightGBM.
- **Perfis:** K-Means (K = 4 por cotovelo, silhueta e Davies-Bouldin), com três dos quatro grupos estáveis no hierárquico de Ward, interpretado com PCA.

## Métricas de avaliação

Todas as métricas são reportadas para treino e validação (para ler overfitting) e para o teste temporal (para ler generalização no tempo). No grão de aluno, ponderadas pelo peso amostral do Inep.

| Modelo | Validação 2024 (fora da amostra) | Teste 2025 |
|---|---|---|
| aluno (LightGBM) | AUC-ROC 0,66 | AUC-ROC 0,65, AUC-PR 0,78; no limiar de operação (0,63): recall de não alfabetizados 69%, precisão de não alfabetizados 43% |
| município, nível (LightGBM) | MAE 8,5 p.p. | MAE 11,4 p.p., viés -7,3 p.p. (salto nacional de 2025), Spearman 0,69 |
| município, risco derivado | AUC 0,80 | AUC 0,77 (classificador direto: 0,60; regra simples do salto necessário: 0,74) |
| perfis (K-Means, K = 4) | silhueta 0,136; concordância com Ward (Rand ajustado) 0,50 | |

O ponto de operação dos dois modelos é definido pela política, não pelo padrão de 0,5: o limiar garante recall mínimo de 70% da classe de interesse (não alfabetizado; não atingiu a meta) nas probabilidades fora da amostra de 2024. A curva de aprendizado do modelo do aluno mostra as curvas de treino e validação convergindo cedo: o limite é de variáveis, não de dados.

## Interpretação dos resultados

SHAP (TreeExplainer sobre o pipeline completo, no espaço transformado, com rótulos de negócio) e importância por permutação concordam no que pesa:

1. **Histórico da rede**: o percentual de alfabetizados do ano anterior é a variável mais forte nos dois modelos (sem ela, o erro do modelo de município sobe quase 5 p.p.); no aluno, o salto necessário para a meta vem logo atrás.
2. **IDEB dos anos iniciais** e a nota de português do 5º ano: outra prova, outra série, mesma rede. Efeito forte e monotônico, de −4 a +3 p.p. no nível previsto.
3. **UF** como fator em si, que mistura gestão estadual e instrumento de avaliação.
4. **Participação e presença na prova**: das escolas com presença abaixo de 80% para as com presença quase total, a proporção de alfabetizados sobe de 52% para 72%.
5. **Fluxo escolar** entra pelo abandono, com efeito de degrau (qualquer abandono nos anos iniciais custa cerca de 1 p.p.), e pela distorção idade-série, com efeito pequeno dentro do modelo porque o histórico e o IDEB já carregam essa informação. Na EDA, sem o histórico, esses são os contextos mais correlacionados com o resultado.
6. **Porte** com sinal negativo (municípios menores alfabetizam mais); **qualificação docente** e **contexto socioeconômico** (INSE, PIB per capita) com efeito pequeno.

As explicações locais (gráficos em cascata) mostram, para um município específico, o que o afasta da média nacional; é a peça que transforma a lista de risco em conversa com o gestor. Figuras em `images/06_*` e tabelas em `reports/importancia_*.csv`.

## Insights encontrados

- **A UF explica um terço da variação entre municípios; a região, quase nada.** Ceará e Bahia são vizinhos e opostos. Regime de colaboração estadual e instrumento de prova pesam mais do que geografia.
- **Fluxo escolar importa mais do que renda.** As correlações de abandono, reprovação e distorção com o indicador são três vezes maiores do que as de INSE e PIB per capita. Redes bem geridas alfabetizam em contextos pobres.
- **Municípios menores alfabetizam mais** (correlação negativa com população), o oposto do senso comum sobre porte e capacidade.
- **85% da variação entre alunos está dentro da escola.** É o teto de qualquer modelo sem dado individual; o valor está em ordenar redes, não em rotular crianças.
- **A regra da meta mudou e o alvo binário aprendeu a regra, não a realidade.** Modelar o nível e comparar com a meta depois é a formulação robusta.
- **2025 foi um ano de salto** (o país subiu 9 p.p.), com regressão à média forte em relação a 2024; modelos treinados em um ano subestimam o seguinte, e o reajuste anual faz parte do método.
- **O Rio Grande do Sul lidera o risco de 2026 por causa da régua, não das redes**: as metas foram ancoradas no nível de 2023 (73%), o estado caiu para 52% em 2024 (enchentes) e voltou a 64% em 2025; a meta de 2026 exige superar o nível de antes do choque. É um caso para repactuar trajetória, e o modelo dimensiona isso.
- **Os perfis cortam as regiões**: o perfil de fluxo comprometido tem municípios em todas as regiões, e o perfil de renda baixa com resultado alto é 82% nordestino (Ceará, Piauí, Paraíba), com INSE igual ao do perfil de fluxo comprometido e resultado 20 p.p. maior.

## Limitações do projeto

- **Sem variáveis do aluno.** Os microdados não trazem sexo, idade, NSE individual nem trajetória. O modelo do aluno é um modelo de contexto; seu AUC reflete esse teto, não um defeito de ajuste.
- **Comparabilidade entre UFs.** Cada estado aplica a própria avaliação, pareada à escala Saeb. Parte do efeito da UF pode ser de instrumento, e o modelo não separa isso de gestão.
- **Série curta.** Três anos do indicador impedem modelos de série temporal e limitam as variáveis de defasagem dupla (deixadas fora do modelo principal).
- **Choques de política.** O salto de 2025 não era previsível a partir de 2024. O modelo prevê trajetória dado o contexto; não prevê programas novos.
- **Fontes de enriquecimento com defasagem.** PIB de 2021, INSE de 2023; para a projeção de 2026 valem as últimas edições publicadas.
- **Predição, não causa.** Distorção idade-série alta é sintoma; reduzi-la por decreto não alfabetiza. Estimar efeitos exige desenho causal.
- **Escola mascarada.** O código da escola nos microdados é fictício e não liga ao Censo Escolar por escola; o contexto é municipal.

## Aplicação prática para políticas públicas

- **Triagem anual antes do ano letivo.** `reports/municipios_risco_2026.csv` lista os municípios pelo risco de não atingir a meta, com o nível previsto, o salto necessário e os fatores de cada um (distorção, IDEB, INSE). É a lista para o regime de colaboração priorizar apoio técnico e formação.
- **Sinal de alerta barato.** Abandono e distorção idade-série nos anos iniciais e presença na prova já estão no Censo Escolar e na aplicação da avaliação; na EDA são os contextos mais correlacionados com o resultado, e acompanhá-los antecipa o indicador sem esperar a divulgação.
- **Estratégia por perfil, não por região.** `reports/perfis_municipios.csv` agrupa municípios de condições parecidas; um programa desenhado para o perfil de fluxo comprometido serve a municípios do Pará e de Minas ao mesmo tempo.
- **Duas leituras de risco.** O mapa do nível atual e o mapa do risco em relação à meta não coincidem: municípios com nível baixo e meta modesta ficam fora da lista; municípios médios com meta ambiciosa entram. A política precisa das duas.
- **Ciclo operacional.** A cada divulgação, `make data`, `make abt` e `make train` reestimam o modelo e o limiar com o ano mais recente; o notebook 04 mostra por que isso é necessário.

## Possíveis evoluções futuras

- **Variáveis de escola e de aluno**: com o Censo Escolar por escola (infraestrutura, docentes, turmas) e dados de trajetória, o teto do modelo do aluno sobe. Depende de o Inep liberar a chave da escola ou de um pareamento seguro.
- **Avaliação causal de programas**: pareamento por escore de propensão e diferenças em diferenças entre redes que adotaram e não adotaram programas de alfabetização, para passar de "o que prevê" a "o que funciona".
- **Série mais longa**: com 2026 e 2027, entram as defasagens duplas, a modelagem da variação anual e, mais adiante, métodos de série temporal por UF.
- **Alocação sequencial de recursos**: tratar a distribuição anual de apoio técnico entre municípios como um problema de decisão sequencial, onde métodos de aprendizado por reforço podem ser explorados.
- **Operação**: reajuste automático a cada divulgação, monitoramento de deriva (a taxa base mudou de 53% para 72% em um ano) e um painel para os gestores estaduais.

## Estrutura do repositório

```
.
├── data/
│   ├── raw/, external/      fontes baixadas por make data (não versionadas, exceto a malha)
│   ├── gold/                Gold em Parquet (versionada)
│   ├── processed/           ABTs de município e de aluno (versionadas)
│   └── manifest.json        hashes dos downloads
├── notebooks/               01 a 06, um por etapa
├── src/
│   ├── data/                catálogo de fontes, download, parsers do Inep e do IBGE, gold, abt
│   ├── preprocessing/       listas de variáveis, ColumnTransformer, splits
│   ├── modeling/            famílias de modelos, busca de hiperparâmetros, persistência, CLI
│   ├── evaluation/          métricas, validação por grupos e temporal, SHAP e permutação
│   └── visualization/       estilo, rótulos de negócio, mapas
├── models/                  pipelines completos (.joblib), metadados (.json), predições
├── tests/                   parsers, montagem das bases (anti-leakage), pipeline, métricas
├── reports/                 rankings, perfis, importâncias, apresentação e link do vídeo
├── images/                  figuras dos notebooks
├── docs/                    metodologia, decisões analíticas, dicionário, fontes, reprodutibilidade
├── Makefile                 data, gold, abt, train, notebooks, test, lint
├── pyproject.toml, uv.lock  dependências (uv)
└── requirements.txt         exportado do lock
```

## Como executar

```bash
uv sync                    # ou: pip install -r requirements.txt
make notebooks             # caminho curto: Gold e ABTs já versionadas
make test                  # 26 testes
```

Do dado bruto: `make data` (cerca de 900 MB), `make gold`, `make abt`, depois `make notebooks`. `make train` treina pela linha de comando. Tempos, determinismo e problemas conhecidos em [docs/reprodutibilidade.md](docs/reprodutibilidade.md).

## Documentação técnica

- [docs/metodologia.md](docs/metodologia.md): fluxo, pipeline, protocolos de validação, o que ficou fora e por quê
- [docs/decisoes_analiticas.md](docs/decisoes_analiticas.md): registro das decisões com motivo e evidência
- [docs/dicionario_de_dados.md](docs/dicionario_de_dados.md): tabelas e campos da Gold e das ABTs
- [docs/fontes_de_dados.md](docs/fontes_de_dados.md): fontes, URLs, anos e alinhamento temporal
- [docs/reprodutibilidade.md](docs/reprodutibilidade.md): como rodar do zero, tempos e determinismo

Histórico do projeto em branches e pull requests, com a justificativa de cada mudança na descrição do PR.
