from flask import flash, redirect, render_template, request, session, url_for
from controlerotas import database, app
from controlerotas.models import Usuario, Bairros, Servico
from controlerotas.forms import FormCriarUsuario, FormBairros, FormCriarServico, FormFiltros
from sqlalchemy.orm import joinedload
from sqlalchemy import distinct, or_
from datetime import timedelta
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote


def obter_usuario_logado():
    """Retorna o objeto Usuario logado ou None"""
    if 'usuario_logado' not in session:
        return None
    return Usuario.query.get(session['usuario_logado'])


def verificar_permissao_admin():
    """Verifica se o usuário logado é admin"""
    usuario = obter_usuario_logado()
    return usuario and usuario.tipo == 'admin'


def verificar_permissao_operador():
    """Verifica se o usuário logado é operador"""
    usuario = obter_usuario_logado()
    return usuario and usuario.tipo == 'operador'


def verificar_permissao_entregador():
    """Verifica se o usuário logado é entregador"""
    usuario = obter_usuario_logado()
    return usuario and usuario.tipo == 'entregador'


@app.route("/")
def home():
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))

    # Obter usuário logado
    usuario_logado = obter_usuario_logado()
    
    # Criar formulário de filtros
    form_filtros = FormFiltros()
    
    # Obter filtros da URL
    filtro_usuario = request.args.get('usuario', '')
    filtro_bairro = request.args.get('bairro', '')
    filtro_prestador = request.args.get('prestador', '')
    
    # Query base com joinedload para otimizar
    query_base = Servico.query.options(joinedload(Servico.usuario))
    
    # Aplicar filtros se especificados
    if filtro_usuario:
        query_base = query_base.join(Usuario).filter(Usuario.usuario == filtro_usuario)
    if filtro_bairro:
        query_base = query_base.filter(Servico.bairro == filtro_bairro)
    if filtro_prestador:
        query_base = query_base.filter(Servico.prestador == filtro_prestador)
    
    # Buscar serviços por status com ordenação específica
    cadastrados = query_base.filter(Servico.status == 'Cadastrado').order_by(Servico.data_criacao.desc()).all()
    em_rota = query_base.filter(Servico.status == 'Em Rota').order_by(Servico.ordem_rota.asc(), Servico.data_em_rota.desc()).all()

    fuso = ZoneInfo("America/Sao_Paulo")
    agora = datetime.now(fuso)
    inicio_dia = datetime.combine(agora.date(), datetime.min.time(), tzinfo=fuso)
    fim_dia = datetime.combine(agora.date(), datetime.max.time(), tzinfo=fuso)

    finalizados = query_base.filter(
        Servico.status == 'Finalizado',
        Servico.data_finalizado >= inicio_dia.astimezone(ZoneInfo("UTC")),
        Servico.data_finalizado <= fim_dia.astimezone(ZoneInfo("UTC"))
    ).order_by(Servico.data_finalizado.desc()).all()

    # Ajustar datas
    for lista in [cadastrados, em_rota, finalizados]:
        for servico in lista:
            servico.data_ajustada = servico.data_criacao - timedelta(hours=3)
            if servico.data_em_rota:
                servico.data_em_rota_ajustada = servico.data_em_rota - timedelta(hours=3)
            else:
                servico.data_em_rota_ajustada = None
            if servico.data_finalizado:
                servico.data_finalizado_ajustada = servico.data_finalizado - timedelta(hours=3)
            else:
                servico.data_finalizado_ajustada = None

    # Carregar opções para os filtros (apenas usuários, bairros e prestadores que têm serviços)
    usuarios_com_servicos = database.session.query(distinct(Usuario.usuario)).join(Servico).order_by(Usuario.usuario).all()
    bairros_com_servicos = database.session.query(distinct(Servico.bairro)).order_by(Servico.bairro).all()
    prestadores_com_servicos = database.session.query(distinct(Servico.prestador)).order_by(Servico.prestador).all()
    
    # Configurar choices dos filtros
    form_filtros.usuario.choices = [('', 'Todos os usuários')] + [(u[0], u[0]) for u in usuarios_com_servicos]
    form_filtros.bairro.choices = [('', 'Todos os bairros')] + [(b[0], b[0]) for b in bairros_com_servicos]
    form_filtros.prestador.choices = [('', 'Todos os prestadores')] + [(p[0], p[0]) for p in prestadores_com_servicos]
    
    # Definir valores atuais dos filtros
    form_filtros.usuario.data = filtro_usuario
    form_filtros.bairro.data = filtro_bairro
    form_filtros.prestador.data = filtro_prestador

    return render_template('home.html',
                           cadastrados=cadastrados,
                           em_rota=em_rota,
                           finalizados=finalizados,
                           form_filtros=form_filtros,
                           usuario_logado=usuario_logado)


# ======================= USUÁRIOS ============================

@app.route('/usuarios')
def usuarios():
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))
    
    usuario_logado = obter_usuario_logado()
    lista_usuarios = Usuario.query.all()
    return render_template('usuarios.html', lista_usuarios=lista_usuarios, usuario_logado=usuario_logado)


@app.route('/usuarios/criar', methods=['GET', 'POST'])
def criar_usuarios():
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))
    
    # Apenas admin pode criar usuários
    if not verificar_permissao_admin():
        flash('Acesso negado. Apenas administradores podem criar usuários.', 'danger')
        return redirect(url_for('usuarios'))

    form = FormCriarUsuario()

    if form.validate_on_submit():
        usuario = form.usuario.data
        senha = form.senha.data
        tipo = form.tipo.data

        novo_usuario = Usuario(usuario=usuario, senha=senha, tipo=tipo)
        database.session.add(novo_usuario)
        database.session.commit()

        flash('Usuário Adicionado com Sucesso!', 'success')
        return redirect(url_for('usuarios'))
    return render_template('criar_usuarios.html', form=form)


@app.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))
    
    # Apenas admin pode editar usuários
    if not verificar_permissao_admin():
        flash('Acesso negado. Apenas administradores podem editar usuários.', 'danger')
        return redirect(url_for('usuarios'))
    
    usuario = Usuario.query.get_or_404(id)
    form = FormCriarUsuario()

    if form.validate_on_submit():
        usuario.usuario = form.usuario.data
        usuario.senha = form.senha.data
        usuario.tipo = form.tipo.data

        database.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('usuarios'))

    form.usuario.data = usuario.usuario
    form.senha.data = usuario.senha
    form.tipo.data = usuario.tipo

    return render_template('criar_usuarios.html', form=form, editar=True)


@app.route('/usuarios/excluir/<int:id>', methods=['POST'])
def excluir_usuario(id):
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))
    
    # Apenas admin pode excluir usuários
    if not verificar_permissao_admin():
        flash('Acesso negado. Apenas administradores podem excluir usuários.', 'danger')
        return redirect(url_for('usuarios'))
    
    usuario = Usuario.query.get_or_404(id)
    database.session.delete(usuario)
    database.session.commit()
    flash('Usuário excluído com sucesso!', 'success')
    return redirect(url_for('usuarios'))


# ======================= BAIRROS ============================

@app.route('/bairros')
def bairros():
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))
    
    usuario_logado = obter_usuario_logado()
    lista_bairros = Bairros.query.order_by(Bairros.nome).all()
    return render_template('bairros.html', lista_bairros=lista_bairros, usuario_logado=usuario_logado)


@app.route('/bairros/criar', methods=['GET', 'POST'])
def criar_bairros():
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))
    
    # Apenas admin pode criar bairros
    if not verificar_permissao_admin():
        flash('Acesso negado. Apenas administradores podem criar bairros.', 'danger')
        return redirect(url_for('bairros'))

    form = FormBairros()

    if form.validate_on_submit():
        nome = form.nome.data
        valor = float(form.valor.data.replace(',', '.'))

        bairro_existente = Bairros.query.filter_by(nome=nome).first()

        if bairro_existente:
            flash('Bairro já cadastrado!', 'danger')
            return redirect(url_for('criar_bairros'))

        bairro = Bairros(nome=nome, valor=valor)
        database.session.add(bairro)
        database.session.commit()

        flash('Bairro cadastrado com sucesso!', 'success')
        return redirect(url_for('bairros'))

    return render_template('criar_bairro.html', form=form)


@app.route('/bairros/editar/<int:id>', methods=['GET', 'POST'])
def editar_bairro(id):
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))
    
    # Apenas admin pode editar bairros
    if not verificar_permissao_admin():
        flash('Acesso negado. Apenas administradores podem editar bairros.', 'danger')
        return redirect(url_for('bairros'))

    bairro = Bairros.query.get_or_404(id)
    form = FormBairros()

    if form.validate_on_submit():
        bairro_existente = Bairros.query.filter_by(nome=form.nome.data).first()
        if bairro_existente and bairro_existente.id != bairro.id:
            flash('Já existe um bairro com esse nome.', 'danger')
            return redirect(url_for('editar_bairro', id=id))

        bairro.nome = form.nome.data
        bairro.valor = float(form.valor.data.replace(',', '.'))
        database.session.commit()
        flash('Bairro atualizado com sucesso!', 'success')
        return redirect(url_for('bairros'))

    form.nome.data = bairro.nome
    form.valor.data = str(bairro.valor)

    return render_template('editar_bairro.html', form=form)


@app.route('/bairros/excluir/<int:id>', methods=['POST'])
def excluir_bairro(id):
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))
    
    # Apenas admin pode excluir bairros
    if not verificar_permissao_admin():
        flash('Acesso negado. Apenas administradores podem excluir bairros.', 'danger')
        return redirect(url_for('bairros'))

    bairro = Bairros.query.get_or_404(id)
    database.session.delete(bairro)
    database.session.commit()
    flash('Bairro excluído com sucesso!', 'success')
    return redirect(url_for('bairros'))


# ======================= SERVIÇOS ============================

@app.route('/servico/criar', methods=['GET', 'POST'])
def criar_servico():
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))
    
    # Entregador não pode criar serviços
    if verificar_permissao_entregador():
        flash('Acesso negado. Entregadores não podem criar serviços.', 'danger')
        return redirect(url_for('home'))

    usuario_logado = obter_usuario_logado()
    form = FormCriarServico()
    
    # Carregar bairros dinamicamente
    bairros = Bairros.query.order_by(Bairros.nome).all()
    form.bairro.choices = [('', 'Selecione')] + [(bairro.nome, bairro.nome) for bairro in bairros]
    
    # Definir valor padrão se não estiver preenchido
    if not form.valor.data:
        form.valor.data = '0,00'

    if form.validate_on_submit():
        valor = float(form.valor.data.replace(',', '.')) if form.valor.data else 0.0

        servico = Servico(
            bairro=form.bairro.data,
            servico=form.servico.data,
            documento=form.documento.data,
            prestador=form.prestador.data,
            taxa=form.taxa.data,
            cartao=form.cartao.data,
            valor=valor,
            obs=form.obs.data if form.obs.data else '',
            cep=form.cep.data,
            rua=form.rua.data,
            numero=form.numero.data,
            bairro2=form.bairro2.data,
            cidade=form.cidade.data,
            estado=form.estado.data,
            complemento=form.complemento.data,
            id_usuario=session['usuario_logado']  # Usando diretamente o id do usuário logado
        )
        database.session.add(servico)
        database.session.commit()
        flash('Serviço cadastrado com sucesso!', 'success')
        return redirect(url_for('home'))

    return render_template("criar_servico.html", form=form, usuario_logado=usuario_logado)


@app.route('/servico/atualizar_status/<int:id>/<string:novo_status>', methods=['POST'])
def atualizar_status(id, novo_status):
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))

    usuario_logado = obter_usuario_logado()
    servico = Servico.query.get_or_404(id)
    
    # Verificar permissões baseadas no tipo de usuário e status
    if novo_status == 'Em Rota':

        if verificar_permissao_entregador():
            flash('Acesso negado. Entregadores não podem mover serviços para "Em Rota".', 'danger')
            return redirect(url_for('home'))
        
        # Operador só pode mover seus próprios serviços
        if verificar_permissao_operador() and servico.id_usuario != usuario_logado.id:
            flash('Acesso negado. Operadores só podem mover seus próprios serviços.', 'danger')
            return redirect(url_for('home'))
    
    elif novo_status == 'Finalizado':
        # Operador só pode finalizar seus próprios serviços
        if verificar_permissao_operador() and servico.id_usuario != usuario_logado.id:
            flash('Acesso negado. Operadores só podem finalizar seus próprios serviços.', 'danger')
            return redirect(url_for('home'))
        # Entregador pode finalizar qualquer serviço (sem restrição)

    servico.status = novo_status

    if novo_status == 'Em Rota':
        servico.data_em_rota = datetime.utcnow()
        # Definir ordem_rota como o próximo número disponível
        max_ordem = database.session.query(database.func.max(Servico.ordem_rota)).filter_by(status='Em Rota').scalar()
        servico.ordem_rota = (max_ordem or 0) + 1
    elif novo_status == 'Finalizado':
        servico.data_finalizado = datetime.utcnow()
        servico.ordem_rota = None  # Limpar ordem quando finalizado

    database.session.commit()

    flash(f'Serviço atualizado para {novo_status} com sucesso.', 'success')
    return redirect(url_for('home'))


# ======================= LOGIN / LOGOUT ============================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        usuario_cadastrado = Usuario.query.filter_by(usuario=usuario, senha=senha).first()

        if usuario_cadastrado:
            session['usuario_logado'] = usuario_cadastrado.id  # ✅ Aqui salva o ID, que é o correto
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Usuário ou senha incorretos!', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('usuario_logado', None)
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))


# ======================= SUPORTE ============================

@app.route('/suporte')
def suporte():
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))
    
    usuario_logado = obter_usuario_logado()
    return render_template('suporte.html', usuario_logado=usuario_logado)




@app.route('/servico/editar/<int:id>', methods=['GET', 'POST'])
def editar_servico(id):
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))

    usuario_logado = obter_usuario_logado()
    servico = Servico.query.get_or_404(id)
    
    # Verificar se o serviço está com status "Cadastrado"
    if servico.status != 'Cadastrado':
        flash('Só é possível editar serviços com status "Cadastrado".', 'danger')
        return redirect(url_for('home'))
    
    # Verificar permissões: admin pode editar qualquer, operador só seus próprios
    if not verificar_permissao_admin() and servico.id_usuario != usuario_logado.id:
        flash('Acesso negado. Você só pode editar seus próprios serviços.', 'danger')
        return redirect(url_for('home'))

    form = FormCriarServico()
    
    # Carregar bairros dinamicamente
    bairros = Bairros.query.order_by(Bairros.nome).all()
    form.bairro.choices = [('', 'Selecione')] + [(bairro.nome, bairro.nome) for bairro in bairros]

    if form.validate_on_submit():
        # Verificar se o checkbox de cancelar foi marcado
        cancelar = request.form.get('cancelar')
        
        if cancelar:
            # Cancelar o serviço
            servico.status = 'Cancelado'
            servico.data_cancelado = datetime.utcnow()
            database.session.commit()
            flash('Serviço cancelado com sucesso!', 'success')
            return redirect(url_for('home'))
        else:
            # Atualizar o serviço normalmente
            servico.bairro = form.bairro.data
            servico.servico = form.servico.data
            servico.documento = form.documento.data
            servico.prestador = form.prestador.data
            servico.taxa = form.taxa.data
            servico.cartao = form.cartao.data
            servico.valor = float(form.valor.data.replace(',', '.')) if form.valor.data else 0.0
            servico.obs = form.obs.data if form.obs.data else ''
            servico.cep = form.cep.data
            servico.rua = form.rua.data
            servico.numero = form.numero.data
            servico.bairro2 = form.bairro2.data
            servico.cidade = form.cidade.data
            servico.estado = form.estado.data
            servico.complemento = form.complemento.data

            database.session.commit()
            flash('Serviço atualizado com sucesso!', 'success')
            return redirect(url_for('home'))

    # Preencher o formulário com os dados atuais
    form.bairro.data = servico.bairro
    form.servico.data = servico.servico
    form.documento.data = servico.documento
    form.prestador.data = servico.prestador
    form.taxa.data = servico.taxa
    form.cartao.data = servico.cartao
    form.valor.data = f"{servico.valor:.2f}".replace(".", ",")
    form.obs.data = servico.obs
    form.cep.data = servico.cep
    form.rua.data = servico.rua
    form.numero.data = servico.numero
    form.bairro2.data = servico.bairro2
    form.cidade.data = servico.cidade
    form.estado.data = servico.estado
    form.complemento.data = servico.complemento


    return render_template("criar_servico.html", form=form, usuario_logado=usuario_logado, servico=servico, editar=True)


@app.route('/servico/voltar_cadastrado/<int:id>', methods=['POST'])
def voltar_cadastrado(id):
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))

    usuario_logado = obter_usuario_logado()
    servico = Servico.query.get_or_404(id)
    
    # Verificar se o serviço está com status "Em Rota"
    if servico.status != 'Em Rota':
        flash('Só é possível voltar serviços que estão "Em Rota".', 'danger')
        return redirect(url_for('home'))

    # Operador só pode voltar seus próprios serviços
    if verificar_permissao_operador() and servico.id_usuario != usuario_logado.id:
        flash('Acesso negado. Operadores só podem voltar seus próprios serviços.', 'danger')
        return redirect(url_for('home'))

    servico.status = 'Cadastrado'
    servico.data_em_rota = None  # Zerar a data de rota
    servico.ordem_rota = None  # Zerar a ordem

    database.session.commit()

    flash('Serviço retornado para "Cadastrado" com sucesso.', 'success')
    return redirect(url_for('home'))



# ======================= AJAX ROUTES ============================

@app.route('/api/bairro/valor/<string:nome_bairro>')
def obter_valor_bairro(nome_bairro):
    """Rota AJAX para obter o valor da taxa de um bairro"""
    if 'usuario_logado' not in session:
        return {'error': 'Não autorizado'}, 401
    
    bairro = Bairros.query.filter_by(nome=nome_bairro).first()
    if bairro:
        # Formatar o valor com vírgula como separador decimal e sempre 2 casas decimais
        valor_formatado = f"{bairro.valor:.2f}".replace('.', ',')
        return {'valor': valor_formatado}
    else:
        return {'valor': '0,00'}






# ======================= REORDENAÇÃO EM ROTA ============================

@app.route('/servico/mover_ordem/<int:id>/<string:direcao>', methods=['POST'])
def mover_ordem_rota(id, direcao):
    """Move um serviço para cima ou para baixo na ordem da coluna Em Rota"""
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))
    
    # Apenas entregador e admin podem reordenar
    if verificar_permissao_operador():
        flash('Acesso negado. Operadores não podem reordenar serviços.', 'danger')
        return redirect(url_for('home'))
    
    servico = Servico.query.get_or_404(id)
    
    if servico.status != 'Em Rota':
        flash('Só é possível reordenar serviços que estão "Em Rota".', 'danger')
        return redirect(url_for('home'))
    
    # Obter todos os serviços em rota ordenados
    servicos_em_rota = Servico.query.filter_by(status='Em Rota').order_by(Servico.ordem_rota.asc()).all()
    
    # Encontrar posição atual
    posicao_atual = None
    for i, s in enumerate(servicos_em_rota):
        if s.id == id:
            posicao_atual = i
            break
    
    if posicao_atual is None:
        flash('Serviço não encontrado na lista.', 'danger')
        return redirect(url_for('home'))
    
    # Determinar nova posição
    if direcao == 'cima' and posicao_atual > 0:
        nova_posicao = posicao_atual - 1
    elif direcao == 'baixo' and posicao_atual < len(servicos_em_rota) - 1:
        nova_posicao = posicao_atual + 1
    else:
        # Não pode mover (já está no topo/fundo)
        return redirect(url_for('home'))
    
    # Trocar as ordens
    servico_atual = servicos_em_rota[posicao_atual]
    servico_destino = servicos_em_rota[nova_posicao]
    
    ordem_temp = servico_atual.ordem_rota
    servico_atual.ordem_rota = servico_destino.ordem_rota
    servico_destino.ordem_rota = ordem_temp
    
    database.session.commit()
    
    return redirect(url_for('home'))



# ======================= CANCELADOS ============================

@app.route('/cancelados')
def cancelados():
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))

    # Obter usuário logado
    usuario_logado = obter_usuario_logado()
    
    # Criar formulário de filtros
    form_filtros = FormFiltros()
    
    # Obter filtros da URL
    filtro_usuario = request.args.get('usuario', '')
    filtro_bairro = request.args.get('bairro', '')
    filtro_prestador = request.args.get('prestador', '')
    
    # Query base com joinedload para otimizar
    query_base = Servico.query.options(joinedload(Servico.usuario))
    
    # Aplicar filtros se especificados
    if filtro_usuario:
        query_base = query_base.join(Usuario).filter(Usuario.usuario == filtro_usuario)
    if filtro_bairro:
        query_base = query_base.filter(Servico.bairro == filtro_bairro)
    if filtro_prestador:
        query_base = query_base.filter(Servico.prestador == filtro_prestador)
    
    # Buscar serviços cancelados
    cancelados = query_base.filter(Servico.status == 'Cancelado').order_by(Servico.data_cancelado.desc()).all()

    # Ajustar datas
    for servico in cancelados:
        servico.data_ajustada = servico.data_criacao - timedelta(hours=3)
        if servico.data_cancelado:
            servico.data_cancelado_ajustada = servico.data_cancelado - timedelta(hours=3)
        else:
            servico.data_cancelado_ajustada = None

    # Carregar opções para os filtros (apenas usuários, bairros e prestadores que têm serviços cancelados)
    usuarios_com_cancelados = database.session.query(distinct(Usuario.usuario)).join(Servico).filter(Servico.status == 'Cancelado').order_by(Usuario.usuario).all()
    bairros_com_cancelados = database.session.query(distinct(Servico.bairro)).filter(Servico.status == 'Cancelado').order_by(Servico.bairro).all()
    prestadores_com_cancelados = database.session.query(distinct(Servico.prestador)).filter(Servico.status == 'Cancelado').order_by(Servico.prestador).all()
    
    # Configurar choices dos filtros
    form_filtros.usuario.choices = [('', 'Todos os usuários')] + [(u[0], u[0]) for u in usuarios_com_cancelados]
    form_filtros.bairro.choices = [('', 'Todos os bairros')] + [(b[0], b[0]) for b in bairros_com_cancelados]
    form_filtros.prestador.choices = [('', 'Todos os prestadores')] + [(p[0], p[0]) for p in prestadores_com_cancelados]
    
    # Definir valores atuais dos filtros
    form_filtros.usuario.data = filtro_usuario
    form_filtros.bairro.data = filtro_bairro
    form_filtros.prestador.data = filtro_prestador

    return render_template('cancelados.html',
                           cancelados=cancelados,
                           form_filtros=form_filtros,
                           usuario_logado=usuario_logado)


@app.route('/servico/cancelar/<int:id>', methods=['POST'])
def cancelar_servico(id):
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))

    usuario_logado = obter_usuario_logado()
    servico = Servico.query.get_or_404(id)
    
    # Verificar se o serviço está com status "Cadastrado"
    if servico.status != 'Cadastrado':
        flash('Só é possível cancelar serviços com status "Cadastrado".', 'danger')
        return redirect(url_for('home'))
    
    # Verificar permissões: admin pode cancelar qualquer, operador só seus próprios
    if not verificar_permissao_admin() and servico.id_usuario != usuario_logado.id:
        flash('Acesso negado. Operadores só podem cancelar seus próprios serviços.', 'danger')
        return redirect(url_for('home'))

    servico.status = 'Cancelado'
    servico.data_cancelado = datetime.utcnow()

    database.session.commit()

    flash('Serviço cancelado com sucesso.', 'success')
    return redirect(url_for('home'))




# ======================= DASHBOARD ============================
@app.route('/dashboard')
def dashboard():
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))

    usuario_logado = obter_usuario_logado()

    # ===== Parâmetros de filtro =====
    periodo = request.args.get('periodo', 'dia')   # 'dia' (padrão) ou 'mes'
    try:
        mes = int(request.args.get('mes', 0))
    except:
        mes = 0
    try:
        ano = int(request.args.get('ano', 0))
    except:
        ano = 0

    # Novo: filtro por usuário (id)
    usuario_id = request.args.get('usuario_id', type=int)

    # ===== Janela de tempo (local -> UTC) =====
    from zoneinfo import ZoneInfo
    fuso = ZoneInfo("America/Sao_Paulo")
    agora_local = datetime.now(fuso)

    if periodo == 'mes':
        if mes < 1 or mes > 12:
            mes = agora_local.month
        if ano < 1:
            ano = agora_local.year

        inicio_local = datetime(ano, mes, 1, 0, 0, 0, tzinfo=fuso)
        if mes == 12:
            inicio_prox_mes_local = datetime(ano + 1, 1, 1, 0, 0, 0, tzinfo=fuso)
        else:
            inicio_prox_mes_local = datetime(ano, mes + 1, 1, 0, 0, 0, tzinfo=fuso)

        label_finalizados = "Finalizados no Mês"
        label_cancelados  = "Cancelados no Mês"

    else:  # período = 'dia'
        inicio_local = datetime(agora_local.year, agora_local.month, agora_local.day, 0, 0, 0, tzinfo=fuso)
        inicio_prox_mes_local = inicio_local + timedelta(days=1)

        label_finalizados = "Finalizados Hoje"
        label_cancelados  = "Cancelados Hoje"

    tz_utc = ZoneInfo("UTC")
    inicio_utc = inicio_local.astimezone(tz_utc)
    fim_utc    = inicio_prox_mes_local.astimezone(tz_utc)

    # Helper para aplicar filtro de usuário (se houver)
    def apply_user(query):
        if usuario_id:
            return query.filter(Servico.id_usuario == usuario_id)
        return query

    # ===== Contagens gerais =====
    total_cadastrados = apply_user(
        Servico.query.filter(
            Servico.status == 'Cadastrado',
            Servico.data_criacao >= inicio_utc,
            Servico.data_criacao <  fim_utc
        )
    ).count()

    total_em_rota = apply_user(
        Servico.query.filter(
            Servico.status == 'Em Rota',
            Servico.data_em_rota.isnot(None),
            Servico.data_em_rota >= inicio_utc,
            Servico.data_em_rota <  fim_utc
        )
    ).count()

    total_finalizados = apply_user(
        Servico.query.filter(
            Servico.status == 'Finalizado',
            Servico.data_finalizado.isnot(None),
            Servico.data_finalizado >= inicio_utc,
            Servico.data_finalizado <  fim_utc
        )
    ).count()

    total_cancelados = apply_user(
        Servico.query.filter(
            Servico.status == 'Cancelado',
            Servico.data_cancelado.isnot(None),
            Servico.data_cancelado >= inicio_utc,
            Servico.data_cancelado <  fim_utc
        )
    ).count()

    total_vendas = apply_user(
        Servico.query.filter(
            Servico.servico == 'Venda',
            Servico.data_finalizado.isnot(None),
            Servico.data_finalizado >= inicio_utc,
            Servico.data_finalizado < fim_utc
        )
    ).count()

    total_condicional = apply_user(
        Servico.query.filter(
            Servico.servico == 'Condicional',
            Servico.data_finalizado.isnot(None),
            Servico.data_finalizado >= inicio_utc,
            Servico.data_finalizado < fim_utc
        )
    ).count()

    total_buscarcond = apply_user(
        Servico.query.filter(
            Servico.servico == 'Buscar_cond',
            Servico.data_finalizado.isnot(None),
            Servico.data_finalizado >= inicio_utc,
            Servico.data_finalizado < fim_utc
        )
    ).count()

    total_troca = apply_user(
        Servico.query.filter(
            Servico.servico == 'Troca',
            Servico.data_finalizado.isnot(None),
            Servico.data_finalizado >= inicio_utc,
            Servico.data_finalizado < fim_utc
        )
    ).count()

    total_recebimento = apply_user(
        Servico.query.filter(
            Servico.servico == 'Recebimento',
            Servico.data_finalizado.isnot(None),
            Servico.data_finalizado >= inicio_utc,
            Servico.data_finalizado < fim_utc
        )
    ).count()

    total_transferencia = apply_user(
        Servico.query.filter(
            Servico.servico == 'Transferencia',
            Servico.data_finalizado.isnot(None),
            Servico.data_finalizado >= inicio_utc,
            Servico.data_finalizado < fim_utc
        )
    ).count()

    total_outros = apply_user(
        Servico.query.filter(
            or_(
                Servico.servico == 'Mercado Livre',
                Servico.servico == 'Correios',
                Servico.servico == 'Outros'
            ),
            Servico.data_finalizado.isnot(None),
            Servico.data_finalizado >= inicio_utc,
            Servico.data_finalizado < fim_utc
        )
    ).count()

    # ===== Estatísticas por Bairro (com filtro de usuário) =====
    bairros_com_servicos = database.session.query(distinct(Servico.bairro)).filter(
        Servico.bairro.isnot(None)
    ).order_by(Servico.bairro).all()

    servicos_por_bairro = []
    for (bairro,) in bairros_com_servicos:
        vendas = apply_user(
            Servico.query.filter(
                Servico.bairro == bairro,
                Servico.servico == 'Venda',
                Servico.data_finalizado.isnot(None),
                Servico.data_finalizado >= inicio_utc,
                Servico.data_finalizado < fim_utc
            )
        ).count()

        condicional = apply_user(
            Servico.query.filter(
                Servico.bairro == bairro,
                Servico.servico == 'Condicional',
                Servico.data_finalizado.isnot(None),
                Servico.data_finalizado >= inicio_utc,
                Servico.data_finalizado < fim_utc
            )
        ).count()

        buscarcond = apply_user(
            Servico.query.filter(
                Servico.bairro == bairro,
                Servico.servico == 'Buscar_cond',
                Servico.data_finalizado.isnot(None),
                Servico.data_finalizado >= inicio_utc,
                Servico.data_finalizado < fim_utc
            )
        ).count()

        trocas = apply_user(
            Servico.query.filter(
                Servico.bairro == bairro,
                Servico.servico == 'Troca',
                Servico.data_finalizado.isnot(None),
                Servico.data_finalizado >= inicio_utc,
                Servico.data_finalizado < fim_utc
            )
        ).count()

        recebimento = apply_user(
            Servico.query.filter(
                Servico.bairro == bairro,
                Servico.servico == 'Recebimento',
                Servico.data_finalizado.isnot(None),
                Servico.data_finalizado >= inicio_utc,
                Servico.data_finalizado < fim_utc
            )
        ).count()

        transferencia = apply_user(
            Servico.query.filter(
                Servico.bairro == bairro,
                Servico.servico == 'Transferencia',
                Servico.data_finalizado.isnot(None),
                Servico.data_finalizado >= inicio_utc,
                Servico.data_finalizado < fim_utc
            )
        ).count()

        outros = apply_user(
            Servico.query.filter(
                Servico.bairro == bairro,
                Servico.servico.in_(['Mercado Livre', 'Correios', 'Outros']),
                Servico.data_finalizado.isnot(None),
                Servico.data_finalizado >= inicio_utc,
                Servico.data_finalizado < fim_utc
            )
        ).count()

        total = vendas + condicional + buscarcond + trocas + recebimento + transferencia + outros

        if total > 0:
            servicos_por_bairro.append({
                'bairro': bairro,
                'vendas': vendas,
                'condicional': condicional,
                'buscarcond': buscarcond,
                'trocas': trocas,
                'recebimento': recebimento,
                'transferencia': transferencia,
                'outros': outros,
                'total': total
            })

    servicos_por_bairro.sort(key=lambda x: x['total'], reverse=True)

    # ===== Estatísticas por Usuário =====
    usuarios_com_servicos = database.session.query(distinct(Usuario.usuario)).join(Servico).order_by(Usuario.usuario).all()

    servicos_por_usuario = []
    for (usuario_nome,) in usuarios_com_servicos:
        usuario_obj = Usuario.query.filter_by(usuario=usuario_nome).first()
        if not usuario_obj:
            continue

        cadastrados = apply_user(
            Servico.query.filter(
                Servico.id_usuario == usuario_obj.id,
                Servico.status == 'Cadastrado',
                Servico.data_criacao >= inicio_utc,
                Servico.data_criacao <  fim_utc
            )
        ).count()

        em_rota = apply_user(
            Servico.query.filter(
                Servico.id_usuario == usuario_obj.id,
                Servico.status == 'Em Rota',
                Servico.data_em_rota.isnot(None),
                Servico.data_em_rota >= inicio_utc,
                Servico.data_em_rota <  fim_utc
            )
        ).count()

        finalizados_periodo = apply_user(
            Servico.query.filter(
                Servico.id_usuario == usuario_obj.id,
                Servico.status == 'Finalizado',
                Servico.data_finalizado.isnot(None),
                Servico.data_finalizado >= inicio_utc,
                Servico.data_finalizado <  fim_utc
            )
        ).count()

        cancelados = apply_user(
            Servico.query.filter(
                Servico.id_usuario == usuario_obj.id,
                Servico.status == 'Cancelado',
                Servico.data_cancelado.isnot(None),
                Servico.data_cancelado >= inicio_utc,
                Servico.data_cancelado <  fim_utc
            )
        ).count()

        total = cadastrados + em_rota + finalizados_periodo + cancelados
        servicos_por_usuario.append({
            'usuario': usuario_nome,
            'cadastrados': cadastrados,
            'em_rota': em_rota,
            'finalizados_hoje': finalizados_periodo,
            'cancelados': cancelados,
            'total': total
        })

    servicos_por_usuario.sort(key=lambda x: x['total'], reverse=True)

    # ===== Opções do select de usuários (somente quem tem serviços) =====
    usuarios_opts = database.session.query(Usuario.id, Usuario.usuario)\
        .join(Servico).distinct().order_by(Usuario.usuario).all()

    # ===== Dados para o seletor de meses =====
    meses_port = [
        (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"), (4, "Abril"),
        (5, "Maio"), (6, "Junho"), (7, "Julho"), (8, "Agosto"),
        (9, "Setembro"), (10, "Outubro"), (11, "Novembro"), (12, "Dezembro")
    ]

    return render_template(
        'dashboard.html',
        usuario_logado=usuario_logado,
        total_cadastrados=total_cadastrados,
        total_em_rota=total_em_rota,
        total_finalizados=total_finalizados,
        total_cancelados=total_cancelados,
        total_vendas=total_vendas,
        total_condicional=total_condicional,
        total_buscarcond=total_buscarcond,
        total_troca=total_troca,
        total_recebimento=total_recebimento,
        total_transferencia=total_transferencia,
        total_outros=total_outros,
        servicos_por_bairro=servicos_por_bairro,
        servicos_por_usuario=servicos_por_usuario,
        label_finalizados=label_finalizados,
        label_cancelados=label_cancelados,
        periodo=periodo,
        mes_sel=mes,
        ano_sel=ano,
        meses_port=meses_port,
        usuarios_opts=usuarios_opts,   # novo
        usuario_id=usuario_id          # novo (para manter "selected" no HTML)
    )


# ======================= GOOGLE ============================
def _endereco_completo(servico):
    """Monta o endereço completo a partir dos campos do serviço."""
    partes = [
        (servico.rua or '').strip(),
        (str(servico.numero) if servico.numero is not None else '').strip(),
        (servico.bairro2 or '').strip(),
        (servico.cidade or '').strip(),
        (servico.estado or '').strip(),
        'Brasil'
    ]
    # tira vazios e junta com vírgula
    return ', '.join([p for p in partes if p])

def _segmentar_rotas(origin, stops, limite_waypoints=9):
    """
    O Google Maps URL aceita até 9 'waypoints' por link (no desktop).
    Divide automaticamente em 1..N links se passar do limite.
    """
    urls = []
    i = 0
    while i < len(stops):
        bloco = stops[i:i + limite_waypoints]
        destination = bloco[-1] if bloco else origin
        waypoints = bloco[:-1]

        base = 'https://www.google.com/maps/dir/?api=1&travelmode=driving'
        url = f"{base}&origin={quote(origin)}&destination={quote(destination)}"
        if waypoints:
            url += "&waypoints=" + quote('|'.join(waypoints), safe='|')

        urls.append(url)
        # próxima perna começa onde esta terminou
        origin = destination
        i += limite_waypoints
    return urls


def _endereco_ok(s):
    """Regras mínimas para considerar o endereço válido."""
    return bool(
        (s.rua or '').strip() and
        (s.numero is not None) and
        (s.cidade or '').strip() and
        (s.estado or '').strip()
    )



def _segmentar_rotas_navegacao(origin, stops, limite_waypoints=9, omitir_origin=False, navegar=False):
    urls = []
    i = 0
    while i < len(stops):
        bloco = stops[i:i + limite_waypoints]
        destination = bloco[-1] if bloco else origin
        waypoints = bloco[:-1]

        base = 'https://www.google.com/maps/dir/?api=1&travelmode=driving'
        url = base
        if not omitir_origin:
            url += f"&origin={quote(origin)}"
        url += f"&destination={quote(destination)}"
        if waypoints:
            url += "&waypoints=" + quote('|'.join(waypoints), safe='|')
        if navegar:
            url += "&dir_action=navigate"  # no celular tenta já iniciar a navegação
        urls.append(url)

        origin = destination
        i += limite_waypoints
    return urls




@app.route('/rota/google')
def rota_google():
    # exige login (segue o padrão do seu app)
    if 'usuario_logado' not in session:
        return redirect(url_for('login'))

    # origem: endereço da sua base/loja/depósito
    origin = app.config.get('ORIGEM_ROTA')
    if not origin:
        flash('Defina ORIGEM_ROTA na configuração do aplicativo (endereço de saída).', 'warning')
        return redirect(url_for('home'))

    # busca serviços com status "Em Rota" ordenando por ordem_rota (e um desempate por id)
    servicos = (Servico.query
                .filter(Servico.status == 'Em Rota',
                        Servico.prestador == 'Motoqueiro')
                .order_by(Servico.ordem_rota.asc(), Servico.id.asc())
                .all())

    # monta lista de paradas a partir dos endereços válidos
    paradas = []
    ignorados = []  # ids de serviços sem endereço completo
    for s in servicos:
        if _endereco_ok(s):
            paradas.append(_endereco_completo(s))
        else:
            ignorados.append(s.id)

    if not paradas:
        flash('Não há serviços "Em Rota" com endereço completo.', 'warning')
        return redirect(url_for('home'))

    if ignorados:
        flash(f'Ignorados {len(ignorados)} serviço(s) sem endereço completo: {", ".join(map(str, ignorados))}.',
              'warning')

    # Detecta se é mobile para usar a localização atual e limitar waypoints
    ua = request.user_agent.string.lower()
    is_mobile = any(k in ua for k in ['android', 'iphone', 'ipad']) or (
                'mobile' in ua and 'windows' not in ua and 'macintosh' not in ua)
    limite = 3 if is_mobile else 9  # celular ~3; desktop ~9

    # No celular: omite origin para o Maps usar o GPS do aparelho e já pedir navegação
    urls = _segmentar_rotas_navegacao(
        origin,  # ainda usamos para desktop e para encadear etapas
        paradas,
        limite_waypoints=limite,
        omitir_origin=is_mobile,
        navegar=False
    )

    # se coube num link só, redireciona direto
    if len(urls) == 1:
        return redirect(urls[0])

    # senão, mostra uma página com os links sequenciais
    return render_template('rotas_google.html', urls=urls)

