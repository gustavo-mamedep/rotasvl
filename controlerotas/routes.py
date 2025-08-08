from flask import flash, redirect, render_template, request, session, url_for
from controlerotas import database, app
from controlerotas.models import Usuario, Bairros, Servico
from controlerotas.forms import FormCriarUsuario, FormBairros, FormCriarServico, FormFiltros
from sqlalchemy.orm import joinedload
from sqlalchemy import distinct
from datetime import timedelta
from datetime import datetime
from zoneinfo import ZoneInfo


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
    
    # Para finalizados, filtrar apenas os do dia atual
    fuso = ZoneInfo("America/Sao_Paulo")
    hoje = datetime.now(fuso).date()
    finalizados = query_base.filter(
        Servico.status == 'Finalizado',
        database.func.date(Servico.data_finalizado) == hoje
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
            valor=valor,
            obs=form.obs.data if form.obs.data else '',
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
            servico.valor = float(form.valor.data.replace(',', '.')) if form.valor.data else 0.0
            servico.obs = form.obs.data if form.obs.data else ''

            database.session.commit()
            flash('Serviço atualizado com sucesso!', 'success')
            return redirect(url_for('home'))

    # Preencher o formulário com os dados atuais
    form.bairro.data = servico.bairro
    form.servico.data = servico.servico
    form.documento.data = servico.documento
    form.prestador.data = servico.prestador
    form.taxa.data = servico.taxa
    form.valor.data = f"{servico.valor:.2f}".replace(".", ",")
    form.obs.data = servico.obs

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
    
    # Data de hoje para filtrar finalizados
    hoje = datetime.now().date()
    
    # Estatísticas gerais
    total_cadastrados = Servico.query.filter_by(status='Cadastrado').count()
    total_em_rota = Servico.query.filter_by(status='Em Rota').count()
    total_finalizados = Servico.query.filter(
        Servico.status == 'Finalizado',
        database.func.date(Servico.data_finalizado) == hoje
    ).count()
    total_cancelados = Servico.query.filter(Servico.data_cancelado.isnot(None)).count()
    
    # Estatísticas por bairro
    bairros_com_servicos = database.session.query(distinct(Servico.bairro)).filter(
        Servico.bairro.isnot(None)
    ).order_by(Servico.bairro).all()
    
    servicos_por_bairro = []
    for bairro_tuple in bairros_com_servicos:
        bairro = bairro_tuple[0]
        
        cadastrados = Servico.query.filter_by(bairro=bairro, status='Cadastrado').count()
        em_rota = Servico.query.filter_by(bairro=bairro, status='Em Rota').count()
        finalizados_hoje = Servico.query.filter(
            Servico.bairro == bairro,
            Servico.status == 'Finalizado',
            database.func.date(Servico.data_finalizado) == hoje
        ).count()
        cancelados = Servico.query.filter(
            Servico.bairro == bairro,
            Servico.data_cancelado.isnot(None)
        ).count()
        
        total = cadastrados + em_rota + finalizados_hoje + cancelados
        
        if total > 0:  # Só incluir bairros que têm serviços
            servicos_por_bairro.append({
                'bairro': bairro,
                'cadastrados': cadastrados,
                'em_rota': em_rota,
                'finalizados_hoje': finalizados_hoje,
                'cancelados': cancelados,
                'total': total
            })
    
    # Ordenar por total de serviços (decrescente)
    servicos_por_bairro.sort(key=lambda x: x['total'], reverse=True)
    
    # Estatísticas por usuário
    usuarios_com_servicos = database.session.query(distinct(Usuario.usuario)).join(Servico).order_by(Usuario.usuario).all()
    
    servicos_por_usuario = []
    for usuario_tuple in usuarios_com_servicos:
        usuario_nome = usuario_tuple[0]
        usuario_obj = Usuario.query.filter_by(usuario=usuario_nome).first()
        
        if usuario_obj:
            cadastrados = Servico.query.filter_by(id_usuario=usuario_obj.id, status='Cadastrado').count()
            em_rota = Servico.query.filter_by(id_usuario=usuario_obj.id, status='Em Rota').count()
            finalizados_hoje = Servico.query.filter(
                Servico.id_usuario == usuario_obj.id,
                Servico.status == 'Finalizado',
                database.func.date(Servico.data_finalizado) == hoje
            ).count()
            cancelados = Servico.query.filter(
                Servico.id_usuario == usuario_obj.id,
                Servico.data_cancelado.isnot(None)
            ).count()
            
            total = cadastrados + em_rota + finalizados_hoje + cancelados
            
            servicos_por_usuario.append({
                'usuario': usuario_nome,
                'cadastrados': cadastrados,
                'em_rota': em_rota,
                'finalizados_hoje': finalizados_hoje,
                'cancelados': cancelados,
                'total': total
            })
    
    # Ordenar por total de serviços (decrescente)
    servicos_por_usuario.sort(key=lambda x: x['total'], reverse=True)
    
    return render_template('dashboard.html',
                           usuario_logado=usuario_logado,
                           total_cadastrados=total_cadastrados,
                           total_em_rota=total_em_rota,
                           total_finalizados=total_finalizados,
                           total_cancelados=total_cancelados,
                           servicos_por_bairro=servicos_por_bairro,
                           servicos_por_usuario=servicos_por_usuario)

