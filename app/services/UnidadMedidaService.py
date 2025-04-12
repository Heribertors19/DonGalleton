from app.models import UnidadMedida
from app import db

class UnidadMedidaService:
    @staticmethod
    def obtenerUnidades():
        # Consulta parametrizada que obtiene todas las unidades de medida
        unidades = UnidadMedida.query.all()
        return [{"idUnidadMedida": u.idUnidadMedida, "nombre": u.nombre} for u in unidades]