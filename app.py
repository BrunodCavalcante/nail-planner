# ======================================================
# Nail Planner
# Sistema web simples para controle de clientes,
# atendimentos e retornos de nail designer.
# ======================================================

from flask import Flask, render_template, request, redirect, session, flash
from datetime import datetime, timedelta, date
import sqlite3

app = Flask(__name__)

# Chave usada pelo Flask para proteger a sessão de login.
# Em produção, troque por uma chave maior e secreta.
app.secret_key = "nail_planner_chave_secreta"

DB_NAME = "nail_planner.db"


def conectar_banco():
    """Abre conexão com o banco SQLite."""
    conexao = sqlite3.connect(DB_NAME)
    conexao.row_factory = sqlite3.Row
    return conexao


def criar_tabelas():
    """Cria as tabelas principais caso ainda não existam."""
    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT,
            observacoes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS atendimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            servico TEXT NOT NULL,
            data_atendimento TEXT NOT NULL,
            data_retorno TEXT NOT NULL,
            observacoes TEXT,
            FOREIGN KEY(cliente_id) REFERENCES clientes(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS avisos_visualizados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_visualizacao TEXT NOT NULL UNIQUE
        )
    """)

    # Usuário padrão inicial.
    cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", ("admin",))
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO usuarios (usuario, senha) VALUES (?, ?)",
            ("admin", "123456")
        )

    conexao.commit()
    conexao.close()


def usuario_logado():
    """Verifica se existe usuário logado na sessão."""
    return "usuario" in session


@app.route("/", methods=["GET", "POST"])
def index():
    """Página principal do sistema: login."""
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "").strip()

        conexao = conectar_banco()
        encontrado = conexao.execute(
            "SELECT * FROM usuarios WHERE usuario = ? AND senha = ?",
            (usuario, senha)
        ).fetchone()
        conexao.close()

        if encontrado:
            session["usuario"] = usuario
            return redirect("/dashboard")

        flash("Usuário ou senha inválidos.")

    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    """Painel inicial com alertas de retorno."""
    if not usuario_logado():
        return redirect("/")

    hoje = date.today()
    limite = hoje + timedelta(days=5)

    conexao = conectar_banco()

    aviso_hoje = conexao.execute(
        "SELECT id FROM avisos_visualizados WHERE data_visualizacao = ?",
        (hoje.strftime("%Y-%m-%d"),)
    ).fetchone()

    mostrar_aviso = aviso_hoje is None

    retornos = conexao.execute("""
        SELECT
            atendimentos.id,
            clientes.nome,
            clientes.telefone,
            atendimentos.servico,
            atendimentos.data_retorno
        FROM atendimentos
        JOIN clientes ON clientes.id = atendimentos.cliente_id
        WHERE date(atendimentos.data_retorno) BETWEEN date(?) AND date(?)
        ORDER BY date(atendimentos.data_retorno) ASC
    """, (hoje.strftime("%Y-%m-%d"), limite.strftime("%Y-%m-%d"))).fetchall()

    agendamentos_proximos = conexao.execute("""
        SELECT
            atendimentos.id,
            clientes.nome,
            clientes.telefone,
            atendimentos.servico,
            atendimentos.data_atendimento,
            atendimentos.observacoes
        FROM atendimentos
        JOIN clientes ON clientes.id = atendimentos.cliente_id
        WHERE date(atendimentos.data_atendimento) BETWEEN date(?) AND date(?)
        ORDER BY date(atendimentos.data_atendimento) ASC
    """, (hoje.strftime("%Y-%m-%d"), limite.strftime("%Y-%m-%d"))).fetchall()

    if mostrar_aviso and len(retornos) > 0:
        conexao.execute(
            "INSERT OR IGNORE INTO avisos_visualizados (data_visualizacao) VALUES (?)",
            (hoje.strftime("%Y-%m-%d"),)
        )
        conexao.commit()

    conexao.close()

    return render_template(
        "dashboard.html",
        retornos=retornos,
        agendamentos_proximos=agendamentos_proximos,
        mostrar_aviso=mostrar_aviso,
        hoje=hoje
    )


@app.route("/clientes", methods=["GET", "POST"])
def clientes():
    """Cadastro e listagem de clientes."""
    if not usuario_logado():
        return redirect("/")

    conexao = conectar_banco()

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        observacoes = request.form.get("observacoes", "").strip()

        if nome:
            conexao.execute(
                "INSERT INTO clientes (nome, telefone, observacoes) VALUES (?, ?, ?)",
                (nome, telefone, observacoes)
            )
            conexao.commit()
            flash("Cliente cadastrada com sucesso!")
        else:
            flash("Informe o nome da cliente.")

    lista_clientes = conexao.execute(
        "SELECT * FROM clientes ORDER BY nome ASC"
    ).fetchall()

    conexao.close()

    return render_template("clientes.html", clientes=lista_clientes)


@app.route("/editar-cliente/<int:cliente_id>", methods=["GET", "POST"])
def editar_cliente(cliente_id):
    """Edita os dados de uma cliente."""
    if not usuario_logado():
        return redirect("/")

    conexao = conectar_banco()

    cliente = conexao.execute(
        "SELECT * FROM clientes WHERE id = ?",
        (cliente_id,)
    ).fetchone()

    if cliente is None:
        conexao.close()
        flash("Cliente não encontrada.")
        return redirect("/clientes")

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        observacoes = request.form.get("observacoes", "").strip()

        if nome:
            conexao.execute("""
                UPDATE clientes
                SET nome = ?, telefone = ?, observacoes = ?
                WHERE id = ?
            """, (nome, telefone, observacoes, cliente_id))
            conexao.commit()
            flash("Cliente atualizada com sucesso!")
            conexao.close()
            return redirect("/clientes")

        flash("Informe o nome da cliente.")

    conexao.close()
    return render_template("editar_cliente.html", cliente=cliente)


@app.route("/excluir-cliente/<int:cliente_id>", methods=["POST"])
def excluir_cliente(cliente_id):
    """Exclui uma cliente e seus atendimentos."""
    if not usuario_logado():
        return redirect("/")

    conexao = conectar_banco()

    conexao.execute("DELETE FROM atendimentos WHERE cliente_id = ?", (cliente_id,))
    conexao.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))

    conexao.commit()
    conexao.close()

    flash("Cliente excluída com sucesso!")
    return redirect("/clientes")


@app.route("/novo-agendamento", methods=["GET", "POST"])
def novo_agendamento():
    """Registra agendamento e calcula retorno automaticamente."""
    if not usuario_logado():
        return redirect("/")

    conexao = conectar_banco()
    lista_clientes = conexao.execute(
        "SELECT * FROM clientes ORDER BY nome ASC"
    ).fetchall()

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        servico = request.form.get("servico", "").strip()
        data_atendimento = request.form.get("data_atendimento")
        dias_retorno = int(request.form.get("dias_retorno", 15))
        observacoes = request.form.get("observacoes", "").strip()

        data_base = datetime.strptime(data_atendimento, "%Y-%m-%d").date()
        data_retorno = data_base + timedelta(days=dias_retorno)

        conexao.execute("""
            INSERT INTO atendimentos
            (cliente_id, servico, data_atendimento, data_retorno, observacoes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            cliente_id,
            servico,
            data_atendimento,
            data_retorno.strftime("%Y-%m-%d"),
            observacoes
        ))

        conexao.commit()
        conexao.close()

        flash("Atendimento salvo e retorno agendado automaticamente!")
        return redirect("/agenda?data=" + data_atendimento)

    conexao.close()

    return render_template("novo_agendamento.html", clientes=lista_clientes)


@app.route("/novo-atendimento", methods=["GET", "POST"])
def novo_atendimento():
    """Registra atendimento simples sem data de retorno."""
    if not usuario_logado():
        return redirect("/")

    conexao = conectar_banco()
    lista_clientes = conexao.execute(
        "SELECT * FROM clientes ORDER BY nome ASC"
    ).fetchall()

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        servico = request.form.get("servico", "").strip()
        data_atendimento = request.form.get("data_atendimento")
        observacoes = request.form.get("observacoes", "").strip()

        # Como este é um atendimento simples, sem retorno,
        # a data_retorno fica igual à data do atendimento apenas para manter compatibilidade com o banco.
        conexao.execute("""
            INSERT INTO atendimentos
            (cliente_id, servico, data_atendimento, data_retorno, observacoes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            cliente_id,
            servico,
            data_atendimento,
            data_atendimento,
            observacoes
        ))

        conexao.commit()
        conexao.close()

        flash("Atendimento salvo com sucesso!")
        return redirect("/agenda?data=" + data_atendimento)

    conexao.close()

    return render_template("novo_atendimento.html", clientes=lista_clientes)


@app.route("/agenda")
def agenda():
    """Mostra agenda com calendário mensal e atendimentos do dia selecionado."""
    if not usuario_logado():
        return redirect("/")

    data_selecionada = request.args.get("data", date.today().strftime("%Y-%m-%d"))

    data_obj = datetime.strptime(data_selecionada, "%Y-%m-%d").date()
    ano = int(request.args.get("ano", data_obj.year))
    mes = int(request.args.get("mes", data_obj.month))

    import calendar
    cal = calendar.Calendar(firstweekday=6)
    semanas = cal.monthdatescalendar(ano, mes)

    mes_anterior = mes - 1
    ano_anterior = ano
    if mes_anterior == 0:
        mes_anterior = 12
        ano_anterior -= 1

    proximo_mes = mes + 1
    proximo_ano = ano
    if proximo_mes == 13:
        proximo_mes = 1
        proximo_ano += 1

    nomes_meses = [
        "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]

    conexao = conectar_banco()

    atendimentos = conexao.execute("""
        SELECT
            atendimentos.id,
            clientes.nome,
            clientes.telefone,
            atendimentos.servico,
            atendimentos.data_atendimento,
            atendimentos.data_retorno,
            atendimentos.observacoes
        FROM atendimentos
        JOIN clientes ON clientes.id = atendimentos.cliente_id
        WHERE date(atendimentos.data_atendimento) = date(?)
        ORDER BY atendimentos.id DESC
    """, (data_selecionada,)).fetchall()

    datas_com_agendamento = conexao.execute("""
        SELECT data_atendimento, COUNT(*) AS total
        FROM atendimentos
        WHERE strftime('%Y', data_atendimento) = ?
          AND strftime('%m', data_atendimento) = ?
        GROUP BY data_atendimento
    """, (str(ano), str(mes).zfill(2))).fetchall()

    dias_com_agendamento = {
        item["data_atendimento"]: item["total"]
        for item in datas_com_agendamento
    }

    conexao.close()

    return render_template(
        "agenda.html",
        atendimentos=atendimentos,
        data_selecionada=data_selecionada,
        semanas=semanas,
        ano=ano,
        mes=mes,
        nome_mes=nomes_meses[mes],
        ano_anterior=ano_anterior,
        mes_anterior=mes_anterior,
        proximo_ano=proximo_ano,
        proximo_mes=proximo_mes,
        dias_com_agendamento=dias_com_agendamento
    )


@app.route("/editar-atendimento/<int:atendimento_id>", methods=["GET", "POST"])
def editar_atendimento(atendimento_id):
    """Edita um atendimento/agendamento."""
    if not usuario_logado():
        return redirect("/")

    conexao = conectar_banco()

    atendimento = conexao.execute(
        "SELECT * FROM atendimentos WHERE id = ?",
        (atendimento_id,)
    ).fetchone()

    if atendimento is None:
        conexao.close()
        flash("Atendimento não encontrado.")
        return redirect("/agenda")

    lista_clientes = conexao.execute(
        "SELECT * FROM clientes ORDER BY nome ASC"
    ).fetchall()

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        servico = request.form.get("servico", "").strip()
        data_atendimento = request.form.get("data_atendimento")
        dias_retorno = int(request.form.get("dias_retorno", 15))
        observacoes = request.form.get("observacoes", "").strip()

        data_base = datetime.strptime(data_atendimento, "%Y-%m-%d").date()
        data_retorno = data_base + timedelta(days=dias_retorno)

        conexao.execute("""
            UPDATE atendimentos
            SET cliente_id = ?,
                servico = ?,
                data_atendimento = ?,
                data_retorno = ?,
                observacoes = ?
            WHERE id = ?
        """, (
            cliente_id,
            servico,
            data_atendimento,
            data_retorno.strftime("%Y-%m-%d"),
            observacoes,
            atendimento_id
        ))

        conexao.commit()
        conexao.close()

        flash("Atendimento atualizado com sucesso!")
        return redirect("/agenda?data=" + data_atendimento)

    conexao.close()

    return render_template(
        "editar_atendimento.html",
        atendimento=atendimento,
        clientes=lista_clientes
    )


@app.route("/excluir-atendimento/<int:atendimento_id>", methods=["POST"])
def excluir_atendimento(atendimento_id):
    """Exclui um atendimento/agendamento."""
    if not usuario_logado():
        return redirect("/")

    data_voltar = request.form.get("data_voltar", date.today().strftime("%Y-%m-%d"))

    conexao = conectar_banco()
    conexao.execute("DELETE FROM atendimentos WHERE id = ?", (atendimento_id,))
    conexao.commit()
    conexao.close()

    flash("Atendimento excluído com sucesso!")
    return redirect("/agenda?data=" + data_voltar)


@app.route("/logout")
def logout():
    """Sai do sistema."""
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    criar_tabelas()
    app.run(debug=True, host="0.0.0.0", port=5000)
