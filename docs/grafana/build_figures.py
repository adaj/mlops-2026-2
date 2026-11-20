"""Gera docs/grafana/apostila-figuras.json: o dashboard usado para as figuras da apostila.

Cada painel responde a uma figura do capitulo, com series filtradas, cores fixas
e legendas no vocabulario do texto. Os instantes do experimento ficam em T0/T1/T2
(epoch, segundos): inicio da fase estavel, inicio do portugues e fim.

Uso:
    python docs/grafana/build_figures.py --t0 1795150467 --t1 1795150708 --t2 1795150948
Depois publique com apply.py (ou importe o JSON no Grafana) e capture cada painel
pela URL /d-solo/apostila-figuras?panelId=<id>&theme=light (from/to em ISO 8601),
num painel de ~600 px CSS de largura: a fonte fica legivel quando a figura entra no documento
com 432 pt (largura em px ~ 1,35 x largura em pt).
"""
import argparse
import json
from pathlib import Path

PROM = {"type": "prometheus", "uid": "prometheus"}

# Paleta fixa (a mesma em todas as figuras)
PETROLEO, PETROLEO_CLARO = "#0E7C7B", "#8FD1CF"
AZUL, AZUL_CLARO = "#1F60C4", "#9DC3F7"
ROXO = "#8F3BB8"
CINZA_CTX, CINZA_REF = "#BDBDBD", "#8A8A8A"
VERMELHO, LARANJA, VERDE = "#C4162A", "#FF9830", "#56A64B"

M3, M7 = "confusion-clf", "clair_intents-clf"
NOME = {M3: "3 classes", M7: "7 classes"}
VAR = {"input_words": "comprimento", "predicted_intent": "classe prevista", "confidence": "confiança"}


def q(expr, legend=None, ref="A", instant=False, table=False, **kw):
    t = {"refId": ref, "datasource": PROM, "expr": expr}
    if legend:
        t["legendFormat"] = legend
    if instant:
        t.update(instant=True, range=False)
    if table:
        t["format"] = "table"
    t.update(kw)
    return t


def cor(nome, c, largura=None, legenda=True, tracejado=False):
    props = [{"id": "color", "value": {"mode": "fixed", "fixedColor": c}}]
    if largura:
        props.append({"id": "custom.lineWidth", "value": largura})
    if not legenda:
        props.append({"id": "custom.hideFrom", "value": {"legend": True, "tooltip": False, "viz": False}})
    if tracejado:
        props.append({"id": "custom.lineStyle", "value": {"fill": "dash", "dash": [10, 6]}})
    return {"matcher": {"id": "byName", "options": nome}, "properties": props}


def limiar(*passos):
    """passos = (valor, cor); a base fica transparente."""
    return {"mode": "absolute",
            "steps": [{"color": "transparent", "value": None}] + [{"color": c, "value": v} for v, c in passos]}


def serie_tempo(pid, titulo, targets, overrides, pos, minv=None, maxv=None, log=False,
                limiares=None, legenda=True, unit="none", decimals=None):
    custom = {"lineWidth": 3, "fillOpacity": 0, "showPoints": "never", "spanNulls": True,
              "thresholdsStyle": {"mode": "dashed" if limiares else "off"}}
    if log:
        custom["scaleDistribution"] = {"type": "log", "log": 10}
    d = {"custom": custom, "unit": unit, "color": {"mode": "fixed", "fixedColor": CINZA_CTX}}
    if limiares:
        d["thresholds"] = limiares
    if minv is not None:
        d["min"] = minv
    if maxv is not None:
        d["max"] = maxv
    if decimals is not None:
        d["decimals"] = decimals
    return {"id": pid, "type": "timeseries", "title": titulo, "datasource": PROM,
            "gridPos": dict(zip("xywh", pos)), "targets": targets, "interval": "15s",
            "fieldConfig": {"defaults": d, "overrides": overrides},
            "options": {"legend": {"showLegend": legenda, "displayMode": "list", "placement": "bottom"},
                        "tooltip": {"mode": "none"}}}


def psi(model, feature):
    return f'max(drift_psi{{model="{model}", feature="{feature}"}})'


def build(t0, t1, t2, tz="browser"):
    panels = []

    # F5: PSI atual, um stat por modelo
    for pid, model, x in ((1, M3, 0), (2, M7, 6)):
        panels.append({
            "id": pid, "type": "stat", "title": f"Modelo de {NOME[model]}", "datasource": PROM,
            "gridPos": {"x": x, "y": 0, "w": 6, "h": 8},
            "targets": [q(psi(model, f), VAR[f], ref=r, instant=True)
                        for r, f in zip("ABC", VAR)],
            "fieldConfig": {"defaults": {
                "unit": "none", "decimals": 2, "color": {"mode": "thresholds"},
                "thresholds": {"mode": "absolute", "steps": [
                    {"color": VERDE, "value": None}, {"color": LARANJA, "value": 0.1},
                    {"color": VERMELHO, "value": 0.25}]}}, "overrides": []},
            "options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "orientation": "horizontal",
                        "textMode": "value_and_name", "colorMode": "background_solid",
                        "graphMode": "none", "justifyMode": "auto", "wideLayout": True,
                        "text": {"titleSize": 15, "valueSize": 26}}})

    # F6: PSI ao longo do tempo
    panels.append(serie_tempo(
        3, "PSI ao longo do tempo",
        [q(psi(M3, "input_words"), "comprimento", "A"),
         q(psi(M7, "predicted_intent"), "7 classes · classe prevista", "B"),
         q(psi(M3, "predicted_intent"), "3 classes · classe prevista", "C"),
         q(psi(M3, "confidence"), "3 classes · confiança", "D"),
         q(psi(M7, "confidence"), "7 classes · confiança", "E")],
        [cor("comprimento", PETROLEO, 3), cor("7 classes · classe prevista", AZUL, 3)]
        + [cor(n, CINZA_CTX, 1.5, legenda=False)
           for n in ("3 classes · classe prevista", "3 classes · confiança", "7 classes · confiança")],
        (0, 8, 12, 8), minv=0, maxv=4, limiares=limiar((0.25, VERMELHO)), decimals=1))

    # F7: p-valor do KS
    pv = lambda m, f: f'max(drift_ks_pvalue{{model="{m}", feature="{f}"}})'
    panels.append(serie_tempo(
        4, "Teste KS: p-valor",
        [q(pv(M3, "input_words"), "comprimento", "A"),
         q(pv(M3, "confidence"), "3 classes · confiança", "B"),
         q(pv(M7, "confidence"), "7 classes · confiança", "C")],
        [cor("comprimento", PETROLEO, 3), cor("3 classes · confiança", ROXO, 3),
         cor("7 classes · confiança", AZUL, 3)],
        (0, 16, 12, 8), minv=1e-10, maxv=1, log=True, limiares=limiar((0.01, VERMELHO)), unit="sci"))

    # F8: confianca do 7 classes, PSI x D
    d_crit = 1.628 * ((200 + 150) / (200 * 150)) ** 0.5   # D a partir do qual p < 0,01
    panels.append(serie_tempo(
        5, "7 classes · confiança: PSI", [q(psi(M7, "confidence"), "PSI", "A")],
        [cor("PSI", AZUL, 3)], (0, 24, 12, 5), minv=0, maxv=1,
        limiares=limiar((0.1, LARANJA), (0.25, VERMELHO)), legenda=False, decimals=1))
    panels.append(serie_tempo(
        6, "7 classes · confiança: D do KS",
        [q(f'max(drift_ks_statistic{{model="{M7}", feature="confidence"}})', "D", "A")],
        [cor("D", AZUL, 3)], (0, 29, 12, 5), minv=0, maxv=1,
        limiares=limiar((round(d_crit, 3), CINZA_REF)), legenda=False, decimals=1))

    # F9: faixas de comprimento (referencia x fim da fase estavel x fim do portugues)
    les = ["1", "2", "3", "5", "8", "13", "21", "34"]
    nomes = ["1", "2", "3", "4–5", "6–8", "9–13", "14–21", "22–34"]

    def faixas_prod(t):
        inc = lambda le: f'sum(increase(input_words_bucket{{le="{le}"}}[3m] @ {t}))'
        tot = f'sum(increase(input_words_count[3m] @ {t}))'
        partes, ant = [], None
        for i, (le, nome) in enumerate(zip(les, nomes)):
            num = inc(le) if ant is None else f"({inc(le)} - {inc(ant)})"
            partes.append(f'label_replace(label_replace({num} / {tot}, "faixa", "{nome}", "", ""), '
                          f'"ordem", "{i + 1:02d}", "", "")')
            ant = le
        return " or ".join(partes)   # 35+ fica de fora: vazia nos tres conjuntos

    ref_partes = []
    for i, (le, nome) in enumerate(zip(les, nomes)):
        ref_partes.append(
            f'label_replace(label_replace(max(reference_input_words_bucket_share{{model="{M3}", le="{le}"}}), '
            f'"faixa", "{nome}", "", ""), "ordem", "{i + 1:02d}", "", "")')

    panels.append(barras(
        7, "Comprimento das mensagens por faixa",
        [q(" or ".join(ref_partes), ref="A", instant=True, table=True),
         q(faixas_prod(t1), ref="B", instant=True, table=True),
         q(faixas_prod(t2), ref="C", instant=True, table=True)],
        "faixa", ["ordem"], (0, 34, 12, 9), "vertical",
        [("referência", CINZA_REF), ("fase estável", PETROLEO_CLARO), ("fase em português", PETROLEO)],
        show_value="never", maxv=0.6, decimais=None))

    # F10: classes previstas pelo modelo de 7 classes
    def classes(t):
        return (f'sum by (intent) (increase(prediction_count_total{{model="{M7}", intent!="ping"}}[3m] @ {t})) '
                f'/ scalar(sum(increase(prediction_count_total{{model="{M7}"}}[3m] @ {t})))')

    panels.append(barras(
        8, "Classes previstas · modelo de 7 classes",
        [q(f'max by (intent) (reference_class_share{{model="{M7}", intent!="ping"}})', ref="A",
           instant=True, table=True),
         q(classes(t1), ref="B", instant=True, table=True),
         q(classes(t2), ref="C", instant=True, table=True)],
        "intent", [], (0, 43, 12, 11), "horizontal",
        [("referência", CINZA_REF), ("fase estável", AZUL_CLARO), ("fase em português", AZUL)],
        show_value="always", sort_by="referência", maxv=1, eixo_valores=False, value_size=15))

    # F11: estados de cada instancia do alerta, reconstruidos a partir do PSI
    alvo = []
    # Reconstroi a regra (avaliada a cada 30 s, "for 1m"): 0 = Normal; 1 = acima do limiar, mas
    # ainda sem 3 avaliacoes seguidas (Pending); 2 = acima nas ultimas 3 avaliacoes (Firing).
    # Os subqueries de 30 s ficam alinhados aos instantes :00/:30, como as avaliacoes do Grafana.
    for i, (m, f) in enumerate([(m, f) for m in (M3, M7) for f in VAR]):
        x = f"({psi(m, f)} > bool 0.25)"
        expr = (f"{x} + (min_over_time({x}[61s:30s]) * "
                f"(count_over_time({x}[61s:30s]) >= bool 3))")
        alvo.append(q(expr, f"{NOME[m]} · {VAR[f]}", "ABCDEF"[i], interval="30s"))
    panels.append({
        "id": 9, "type": "state-timeline", "title": "Alerta PSI > 0,25: estado de cada instância",
        "datasource": PROM, "gridPos": {"x": 0, "y": 54, "w": 12, "h": 8}, "targets": alvo,
        "interval": "30s",
        "fieldConfig": {"defaults": {
            # cor fixa + cores nos mapeamentos: assim a legenda mostra Normal/Pending/Firing
            "color": {"mode": "fixed", "fixedColor": "#D9D9D9"},
            "thresholds": {"mode": "absolute", "steps": [
                {"color": "#D9D9D9", "value": None}, {"color": LARANJA, "value": 1},
                {"color": VERMELHO, "value": 2}]},
            "mappings": [{"type": "value", "options": {
                "0": {"text": "Normal", "color": "#D9D9D9", "index": 0},
                "1": {"text": "Pending", "color": LARANJA, "index": 1},
                "2": {"text": "Firing", "color": VERMELHO, "index": 2}}}],
            "custom": {"lineWidth": 0, "fillOpacity": 90}}, "overrides": []},
        "options": {"mergeValues": True, "showValue": "never", "rowHeight": 0.8, "alignValue": "left",
                    "legend": {"showLegend": True, "displayMode": "list", "placement": "bottom"},
                    "tooltip": {"mode": "none"}}})

    return {
        "uid": "apostila-figuras", "title": "Apostila · figuras do drift",
        "tags": ["apostila"], "timezone": tz, "editable": True, "schemaVersion": 39,
        "time": {"from": str((t0 - 30) * 1000), "to": str((t2 + 120) * 1000)},
        "annotations": {"list": [
            {"builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"}, "enable": False,
             "hide": True, "iconColor": "rgba(0, 211, 255, 1)", "name": "Annotations & Alerts",
             "type": "dashboard"},
            {"datasource": {"type": "grafana", "uid": "-- Grafana --"}, "enable": True,
             "iconColor": "rgba(150, 150, 150, 0.35)", "name": "fase",
             "target": {"type": "tags", "tags": ["fase"], "limit": 10, "matchAny": True}}]},
        "panels": panels,
    }


def barras(pid, titulo, targets, campo, ocultos, pos, orientacao, series, show_value, sort_by=None,
           maxv=None, decimais=0, eixo_valores=True, value_size=12):
    renomear = {f"Value #{r}": n for r, (n, _) in zip("ABC", series)}
    excluir = {"Time": True, **{c: True for c in ocultos}}
    transf = [{"id": "merge", "options": {}}]
    if ocultos:
        transf.append({"id": "sortBy", "options": {"sort": [{"field": ocultos[0]}]}})
    transf.append({"id": "organize", "options": {
        "excludeByName": excluir, "renameByName": {campo: " ", **renomear},
        "indexByName": {campo: 0, **{n: i + 1 for i, (n, _) in enumerate(series)}}}})
    if sort_by:
        transf.append({"id": "sortBy", "options": {"sort": [{"field": sort_by, "desc": True}]}})
    return {
        "id": pid, "type": "barchart", "title": titulo, "datasource": PROM,
        "gridPos": dict(zip("xywh", pos)), "targets": targets, "transformations": transf,
        "fieldConfig": {"defaults": dict(
                            {"unit": "percentunit", "min": 0, "max": maxv,
                             "custom": {"fillOpacity": 90, "lineWidth": 0,
                                        "axisPlacement": "auto" if eixo_valores else "hidden"}},
                            **({"decimals": decimais} if decimais is not None else {})),
                        # o campo das categorias nao herda a unidade (senao "1" vira "100%")
                        "overrides": [cor(n, c) for n, c in series] + [
                            {"matcher": {"id": "byName", "options": " "},
                             "properties": [{"id": "unit", "value": "none"},
                                            {"id": "custom.axisPlacement", "value": "auto"}]}]},
        "options": {"xField": " ", "orientation": orientacao, "groupWidth": 0.85, "barWidth": 0.9,
                    "showValue": show_value, "text": {"valueSize": value_size}, "xTickLabelRotation": 0,
                    "legend": {"showLegend": True, "displayMode": "list", "placement": "bottom"},
                    "tooltip": {"mode": "none"}}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--t0", type=int, required=True, help="inicio da fase estavel (epoch, s)")
    ap.add_argument("--t1", type=int, required=True, help="inicio do portugues (epoch, s)")
    ap.add_argument("--t2", type=int, required=True, help="fim do experimento (epoch, s)")
    ap.add_argument("--tz", default="browser",
                    help="fuso exibido nos eixos (ex.: Asia/Bangkok); so muda a exibicao do horario")
    a = ap.parse_args()
    out = Path(__file__).with_name("apostila-figuras.json")
    out.write_text(json.dumps(build(a.t0, a.t1, a.t2, a.tz), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"gerado: {out}")
