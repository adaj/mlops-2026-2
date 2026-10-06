

router = FastAPI()


@router.get("/dados/{id}", response_model=Dados)
def get_dados():
    dados = banco_de_dados.get(id)
    return dados


@router.post("/dados" )
def create_dados(dados: Dados):
    # Lógica para criar dados no banco de dados
    return {"message": "Dados criados com sucesso", "dados": dados}
    