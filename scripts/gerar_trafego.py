"""Gera trafego para a API, em cenarios com e sem drift, para o Grafana ter o que mostrar.

Cenarios (--cenario):
  estavel    mensagens do mesmo "mundo" da referencia: exemplos dos dados de
             TREINO (ingles, chat com a Clair), sorteando por igual entre as
             classes, como os conjuntos de referencia. Esperado: PSI baixo.
  portugues  mensagens de alunos em portugues, que o modelo nunca viu.
             Drift SUBITO quando se troca de "estavel" para "portugues".
  gradual    comeca 100% estavel e termina 100% em portugues ao longo de
             --duracao: drift GRADUAL.

Uso:
    python scripts/gerar_trafego.py --cenario estavel --duracao 300
    python scripts/gerar_trafego.py --cenario portugues --duracao 300
    python scripts/gerar_trafego.py --cenario gradual --duracao 600 --intervalo 0.3

Precisa de PyYAML (ja esta no requirements.txt).
"""
import argparse
import json
import random
import time
import urllib.request
from pathlib import Path

import yaml

TRAIN_DIR = Path(__file__).resolve().parent.parent / "src/modules/intent_classifier/data/train"

PORTUGUES = [
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


def carregar_estavel():
    """{(arquivo, classe): [exemplos]} dos dados de treino."""
    grupos = {}
    for arquivo in sorted(TRAIN_DIR.glob("*_examples.yml")):
        for item in yaml.safe_load(arquivo.read_text(encoding="utf-8")):
            grupos[(arquivo.stem, item["intent"])] = [str(e) for e in item["examples"]]
    return grupos


def sortear(cenario, progresso, grupos):
    """Escolhe uma mensagem. progresso vai de 0 (inicio) a 1 (fim)."""
    p_portugues = {"estavel": 0.0, "portugues": 1.0, "gradual": progresso}[cenario]
    if random.random() < p_portugues:
        return random.choice(PORTUGUES)
    # sorteia primeiro a classe (todas com a mesma chance), depois o exemplo
    return random.choice(grupos[random.choice(list(grupos))])


def enviar(url, texto):
    corpo = json.dumps({"nome": "gerador", "text": texto}).encode()
    req = urllib.request.Request(f"{url}/predictions", data=corpo,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.status


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cenario", choices=["estavel", "portugues", "gradual"], default="estavel")
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--duracao", type=float, default=300, help="segundos (padrao: 300)")
    ap.add_argument("--intervalo", type=float, default=0.5,
                    help="pausa media entre mensagens, em segundos (padrao: 0.5)")
    args = ap.parse_args()

    grupos = carregar_estavel()
    inicio = time.time()
    fim = inicio + args.duracao
    ok = erros = 0
    print(f"cenario={args.cenario}, {len(grupos)} classes de referencia, duracao={args.duracao:.0f}s")
    while time.time() < fim:
        progresso = (time.time() - inicio) / args.duracao
        try:
            enviar(args.url, sortear(args.cenario, progresso, grupos))
            ok += 1
        except Exception as e:  # noqa: BLE001 - so contamos e seguimos
            erros += 1
            print(f"erro: {e}")
        if (ok + erros) % 20 == 0:
            print(f"[{progresso:4.0%}] {ok} enviadas, {erros} erros")
        # pausa aleatoria em torno do intervalo: trafego menos "robotico"
        time.sleep(random.uniform(0.5, 1.5) * args.intervalo)
    print(f"fim: {ok} enviadas, {erros} erros")


if __name__ == "__main__":
    main()
