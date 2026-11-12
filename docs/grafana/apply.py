"""Publica no Grafana o dashboard e as regras de alerta deste diretorio.

Uso (com a stack rodando):
    python docs/grafana/build_dashboard.py      # (re)gera os JSON
    python docs/grafana/apply.py                # publica em http://localhost:3000

Como o container lgtm nao guarda dados entre recriacoes, rode este script
sempre que subir a stack do zero. So usa a biblioteca padrao do Python.
"""
import argparse
import base64
import json
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent


def call(base, auth, method, path, body=None, extra_headers=None):
    req = urllib.request.Request(base + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    req.add_header("Content-Type", "application/json")
    for k, v in (extra_headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default="http://localhost:3000")
    ap.add_argument("--user", default="admin")
    ap.add_argument("--password", default="admin")
    args = ap.parse_args()
    base, auth = args.url.rstrip("/"), f"{args.user}:{args.password}"
    # editavel na interface (sem isso, regras criadas pela API ficam somente leitura)
    editable = {"X-Disable-Provenance": "true"}

    dashboard = json.loads((HERE / "intent-clf-obs.json").read_text(encoding="utf-8"))
    st, r = call(base, auth, "POST", "/api/dashboards/db",
                 {"dashboard": dashboard, "overwrite": True, "message": "apply.py"})
    print("dashboard:", st, r.get("url") if isinstance(r, dict) else r)

    st, r = call(base, auth, "POST", "/api/folders", {"uid": "mlops", "title": "MLOps"})
    print("pasta MLOps:", st if st in (200, 409, 412) else (st, r))

    for rule in json.loads((HERE / "alert-rules.json").read_text(encoding="utf-8")):
        st, r = call(base, auth, "PUT", f"/api/v1/provisioning/alert-rules/{rule['uid']}", rule, editable)
        if st == 404:   # ainda nao existe: cria
            st, r = call(base, auth, "POST", "/api/v1/provisioning/alert-rules", rule, editable)
        print(f"alerta {rule['uid']}:", st, "" if st in (200, 201) else r)

    # avalia o grupo a cada 30 s (o PUT exige o grupo inteiro, entao lemos antes)
    st, group = call(base, auth, "GET", "/api/v1/provisioning/folder/mlops/rule-groups/drift")
    if st == 200:
        group["interval"] = 30
        st, r = call(base, auth, "PUT", "/api/v1/provisioning/folder/mlops/rule-groups/drift",
                     group, editable)
    print("grupo drift (avaliar a cada 30 s):", st, "" if st == 200 else r)


if __name__ == "__main__":
    main()
