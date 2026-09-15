# Métricas dos modelos

Tabela consolidada, gerada a partir de `models/*.json` (os mesmos números dos notebooks 03 e 04). Todas as métricas do modelo do aluno são ponderadas pelo peso amostral do Inep. Validação = fora da amostra em 2024 (folds por município); teste = 2025, aberto uma vez.

## Modelo do aluno (alfabetizado, proficiência >= 743)

| Conjunto | AUC-ROC | AUC-PR | Acurácia | Precisão | Recall | F1 | Precisão não alfab. | Recall não alfab. | Limiar |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| validação 2024 (fora da amostra, limiar 0,5) | 0,663 | 0,738 | 0,635 | 0,657 | 0,803 | 0,723 | 0,578 | 0,391 | 0,50 |
| validação 2024 (fora da amostra, limiar de operação) | 0,663 | 0,738 | 0,594 | 0,724 | 0,508 | 0,597 | 0,502 | 0,718 | 0,63 |
| teste 2025 (limiar 0,5) | 0,646 | 0,776 | 0,651 | 0,704 | 0,809 | 0,753 | 0,490 | 0,350 | 0,50 |
| teste 2025 (limiar de operação) | 0,646 | 0,776 | 0,577 | 0,761 | 0,518 | 0,617 | 0,428 | 0,689 | 0,63 |

Comparação das famílias na busca de hiperparâmetros (amostra estratificada de 300 mil, 3 folds por município):

| Família | AUC validação | AUC treino |
|---|---:|---:|
| logistica | 0,664 | 0,668 |
| random_forest | 0,665 | 0,692 |
| lightgbm | 0,667 | 0,692 |

Ablação por bloco de variáveis (mesma validação):

| Variáveis | Nº | AUC validação | AUC treino |
|---|---:|---:|---:|
| só aluno e escola (rede, UF, tamanho, presença) | 4 | 0,642 | 0,664 |
| contexto municipal sem histórico | 39 | 0,659 | 0,689 |
| só histórico do indicador e UF | 4 | 0,649 | 0,668 |
| completo | 42 | 0,664 | 0,691 |

## Modelo de município (nível do indicador e risco derivado)

Backtest temporal: treino em 2024, teste em 2025.

| Métrica | Valor |
|---|---:|
| MAE treino 2024 (p.p.) | 7,358 |
| MAE validação 2024 (p.p.) | 8,486 |
| R² validação 2024 | 0,646 |
| AUC do risco, validação 2024 | 0,797 |
| MAE teste 2025 (p.p.) | 11,377 |
| Viés teste 2025 (p.p.) | -7,323 |
| Spearman do nível, teste 2025 | 0,693 |
| AUC do risco, teste 2025 | 0,772 |

Classificador direto do alvo binário (comparação, não entregue):

| Família | AUC validação 2024 | AUC teste 2025 |
|---|---:|---:|
| logistica | 0,810 | 0,753 |
| random_forest | 0,806 | 0,627 |
| lightgbm | 0,812 | 0,598 |

Ponto de operação (limiar 0,53 sobre a probabilidade de atingir):

| Conjunto | AUC-ROC | Acurácia | Precisão | Recall | F1 | Precisão não atingiu | Recall não atingiu |
|---|---:|---:|---:|---:|---:|---:|---:|
| validação 2024 | 0,797 | 0,723 | 0,739 | 0,740 | 0,739 | 0,706 | 0,704 |
| teste 2025 | 0,772 | 0,652 | 0,887 | 0,589 | 0,708 | 0,439 | 0,811 |

Projeção 2026: 5.477 municípios com meta. 936 com risco acima de 50% (`reports/municipios_risco_2026.csv`).

## Calibração e incerteza (notebook 06, sobre as predições salvas)

Intervalo de 95% por bootstrap de municípios inteiros; Brier da taxa base = p(1-p).

| Modelo | AUC | IC 95% | KS | Brier | Brier da taxa base |
|---|---:|---:|---:|---:|---:|
| aluno, teste 2025 | 0,646 | 0,638 a 0,656 | 0,210 | 0,216 | 0,226 |
| município, risco no backtest 2025 | 0,772 | 0,758 a 0,785 | 0,408 | 0,243 | 0,203 |
| município, risco com o efeito ano | 0,772 |  |  | 0,189 |  |

## Falsificação e extrapolação

Resumo; tabela completa em `reports/robustez.md`.

| Teste | Município | Aluno |
|---|---|---|
| alvo embaralhado | MAE 16,2 p.p., AUC do risco 0,52 | AUC 0,655 (embaralhado dentro do município) contra 0,665 |
| modelo contra regra simples | +0,029 de AUC (IC 0,021 a 0,037) | +0,006 (IC 0,004 a 0,009) |
| completa contra antes da prova | | +0,005 (IC 0,003 a 0,007) |
| estabilidade da lista de 2026 | núcleo 926, franja 17 | |
| estado nunca visto | MAE 8,5 para 11,3 p.p.; AUC do risco 0,80 para 0,64 | AUC 0,665 para 0,641 |

## Perfis territoriais

K-Means com K = 4: silhueta 0,136, Davies-Bouldin 1,937; concordância com o hierárquico de Ward (Rand ajustado) 0,50. Perfis em `reports/perfis_municipios.csv`.
