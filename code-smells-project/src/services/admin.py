import logging

from ..database import transaction
from ..errors import ApiError
from ..models.system import COUNT_QUERIES, SystemModel
from ..validation import object_data

logger = logging.getLogger(__name__)


class AdminService:
    def __init__(self, db, enable_reset=False, disposable=False):
        self.db = db
        self.model = SystemModel(db)
        self.enable_reset = enable_reset
        self.disposable = disposable

    def query(self, data):
        data = object_data(data)
        sql = data.get("sql")
        if not isinstance(sql, str) or not sql.strip():
            raise ApiError("Query não informada")
        operation = " ".join(sql.strip().removesuffix(";").split()).upper()
        if operation not in COUNT_QUERIES:
            raise ApiError("Somente consultas predefinidas de contagem são permitidas")
        return self.model.predefined_count(operation)

    def reset(self, data):
        if not self.enable_reset or not self.disposable:
            raise ApiError("Reset desabilitado para este banco", status=403)
        data = object_data(data)
        if data.get("confirmacao") != "RESET":
            raise ApiError("Confirmação RESET é obrigatória")
        with transaction(self.db):
            self.model.clear_data()
        logger.warning("Reset autorizado do banco descartável concluído")
