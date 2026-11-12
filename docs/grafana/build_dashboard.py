"""Gera docs/grafana/intent-clf-obs.json (dashboard como codigo).

Uso:  python docs/grafana/build_dashboard.py
Depois importe o JSON no Grafana (Dashboards > New > Import).
"""
import json
from pathlib import Path

PROM = {"type": "prometheus", "uid": "prometheus"}
LOKI = {"type": "loki", "uid": "loki"}
M = 'model=~"$model"'                      # filtro da variavel "Modelo"
RI = "$__rate_interval"
_ids = iter(range(1, 200))


def q(expr, legend=None, ref="A", instant=False, ds=PROM, **kw):
    t = {"refId": ref, "datasource": ds, "expr": expr}
    if legend:
        t["legendFormat"] = legend
    if instant:
        t.update(instant=True, range=False)
    t.update(kw)
    return t


def row(title, y):
    return {"type": "row", "title": title, "id": next(_ids), "collapsed": False,
            "panels": [], "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}}


def panel(kind, title, pos, targets, desc="", unit=None, decimals=None,
          minv=None, maxv=None, options=None, defaults=None, ds=PROM):
    d = dict(defaults or {})
    if unit:
        d["unit"] = unit
    if decimals is not None:
        d["decimals"] = decimals
    if minv is not None:
        d["min"] = minv
    if maxv is not None:
        d["max"] = maxv
    p = {"id": next(_ids), "type": kind, "title": title, "description": desc,
         "datasource": ds, "gridPos": dict(zip("xywh", pos)), "targets": targets,
         "fieldConfig": {"defaults": d, "overrides": []}}
    if options:
        p["options"] = options
    return p


GREEN = {"color": {"mode": "fixed", "fixedColor": "green"}}
STAT = {"reduceOptions": {"calcs": ["lastNotNull"]}, "graphMode": "none",
        "colorMode": "value", "textMode": "value"}
BARS = {"reduceOptions": {"calcs": ["lastNotNull"]}, "orientation": "horizontal",
        "displayMode": "gradient", "showUnfilled": True, "valueMode": "color",
        "namePlacement": "left", "text": {"titleSize": 13, "valueSize": 15},
        "minVizHeight": 14, "maxVizHeight": 22}
BLUE_GRAD = {"color": {"mode": "continuous-BlPu"}}


def mean(metric, by=None, window=RI, sel=""):
    """Media de um histograma: soma / contagem na janela."""
    b = f"sum by ({by}) " if by else "sum "
    s = f"{{{sel}}}" if sel else ""
    return (f"{b}(increase({metric}_sum{s}[{window}])) / "
            f"{b}(increase({metric}_count{s}[{window}]))")


panels = []
y = 0

# ---------------------------------------------------------------- Trafego
panels.append(row("Tráfego e tempo de resposta", y)); y += 1
panels += [
    panel("stat", "Mensagens processadas no período", (0, y, 5, 7),
          [q("sum(increase(input_words_count[$__range]))", "mensagens", instant=True)],
          "Cada mensagem passa por TODOS os modelos, então contamos mensagens, não predições.",
          unit="short", decimals=0, options=STAT, defaults=GREEN),
    panel("timeseries", "Mensagens por minuto", (5, y, 7, 7),
          [q(f"sum(rate(input_words_count[{RI}])) * 60", "mensagens/min")],
          "Ritmo de chegada de mensagens na API.", unit="reqpm", decimals=1,
          defaults={"custom": {"lineWidth": 2, "fillOpacity": 15, "showPoints": "auto"}}),
    panel("timeseries", "Para onde vai o tempo de uma requisição (mediana)", (12, y, 12, 7),
          [q('histogram_quantile(0.5, sum by (le) (rate(http_server_duration_milliseconds_bucket'
             f'{{http_target="/predictions"}}[{RI}]))) / 1000',
             "requisição completa (POST /predictions)"),
           q(f"histogram_quantile(0.5, sum by (le, model) (rate(prediction_latency_seconds_bucket{{{M}}}[{RI}])))",
             "só a inferência: {{model}}", ref="B")],
          "Tempo típico (mediana) da requisição inteira comparado ao tempo de cada modelo. "
          "A diferença entre a linha de cima e a soma das inferências é o resto do trabalho "
          "da API, principalmente a gravação no MongoDB.",
          unit="s", minv=0, defaults={"custom": {"lineWidth": 2}}),
]
y += 7

# ---------------------------------------------------------------- Modelos
panels.append(row("Desempenho dos modelos", y)); y += 1
panels += [
    panel("timeseries", "Latência de inferência: típica (p50) e pior caso (p95)", (0, y, 12, 7),
          [q(f"histogram_quantile(0.95, sum by (le, model) (rate(prediction_latency_seconds_bucket{{{M}}}[{RI}])))", "p95 {{model}}"),
           q(f"histogram_quantile(0.50, sum by (le, model) (rate(prediction_latency_seconds_bucket{{{M}}}[{RI}])))", "p50 {{model}}", ref="B")],
          "p50: metade das inferências foi mais rápida que este valor (o caso típico). "
          "p95: 95% foram mais rápidas; só 1 em cada 20 demorou mais (o pior caso frequente).",
          unit="s", minv=0, defaults={"custom": {"lineWidth": 2}}),
    panel("stat", "Erros HTTP (5xx) no período", (12, y, 5, 7),
          [q('(sum(increase(http_server_duration_milliseconds_count{http_status_code=~"5.."}[$__range])) or vector(0)) '
             '/ sum(increase(http_server_duration_milliseconds_count{http_target!=""}[$__range]))', "erros", instant=True)],
          "Fração das requisições que terminaram em erro do servidor. Vazio = nenhum erro.",
          unit="percentunit", decimals=1, options=STAT,
          defaults={"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [
              {"color": "green", "value": None}, {"color": "orange", "value": 0.01}, {"color": "red", "value": 0.05}]}}),
    panel("timeseries", "Requisições por segundo, por rota e status", (17, y, 7, 7),
          [q(f'sum by (http_target, http_status_code) (rate(http_server_duration_milliseconds_count{{http_target!=""}}[{RI}]))',
             "{{http_target}} → {{http_status_code}}")],
          "Métrica automática do FastAPIInstrumentor.", unit="reqps", decimals=2),
]
y += 7

# ---------------------------------------------------------------- Drift
PSI_STEPS = {"mode": "absolute", "steps": [
    {"color": "green", "value": None}, {"color": "orange", "value": 0.1}, {"color": "red", "value": 0.25}]}
FEATURES = ("Variáveis: input_words = comprimento das mensagens (data drift); "
            "predicted_intent = classe prevista e confidence = confiança (prediction drift). ")
WINDOW_DESC = ("Produção = janela das últimas mensagens (DRIFT_WINDOW_SIZE, padrão 200); "
               "referência = predições do mesmo modelo nos conjuntos de data/reference/. "
               "Só é calculado com pelo menos 30 mensagens na janela.")

panels.append(row("Drift: produção × referência", y)); y += 1
panels += [
    panel("stat", "PSI atual", (0, y, 8, 9),
          [q(f"max by (model, feature) (drift_psi{{{M}}})", "{{model}} · {{feature}}", instant=True)],
          "Population Stability Index de cada variável. Regra de bolso: abaixo de 0,1 estável "
          "(verde); de 0,1 a 0,25 mudança moderada (laranja); acima de 0,25 mudança "
          "significativa (vermelho). " + FEATURES + WINDOW_DESC,
          unit="none", decimals=2,
          options={**STAT, "textMode": "value_and_name", "orientation": "horizontal",
                   "colorMode": "background", "text": {"titleSize": 12, "valueSize": 20}},
          defaults={"color": {"mode": "thresholds"}, "thresholds": PSI_STEPS}),
    panel("timeseries", "PSI ao longo do tempo", (8, y, 8, 9),
          [q(f"max by (model, feature) (drift_psi{{{M}}})", "{{model}} · {{feature}}")],
          "Evolução do PSI. As linhas tracejadas horizontais marcam os limites 0,1 e 0,25. "
          "Um drift SÚBITO aparece como um degrau; um GRADUAL, como uma rampa. " + WINDOW_DESC,
          unit="none", decimals=2, minv=0,
          defaults={"custom": {"lineWidth": 2, "thresholdsStyle": {"mode": "dashed"}},
                    "color": {"mode": "palette-classic"}, "thresholds": PSI_STEPS}),
    panel("timeseries", "Teste KS: p-valor", (16, y, 8, 9),
          [q(f"max by (model, feature) (drift_ks_pvalue{{{M}}})", "{{model}} · {{feature}}")],
          "Kolmogorov-Smirnov compara as DISTRIBUIÇÕES inteiras (não só a média) de comprimento "
          "e de confiança. p-valor: chance de ver uma diferença desse tamanho se não houvesse "
          "drift. Abaixo da linha vermelha (0,01) = diferença estatisticamente significativa. "
          "Escala logarítmica: cada linha de grade é 10x menor. " + WINDOW_DESC,
          unit="sci",
          defaults={"custom": {"lineWidth": 2, "thresholdsStyle": {"mode": "dashed"},
                               "scaleDistribution": {"type": "log", "log": 10}},
                    "min": 1e-6, "max": 1, "color": {"mode": "palette-classic"},
                    "thresholds": {"mode": "absolute", "steps": [
                        {"color": "transparent", "value": None}, {"color": "red", "value": 0.01}]}}),
]
y += 9

# ---------------------------------------------------------------- Entrada
REF_STYLE = [{"matcher": {"id": "byRegexp", "options": "^referência.*"},
              "properties": [{"id": "custom.lineStyle", "value": {"fill": "dash", "dash": [10, 6]}},
                             {"id": "custom.fillOpacity", "value": 0}]}]


def compare_bars(title, desc, prod_expr, ref_expr, pos, unit, decimals, maxv=None):
    """Barras produção × referência por classe, repetidas para cada modelo."""
    p = panel("barchart", title, pos,
              [q(prod_expr, instant=True, format="table"),
               q(ref_expr, ref="B", instant=True, format="table")],
              desc, unit=unit, decimals=decimals, minv=0, maxv=maxv,
              options={"xField": "intent", "orientation": "horizontal", "groupWidth": 0.75,
                       "barWidth": 0.9, "showValue": "auto", "xTickLabelRotation": 0,
                       "legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
                       "tooltip": {"mode": "multi"}},
              defaults={"color": {"mode": "palette-classic"}})
    p["transformations"] = [
        {"id": "merge", "options": {}},
        {"id": "organize", "options": {"excludeByName": {"Time": True, "model": True},
                                       "renameByName": {"Value #A": "produção", "Value #B": "referência"}}},
    ]
    p["repeat"], p["repeatDirection"], p["maxPerRow"] = "model", "h", 2
    return p


SEL1 = 'model="$model"'   # dentro de painel repetido: um modelo por painel
REF_DESC = (" A referência é o mesmo modelo rodando, no startup da API, sobre um conjunto "
            "rotulado e balanceado (data/reference/), diferente do treino.")

panels.append(row("Dados de entrada", y)); y += 1
panels += [
    panel("stat", "Comprimento médio das mensagens", (0, y, 5, 8),
          [q(mean("input_words", window="$__range"), "palavras", instant=True)],
          "Média de palavras por mensagem no período.", unit="none", decimals=1,
          options=STAT, defaults=GREEN),
    panel("timeseries", "Comprimento médio: produção × referência", (5, y, 7, 8),
          [q(mean("input_words"), "produção"),
           q(f'max by (model) (reference_input_words_mean{{intent="_all", {M}}})', "referência ({{model}})", ref="B")],
          "Linha cheia: mensagens reais. Tracejadas: média dos conjuntos de referência de "
          "cada modelo. Um afastamento persistente é sinal de data drift na entrada." + REF_DESC,
          unit="none", decimals=1, minv=0, defaults={"custom": {"lineWidth": 2}}),
    panel("bargauge", "Distribuição do comprimento (palavras)", (12, y, 12, 8),
          [q("sum by (le) (increase(input_words_bucket[$__range]))", "{{le}}", instant=True, format="heatmap")],
          "Quantas mensagens caíram em cada faixa de comprimento. O número embaixo é o limite "
          "superior da faixa: '5' = 4 ou 5 palavras; '8' = de 6 a 8 palavras.",
          unit="short", decimals=0, minv=0,
          options={**BARS, "orientation": "vertical", "namePlacement": "auto", "text": {}}, defaults=BLUE_GRAD),
]
panels[-2]["fieldConfig"]["overrides"] = REF_STYLE
y += 8

# ---------------------------------------------------------------- Saida
panels.append(row("Saída dos modelos: produção × referência", y)); y += 1
panels += [
    panel("stat", "Acurácia nos dados de referência", (0, y, 6, 8),
          [q(f"max by (model) (reference_accuracy{{{M}}})", "{{model}}", instant=True)],
          "Acerto do modelo no conjunto de referência rotulado, calculado no startup. "
          "Em produção não há rótulos, então esta é a única acurácia que conseguimos medir "
          "continuamente; as outras comparações abaixo são indícios indiretos." + REF_DESC,
          unit="percentunit", decimals=0,
          options={**STAT, "textMode": "value_and_name", "orientation": "vertical"},
          defaults={"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [
              {"color": "red", "value": None}, {"color": "orange", "value": 0.5}, {"color": "green", "value": 0.7}]}}),
    panel("timeseries", "Confiança média: produção × referência", (6, y, 18, 8),
          [q(mean("prediction_confidence", "model", sel=M), "produção {{model}}"),
           q(f'max by (model) (reference_confidence_mean{{intent="_all", {M}}})', "referência {{model}}", ref="B")],
          "Probabilidade média da classe escolhida. Compare cada modelo com a SUA referência "
          "(tracejada): o nível absoluto varia muito entre modelos (o clair_intents-clf tem "
          "probabilidades achatadas mesmo acertando), mas uma queda em relação à referência "
          "indica que as mensagens estão diferentes do que o modelo conhece." + REF_DESC,
          unit="percentunit", decimals=0, minv=0, maxv=1, defaults={"custom": {"lineWidth": 2}}),
]
panels[-1]["fieldConfig"]["overrides"] = REF_STYLE
y += 8
panels.append(compare_bars(
    "Distribuição das classes previstas · $model",
    "Fração das predições em cada classe. A referência é balanceada nos RÓTULOS, mas as "
    "barras mostram as classes PREVISTAS, então já incluem os erros do modelo. Diferenças "
    "grandes entre produção e referência = prediction drift (ou um público diferente)." + REF_DESC,
    f"sum by (model, intent) (increase(prediction_count_total{{{SEL1}}}[$__range])) "
    f"/ on (model) group_left sum by (model) (increase(prediction_count_total{{{SEL1}}}[$__range]))",
    f"max by (model, intent) (reference_class_share{{{SEL1}}})",
    (0, y, 24, 10), "percentunit", 0, 1))
y += 10
panels.append(compare_bars(
    "Confiança média por classe prevista · $model",
    "Quando o modelo escolhe esta classe, com que certeza escolhe? Classes sem predições "
    "no período aparecem só com a barra de referência." + REF_DESC,
    f"({mean('prediction_confidence', 'model, intent', '$__range', SEL1)}) "
    f"and on (model, intent) sum by (model, intent) (increase(prediction_confidence_count{{{SEL1}}}[$__range])) > 0",
    f'max by (model, intent) (reference_confidence_mean{{{SEL1}, intent!="_all"}})',
    (0, y, 24, 10), "percentunit", 0, 1))
y += 10
panels.append(compare_bars(
    "Comprimento médio por classe prevista · $model",
    "Média de palavras das mensagens que receberam cada classe, em produção e na referência." + REF_DESC,
    f"({mean('prediction_input_words', 'model, intent', '$__range', SEL1)}) "
    f"and on (model, intent) sum by (model, intent) (increase(prediction_input_words_count{{{SEL1}}}[$__range])) > 0",
    f'max by (model, intent) (reference_input_words_mean{{{SEL1}, intent!="_all"}})',
    (0, y, 24, 10), "none", 1))
y += 10

# ---------------------------------------------------------------- Logs
panels.append(row("Logs", y)); y += 1
panels.append(panel("logs", "Últimas predições (Loki)", (0, y, 24, 9),
                    [q('{service_name="intent-clf"} |= "Predicao concluida"', ds=LOKI)],
                    "Clique numa linha para ver o trace_id e abrir o trace no Tempo.",
                    options={"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending",
                             "enableLogDetails": True}, ds=LOKI))

dashboard = {
    "uid": "intent-clf-obs", "title": "Classificador de Intenções · Observabilidade",
    "tags": ["mlops", "intent-clf"], "timezone": "browser", "refresh": "10s",
    "time": {"from": "now-15m", "to": "now"}, "schemaVersion": 41,
    "templating": {"list": [{
        "type": "query", "name": "model", "label": "Modelo", "datasource": PROM,
        "query": {"qryType": 1, "query": "label_values(prediction_count_total, model)",
                  "refId": "PrometheusVariableQueryEditor-VariableQuery"},
        "definition": "label_values(prediction_count_total, model)", "refresh": 2,
        "multi": True, "includeAll": True, "sort": 1,
        "current": {"text": ["All"], "value": ["$__all"]}}]},
    "panels": panels,
}

# ---------------------------------------------------------------- Alertas
PANEL_ID = {p["title"]: p["id"] for p in panels}


def alert(uid, title, expr, op, threshold, summary, description, panel_title):
    return {
        "uid": uid, "title": title, "ruleGroup": "drift", "folderUID": "mlops",
        "condition": "C", "for": "1m", "noDataState": "OK", "execErrState": "Error",
        "labels": {"team": "mlops", "severity": "warning"},
        "annotations": {"summary": summary, "description": description,
                        "__dashboardUid__": "intent-clf-obs",
                        "__panelId__": str(PANEL_ID[panel_title])},
        "data": [
            {"refId": "A", "datasourceUid": "prometheus", "relativeTimeRange": {"from": 300, "to": 0},
             "model": {"refId": "A", "expr": expr, "instant": True, "range": False}},
            {"refId": "B", "datasourceUid": "__expr__",
             "model": {"refId": "B", "type": "reduce", "expression": "A", "reducer": "last"}},
            {"refId": "C", "datasourceUid": "__expr__",
             "model": {"refId": "C", "type": "threshold", "expression": "B",
                       "conditions": [{"evaluator": {"type": op, "params": [threshold]}}]}},
        ],
    }


alerts = [
    alert("drift-psi", "Drift: PSI acima de 0,25",
          "max by (model, feature) (drift_psi)", "gt", 0.25,
          "PSI de {{ $labels.feature }} em {{ $labels.model }} = {{ humanize $values.B.Value }}",
          "A distribuição de produção se afastou da referência (PSI > 0,25 por 1 minuto). "
          "input_words = data drift na entrada; predicted_intent e confidence = prediction drift.",
          "PSI ao longo do tempo"),
    alert("drift-ks", "Drift: teste KS significativo (p < 0,01)",
          "max by (model, feature) (drift_ks_pvalue)", "lt", 0.01,
          "KS de {{ $labels.feature }} em {{ $labels.model }}: p = {{ humanize $values.B.Value }}",
          "As distribuições de produção e referência diferem com p-valor abaixo de 0,01 por 1 minuto.",
          "Teste KS: p-valor"),
]
Path(__file__).with_name("alert-rules.json").write_text(
    json.dumps(alerts, ensure_ascii=False, indent=2), encoding="utf-8")

out = Path(__file__).with_name("intent-clf-obs.json")
out.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{out} ({len(panels)} itens)")
