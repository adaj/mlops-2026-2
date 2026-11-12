# Criando um dashboard no Grafana (passo a passo)

Guia escrito e testado no **Grafana 13.3** que vem na imagem `grafana/otel-lgtm`. A interface do Grafana muda bastante entre versões: se um botão não estiver onde o guia diz, procure pelo mesmo nome.

O dashboard pronto, para comparação, está em [`intent-clf-obs.json`](intent-clf-obs.json) (veja "Importar" no fim).

---

## Antes de começar: três armadilhas que confundem

1. **O gráfico de exemplo não é o seu dado.** Ao criar um painel, o Grafana já mostra uma linha subindo e descendo. É o data source `-- Grafana --` com dados aleatórios (*Random Walk*). Enquanto você não trocar o *Data source* para **Prometheus** (ou **Loki**), nada do que aparece vem da sua API.
2. **O período padrão é "Last 6 hours".** Uma rajada de 20 requisições vira um risquinho no canto direito. Troque para **Last 15 minutes** no seletor de tempo (canto superior direito).
3. **Métricas chegam a cada 15 s.** Depois de mandar requisições, espere uns 15 a 30 segundos e clique em **Refresh**.

---

## 1. Gerar tráfego

Com dado constante os gráficos ficam vazios ou retos. Antes de tudo, rode no terminal:

```bash
for i in $(seq 1 10); do
  for t in "não entendi nada" "pode repetir a explicação?" "agora ficou claro, obrigado" \
           "qual é o prazo da entrega?" "oi, tudo bem?" "quem é você?"; do
    curl -s -X POST localhost:8000/predictions -H 'Content-Type: application/json' \
      -d "{\"nome\":\"teste\",\"text\":\"$t\"}" > /dev/null
  done
done
```

## 2. Criar o dashboard vazio

1. Menu (☰, canto superior esquerdo) → **Dashboards** → botão **New** → **New dashboard**.
2. A tela mostra "New dashboard" no centro e um painel lateral **Add** à direita.
3. Ainda no centro, em *Select layout*, deixe **Custom grid** se quiser arrastar e redimensionar os painéis livremente (no **Auto grid**, todos ficam do mesmo tamanho).

## 3. Primeiro painel: "Predições por minuto"

1. No painel lateral **Add**, clique no quadro com o **+** abaixo de *Panel*. Aparece um painel "New panel" no dashboard.
2. Clique em **Configure visualization** (no meio do painel). Abre o **editor do painel**, que tem três áreas:
   - **em cima**, a pré-visualização do gráfico;
   - **embaixo**, a aba **Queries** (de onde vêm os dados);
   - **à direita**, as opções da visualização.
3. Embaixo, em **Data source**, clique em `-- Grafana --` e escolha **Prometheus**.
4. Na query **A**, à direita, há o seletor **Builder | Code**. Clique em **Code**. (O *Builder* monta a query com menus; o *Code* aceita PromQL digitado, que é o que usamos nos guias.)
5. Clique no campo *Enter a PromQL query…* e cole:
   ```
   sum by (model) (rate(prediction_count_total[$__rate_interval])) * 60
   ```
   Se aparecer uma lista de sugestões, aperte **Esc**.
6. Clique em **Run queries** (ou **Shift+Enter**). A pré-visualização passa a mostrar uma linha por modelo.
7. Logo abaixo da query, abra **Options** e, em **Legend**, escolha **Custom** e escreva `{{model}}`. Isso troca o nome comprido da série pelo nome do modelo.
8. À direita, se aparecer a lista *Suggestions / All visualizations*, clique em **All visualizations** → **Time series**. Aparecem as opções do painel.
9. Em **Panel options → Title**, troque "New panel" por `Predições por minuto, por modelo`.
10. Para achar qualquer opção sem rolar, use a **lupa** no topo das opções da direita. Digite `unit`, clique na caixa *Choose* que aparecer e escreva `rpm` → escolha **Throughput / requests/min (rpm)**. Clique em **Clear** para limpar a busca.
11. Clique em **Back** (canto superior direito) para voltar ao dashboard.

## 4. Salvar

1. Clique em **Save** (azul, canto superior direito). Abre uma gaveta à direita.
2. Em **Title**, dê um nome **único**. Se aparecer *"A dashboard or a folder with the same name already exists"*, o botão Save fica desabilitado: troque o nome (existe um "New dashboard" vazio salvo antes).
3. Clique em **Save**.
4. Para sair do modo de edição, clique em **Exit edit**. Às vezes o Grafana pergunta *Unsaved changes* mesmo sem você ter mexido em nada (ele atualiza o formato interno do dashboard). Se você acabou de salvar, pode clicar em **Discard**.

Para editar de novo: abra o dashboard → **Edit** (canto superior direito) → passe o mouse sobre o painel → menu **⋮** → **Edit**.

## 5. Os outros painéis

Para cada linha da tabela: no modo de edição, **+** (canto superior esquerdo) ou painel lateral **Add** → **Panel** → **Configure visualization**, e repita os passos 3 a 11 da seção anterior, trocando a query, o tipo e a unidade.

| Título | Visualização | Query (modo **Code**) | Legend | Unit / ajustes |
| --- | --- | --- | --- | --- |
| Predições no período, por modelo | **Stat** | `sum by (model) (increase(prediction_count_total[$__range]))` | `{{model}}` | *short*, Decimals 0. Em **Options** da query, *Type*: **Instant** |
| Latência de inferência p95, por modelo | **Time series** | `histogram_quantile(0.95, sum by (le, model) (rate(prediction_latency_seconds_bucket[$__rate_interval])))` | `p95 {{model}}` | *seconds (s)*. Para o p50, **+ Add query** com `0.50` |
| Distribuição da latência | **Heatmap** | `sum by (le) (increase(prediction_latency_seconds_bucket[$__rate_interval]))` | `{{le}}` | Em **Options** da query, *Format*: **Heatmap**. À direita, *Calculate from data*: **No** |
| Distribuição das intenções | **Bar gauge** | `sum by (model, intent) (increase(prediction_count_total[$__range]))` | `{{model}} · {{intent}}` | *Type*: **Instant**; *Orientation*: **Horizontal** |
| Requisições por segundo, por rota | **Time series** | `sum by (http_target, http_status_code) (rate(http_server_duration_milliseconds_count{http_target!=""}[$__rate_interval]))` | `{{http_target}} → {{http_status_code}}` | *requests/sec (rps)* |
| Últimas predições | **Logs** | Data source **Loki**, modo **Code**: `{service_name="intent-clf"} \|= "Predicao"` | — | — |

**Os números de um Stat aparecem vermelhos?** O Stat colore pelo limite padrão (vermelho acima de 80). Na lupa das opções, procure `thresholds` e apague o passo vermelho (ou troque a cor para verde).

## 6. Variável para filtrar por modelo

1. No modo de edição (**Edit**), clique na **engrenagem** da barra lateral direita → **View all settings** → aba **Variables** → **Add variable**.
2. *Variable type*: **Query**; *Name*: `model`; *Label*: `Modelo`; *Data source*: **Prometheus**.
3. Em *Query type* escolha **Label values**, *Label* `model`, *Metric* `prediction_count_total`.
4. Em *Selection options*, ligue **Multi-value** e **Include All option**. Clique em **Back to dashboard** (canto superior direito).
5. Nas queries dos painéis de modelo, acrescente o filtro `{model=~"$model"}`. Exemplo:
   `sum by (model) (rate(prediction_count_total{model=~"$model"}[$__rate_interval])) * 60`

## 7. Organizar em seções

No painel lateral **Add**, use **Add row** para criar seções ("Saúde do serviço", "Modelos", "Saída do modelo") e arraste os painéis para dentro.

## 8. Exportar e importar (importante)

O container `lgtm` **não tem volume persistente**: `docker compose down` ou recriar o container **apaga os dashboards**.

- **Exportar:** com o dashboard aberto, na barra lateral direita clique no ícone de **exportar** (seta para baixo numa bandeja) → **Export as code** → **Download file**. Salve em `docs/grafana/` e faça commit.
- **Importar:** **Dashboards** → **New** → **Import** → arraste o `.json` (ou cole o conteúdo) → **Import**.

---

## Por que essas queries?

| Função | O que faz | Quando usar |
| --- | --- | --- |
| `rate(x[janela])` | variação **por segundo** de um contador, em média na janela | gráficos ao longo do tempo (Time series) |
| `increase(x[janela])` | quanto o contador **subiu** na janela | totais (Stat, Bar gauge) |
| `$__range` | a janela inteira escolhida no seletor de tempo | "no período" |
| `$__rate_interval` | janela que o Grafana calcula para ter pontos suficientes | sempre dentro do `rate()` em gráficos |
| `sum by (rótulo)` | soma as séries mantendo só aquele rótulo | uma linha por modelo, por intenção, etc. |
| `histogram_quantile(0.95, sum by (le, …) (rate(x_bucket[…])))` | percentil a partir dos buckets do histograma | latência p95/p50; o `le` **precisa** estar no `by` |

Os números de `increase()` podem vir "quebrados" (ex.: 62,1 em vez de 60). O Prometheus extrapola até as bordas da janela. Por isso usamos *Decimals 0* nos totais.
