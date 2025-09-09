from controlerotas import database
from datetime import datetime


class Usuario(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    usuario = database.Column(database.String, nullable=False, unique=True)
    senha = database.Column(database.String, nullable=False)
    tipo = database.Column(database.String, nullable=False)


class Servico(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    bairro = database.Column(database.String, nullable=False)
    servico = database.Column(database.String, nullable=False)
    documento = database.Column(database.String, nullable=False)
    prestador = database.Column(database.String, nullable=False)
    taxa = database.Column(database.Boolean, nullable=False)
    cartao = database.Column(database.Boolean, nullable=False)
    valor = database.Column(database.Float, nullable=False)
    obs = database.Column(database.Text, nullable=False)
    data_criacao = database.Column(database.DateTime, nullable=False, default=datetime.utcnow)
    status = database.Column(database.String, nullable=False, default='Cadastrado')
    data_em_rota = database.Column(database.DateTime, nullable=True)
    data_finalizado = database.Column(database.DateTime, nullable=True)
    data_cancelado = database.Column(database.DateTime, nullable=True)
    ordem_rota = database.Column(database.Integer, nullable=True)

    cep = database.Column(database.String, nullable=True)
    rua = database.Column(database.String, nullable=True)
    numero = database.Column(database.Integer, nullable=True)
    bairro2 = database.Column(database.String, nullable=True)
    cidade = database.Column(database.String, nullable=True)
    estado = database.Column(database.String, nullable=True)
    complemento = database.Column(database.String, nullable=True)

    id_usuario = database.Column(database.Integer, database.ForeignKey('usuario.id'), nullable=False)
    usuario = database.relationship('Usuario', backref='servicos')

class Bairros(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    nome = database.Column(database.String, nullable=False, unique=True)
    valor = database.Column(database.Float, nullable=False)


