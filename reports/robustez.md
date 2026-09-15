# Evidências de robustez

Tabela única com os testes que tentam derrubar os dois modelos: intervalos de confiança, calibração, falsificação e extrapolação. Os números vêm dos notebooks 04 (município) e 06 (aluno), sobre as predições salvas em `models/`; nada é retreinado além do necessário para os testes, e o modelo do aluno é reajustado só em amostra de 300 mil linhas com os hiperparâmetros já escolhidos.

## Incerteza e calibração (`reports/intervalos_confianca.csv`, `reports/calibracao.csv`)

| Modelo | AUC | IC 95% (bootstrap de municípios) | KS | Brier | Brier da taxa base |
|---|---:|---:|---:|---:|---:|
| aluno, teste 2025 | 0,646 | 0,638 a 0,656 | 0,210 | 0,216 | 0,226 |
| município, risco no backtest 2025 | 0,772 | 0,758 a 0,785 | 0,408 | 0,243 | 0,203 |
| município, risco com o efeito ano conhecido | 0,772 | | | 0,189 | 0,203 |

## Falsificação (`reports/falsificacao.csv`, `reports/falsificacao_aluno.csv`)

| Teste | Município | Aluno |
|---|---|---|
| alvo embaralhado | MAE 16,2 p.p. (prever a média: 16,1); Spearman 0,02; AUC do risco 0,52 | AUC 0,655 com o alvo embaralhado dentro do município, contra 0,665 com o alvo verdadeiro: quase toda a ordenação vem do município |
| modelo contra regra simples, IC pareado (97,5% por comparação, Bonferroni) | +0,029 de AUC sobre "salto necessário" (IC 0,019 a 0,039); +0,126 sobre "% alfabetizados no ano anterior" (0,110 a 0,143) | +0,006 sobre "% alfabetizados do município no ano anterior" (IC 0,004 a 0,009) |
| variante completa contra antes da prova | | +0,005 (IC 0,003 a 0,008) |
| ausência prediz o alvo | maior AUC de um indicador de ausência: 0,504 | |
| gate automático de vazamento (`tests/test_vazamento.py`) | nenhuma variável isolada com AUC acima de 0,90 (maior: salto necessário, 0,62); ausência abaixo de 0,60 | maior AUC isolado 0,64 (% alfabetizados no ano anterior) |
| estabilidade da lista de 2026 | 926 municípios na lista em 95% ou mais de 500 reamostras dos resíduos; franja de 17 | |

## Extrapolação para estado nunca visto (`reports/extrapolacao_uf.csv`, `reports/extrapolacao_uf_aluno.csv`)

| Protocolo | Município (base de 2024) | Aluno (amostra de 300 mil, 2024) |
|---|---|---|
| folds por município (estado conhecido) | MAE 8,5 p.p.; AUC do risco 0,80 | AUC 0,665 |
| leave-one-UF-out / folds por UF (estado nunca visto) | MAE 11,3 p.p.; AUC do risco 0,64 | AUC 0,641 |
| dentro de cada UF | AUC quase igual (Ceará 0,90 para 0,83; Minas 0,82 para 0,76; demais iguais); o que muda é o patamar, com viés de até +19 p.p. (RS) e -9 (GO, CE) | mediana da diferença -0,002 |

Leitura: os dois modelos generalizam para municípios novos de estados conhecidos, que é o caso da projeção de 2026; em um estado novo a ordenação dentro do estado se mantém, mas o nível erra, e o risco municipal, que compara nível com meta, fica comprometido até que o estado entre no treino.
