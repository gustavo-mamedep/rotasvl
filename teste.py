from controlerotas import database, app
from controlerotas.models import Usuario

with app.app_context():
    # Verifica se já existe usuário no banco
    if Usuario.query.first():
        print("Já existe pelo menos um usuário cadastrado.")
    else:
        # Crie o usuário manualmente aqui:
        novo_usuario = Usuario(
            usuario='admin',
            senha='123456',  # Atenção: armazene senhas com hash na prática!
            tipo='admin'     # Ou o tipo que você queira
        )
        database.session.add(novo_usuario)
        database.session.commit()
        print("Usuário admin criado com sucesso!")