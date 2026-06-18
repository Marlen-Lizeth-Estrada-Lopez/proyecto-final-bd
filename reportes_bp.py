from flask import Blueprint, render_template, request, redirect, url_for, session
from bd import get_connection

reportes_bp = Blueprint('reportes_bp', __name__)

@reportes_bp.route('/reporte1')
def reporte1():
    if session.get('rol') not in ('administrador', 'asesor'):
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cur = conn.cursor()

    filtro = ""
    params = ()
    if session['rol'] == 'asesor':
        cur.execute("""
            SELECT e.cod_agencia
            FROM USUARIO u
            JOIN EMPLEADO e ON u.id_empleado = e.id
            WHERE u.id = %s
        """, (session['id'],))
        agencia = cur.fetchone()
        if agencia:
            filtro = "AND c.cod_agencia = %s"
            params = (agencia[0],)

    query = f"""
        SELECT a.num_ced,
               a.prim_ape || ' ' || COALESCE(a.seg_ape, '') AS apellidos,
               a.prim_nom || ' ' || COALESCE(a.seg_nom, '') AS nombres,
               a.estado, a.fecha_afi,
               CASE WHEN f.num_ced IS NOT NULL THEN 'Fundador' ELSE 'Regular' END AS tipo,
               ag.nombre AS agencia
        FROM ASOCIADO a
        LEFT JOIN FUNDADORES f ON a.num_ced = f.num_ced
        LEFT JOIN CUENTAS c ON c.ced_asociado = a.num_ced
        LEFT JOIN AGENCIA ag ON ag.cod = c.cod_agencia
        WHERE 1=1 {filtro}
        GROUP BY a.num_ced, a.prim_ape, a.seg_ape, a.prim_nom, a.seg_nom,
                 a.estado, a.fecha_afi, f.num_ced, ag.nombre
        ORDER BY a.prim_ape
    """
    cur.execute(query, params)
    asociados = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('reporte1.html', asociados=asociados)

@reportes_bp.route('/reporte2', methods=['GET', 'POST'])
def reporte2():
    if session.get('rol') not in ('administrador', 'asesor'):
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cur = conn.cursor()

    if session['rol'] == 'asesor':
        cur.execute("""
            SELECT e.cod_agencia
            FROM USUARIO u
            JOIN EMPLEADO e ON u.id_empleado = e.id
            WHERE u.id = %s
        """, (session['id'],))
        agencia = cur.fetchone()
        if agencia:
            cur.execute("SELECT num_cuent FROM CUENTAS WHERE cod_agencia = %s ORDER BY num_cuent", (agencia[0],))
        else:
            cur.execute("SELECT num_cuent FROM CUENTAS ORDER BY num_cuent")
    else:
        cur.execute("SELECT num_cuent FROM CUENTAS ORDER BY num_cuent")
    cuentas = cur.fetchall()

    movimientos = []
    saldo = 0
    if request.method == 'POST':
        num_cue = request.form['num_cue']
        fecha_ini = request.form['fecha_ini']
        fecha_fin = request.form['fecha_fin']
        cur.execute("""
            SELECT num_tran, fecha, hora, tipo, canal, valor
            FROM MOVIMIENTOS
            WHERE num_cue=%s AND fecha BETWEEN %s AND %s
            ORDER BY fecha, hora
        """, (num_cue, fecha_ini, fecha_fin))
        movimientos = cur.fetchall()
        cur.execute("""
            SELECT COALESCE(SUM(CASE WHEN tipo IN ('deposito','transferencia entrante') THEN valor
                                     WHEN tipo IN ('retiro','transferencia saliente') THEN -valor END), 0)
            FROM MOVIMIENTOS WHERE num_cue=%s AND fecha <= %s
        """, (num_cue, fecha_fin))
        saldo = cur.fetchone()[0]

    cur.close()
    conn.close()
    return render_template('reporte2.html', movimientos=movimientos, saldo=saldo, cuentas=cuentas)

@reportes_bp.route('/reporte3')
def reporte3():
    if session.get('rol') not in ('administrador', 'asesor'):
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cur = conn.cursor()

    filtro = ""
    params = ()
    if session['rol'] == 'asesor':
        cur.execute("""
            SELECT e.cod_agencia
            FROM USUARIO u
            JOIN EMPLEADO e ON u.id_empleado = e.id
            WHERE u.id = %s
        """, (session['id'],))
        agencia = cur.fetchone()
        if agencia:
            filtro = "AND cr.cod_agencia = %s"
            params = (agencia[0],)

    query = f"""
        SELECT lc.nombre_linea, cr.estado,
               COUNT(*) AS num_creditos,
               SUM(cr.valor_aprob) AS total_aprobado,
               ROUND(100.0 * SUM(cr.valor_aprob) / SUM(SUM(cr.valor_aprob)) OVER (), 2) AS porcentaje
        FROM CREDITO cr
        JOIN LINEA_CREDITO lc ON cr.cod_linea = lc.cod_linea
        WHERE cr.valor_aprob IS NOT NULL {filtro}
        GROUP BY lc.nombre_linea, cr.estado
        ORDER BY lc.nombre_linea
    """
    cur.execute(query, params)
    cartera = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('reporte3.html', cartera=cartera)

@reportes_bp.route('/reporte4')
def reporte4():
    if session.get('rol') not in ('administrador', 'asesor'):
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cur = conn.cursor()

    filtro = ""
    params = ()
    if session['rol'] == 'asesor':
        cur.execute("""
            SELECT e.cod_agencia
            FROM USUARIO u
            JOIN EMPLEADO e ON u.id_empleado = e.id
            WHERE u.id = %s
        """, (session['id'],))
        agencia = cur.fetchone()
        if agencia:
            filtro = "AND cr.cod_agencia = %s"
            params = (agencia[0],)

    query = f"""
        SELECT a.num_ced, a.prim_nom || ' ' || a.prim_ape AS nombre_asociado,
               cr.num_rad, p.num_cuota,
               (cr.fecha_prim_ven + ((p.num_cuota - 1) * INTERVAL '1 month'))::date AS fecha_vencimiento,
               (CURRENT_DATE - (cr.fecha_prim_ven + ((p.num_cuota - 1) * INTERVAL '1 month'))::date) AS dias_mora,
               e.prim_nom || ' ' || e.prim_ape AS nombre_asesor
        FROM PAGO p
        JOIN CREDITO cr ON p.num_credito = cr.num_rad
        JOIN ASOCIADO a ON cr.ced_asociado = a.num_ced
        JOIN ASESORIA aes ON aes.id_asociado = a.num_ced
        JOIN EMPLEADO e ON aes.id_emp = e.id
        WHERE p.estado = 'pendiente'
          AND cr.fecha_prim_ven IS NOT NULL
          AND (cr.fecha_prim_ven + ((p.num_cuota - 1) * INTERVAL '1 month'))::date < CURRENT_DATE
          AND aes.fecha_inicio = (SELECT MAX(fecha_inicio) FROM ASESORIA WHERE id_asociado = a.num_ced)
          {filtro}
        ORDER BY dias_mora DESC
    """
    cur.execute(query, params)
    mora = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('reporte4.html', mora=mora)

@reportes_bp.route('/reporte5', methods=['GET', 'POST'])
def reporte5():
    if session.get('rol') not in ('administrador', 'asesor'):
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cur = conn.cursor()

    if session['rol'] == 'asesor':
        cur.execute("""
            SELECT e.cod_agencia
            FROM USUARIO u
            JOIN EMPLEADO e ON u.id_empleado = e.id
            WHERE u.id = %s
        """, (session['id'],))
        agencia = cur.fetchone()
        if agencia:
            cur.execute("SELECT num_rad FROM CREDITO WHERE cod_agencia = %s AND estado NOT IN ('cancelado','castigado') ORDER BY num_rad", (agencia[0],))
        else:
            cur.execute("SELECT num_rad FROM CREDITO WHERE estado NOT IN ('cancelado','castigado') ORDER BY num_rad")
    else:
        cur.execute("SELECT num_rad FROM CREDITO WHERE estado NOT IN ('cancelado','castigado') ORDER BY num_rad")
    creditos = cur.fetchall()

    pagos = []
    if request.method == 'POST':
        num_credito = request.form['num_credito']
        cur.execute("""
            SELECT p.num_cuota,
                   (cr.fecha_prim_ven + ((p.num_cuota - 1) * INTERVAL '1 month'))::date AS fecha_prog,
                   p.fecha_pago, p.valor_pago, p.estado
            FROM PAGO p
            JOIN CREDITO cr ON p.num_credito = cr.num_rad
            WHERE p.num_credito=%s
            ORDER BY p.num_cuota
        """, (num_credito,))
        pagos = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('reporte5.html', pagos=pagos, creditos=creditos)

@reportes_bp.route('/reporte6')
def reporte6():
    if session.get('rol') not in ('administrador', 'asesor'):
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cur = conn.cursor()

    filtro = ""
    params = ()
    if session['rol'] == 'asesor':
        cur.execute("""
            SELECT e.cod_agencia
            FROM USUARIO u
            JOIN EMPLEADO e ON u.id_empleado = e.id
            WHERE u.id = %s
        """, (session['id'],))
        agencia = cur.fetchone()
        if agencia:
            filtro = "AND e.cod_agencia = %s"
            params = (agencia[0],)

    query = f"""
        SELECT e.id, e.prim_nom || ' ' || e.prim_ape AS nombre_asesor,
               ag.nombre AS agencia,
               COUNT(DISTINCT aes.id_asociado) AS asociados_atendidos,
               COUNT(DISTINCT cr.num_rad) AS creditos_radicados,
               COALESCE(SUM(cr.valor_aprob), 0) AS valor_total,
               COUNT(DISTINCT cu.num_cuent) AS cuentas_abiertas
        FROM EMPLEADO e
        JOIN AGENCIA ag ON e.cod_agencia = ag.cod
        LEFT JOIN ASESORIA aes ON aes.id_emp = e.id
        LEFT JOIN CREDITO cr ON cr.ced_asociado = aes.id_asociado AND cr.cod_agencia = e.cod_agencia
        LEFT JOIN CUENTAS cu ON cu.ced_asociado = aes.id_asociado AND cu.cod_agencia = e.cod_agencia
        WHERE e.cargo IN ('Asesor', 'Cajero') {filtro}
        GROUP BY e.id, e.prim_nom, e.prim_ape, ag.nombre
        ORDER BY asociados_atendidos DESC
    """
    cur.execute(query, params)
    productividad = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('reporte6.html', productividad=productividad)

@reportes_bp.route('/reporte7')
def reporte7():
    if session.get('rol') not in ('administrador', 'asesor'):
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cur = conn.cursor()

    filtro = ""
    params = ()
    if session['rol'] == 'asesor':
        cur.execute("""
            SELECT e.cod_agencia
            FROM USUARIO u
            JOIN EMPLEADO e ON u.id_empleado = e.id
            WHERE u.id = %s
        """, (session['id'],))
        agencia = cur.fetchone()
        if agencia:
            filtro = "AND cr.cod_agencia = %s"
            params = (agencia[0],)

    query = f"""
        SELECT cr.num_rad,
               at.num_ced, at.prim_nom || ' ' || at.prim_ape AS nombre_titular,
               ac.num_ced, ac.prim_nom || ' ' || ac.prim_ape AS nombre_codeudor,
               cr.valor_aprob, cd.fecha_fir, cr.estado, lc.nombre_linea
        FROM CODEUDOR cd
        JOIN CREDITO cr ON cd.num_credito = cr.num_rad
        JOIN ASOCIADO at ON cr.ced_asociado = at.num_ced
        JOIN ASOCIADO ac ON cd.ced_asociado = ac.num_ced
        JOIN LINEA_CREDITO lc ON cr.cod_linea = lc.cod_linea
        WHERE 1=1 {filtro}
        ORDER BY cr.num_rad
    """
    cur.execute(query, params)
    codeudores = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('reporte7.html', codeudores=codeudores)