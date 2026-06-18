from flask import Blueprint, render_template, request, redirect, url_for, session
from bd import get_connection

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

@admin_bp.route('/')
def admin():
    if session.get('rol') != 'administrador':
        return redirect(url_for('auth.login'))
    return render_template('admin.html')

# ---------- AGENCIAS ----------
@admin_bp.route('/agencias')
def admin_agencias():
    if session.get('rol') != 'administrador':
        return redirect(url_for('auth.login'))
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT cod, nombre, munic, tel, fecha_ape, dir FROM AGENCIA ORDER BY nombre")
    agencias = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_agencias.html', agencias=agencias)

@admin_bp.route('/agencias/nueva', methods=['GET', 'POST'])
def admin_agencia_nueva():
    if session.get('rol') != 'administrador':
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO AGENCIA (cod, nombre, munic, tel, fecha_ape, dir)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (request.form['cod'], request.form['nombre'], request.form['munic'],
              request.form['tel'], request.form['fecha_ape'], request.form['dir']))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('admin_bp.admin_agencias'))
    return render_template('admin_agencia_form.html', agencia=None)

@admin_bp.route('/agencias/editar/<int:cod>', methods=['GET', 'POST'])
def admin_agencia_editar(cod):
    if session.get('rol') != 'administrador':
        return redirect(url_for('auth.login'))
    conn = get_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        cur.execute("""
            UPDATE AGENCIA SET nombre=%s, munic=%s, tel=%s, dir=%s WHERE cod=%s
        """, (request.form['nombre'], request.form['munic'],
              request.form['tel'], request.form['dir'], cod))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('admin_bp.admin_agencias'))
    cur.execute("SELECT cod, nombre, munic, tel, fecha_ape, dir FROM AGENCIA WHERE cod=%s", (cod,))
    agencia = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('admin_agencia_form.html', agencia=agencia)

# ---------- EMPLEADOS ----------
@admin_bp.route('/empleados')
def admin_empleados():
    if session.get('rol') != 'administrador':
        return redirect(url_for('auth.login'))
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT e.id, e.prim_nom || ' ' || e.prim_ape AS nombre, e.cargo,
               e.est_lab, ag.nombre AS agencia,
               s.prim_nom || ' ' || s.prim_ape AS supervisor
        FROM EMPLEADO e
        JOIN AGENCIA ag ON e.cod_agencia = ag.cod
        LEFT JOIN EMPLEADO s ON e.supervisor_id = s.id
        ORDER BY e.prim_ape
    """)
    empleados = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_empleados.html', empleados=empleados)

@admin_bp.route('/empleados/nuevo', methods=['GET', 'POST'])
def admin_empleado_nuevo():
    if session.get('rol') != 'administrador':
        return redirect(url_for('auth.login'))
    conn = get_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        cur.execute("""
            INSERT INTO EMPLEADO (id, prim_nom, seg_nom, prim_ape, seg_ape, cargo,
                                  fecha_ingre, sal_base, correo_corp, est_lab, cod_agencia, supervisor_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (request.form['id'], request.form['prim_nom'], request.form.get('seg_nom'),
              request.form['prim_ape'], request.form.get('seg_ape'), request.form['cargo'],
              request.form['fecha_ingre'], request.form['sal_base'], request.form['correo_corp'],
              request.form['est_lab'], request.form['cod_agencia'],
              request.form.get('supervisor_id') or None))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('admin_bp.admin_empleados'))
    cur.execute("SELECT cod, nombre FROM AGENCIA ORDER BY nombre")
    agencias = cur.fetchall()
    cur.execute("SELECT id, prim_nom || ' ' || prim_ape FROM EMPLEADO ORDER BY prim_ape")
    supervisores = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_empleado_form.html', empleado=None, agencias=agencias, supervisores=supervisores)

# ---------- USUARIOS ----------
@admin_bp.route('/usuarios')
def admin_usuarios():
    if session.get('rol') != 'administrador':
        return redirect(url_for('auth.login'))
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, usuario, rol FROM USUARIO ORDER BY rol")
    usuarios = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_usuarios.html', usuarios=usuarios)

@admin_bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
def admin_usuario_nuevo():
    if session.get('rol') != 'administrador':
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO USUARIO (usuario, contrasena, rol, id_empleado, id_asociado)
            VALUES (%s, %s, %s, %s, %s)
        """, (request.form['usuario'], request.form['contrasena'], request.form['rol'],
              request.form.get('id_empleado') or None, request.form.get('id_asociado') or None))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('admin_bp.admin_usuarios'))
    return render_template('admin_usuario_form.html')

@admin_bp.route('/usuarios/reset/<int:id>', methods=['POST'])
def admin_reset_password(id):
    if session.get('rol') != 'administrador':
        return redirect(url_for('auth.login'))
    nueva = request.form['nueva_contrasena']
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE USUARIO SET contrasena=%s WHERE id=%s", (nueva, id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('admin_bp.admin_usuarios'))

# ---------- BITÁCORA ----------
@admin_bp.route('/bitacora')
def admin_bitacora():
    if session.get('rol') != 'administrador':
        return redirect(url_for('auth.login'))
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id, u.usuario, b.operacion, b.fecha_hora
        FROM BITACORA b
        JOIN USUARIO u ON b.usuario_id = u.id
        ORDER BY b.fecha_hora DESC
    """)
    registros = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_bitacora.html', registros=registros)