from sqlalchemy import ForeignKey, Integer, Float, String
from sqlalchemy.orm import Mapped, mapped_column
from .. import db

class DetalleVenta(db.Model):
    __tablename__ = "detalleventa"
    idDetalleVenta: Mapped[int] = mapped_column(primary_key=True)
    idVenta: Mapped[int] = mapped_column(ForeignKey("venta.idVenta"), nullable=False)
    idTipoGalleta: Mapped[int] = mapped_column(
        ForeignKey("tipogalleta.idTipoGalleta"), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    costoActual: Mapped[float] = mapped_column(Float, nullable=False)
    tiposVentaNombre: Mapped[str] = mapped_column(String(255), nullable=False)
    ventaEquivalenciaPiezas: Mapped[int] = mapped_column(Integer, nullable=False)
        # Relación con TipoGalleta
    tipo_galleta: Mapped["TipoGalleta"] = db.relationship("TipoGalleta", back_populates="detalles_venta")
    
    def calcular_piezas(self, galleta):
        """Convierte cualquier tipo de venta a cantidad en piezas"""
        peso_individual = float(galleta.pesoIndividualGalleta)
        
        if self.tiposVentaNombre == 'pieza':
            return self.cantidad
        elif self.tiposVentaNombre == 'gramo':
            return int(self.cantidad / peso_individual)
        elif self.tiposVentaNombre == 'kilo':
            return int((self.cantidad * 1000) / peso_individual)
        elif self.tiposVentaNombre == 'paquete_1kg':
            return int(1000 / peso_individual) * self.cantidad
        elif self.tiposVentaNombre == 'paquete_700gr':
            return int(700 / peso_individual) * self.cantidad
        elif self.tiposVentaNombre == 'especial':
            return self.cantidad
        else:
            raise ValueError("Tipo de venta no válido")

    def calcular_precio(self, galleta):
        """Calcula el precio según el tipo de venta"""
        # Acceder al peso individual desde la receta relacionada con TipoGalleta
        peso_individual = float(galleta.receta.pesoIndividualGalleta)  # Asegúrate de acceder correctamente a receta
        
        if self.tiposVentaNombre in ['pieza', 'especial']:
            precio = galleta.costo * self.cantidad
        elif self.tiposVentaNombre == 'gramo':
            precio = (galleta.costo / peso_individual) * self.cantidad
        elif self.tiposVentaNombre == 'kilo':
            precio = (galleta.costo * 1000 / peso_individual) * self.cantidad
        elif self.tiposVentaNombre == 'paquete_1kg':
            precio = 150 * self.cantidad  # Precio fijo $150 por paquete de 1kg
        elif self.tiposVentaNombre == 'paquete_700gr':
            precio = 105 * self.cantidad  # Precio fijo $105 por paquete de 700gr
        
        # Aplicar descuento si es especial
        if self.tiposVentaNombre == 'especial':
            precio *= 0.9
        
        return precio