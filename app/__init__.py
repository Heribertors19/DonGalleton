from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from flask_login import LoginManager
import os
from datetime import timedelta
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

mail = Mail()

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    secretKey = os.urandom(24)
    app.config["SECRET_KEY"] = secretKey

    #app.config["SQLALCHEMY_DATABASE_URI"] = (
        #"mysql://admin:f)dg*sdv*45dfv4*(eg*rt9e$r^t@dongalleto.czo0c2qug12y.us-east-2.rds.amazonaws.com/don_galleto"
    #)
    
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql://admin:f)dg*sdv*45dfv4*(eg*rt9e$r^t@dongalleto.czo0c2qug12y.us-east-2.rds.amazonaws.com/don_galleto")
    #app.config["SQLALCHEMY_DATABASE_URI"] = ("mysql://admin:f)dg*sdv*45dfv4*(eg*rt9e$r^t@dongalleto.czo0c2qug12y.us-east-2.rds.amazonaws.com/don_galleto")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    #app.config["SQLALCHEMY_DATABASE_URI"]= "mysql+pymysql://root:root@localhost/don_galleto"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=10)
    app.config["RECAPTCHA_PUBLIC_KEY"] = "6LeNBv4qAAAAABxh1YnTEsnadUUmb0BsIScbdVTy"
    app.config["RECAPTCHA_PRIVATE_KEY"] = "6LeNBv4qAAAAALstD0pAohuwGbISucZZbGwgalzM"
    csrf = CSRFProtect(app)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Servidor SMTP de Gmail
    app.config['MAIL_PORT'] = 587  # Puerto TLS de Gmail
    app.config['MAIL_USE_TLS'] = True  # Habilitar TLS para seguridad
    app.config['MAIL_USERNAME'] = 'mrcookiesoftware@gmail.com'
    app.config['MAIL_PASSWORD'] = 'sjucvnkioftpflpt'
    app.config['MAIL_DEFAULT_SENDER'] = 'mrcookiesoftware@gmail.com'
    
    mail.init_app(app)






    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from .models.Usuario import Usuario

    @login_manager.user_loader
    def load_user(username):
        return Usuario.query.get(username)

    from .routes.auth import auth

    from .routes.home import home_bp, inicio_bp, home_c

    from .routes.receta import receta_bp

    from .routes.insumo import insumo

    from .routes.mermas import mermas_bp
    
    from .routes.produccion import produccion_bp
    
    from .routes.stock import stock_bp
    
    from.routes.punto_venta import punto_venta_bp
    
    from.routes.proveedores import proveedores_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(inicio_bp)
    app.register_blueprint(home_c)
    app.register_blueprint(auth)
    app.register_blueprint(receta_bp)
    app.register_blueprint(insumo)
    app.register_blueprint(mermas_bp)
    app.register_blueprint(produccion_bp)
    app.register_blueprint(stock_bp)
    app.register_blueprint(punto_venta_bp)
    app.register_blueprint(proveedores_bp)


    with app.app_context():
        db.create_all()

    return app

