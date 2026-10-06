

class Banco:
    def __init__(self, nome: str, host: str, porta: int, usuario: str, senha: str):
        self.nome = nome
        self.host = host
        self.porta = porta
        self.usuario = usuario
        self.senha = senha

    def __str__(self):
        return f"Banco(nome={self.nome}, host={self.host}, porta={self.porta}, usuario={self.usuario})"

    def get():
        # Lógica para obter dados do banco de dados
        pass