from flask import Blueprint, render_template, request, redirect, url_for, session
from bd import get_connection

comun_bp = Blueprint('comun_bp', __name__)

# CREAR ASOCIADO (no hay listado, ya está en Reporte 1)
@comun_bp.route('/asociados/nuevo', methods=['GET', 'POST'])
def crear_asociado():
    if session.get('rol') not in ('administrador', 'asesor'):
        return redirect(url_for('auth.login'))

    error = None
    if request.method == 'POST':
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT num_ced FROM ASOCIADO WHERE num_ced=%s", (request.form['num_ced'],))
        if cur.fetchone():
            error = 'Ya existe un asociado con esa cédula.'
        else:
            cur.execute("""
                INSERT INTO ASOCIADO (num_ced, prim_nom, seg_nom, prim_ape, seg_ape,
                                      fecha_nto, estado, correo, tel, muni, dir, fecha_afi)
                VALUES (%s,%s,%s,%s,%s,%s,'activo',%s,%s,%s,%s,%s)
            """, (request.form['num_ced'], request.form['prim_nom'], request.form.get('seg_nom'),
                  request.form['prim_ape'], request.form.get('seg_ape'), request.form['fecha_nto'],
                  request.form['correo'], request.form['tel'], request.form['muni'],
                  request.form['dir'], request.form['fecha_afi']))
            if request.form.get('es_fundador'):
                cur.execute("""
                    INSERT INTO FUNDADORES (num_ced, num_acta, anio_vec, descripcion)
                    VALUES (%s,%s,%s,%s)
                """, (request.form['num_ced'], request.form['num_acta'],
                      request.form['anio_vec'], request.form['descripcion']))
            conn.commit()
            cur.close()
            conn.close()
            # Redirigir al panel principal según el rol
            if session['rol'] == 'administrador':
                return redirect(url_for('admin_bp.admin'))
            else:
                return redirect(url_for('asesor_bp.asesor'))
        cur.close()
        conn.close()
    return render_template('asociado_form.html', error=error, rol=session['rol'])

# CREAR BENEFICIARIO
@comun_bp.route('/beneficiarios/nuevo', methods=['GET', 'POST'])
def crear_beneficiario():
    if session.get('rol') not in ('administrador', 'asesor'):
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO BENEFICIARIO (num_doc, num_ced, prim_nom, seg_nom, prim_ape, seg_ape, paren, porcen, tel)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (request.form['num_doc'], request.form['num_ced'], request.form['prim_nom'],
              request.form.get('seg_nom'), request.form['prim_ape'], request.form.get('seg_ape'),
              request.form['paren'], request.form['porcen'], request.form['tel']))
        conn.commit()
        cur.close()
        conn.close()
        if session['rol'] == 'administrador':
            return redirect(url_for('admin_bp.admin'))
        else:
            return redirect(url_for('asesor_bp.asesor'))
    return render_template('beneficiario_form.html', rol=session['rol'])

# CUENTAS (listado + creación)
@comun_bp.route('/cuentas')
def listar_cuentas():
    if session.get('rol') not in ('administrador', 'asesor'):
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cur = conn.cursor()

    if session['rol'] == 'administrador':
        cur.execute("""
            SELECT c.num_cuent, a.prim_nom || ' ' || a.prim_ape AS titular,
                   c.estado, c.fecha_ape, ag.nombre AS agencia
            FROM CUENTAS c
            JOIN ASOCIADO a ON c.ced_asociado = a.num_ced
            JOIN AGENCIA ag ON c.cod_agencia = ag.cod
            ORDER BY c.fecha_ape DESC
        """)
    else:
        cur.execute("""
            SELECT e.cod_agencia
            FROM USUARIO u
            JOIN EMPLEADO e ON u.id_empleado = e.id
            WHERE u.id = %s
        """, (session['id'],))
        agencia = cur.fetchone()
        if agencia:
            cur.execute("""
                SELECT c.num_cuent, a.prim_nom || ' ' || a.prim_ape AS titular,
                       c.estado, c.fecha_ape, ag.nombre AS agencia
                FROM CUENTAS c
                JOIN ASOCIADO a ON c.ced_asociado = a.num_ced
                JOIN AGENCIA ag ON c.cod_agencia = ag.cod
                WHERE c.cod_agencia = %s
                ORDER BY c.fecha_ape DESC
            """, (agencia[0],))
        else:
            cur.execute("SELECT * FROM CUENTAS WHERE 1=0")

    cuentas = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('cuentas.html', cuentas=cuentas, rol=session['rol'])

@comun_bp.route('/cuentas/nueva', methods=['GET', 'POST'])
def crear_cuenta():
    if session.get('rol') not in ('administrador', 'asesor'):
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cur = conn.cursor()

    agencia_asesor = None
    if session['rol'] == 'asesor':
        cur.execute("""
            SELECT e.cod_agencia
            FROM USUARIO u
            JOIN EMPLEADO e ON u.id_empleado = e.id
            WHERE u.id = %s
        """, (session['id'],))
        result = cur.fetchone()
        if result:
            agencia_asesor = result[0]

    if request.method == 'POST':
        num_cuent = request.form['num_cuent']
        fecha_ape = request.form['fecha_ape']
        ced_asociado = request.form['ced_asociado']
        cod_agencia = request.form['cod_agencia']

        if session['rol'] == 'asesor' and agencia_asesor:
            cod_agencia = agencia_asesor

        cur.execute("""
            INSERT INTO CUENTAS (num_cuent, estado, fecha_ape, ced_asociado, cod_agencia)
            VALUES (%s, 'activa', %s, %s, %s)
        """, (num_cuent, fecha_ape, ced_asociado, cod_agencia))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('comun_bp.listar_cuentas'))

    # GET: mostrar formulario
    cur.execute("SELECT num_ced, prim_nom || ' ' || prim_ape FROM ASOCIADO WHERE estado='activo'")
    asociados = cur.fetchall()

    if session['rol'] == 'administrador':
        cur.execute("SELECT cod, nombre FROM AGENCIA ORDER BY nombre")
        agencias = cur.fetchall()
    else:
        if agencia_asesor:
            cur.execute("SELECT cod, nombre FROM AGENCIA WHERE cod = %s", (agencia_asesor,))
            agencias = cur.fetchall()
        else:
            agencias = []

    cur.close()
    conn.close()
    return render_template('cuenta_form.html',
                           asociados=asociados,
                           agencias=agencias,
                           rol=session['rol'],
                           agencia_asesor=agencia_asesor)

# MOVIMIENTOS
@comun_bp.route('/movimientos/nuevo', methods=['GET', 'POST'])
def registrar_movimiento():
    if session.get('rol') not in ('administrador', 'asesor'):
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cur = conn.cursor()
    error = None

    if session['rol'] == 'asesor':
        cur.execute("""
            SELECT e.cod_agencia
            FROM USUARIO u
            JOIN EMPLEADO e ON u.id_empleado = e.id
            WHERE u.id = %s
        """, (session['id'],))
        agencia = cur.fetchone()
        if agencia:
            cur.execute("SELECT num_cuent FROM CUENTAS WHERE estado='activa' AND cod_agencia = %s ORDER BY num_cuent", (agencia[0],))
        else:
            cur.execute("SELECT num_cuent FROM CUENTAS WHERE 1=0")
    else:
        cur.execute("SELECT num_cuent FROM CUENTAS WHERE estado='activa' ORDER BY num_cuent")
    cuentas = cur.fetchall()

    if request.method == 'POST':
        num_tran = request.form['num_tran']
        tipo = request.form['tipo']
        canal = request.form['canal']
        valor = float(request.form['valor'])
        num_cue = request.form['num_cue']
        num_cue_destino = request.form.get('num_cue_destino') or None

        if tipo in ('retiro', 'transferencia saliente'):
            cur.execute("""
                SELECT COALESCE(SUM(CASE WHEN tipo IN ('deposito','transferencia entrante') THEN valor
                                        WHEN tipo IN ('retiro','transferencia saliente') THEN -valor END), 0)
                FROM MOVIMIENTOS WHERE num_cue = %s
            """, (num_cue,))
            saldo = cur.fetchone()[0]
            if saldo < valor:
                error = 'Saldo insuficiente para realizar el retiro o transferencia.'

        if not error:
            cur.execute("""
                INSERT INTO MOVIMIENTOS (num_tran, tipo, hora, fecha, canal, valor, num_cue, num_cue_destino)
                VALUES (%s, %s, CURRENT_TIME, CURRENT_DATE, %s, %s, %s, %s)
            """, (num_tran, tipo, canal, valor, num_cue, num_cue_destino))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('comun_bp.listar_cuentas'))

    cur.close()
    conn.close()
    return render_template('movimiento_form.html', cuentas=cuentas, error=error, rol=session['rol'])

# CRÉDITOS (listado + creación)
@comun_bp.route('/creditos')
def listar_creditos():
    if session.get('rol') not in ('administrador', 'asesor'):
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cur = conn.cursor()

    if session['rol'] == 'administrador':
        cur.execute("""
            SELECT cr.num_rad, a.prim_nom || ' ' || a.prim_ape AS titular,
                   lc.nombre_linea, cr.valor_aprob, cr.estado, cr.plazo,
                   ag.nombre AS agencia
            FROM CREDITO cr
            JOIN ASOCIADO a ON cr.ced_asociado = a.num_ced
            JOIN LINEA_CREDITO lc ON cr.cod_linea = lc.cod_linea
            JOIN AGENCIA ag ON cr.cod_agencia = ag.cod
            ORDER BY cr.num_rad DESC
        """)
    else:
        cur.execute("""
            SELECT e.cod_agencia
            FROM USUARIO u
            JOIN EMPLEADO e ON u.id_empleado = e.id
            WHERE u.id = %s
        """, (session['id'],))
        agencia = cur.fetchone()
        if agencia:
            cur.execute("""
                SELECT cr.num_rad, a.prim_nom || ' ' || a.prim_ape AS titular,
                       lc.nombre_linea, cr.valor_aprob, cr.estado, cr.plazo,
                       ag.nombre AS agencia
                FROM CREDITO cr
                JOIN ASOCIADO a ON cr.ced_asociado = a.num_ced
                JOIN LINEA_CREDITO lc ON cr.cod_linea = lc.cod_linea
                JOIN AGENCIA ag ON cr.cod_agencia = ag.cod
                WHERE cr.cod_agencia = %s
                ORDER BY cr.num_rad DESC
            """, (agencia[0],))
        else:
            cur.execute("SELECT * FROM CREDITO WHERE 1=0")

    creditos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('creditos.html', creditos=creditos, rol=session['rol'])

@comun_bp.route('/creditos/nuevo', methods=['GET', 'POST'])
def crear_credito():
    if session.get('rol') not in ('administrador', 'asesor'):
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cur = conn.cursor()

    agencia_asesor = None
    if session['rol'] == 'asesor':
        cur.execute("""
            SELECT e.cod_agencia
            FROM USUARIO u
            JOIN EMPLEADO e ON u.id_empleado = e.id
            WHERE u.id = %s
        """, (session['id'],))
        result = cur.fetchone()
        if result:
            agencia_asesor = result[0]

    if request.method == 'POST':
        num_rad = request.form['num_rad']
        valor_sol = request.form['valor_sol']
        plazo = int(request.form['plazo'])
        ced_asociado = request.form['ced_asociado']
        cod_linea = request.form['cod_linea']
        cod_agencia = request.form['cod_agencia']
        ced_codeudor = request.form.get('ced_codeudor')

        if session['rol'] == 'asesor' and agencia_asesor:
            cod_agencia = agencia_asesor

        # 1. Insertar el crédito
        cur.execute("""
            INSERT INTO CREDITO (num_rad, valor_sol, valor_aprob, estado, fecha_prim_ven,
                                 fecha_apro, plazo, ced_asociado, cod_linea, cod_agencia)
            VALUES (%s, %s, %s, 'en estudio', NULL, NULL, %s, %s, %s, %s)
        """, (num_rad, valor_sol, valor_sol, plazo, ced_asociado, cod_linea, cod_agencia))

        # 2. Generar el plan de pagos (una fila por cada cuota)
        for cuota in range(1, plazo + 1):
            cur.execute("""
                INSERT INTO PAGO (num_credito, num_cuota, estado, cod_agencia)
                VALUES (%s, %s, 'pendiente', %s)
            """, (num_rad, cuota, cod_agencia))

        # 3. Codeudor (opcional)
        if ced_codeudor:
            cur.execute("""
                INSERT INTO CODEUDOR (num_credito, ced_asociado, fecha_fir)
                VALUES (%s, %s, CURRENT_DATE)
            """, (num_rad, ced_codeudor))

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('comun_bp.listar_creditos'))

    # GET: mostrar formulario
    cur.execute("SELECT num_ced, prim_nom || ' ' || prim_ape FROM ASOCIADO WHERE estado='activo'")
    asociados = cur.fetchall()

    cur.execute("SELECT cod_linea, nombre_linea FROM LINEA_CREDITO")
    lineas = cur.fetchall()

    if session['rol'] == 'administrador':
        cur.execute("SELECT cod, nombre FROM AGENCIA ORDER BY nombre")
        agencias = cur.fetchall()
    else:
        if agencia_asesor:
            cur.execute("SELECT cod, nombre FROM AGENCIA WHERE cod = %s", (agencia_asesor,))
            agencias = cur.fetchall()
        else:
            agencias = []

    cur.close()
    conn.close()
    return render_template('credito_form.html',
                           asociados=asociados,
                           lineas=lineas,
                           agencias=agencias,
                           rol=session['rol'],
                           agencia_asesor=agencia_asesor)

# PAGOS
@comun_bp.route('/pagos/nuevo', methods=['GET', 'POST'])
def registrar_pago():
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
            cur.execute("SELECT num_rad FROM CREDITO WHERE estado NOT IN ('cancelado','castigado') AND cod_agencia = %s ORDER BY num_rad", (agencia[0],))
        else:
            cur.execute("SELECT num_rad FROM CREDITO WHERE 1=0")
    else:
        cur.execute("SELECT num_rad FROM CREDITO WHERE estado NOT IN ('cancelado','castigado') ORDER BY num_rad")
    creditos = cur.fetchall()

    if request.method == 'POST':
        num_credito = request.form['num_credito']
        num_cuota = request.form['num_cuota']
        valor_pago = request.form['valor_pago']

        cur.execute("""
            UPDATE PAGO SET estado = 'a tiempo', fecha_pago = CURRENT_DATE, valor_pago = %s
            WHERE num_credito = %s AND num_cuota = %s
        """, (valor_pago, num_credito, num_cuota))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('comun_bp.listar_creditos'))

    cur.close()
    conn.close()
    return render_template('pago_form.html', creditos=creditos, rol=session['rol'])