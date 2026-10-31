from flask import Blueprint, current_app, g, jsonify, request
from ..errors import ApiError
from ..validation import integer
from . import serializers
from .auth import owner, protected


def payload():
    data = request.get_json()
    if not isinstance(data, dict):
        raise ApiError("Envie um objeto JSON")
    return data


def register_routes(app):
    api = Blueprint("api", __name__)

    @api.before_request
    def dependencies():
        for name, value in (request.view_args or {}).items():
            integer(value, name, minimum=1)
        if request.endpoint != "api.index":
            g.controllers = current_app.extensions["build_controllers"]()

    @api.get("/")
    def index():
        return jsonify(mensagem="Bem-vindo à API da Loja", versao="1.0.0", endpoints={
            "produtos": "/produtos", "usuarios": "/usuarios", "pedidos": "/pedidos",
            "login": "/login", "relatorios": "/relatorios/vendas", "health": "/health"})

    @api.get("/health")
    def health():
        return jsonify(g.controllers["system"].health())

    @api.get("/produtos")
    def list_products():
        return jsonify(dados=[serializers.product(row) for row in g.controllers["products"].list()], sucesso=True)

    @api.get("/produtos/busca")
    def search_products():
        rows = g.controllers["products"].search(request.args)
        return jsonify(dados=[serializers.product(row) for row in rows], total=len(rows), sucesso=True)

    @api.get("/produtos/<int:id>")
    def find_product(id):
        return jsonify(dados=serializers.product(g.controllers["products"].find(id)), sucesso=True)

    @api.post("/produtos")
    @protected(admin=True)
    def create_product():
        product_id = g.controllers["products"].create(payload())
        return jsonify(dados={"id": product_id}, sucesso=True, mensagem="Produto criado"), 201

    @api.put("/produtos/<int:id>")
    @protected(admin=True)
    def update_product(id):
        g.controllers["products"].update(id, payload())
        return jsonify(sucesso=True, mensagem="Produto atualizado")

    @api.delete("/produtos/<int:id>")
    @protected(admin=True)
    def delete_product(id):
        g.controllers["products"].delete(id)
        return jsonify(sucesso=True, mensagem="Produto deletado")

    @api.get("/usuarios")
    @protected(admin=True)
    def list_users():
        return jsonify(dados=[serializers.user(row) for row in g.controllers["users"].list()], sucesso=True)

    @api.get("/usuarios/<int:id>")
    @protected()
    def find_user(id):
        owner(id)
        return jsonify(dados=serializers.user(g.controllers["users"].find(id)), sucesso=True)

    @api.post("/usuarios")
    def create_user():
        return jsonify(dados={"id": g.controllers["users"].create(payload())}, sucesso=True), 201

    @api.post("/login")
    def login():
        user = g.controllers["users"].login(payload())
        return jsonify(dados=serializers.login_user(user), sucesso=True, mensagem="Login OK")

    @api.post("/pedidos")
    @protected()
    def create_order():
        result = g.controllers["orders"].create(payload(), g.identity)
        return jsonify(dados=result, sucesso=True, mensagem="Pedido criado com sucesso"), 201

    @api.get("/pedidos")
    @protected(admin=True)
    def list_orders():
        return jsonify(dados=[serializers.order(row) for row in g.controllers["orders"].list()], sucesso=True)

    @api.get("/pedidos/usuario/<int:usuario_id>")
    @protected()
    def user_orders(usuario_id):
        owner(usuario_id)
        return jsonify(dados=[serializers.order(row) for row in g.controllers["orders"].list(usuario_id)], sucesso=True)

    @api.put("/pedidos/<int:pedido_id>/status")
    @protected(admin=True)
    def update_order_status(pedido_id):
        g.controllers["orders"].update_status(pedido_id, payload())
        return jsonify(sucesso=True, mensagem="Status atualizado")

    @api.get("/relatorios/vendas")
    @protected(admin=True)
    def sales():
        return jsonify(dados=g.controllers["system"].sales(), sucesso=True)

    @api.post("/admin/query")
    @protected(admin=True)
    def query():
        return jsonify(dados=g.controllers["system"].query(payload()), sucesso=True)

    @api.post("/admin/reset-db")
    @protected(admin=True)
    def reset():
        g.controllers["system"].reset(payload())
        return jsonify(mensagem="Banco de dados resetado", sucesso=True)

    app.register_blueprint(api)
