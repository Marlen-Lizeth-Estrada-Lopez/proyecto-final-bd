from flask import Blueprint, render_template, request, redirect, url_for, session
from bd import get_connection
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena']
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, rol FROM USUARIO WHERE usuario = %s AND contrasena = %s", (usuario, contrasena))
        user = cur.fetchone()
        
        if user:
            session['id'] = user[0]
            session['rol'] = user[1]
            
            #REGISTRAR LOGIN EN BITÁCORA
            cur.execute("""
                INSERT INTO BITACORA (usuario_id, operacion)
                VALUES (%s, %s)
            """, (user[0], f"Inicio de sesión: {usuario} ({user[1]})"))
            conn.commit()
            
            cur.close()
            conn.close()
            
            if user[1] == 'administrador':
                return redirect(url_for('admin_bp.admin'))
            elif user[1] == 'asesor':
                return redirect(url_for('asesor_bp.asesor'))
            else:
                return redirect(url_for('asociado_bp.asociado'))
        else:
            cur.close()
            conn.close()
            return render_template('login.html', error='Usuario o contraseña incorrectos')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    if session.get('id'):
        conn = get_connection()
        cur = conn.cursor()
        #REGISTRAR LOGOUT EN BITÁCORA
        cur.execute("""
            INSERT INTO BITACORA (usuario_id, operacion)
            VALUES (%s, %s)
        """, (session['id'], f"Cierre de sesión: Usuario ID {session['id']}"))
        conn.commit()
        cur.close()
        conn.close()
    
    session.clear()
    return redirect(url_for('auth.login'))