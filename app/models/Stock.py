from app import db

class Stock(db.Model):
    __tablename__ = 'stock'  
    __table_args__ = {'extend_existing': True}

    idInsumo = db.Column(db.Integer, primary_key=True)
    nombre_insumo = db.Column(db.String(100))
    precio_unitario_actual = db.Column(db.Float)
    stock_total = db.Column(db.Float)
    idProveedor = db.Column(db.Integer)
    idPresentacion = db.Column(db.Integer)
    nombre_presentacion = db.Column(db.String(100))
    abreviatura_presentacion = db.Column(db.String(10))
    equivalencia_presentacion = db.Column(db.Float)
    idCategoria = db.Column(db.Integer)
    fecha_caducidad_mas_proxima = db.Column(db.Date)
