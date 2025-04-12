from sqlalchemy import ForeignKey, Integer, DateTime,func
from sqlalchemy.orm import Mapped, mapped_column, validates
from .. import db, relationship
from datetime import datetime
from pytz import timezone
from flask import current_app
ESTADOS_PRODUCCION = [
    'sin_iniciar',
    'en_preparacion',
    'amasando',
    'cortando',
    'mezclando',
    'cocinando',
    'enfriando',
    'terminada'
]

class LoteGalleta(db.Model):
    __tablename__ = "lotegalleta"
    
    idLoteGalleta: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fechaPreparacion = db.Column(db.DateTime, server_default=db.func.now())
    idTipoGalleta: Mapped[int] = mapped_column(ForeignKey("tipogalleta.idTipoGalleta"))
    tipo_galleta: Mapped["TipoGalleta"] = relationship(back_populates="lotes")
    cantidadProducida: Mapped[int] = mapped_column(Integer, server_default='0')  # Nombre exacto como en BD
    cantidadDisponible: Mapped[int] = mapped_column(Integer, server_default='0')
    estatus: Mapped[str] = mapped_column(db.String(20), server_default='sin_iniciar')  # Asegura coincidencia con BD
    @validates('estatus')
    def valida_estatus(self, key, value):
        if value not in ESTADOS_PRODUCCION:
            raise ValueError(f"Estado inválido. Debe ser uno de: {ESTADOS_PRODUCCION}")
        return value
    @property
    def fecha_local(self):
        """Devuelve la fecha en la zona horaria configurada"""
        if self.fechaPreparacion is None:
            return None
            
        tz = timezone(current_app.config.get('TIMEZONE', 'UTC'))
        return self.fechaPreparacion.replace(tzinfo=timezone('UTC')).astimezone(tz)
    
     # Relación con Receta
    receta_id = db.Column(db.Integer, db.ForeignKey('receta.idReceta'))
    receta = db.relationship('Receta', backref='lotes', lazy=True)