# MLOps 2026.2 - API de Classificação de Intenções

API em FastAPI que classifica a intenção de uma mensagem usando um ou mais
modelos treinados e versionados no [Weights & Biases](https://wandb.ai) (W&B).

## Pré-requisitos

- [Conda](https://docs.conda.io/en/latest/miniconda.html) (Miniconda ou Anaconda)
- Git
- Uma conta no [W&B](https://wandb.ai) com acesso aos modelos usados na aula

## 1. Instalar

```bash
git clone https://github.com/adaj/mlops-2026-2.git
cd mlops-2026-2

conda create -n mlops-2026-2 python=3.11
conda activate mlops-2026-2
pip install -r requirements.txt
```

A instalação demora alguns minutos, principalmente por causa do TensorFlow.

## 2. Configurar as variáveis de ambiente

Copie o arquivo de exemplo e preencha os valores:

```bash
cp .env.example .env
```

| Variável | O que é |
| --- | --- |
| `WANDB_API_KEY` | Sua chave pessoal do W&B. Pegue em <https://wandb.ai/authorize> |
| `WANDB_MODELS` | Os modelos que a API vai carregar, separados por vírgula |

Cada modelo em `WANDB_MODELS` é o nome completo do artefato no W&B, no formato
`entidade/projeto/artefato:versao`. Exemplo com dois modelos:

```bash
WANDB_MODELS=entidade/projeto/confusion-clf:v1,entidade/projeto/clair-intents:v3
```

> O arquivo `.env` contém a sua chave e **nunca deve ser commitado**. Ele já está
> no `.gitignore`. Só o `.env.example` (sem valores reais) vai para o git.

## 3. Rodar a API

Na **raiz** do projeto (a pasta que contém `src/`), com o ambiente ativado:

```bash
uvicorn src.app:app --port 8000
```

Na primeira execução, os modelos são baixados do W&B, então a subida demora.
Quando aparecer `Application startup complete`, a API está pronta.

Para usar outra porta, troque o número (ex.: `--port 8001`). Outras opções úteis:

| Opção | Para que serve |
| --- | --- |
| `--port 8001` | usar outra porta |
| `--host 0.0.0.0` | aceitar conexões de outras máquinas da rede |
| `--log-level debug` | mais detalhes no terminal |

> Evite `--reload` aqui: ele recarregaria os modelos a cada arquivo salvo.

## 4. Testar

Abra o Swagger no navegador: <http://localhost:8000/docs>

1. Clique em `POST /intent-classifier/predictions`.
2. Clique em **Try it out**. O corpo já vem preenchido com um exemplo.
3. Clique em **Execute** e veja a resposta, com o resultado de cada modelo.

Ou pelo terminal:

```bash
curl -X POST http://localhost:8000/intent-classifier/predictions \
  -H "Content-Type: application/json" \
  -d '{"text": "Não entendi como resolver esse exercício", "nome": "Maria"}'
```

Exemplo de resposta (resumida):

```json
{
  "mensagem": {"text": "Não entendi como resolver esse exercício", "nome": "Maria", "...": "..."},
  "resultados": {
    "confusion-clf:v1": {"top_intent": "confusion", "probs": {"confusion": 0.91, "...": 0.09}},
    "clair-intents:v3": {"top_intent": "help_request", "probs": {"...": 0.7}}
  },
  "created_at": "2026-10-08T14:30:02Z"
}
```
