from flask import Blueprint, render_template, request, redirect, url_for, session, Response
from bd import get_connection
import csv
from io import StringIO

asociado_bp = Blueprint('asociado_bp', __name__, url_prefix='/asociado')

@asociado_bp.route('/')
def asociado():
    if session.get('rol') != 'asociado':
        return redirect(url_for('auth.login'))
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id_asociado, a.prim_nom, a.prim_ape,
               a.num_ced, a.correo, a.tel, a.dir, a.muni, a.fecha_afi, a.estado
        FROM USUARIO u JOIN ASOCIADO a ON u.id_asociado = a.num_ced
        WHERE u.id = %s
    """, (session['id'],))
    perfil = cur.fetchone()
    cur.execute("SELECT prim_nom || ' ' || prim_ape, paren, porcen FROM BENEFICIARIO WHERE num_ced=%s", (perfil[0],))
    beneficiarios = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('asociado_perfil.html', perfil=perfil, beneficiarios=beneficiarios)

@asociado_bp.route('/cuentas', methods=['GET', 'POST'])
def asociado_cuentas():
    if session.get('rol') != 'asociado':
        return redirect(url_for('auth.login'))
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Obtener ID del asociado
    cur.execute("SELECT id_asociado FROM USUARIO WHERE id=%s", (session['id'],))
    num_ced = cur.fetchone()[0]
    
    # Obtener cuentas del asociado con saldo
    cur.execute("""
        SELECT c.num_cuent, c.estado, c.fecha_ape, ag.nombre,
               COALESCE(SUM(CASE WHEN m.tipo IN ('deposito','transferencia entrante') THEN m.valor
                                 WHEN m.tipo IN ('retiro','transferencia saliente') THEN -m.valor END), 0) AS saldo
        FROM CUENTAS c
        JOIN AGENCIA ag ON c.cod_agencia = ag.cod
        LEFT JOIN MOVIMIENTOS m ON m.num_cue = c.num_cuent
        WHERE c.ced_asociado=%s
        GROUP BY c.num_cuent, c.estado, c.fecha_ape, ag.nombre
    """, (num_ced,))
    cuentas = cur.fetchall()
    
    # Variables para extracto
    movimientos = []
    saldo_extracto = 0
    cuenta_seleccionada = None
    fecha_ini = ''
    fecha_fin = ''
    tipo_seleccionado = ''
    canal_seleccionado = ''
    
    if request.method == 'POST':
        # Obtener filtros del formulario
        num_cue = request.form.get('num_cue')
        fecha_ini = request.form.get('fecha_ini', '')
        fecha_fin = request.form.get('fecha_fin', '')
        tipo = request.form.get('tipo', '')
        canal = request.form.get('canal', '')
        
        # Validar que se haya seleccionado una cuenta
        if num_cue:
            # Construir consulta de movimientos con filtros
            query = """
                SELECT num_tran, fecha, hora, tipo, canal, valor
                FROM MOVIMIENTOS
                WHERE num_cue = %s
            """
            params = [num_cue]
            
            if fecha_ini:
                query += " AND fecha >= %s"
                params.append(fecha_ini)
            if fecha_fin:
                query += " AND fecha <= %s"
                params.append(fecha_fin)
            if tipo and tipo != 'Todos':
                query += " AND tipo = %s"
                params.append(tipo)
            if canal and canal != 'Todos':
                query += " AND canal = %s"
                params.append(canal)
            
            query += " ORDER BY fecha, hora"
            
            cur.execute(query, params)
            movimientos = cur.fetchall()
            
            # Calcular saldo hasta la fecha fin (o hasta hoy si no hay fecha fin)
            if fecha_fin:
                cur.execute("""
                    SELECT COALESCE(SUM(CASE WHEN tipo IN ('deposito','transferencia entrante') THEN valor
                                            WHEN tipo IN ('retiro','transferencia saliente') THEN -valor END), 0)
                    FROM MOVIMIENTOS
                    WHERE num_cue = %s AND fecha <= %s
                """, (num_cue, fecha_fin))
            else:
                cur.execute("""
                    SELECT COALESCE(SUM(CASE WHEN tipo IN ('deposito','transferencia entrante') THEN valor
                                            WHEN tipo IN ('retiro','transferencia saliente') THEN -valor END), 0)
                    FROM MOVIMIENTOS
                    WHERE num_cue = %s
                """, (num_cue,))
            saldo_extracto = cur.fetchone()[0]
            cuenta_seleccionada = num_cue
            tipo_seleccionado = tipo
            canal_seleccionado = canal
    
    cur.close()
    conn.close()
    
    return render_template('asociado_cuentas.html', 
                           cuentas=cuentas,
                           movimientos=movimientos,
                           saldo_extracto=saldo_extracto,
                           cuenta_seleccionada=cuenta_seleccionada,
                           fecha_ini=fecha_ini,
                           fecha_fin=fecha_fin,
                           tipo_seleccionado=tipo_seleccionado,
                           canal_seleccionado=canal_seleccionado)

@asociado_bp.route('/extracto/csv')
def descargar_extracto_csv():
    if session.get('rol') != 'asociado':
        return redirect(url_for('auth.login'))
    
    # Obtener parámetros de la URL
    num_cue = request.args.get('num_cue')
    fecha_ini = request.args.get('fecha_ini')
    fecha_fin = request.args.get('fecha_fin')
    tipo = request.args.get('tipo')
    canal = request.args.get('canal')
    
    if not num_cue or not fecha_ini or not fecha_fin:
        # Si faltan parámetros, redirigir a cuentas
        return redirect(url_for('asociado_bp.asociado_cuentas'))
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Construir consulta con filtros
    query = """
        SELECT num_tran, fecha, hora, tipo, canal, valor
        FROM MOVIMIENTOS
        WHERE num_cue = %s AND fecha BETWEEN %s AND %s
    """
    params = [num_cue, fecha_ini, fecha_fin]
    
    if tipo and tipo != 'Todos':
        query += " AND tipo = %s"
        params.append(tipo)
    if canal and canal != 'Todos':
        query += " AND canal = %s"
        params.append(canal)
    
    query += " ORDER BY fecha, hora"
    
    cur.execute(query, params)
    movimientos = cur.fetchall()
    cur.close()
    conn.close()
    
    # Crear CSV en memoria
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['N° Transacción', 'Fecha', 'Hora', 'Tipo', 'Canal', 'Valor'])
    for m in movimientos:
        writer.writerow([m[0], m[1], m[2], m[3], m[4], m[5]])
    
    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={
        'Content-Disposition': f'attachment; filename=extracto_cuenta_{num_cue}.csv'
    })

@asociado_bp.route('/creditos')
def asociado_creditos():
    if session.get('rol') != 'asociado':
        return redirect(url_for('auth.login'))
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id_asociado FROM USUARIO WHERE id=%s", (session['id'],))
    num_ced = cur.fetchone()[0]
    cur.execute("""
        SELECT cr.num_rad, lc.nombre_linea, cr.valor_aprob, cr.plazo,
               cr.estado, cr.fecha_prim_ven,
               COUNT(CASE WHEN p.estado != 'pendiente' THEN 1 END) AS cuotas_pagadas
        FROM CREDITO cr
        JOIN LINEA_CREDITO lc ON cr.cod_linea = lc.cod_linea
        LEFT JOIN PAGO p ON p.num_credito = cr.num_rad
        WHERE cr.ced_asociado=%s
        GROUP BY cr.num_rad, lc.nombre_linea, cr.valor_aprob, cr.plazo, cr.estado, cr.fecha_prim_ven
    """, (num_ced,))
    creditos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('asociado_creditos.html', creditos=creditos)

@asociado_bp.route('/actualizacion', methods=['GET', 'POST'])
def asociado_actualizacion():
    if session.get('rol') != 'asociado':
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        conn = get_connection()
        cur = conn.cursor()
        
        # Obtener el ID del asociado y su número de cédula
        cur.execute("SELECT id_asociado FROM USUARIO WHERE id=%s", (session['id'],))
        num_ced = cur.fetchone()[0]
        
        # Variables para registrar qué se modificó
        cambios = []
        
        if request.form.get('tel'):
            nuevo_tel = request.form['tel']
            cur.execute("UPDATE ASOCIADO SET tel=%s WHERE num_ced=%s", (nuevo_tel, num_ced))
            cambios.append(f"Teléfono actualizado a {nuevo_tel}")
        
        if request.form.get('correo'):
            nuevo_correo = request.form['correo']
            cur.execute("UPDATE ASOCIADO SET correo=%s WHERE num_ced=%s", (nuevo_correo, num_ced))
            cambios.append(f"Correo actualizado a {nuevo_correo}")
        
        if request.form.get('dir'):
            nueva_dir = request.form['dir']
            cur.execute("UPDATE ASOCIADO SET dir=%s WHERE num_ced=%s", (nueva_dir, num_ced))
            cambios.append(f"Dirección actualizada a {nueva_dir}")
        
        # Si hubo cambios, registrar en la bitácora
        if cambios:
            descripcion = f"Asociado {num_ced} actualizó: " + ", ".join(cambios)
            cur.execute("""
                INSERT INTO BITACORA (usuario_id, operacion)
                VALUES (%s, %s)
            """, (session['id'], descripcion))
        
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('asociado_bp.asociado'))
    
    return render_template('asociado_actualizacion.html')