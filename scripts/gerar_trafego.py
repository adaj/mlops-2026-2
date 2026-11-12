"""Gera trafego continuo para a API, para os graficos do Grafana terem o que mostrar.

Uso:
    python scripts/gerar_trafego.py                     # 5 min, ~2 mensagens/s
    python scripts/gerar_trafego.py --duracao 60 --intervalo 0.2
    python scripts/gerar_trafego.py --url http://localhost:8000

So usa a biblioteca padrao do Python (nao precisa instalar nada).
"""
import argparse
import json
import random
import time
import urllib.request

# Mensagens de chat de alunos, de tamanhos variados (1 a ~30 palavras)
MENSAGENS = [
    "oi", "ok", "?", "valeu", "oi, tudo bem?", "quem é você?",
    "não entendi nada", "pode repetir?", "agora ficou claro, obrigado",
    "tenho certeza que a resposta é 42", "qual é o prazo da entrega do trabalho?",
    "me ajuda com o exercício 3 da lista de cinemática",
    "não quero responder isso agora", "concordo com o que você falou",
    "isso não faz sentido pra mim",
    "beleza, entendi a ideia geral mas ainda tenho dúvida no gráfico de posição por tempo",
    "professor, eu tentei resolver a questão da velocidade média mas não consegui "
    "entender por que o tempo total entra no denominador",
    "acho que a gente precisa revisar a parte de aceleração antes de seguir, porque eu "
    "e meu colega chegamos em respostas diferentes e nenhum dos dois sabe qual está certa",
]


def enviar(url, texto):
    corpo = json.dumps({"nome": "gerador", "text": texto}).encode()
    req = urllib.request.Request(f"{url}/predictions", data=corpo,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--duracao", type=float, default=300, help="segundos (padrao: 300)")
    ap.add_argument("--intervalo", type=float, default=0.5,
                    help="pausa media entre mensagens, em segundos (padrao: 0.5)")
    args = ap.parse_args()

    fim = time.time() + args.duracao
    ok = erros = 0
    while time.time() < fim:
        try:
            enviar(args.url, random.choice(MENSAGENS))
            ok += 1
        except Exception as e:  # noqa: BLE001 - so contamos e seguimos
            erros += 1
            print(f"erro: {e}")
        if (ok + erros) % 20 == 0:
            print(f"{ok} enviadas, {erros} erros")
        # pausa aleatoria em torno do intervalo: trafego menos "robotico"
        time.sleep(random.uniform(0.5, 1.5) * args.intervalo)
    print(f"fim: {ok} enviadas, {erros} erros")


if __name__ == "__main__":
    main()
