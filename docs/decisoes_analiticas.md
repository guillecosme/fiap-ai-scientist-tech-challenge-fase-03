# Decisões analíticas

Registro das decisões tomadas ao longo do projeto, com o motivo e a evidência. A ideia é a mesma de um registro de decisões de arquitetura: quem ler daqui a seis meses entende por que o pipeline é do jeito que é. As decisões estão em ordem cronológica e apontam para o notebook ou módulo onde foram aplicadas.

## Base de dados

| # | Decisão | Motivo | Onde |
|---|---|---|---|
| D1 | Recompor a Gold da Fase 2 com fontes reais do Inep e do IBGE, no mesmo contrato de esquema | O feedback da Fase 2 apontou que indicador e metas eram simulados; o Inep passou a publicar resultados, metas e microdados | `src/data/gold.py`, `docs/fontes_de_dados.md` |
| D2 | Reproduzir o cálculo oficial do percentual (média ponderada pelo peso amostral entre presentes com prova preenchida) | Sem a ponderação o erro médio contra o número publicado é de 0,35 p.p.; com ela, 0,03 p.p. O modelo precisa ser comparado com a régua que o gestor usa | notebook 01 |
| D3 | Ausentes ficam em `fato_aluno` com `alfabetizado = 0` mas fora do universo do alvo | O Inep não conta ausentes no denominador; incluí-los faria o modelo prever ausência, não alfabetização | notebook 01, `src/data/abt.py` |
| D4 | Nos anos com microdados, o percentual municipal vem do agregado exato (TS_MUNICIPIO), não da planilha | A planilha de 2025 publica percentuais arredondados para inteiros | notebook 01, `src/data/gold.py` |
| D5 | A trajetória de metas de cada município vem inteira de uma única planilha (a mais recente completa), com a precisão das anteriores quando coincidem; meta zero é ausente | Alguns municípios tiveram metas repactuadas e dois têm meta 2030 igual a zero na fonte; misturar planilhas criava quedas artificiais | notebook 01, `src/data/gold.py` |
| D6 | PIB de 2021 em vez de 2022 | O IBGE ainda não divulgou a composição setorial do valor adicionado de 2022 | `src/data/sources.py` |
| D7 | Alinhamento temporal: para o ano-alvo t entram o Censo Escolar de t, o rendimento de t-1, o IDEB até t-1, o indicador de t-1 e a meta de t | Nada que só seja conhecido depois da prova pode entrar como variável; regra testada em `tests/test_abt.py` | `src/data/abt.py` |
| D8 | Versionar a Gold e as ABTs em Parquet (cerca de 50 MB no total) | Notebooks e modelos ficam reproduzíveis sem baixar 900 MB de fontes | `.gitignore` |

## Análise exploratória

| # | Decisão | Motivo | Onde |
|---|---|---|---|
| D9 | UF entra como categórica (one-hot); região fica de fora | A UF explica um terço da variação do indicador entre municípios; a região, 6% | notebook 02, H1 |
| D10 | Validação por grupos de município (`StratifiedGroupKFold`) | O mesmo município não pode estar em treino e validação; o cenário real é prever municípios e alunos já conhecidos em um ano novo, não UFs novas | notebook 02, H1 |
| D11 | Contexto socioeconômico entra, mas com expectativa de peso baixo | INSE e PIB per capita têm correlação fraca com o indicador (0,09 e 0,04); porte e ruralidade pesam mais | notebook 02, H2 a H4 |
| D12 | Transformação log1p nas variáveis de porte e renda, dentro do pipeline | Assimetria acima de 6 em PIB per capita e densidade | notebook 02, bloco 7 |
| D13 | Árvores e boosting além da regressão logística | As relações com fluxo escolar e formação docente não são lineares | notebook 02, H5 a H8 |
| D14 | Histórico do indicador e IDEB entram, com ablação obrigatória | São os preditores mais fortes (0,69 e 0,49 de Spearman); é preciso medir quanto o contexto acrescenta além deles | notebook 02, H9 e H10 |
| D15 | Teste temporal (treino em 2024, teste em 2025) e saída em probabilidade | A taxa de atingimento subiu de 53% para 72% entre os anos; a probabilidade precisa ser lida com a taxa base do ano | notebook 02, H11 |
| D16 | `nivel_t1` e `meta_t` fora do modelo | Redundantes com `indicador_t1` e `salto_necessario` (Spearman de 0,98 e 0,63) | notebook 02, bloco 6 |
| D17 | Imputação pela mediana ajustada no treino, com indicador de ausência para o histórico | Nulos concentrados no histórico (município sem resultado no ano anterior), o que é informativo | notebook 02, bloco 7 |
| D18 | Pesos amostrais do Inep nas métricas do modelo de aluno; AUC-ROC como métrica principal e recall de "não alfabetizado" como métrica de política | 85% da variância do alvo está entre alunos da mesma escola, nível em que não há variáveis; o modelo é útil para ordenar risco, não para acertar o aluno individual | notebook 02, H12 a H14 |

## Modelagem

| # | Decisão | Motivo | Onde |
|---|---|---|---|
| D19 | Busca de hiperparâmetros do modelo do aluno em amostra estratificada de 300 mil, ajuste final na base inteira | 1,85 milhão de linhas tornam a busca cara demais para o ganho; a curva de aprendizado mostra que o modelo satura muito antes desse volume | notebook 03 |
| D20 | LightGBM como modelo do aluno | melhor AUC de validação (0,667), à frente da logística (0,664) e da Random Forest (0,665); gap treino-validação pequeno em todas | notebook 03 |
| D21 | Limiar de operação por recall mínimo de 70% da classe "não alfabetizado", escolhido nas probabilidades fora da amostra de 2024 | a classe de interesse para política é a de risco; 0,5 daria recall de 39% | notebook 03 |
| D22 | Modelo de município formulado como regressão do nível do indicador, com o risco derivado da distribuição dos resíduos | a regra da meta mudou entre 2024 e 2025; o classificador direto cai de 0,81 para 0,60 de AUC no teste temporal, a regressão do nível mantém 0,77 | notebook 04 |
| D23 | Ajuste final do modelo de município nas linhas com alvo em 2025 (não em 2024 + 2025) | os rankings dos dois ajustes têm correlação 0,88, mas 2024 carrega choques localizados (queda de 20 p.p. do Rio Grande do Sul) que penalizavam municípios gaúchos além do que 2025 justifica | notebook 04 |
| D24 | Backtest temporal 2024 para 2025 como a métrica de generalização reportada | é a única estimativa honesta do desempenho em um ano novo; a validação cruzada dentro do ano superestima | notebooks 03 e 04 |
| D25 | K = 4 nos perfis, K-Means com contraste hierárquico | silhueta e Davies-Bouldin empatam entre 3 e 5; 4 dá perfis interpretáveis e grandes; três dos quatro são estáveis no hierárquico de Ward | notebook 05 |
| D26 | SHAP no espaço transformado com rótulos de negócio, mais permutação como segunda opinião | o feedback da Fase 1 pediu nomes de negócio nos gráficos; a permutação confirma que o histórico é a variável de que o modelo mais depende | notebook 06 |
| D27 | Sem ARIMA, sem inferência causal, sem reforço | três pontos de série, projeto preditivo; registrados como evoluções futuras | `docs/metodologia.md` |
