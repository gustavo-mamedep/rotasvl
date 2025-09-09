from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Length, Optional


class FormCriarUsuario(FlaskForm):
    usuario = StringField('Usuário', validators=[DataRequired()])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(6, 20)])
    tipo = SelectField('Tipo', choices=[
        ('', 'Selecione'),
        ('admin', 'Administrador'),
        ('operador', 'Operador'),
        ('entregador', 'Entregador')
    ], validators=[DataRequired()])
    botao_submit_criar = SubmitField('Criar Usuário')


class FormCriarServico(FlaskForm):
    bairro = SelectField('Bairro', choices=[], validators=[DataRequired()])
    servico = SelectField('Serviço', choices=[
        ('', 'Selecione'),
        ('Venda', 'Venda'),
        ('Condicional', 'Condicional'),
        ('Buscar_cond', 'Buscar Condicional'),
        ('Troca', 'Troca'),
        ('Recebimento', 'Recebimento'),
        ('Transferencia', 'Transferência'),
        ('Mercado Livre', 'Mercado Livre'),
        ('Correios', 'Correios'),
        ('Outros', 'Outros')
    ], validators=[DataRequired()])
    documento = StringField('Documento', validators=[DataRequired()])
    prestador = SelectField('Prestador', choices=[
        ('Motoqueiro', 'Motoqueiro'),
        ('Uber', 'Uber'),
        ('Outros', 'Outros')
    ], validators=[DataRequired()])
    taxa = BooleanField('Com Taxa ?')
    cartao = BooleanField('Maquina Cartão ?')
    valor = StringField('Valor', default='0,00')
    obs = TextAreaField('Observação')
    cep = StringField('CEP', validators=[Optional(), Length(max=9)])
    rua = StringField('Endereço',)
    numero = IntegerField('Número', validators=[Optional()])
    bairro2 = StringField('Bairro')
    cidade = StringField('Cidade')
    estado = StringField('Estado')
    complemento = StringField('Complemento')
    botao_submit_servico = SubmitField('Criar Serviço')



class FormBairros(FlaskForm):
    nome = StringField('Bairro', validators=[DataRequired()])
    valor = StringField('Valor da Taxa', validators=[DataRequired()])
    botao_submit_bairro = SubmitField('Criar Bairro')


class FormFiltros(FlaskForm):
    usuario = SelectField('Usuário', choices=[], default='')
    bairro = SelectField('Bairro', choices=[], default='')
    prestador = SelectField('Prestador', choices=[], default='')
    botao_limpar = SubmitField('Limpar Filtros')

