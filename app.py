from flask import Flask
from auth import auth_bp
from admin_bp import admin_bp
from asesor_bp import asesor_bp
from asociado_bp import asociado_bp
from reportes_bp import reportes_bp
from comun_bp import comun_bp

app = Flask(__name__)
app.secret_key = 'coovalluna2026'

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)       # /admin/agencias, /admin/empleados, /admin/usuarios, /admin/bitacora
app.register_blueprint(asesor_bp)      # solo /asesor (dashboard)
app.register_blueprint(asociado_bp)    # /asociado/*
app.register_blueprint(reportes_bp)    # /reporte1 ... /reporte7
app.register_blueprint(comun_bp)       # TODO lo compartido

if __name__ == '__main__':
    app.run(debug=True)