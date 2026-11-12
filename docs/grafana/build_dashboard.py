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

# ---------------------------------------------------------------- Entrada
panels.append(row("Dados de entrada", y)); y += 1
panels += [
    panel("stat", "Comprimento médio das mensagens", (0, y, 5, 8),
          [q(mean("input_words", window="$__range"), "palavras", instant=True)],
          "Média de palavras por mensagem no período.", unit="none", decimals=1,
          options=STAT, defaults=GREEN),
    panel("timeseries", "Comprimento médio ao longo do tempo", (5, y, 7, 8),
          [q(mean("input_words"), "palavras por mensagem")],
          "Uma mudança persistente aqui é um sinal de data drift na entrada.",
          unit="none", decimals=1, minv=0, defaults={"custom": {"lineWidth": 2}}),
    panel("bargauge", "Distribuição do comprimento (palavras)", (12, y, 12, 8),
          [q("sum by (le) (increase(input_words_bucket[$__range]))", "{{le}}", instant=True, format="heatmap")],
          "Quantas mensagens caíram em cada faixa de comprimento. O número embaixo é o limite "
          "superior da faixa: '5' = 4 ou 5 palavras; '8' = de 6 a 8 palavras.",
          unit="short", decimals=0, minv=0,
          options={**BARS, "orientation": "vertical", "namePlacement": "auto", "text": {}}, defaults=BLUE_GRAD),
]
y += 8
panels += [
    panel("bargauge", "Comprimento médio por classe prevista", (0, y, 24, 7),
          [q(f"({mean('prediction_input_words', 'model, intent', '$__range', M)}) "
             f"and on (model, intent) sum by (model, intent) (increase(prediction_input_words_count{{{M}}}[$__range])) > 0",
             "{{model}} · {{intent}}", instant=True)],
          "Média de palavras das mensagens que receberam cada classe. Classes sem nenhuma "
          "predição no período não aparecem.",
          unit="none", decimals=1, minv=0, options=BARS, defaults=BLUE_GRAD),
]
y += 7

# ---------------------------------------------------------------- Saida
panels.append(row("Saída dos modelos", y)); y += 1
panels += [
    panel("bargauge", "Distribuição das classes previstas", (0, y, 8, 11),
          [q(f"sum by (model, intent) (increase(prediction_count_total{{{M}}}[$__range]))",
             "{{model}} · {{intent}}", instant=True)],
          "Quantas vezes cada classe foi prevista no período. Comparar esta 'foto' entre "
          "períodos é a forma mais simples de detectar prediction drift.",
          unit="short", decimals=0, minv=0, options=BARS, defaults=BLUE_GRAD),
    panel("timeseries", "Confiança média por modelo", (8, y, 8, 11),
          [q(mean("prediction_confidence", "model", sel=M), "{{model}}")],
          "Probabilidade média da classe escolhida. Referência do 'chute': 1 / número de "
          "classes (3 classes = 33%; 7 classes = 14%). Quanto mais perto disso, menos o "
          "modelo está discriminando.",
          unit="percentunit", decimals=0, minv=0, maxv=1, defaults={"custom": {"lineWidth": 2}}),
    panel("stat", "Predições com baixa confiança (≤ 50%)", (16, y, 8, 11),
          [q(f'sum by (model) (increase(prediction_confidence_bucket{{{M}, le="0.5"}}[$__range])) '
             f"/ sum by (model) (increase(prediction_confidence_count{{{M}}}[$__range]))", "{{model}}", instant=True)],
          "Fração das predições em que a classe escolhida tinha probabilidade de 50% ou menos.",
          unit="percentunit", decimals=0, options={**STAT, "textMode": "value_and_name", "orientation": "vertical"},
          defaults={"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [
              {"color": "green", "value": None}, {"color": "orange", "value": 0.25}, {"color": "red", "value": 0.5}]}}),
]
y += 11
panels += [
    panel("bargauge", "Confiança média por classe prevista", (0, y, 12, 9),
          [q(f"({mean('prediction_confidence', 'model, intent', '$__range', M)}) "
             f"and on (model, intent) sum by (model, intent) (increase(prediction_confidence_count{{{M}}}[$__range])) > 0",
             "{{model}} · {{intent}}", instant=True)],
          "Quando o modelo escolhe esta classe, com que certeza ele escolhe?",
          unit="percentunit", decimals=0, minv=0, maxv=1, options=BARS, defaults=BLUE_GRAD),
    panel("bargauge", "Margem média entre 1ª e 2ª classe", (12, y, 12, 9),
          [q(f"({mean('prediction_margin', 'model, intent', '$__range', M)}) "
             f"and on (model, intent) sum by (model, intent) (increase(prediction_margin_count{{{M}}}[$__range])) > 0",
             "{{model}} · {{intent}}", instant=True)],
          "Diferença de probabilidade entre a classe escolhida e a segunda colocada. Perto "
          "de 0: o modelo ficou dividido entre duas classes.",
          unit="percentunit", decimals=0, minv=0, maxv=1, options=BARS, defaults=BLUE_GRAD),
]
y += 9

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

out = Path(__file__).with_name("intent-clf-obs.json")
out.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{out} ({len(panels)} itens)")
