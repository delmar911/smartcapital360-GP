"""
SmartCapital 360° - Sistema Inteligente de Control de Accesos
MVP - Backend Flask + SQLite
Proyecto: Gerencia de Proyectos - Politécnico Grancolombiano
Estudiante: Maria Del Mar Artunduaga Artunduaga
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
import secrets

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

# Usar variable de entorno en producción, fallback para desarrollo local
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'db', 'smartcapital.db')

# ─────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS perfil_acceso (
        id_perfil     INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_perfil TEXT NOT NULL,
        descripcion   TEXT,
        horario_inicio TEXT DEFAULT '00:00',
        horario_fin    TEXT DEFAULT '23:59',
        activo        INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS usuario (
        id_usuario    INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre        TEXT NOT NULL,
        apellido      TEXT NOT NULL,
        email         TEXT UNIQUE NOT NULL,
        documento     TEXT UNIQUE NOT NULL,
        id_perfil     INTEGER REFERENCES perfil_acceso(id_perfil),
        estado        INTEGER DEFAULT 1,
        password_hash TEXT,
        rol_sistema   TEXT DEFAULT 'empleado',
        fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS zona (
        id_zona        INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre         TEXT NOT NULL,
        descripcion    TEXT,
        piso           INTEGER,
        nivel_seguridad TEXT DEFAULT 'BAJO'
    );

    CREATE TABLE IF NOT EXISTS controlador (
        id_controlador INTEGER PRIMARY KEY AUTOINCREMENT,
        modelo         TEXT,
        ip_address     TEXT,
        estado_conexion TEXT DEFAULT 'ACTIVO'
    );

    CREATE TABLE IF NOT EXISTS punto_acceso (
        id_punto       INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre         TEXT NOT NULL,
        ubicacion      TEXT,
        tipo_acceso    TEXT DEFAULT 'PEATONAL',
        estado         TEXT DEFAULT 'CERRADO',
        modo_emergencia INTEGER DEFAULT 0,
        id_zona        INTEGER REFERENCES zona(id_zona),
        id_controlador INTEGER REFERENCES controlador(id_controlador)
    );

    CREATE TABLE IF NOT EXISTS credencial (
        id_credencial  INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario     INTEGER REFERENCES usuario(id_usuario),
        codigo_rfid    TEXT UNIQUE,
        tipo_rfid      TEXT DEFAULT 'MIFARE',
        activa         INTEGER DEFAULT 1,
        fecha_expiracion DATETIME
    );

    CREATE TABLE IF NOT EXISTS permiso_perfil_punto (
        id_perfil  INTEGER REFERENCES perfil_acceso(id_perfil),
        id_punto   INTEGER REFERENCES punto_acceso(id_punto),
        PRIMARY KEY (id_perfil, id_punto)
    );

    CREATE TABLE IF NOT EXISTS evento_acceso (
        id_evento   INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario  INTEGER REFERENCES usuario(id_usuario),
        id_punto    INTEGER REFERENCES punto_acceso(id_punto),
        id_credencial INTEGER REFERENCES credencial(id_credencial),
        timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
        resultado   TEXT DEFAULT 'AUTORIZADO',
        metodo_auth TEXT DEFAULT 'RFID',
        observacion TEXT
    );

    CREATE TABLE IF NOT EXISTS alerta (
        id_alerta         INTEGER PRIMARY KEY AUTOINCREMENT,
        id_evento         INTEGER REFERENCES evento_acceso(id_evento),
        tipo_alerta       TEXT,
        timestamp_emision DATETIME DEFAULT CURRENT_TIMESTAMP,
        estado            TEXT DEFAULT 'PENDIENTE',
        id_operador       INTEGER REFERENCES usuario(id_usuario),
        observacion_cierre TEXT
    );

    CREATE TABLE IF NOT EXISTS visitante (
        id_visitante  INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario    INTEGER REFERENCES usuario(id_usuario),
        empresa       TEXT,
        motivo_visita TEXT,
        id_anfitrion  INTEGER REFERENCES usuario(id_usuario),
        fecha_inicio  DATETIME,
        fecha_fin     DATETIME
    );
    """)

    # Seed data if empty
    c.execute("SELECT COUNT(*) FROM perfil_acceso")
    if c.fetchone()[0] == 0:
        c.executescript("""
        INSERT INTO perfil_acceso (nombre_perfil, descripcion, horario_inicio, horario_fin) VALUES
            ('Administrador','Acceso total al sistema','00:00','23:59'),
            ('Directivo','Acceso a todas las zonas del edificio','06:00','22:00'),
            ('Empleado','Acceso a zonas comunes y oficina asignada','07:00','19:00'),
            ('Seguridad','Acceso a consola de monitoreo y zonas operativas','00:00','23:59'),
            ('Visitante','Acceso temporal a zonas autorizadas','08:00','18:00');

        INSERT INTO controlador (modelo, ip_address, estado_conexion) VALUES
            ('HID VertX V1000','192.168.1.10','ACTIVO'),
            ('HID VertX V2000','192.168.1.11','ACTIVO');

        INSERT INTO zona (nombre, descripcion, piso, nivel_seguridad) VALUES
            ('Lobby Principal','Entrada principal del edificio',1,'BAJO'),
            ('Parqueadero','Zona de estacionamiento vehicular',0,'BAJO'),
            ('Piso 3 - Oficinas','Área de trabajo administrativo',3,'MEDIO'),
            ('Piso 5 - Directivos','Área de alta gerencia',5,'ALTO'),
            ('Sala de Servidores','Datacenter del edificio',2,'CRITICO');

        INSERT INTO punto_acceso (nombre, ubicacion, tipo_acceso, id_zona, id_controlador) VALUES
            ('Torniquete Lobby A','Entrada principal lobby',           'PEATONAL',1,1),
            ('Torniquete Lobby B','Entrada secundaria lobby',          'PEATONAL',1,1),
            ('Barrera Parqueadero','Entrada vehicular parqueadero',    'VEHICULAR',2,1),
            ('Puerta Piso 3','Acceso a oficinas piso 3',              'PEATONAL',3,2),
            ('Puerta Piso 5 VIP','Acceso a zona directivos piso 5',   'PEATONAL',4,2),
            ('Sala Servidores','Acceso al datacenter',                 'PEATONAL',5,2);

        INSERT INTO permiso_perfil_punto VALUES
            (1,1),(1,2),(1,3),(1,4),(1,5),(1,6),
            (2,1),(2,2),(2,3),(2,4),(2,5),
            (3,1),(3,2),(3,3),(3,4),
            (4,1),(4,2),(4,3),(4,4),(4,5),(4,6),
            (5,1),(5,3);
        """)

        admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("""INSERT INTO usuario (nombre,apellido,email,documento,id_perfil,estado,password_hash,rol_sistema)
                     VALUES ('Admin','Sistema','admin@smartcapital.co','000000001',1,1,?,'admin')""", (admin_hash,))
        admin_id = c.lastrowid
        c.execute("INSERT INTO credencial (id_usuario, codigo_rfid, tipo_rfid) VALUES (?,?,?)",
                  (admin_id, 'RFID-ADMIN-001', 'MIFARE'))

        emp_hash = hashlib.sha256("emp123".encode()).hexdigest()
        c.execute("""INSERT INTO usuario (nombre,apellido,email,documento,id_perfil,estado,password_hash,rol_sistema)
                     VALUES ('Carlos','Rodríguez','carlos.rodriguez@smartcapital.co','123456789',3,1,?,'empleado')""", (emp_hash,))
        emp_id = c.lastrowid
        c.execute("INSERT INTO credencial (id_usuario, codigo_rfid) VALUES (?,?)", (emp_id, 'RFID-EMP-001'))

        c.execute("""INSERT INTO usuario (nombre,apellido,email,documento,id_perfil,estado,password_hash,rol_sistema)
                     VALUES ('Ana','Martínez','ana.martinez@smartcapital.co','987654321',2,1,?,'empleado')""", (emp_hash,))
        dir_id = c.lastrowid
        c.execute("INSERT INTO credencial (id_usuario, codigo_rfid) VALUES (?,?)", (dir_id, 'RFID-DIR-001'))

        seg_hash = hashlib.sha256("seg123".encode()).hexdigest()
        c.execute("""INSERT INTO usuario (nombre,apellido,email,documento,id_perfil,estado,password_hash,rol_sistema)
                     VALUES ('Pedro','Gómez','pedro.gomez@smartcapital.co','555000111',4,1,?,'seguridad')""", (seg_hash,))
        seg_id = c.lastrowid
        c.execute("INSERT INTO credencial (id_usuario, codigo_rfid) VALUES (?,?)", (seg_id, 'RFID-SEG-001'))

        eventos = [
            (emp_id, 1, 1, 'AUTORIZADO', 'RFID', ''),
            (dir_id, 5, 2, 'AUTORIZADO', 'RFID', ''),
            (emp_id, 4, 1, 'AUTORIZADO', 'RFID', ''),
            (None,   1, None, 'DENEGADO', 'RFID', 'Credencial no reconocida'),
            (emp_id, 5, 1, 'DENEGADO', 'RFID', 'Perfil sin permiso para esta zona'),
        ]
        for ev in eventos:
            c.execute("""INSERT INTO evento_acceso (id_usuario,id_punto,id_credencial,resultado,metodo_auth,observacion)
                         VALUES (?,?,?,?,?,?)""", ev)

        c.execute("SELECT id_evento FROM evento_acceso WHERE resultado='DENEGADO' LIMIT 1")
        ev_row = c.fetchone()
        if ev_row:
            c.execute("""INSERT INTO alerta (id_evento, tipo_alerta, estado)
                         VALUES (?, 'INTENTOS_MULTIPLES', 'PENDIENTE')""", (ev_row[0],))

    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/', methods=['GET'])
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        conn = get_db()
        user = conn.execute("""SELECT u.*, p.nombre_perfil FROM usuario u
                               JOIN perfil_acceso p ON u.id_perfil = p.id_perfil
                               WHERE u.email=? AND u.password_hash=? AND u.estado=1""",
                            (email, pw_hash)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id_usuario']
            session['user_name'] = f"{user['nombre']} {user['apellido']}"
            session['user_role'] = user['rol_sistema']
            session['user_perfil'] = user['nombre_perfil']
            return redirect(url_for('dashboard'))
        error = "Credenciales incorrectas o usuario inactivo."
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    stats = {
        'total_usuarios': conn.execute("SELECT COUNT(*) FROM usuario WHERE estado=1").fetchone()[0],
        'total_puntos': conn.execute("SELECT COUNT(*) FROM punto_acceso").fetchone()[0],
        'eventos_hoy': conn.execute("SELECT COUNT(*) FROM evento_acceso WHERE DATE(timestamp)=DATE('now')").fetchone()[0],
        'alertas_pendientes': conn.execute("SELECT COUNT(*) FROM alerta WHERE estado='PENDIENTE'").fetchone()[0],
        'accesos_autorizados': conn.execute("SELECT COUNT(*) FROM evento_acceso WHERE resultado='AUTORIZADO'").fetchone()[0],
        'accesos_denegados': conn.execute("SELECT COUNT(*) FROM evento_acceso WHERE resultado='DENEGADO'").fetchone()[0],
    }
    eventos_recientes = conn.execute("""
        SELECT e.*, u.nombre||' '||u.apellido as nombre_usuario, pa.nombre as punto_nombre
        FROM evento_acceso e
        LEFT JOIN usuario u ON e.id_usuario=u.id_usuario
        LEFT JOIN punto_acceso pa ON e.id_punto=pa.id_punto
        ORDER BY e.timestamp DESC LIMIT 10
    """).fetchall()
    alertas = conn.execute("""
        SELECT a.*, pa.nombre as punto_nombre
        FROM alerta a
        LEFT JOIN evento_acceso e ON a.id_evento=e.id_evento
        LEFT JOIN punto_acceso pa ON e.id_punto=pa.id_punto
        WHERE a.estado='PENDIENTE' ORDER BY a.timestamp_emision DESC LIMIT 5
    """).fetchall()
    conn.close()
    return render_template('dashboard.html', stats=stats, eventos=eventos_recientes, alertas=alertas)

# ─────────────────────────────────────────────
# USUARIOS
# ─────────────────────────────────────────────

@app.route('/usuarios')
@login_required
def usuarios():
    conn = get_db()
    users = conn.execute("""SELECT u.*, p.nombre_perfil FROM usuario u
                            JOIN perfil_acceso p ON u.id_perfil=p.id_perfil
                            ORDER BY u.nombre""").fetchall()
    perfiles = conn.execute("SELECT * FROM perfil_acceso WHERE activo=1").fetchall()
    conn.close()
    return render_template('usuarios.html', users=users, perfiles=perfiles)

@app.route('/usuarios/crear', methods=['POST'])
@login_required
def crear_usuario():
    data = request.form
    pw_hash = hashlib.sha256(data['password'].encode()).hexdigest()
    try:
        conn = get_db()
        conn.execute("""INSERT INTO usuario (nombre,apellido,email,documento,id_perfil,password_hash,rol_sistema)
                        VALUES (?,?,?,?,?,?,?)""",
                     (data['nombre'], data['apellido'], data['email'], data['documento'],
                      data['id_perfil'], pw_hash, data.get('rol_sistema','empleado')))
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        rfid = f"RFID-{data['documento'][-6:]}-{uid:04d}"
        conn.execute("INSERT INTO credencial (id_usuario, codigo_rfid) VALUES (?,?)", (uid, rfid))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Usuario creado. RFID asignado: {rfid}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/usuarios/toggle/<int:uid>', methods=['POST'])
@login_required
def toggle_usuario(uid):
    conn = get_db()
    user = conn.execute("SELECT estado FROM usuario WHERE id_usuario=?", (uid,)).fetchone()
    nuevo = 0 if user['estado'] == 1 else 1
    conn.execute("UPDATE usuario SET estado=? WHERE id_usuario=?", (nuevo, uid))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'nuevo_estado': nuevo})

# ─────────────────────────────────────────────
# ACCESO SIMULADO
# ─────────────────────────────────────────────

@app.route('/acceso')
@login_required
def acceso():
    conn = get_db()
    puntos = conn.execute("SELECT * FROM punto_acceso ORDER BY nombre").fetchall()
    credenciales = conn.execute("""SELECT c.*, u.nombre||' '||u.apellido as nombre_usuario
                                   FROM credencial c JOIN usuario u ON c.id_usuario=u.id_usuario
                                   WHERE c.activa=1""").fetchall()
    conn.close()
    return render_template('acceso.html', puntos=puntos, credenciales=credenciales)

@app.route('/api/simular_acceso', methods=['POST'])
@login_required
def simular_acceso():
    data = request.get_json()
    rfid = data.get('rfid', '').strip()
    id_punto = int(data.get('id_punto', 0))

    conn = get_db()
    cred = conn.execute("""SELECT c.*, u.id_usuario, u.id_perfil, u.nombre||' '||u.apellido as nombre_usuario, u.estado
                           FROM credencial c JOIN usuario u ON c.id_usuario=u.id_usuario
                           WHERE c.codigo_rfid=? AND c.activa=1""", (rfid,)).fetchone()

    if not cred or not cred['estado']:
        conn.execute("""INSERT INTO evento_acceso (id_punto, resultado, metodo_auth, observacion)
                        VALUES (?,?,?,?)""", (id_punto, 'DENEGADO', 'RFID', 'Credencial no reconocida'))
        conn.commit()
        conn.close()
        return jsonify({'resultado': 'DENEGADO', 'mensaje': 'Credencial no reconocida o inactiva', 'color': 'red'})

    if cred['fecha_expiracion']:
        if datetime.now() > datetime.fromisoformat(cred['fecha_expiracion']):
            conn.execute("""INSERT INTO evento_acceso (id_usuario,id_punto,id_credencial,resultado,metodo_auth,observacion)
                            VALUES (?,?,?,?,?,?)""",
                         (cred['id_usuario'], id_punto, cred['id_credencial'], 'DENEGADO', 'RFID', 'Credencial expirada'))
            conn.commit()
            conn.close()
            return jsonify({'resultado': 'DENEGADO', 'mensaje': 'Credencial expirada', 'color': 'red'})

    permiso = conn.execute("""SELECT 1 FROM permiso_perfil_punto
                              WHERE id_perfil=? AND id_punto=?""",
                           (cred['id_perfil'], id_punto)).fetchone()

    punto = conn.execute("SELECT * FROM punto_acceso WHERE id_punto=?", (id_punto,)).fetchone()
    if punto['modo_emergencia']:
        resultado = 'AUTORIZADO'
        obs = 'Acceso por modo emergencia'
    elif permiso:
        resultado = 'AUTORIZADO'
        obs = ''
    else:
        resultado = 'DENEGADO'
        obs = 'Perfil sin permiso para esta zona'

    conn.execute("""INSERT INTO evento_acceso (id_usuario,id_punto,id_credencial,resultado,metodo_auth,observacion)
                    VALUES (?,?,?,?,?,?)""",
                 (cred['id_usuario'], id_punto, cred['id_credencial'], resultado, 'RFID', obs))

    if resultado == 'DENEGADO':
        ev_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        n_denied = conn.execute("""SELECT COUNT(*) FROM evento_acceso
                                   WHERE id_usuario=? AND id_punto=? AND resultado='DENEGADO'
                                   AND timestamp > datetime('now','-10 minutes')""",
                                (cred['id_usuario'], id_punto)).fetchone()[0]
        if n_denied >= 2:
            conn.execute("INSERT INTO alerta (id_evento, tipo_alerta) VALUES (?, 'INTENTOS_MULTIPLES')", (ev_id,))

    conn.commit()
    conn.close()

    return jsonify({
        'resultado': resultado,
        'mensaje': f"{'✅ Acceso autorizado' if resultado=='AUTORIZADO' else '❌ Acceso denegado'} — {cred['nombre_usuario']}",
        'color': 'green' if resultado == 'AUTORIZADO' else 'red',
        'obs': obs
    })

# ─────────────────────────────────────────────
# EMERGENCIA
# ─────────────────────────────────────────────

@app.route('/api/emergencia', methods=['POST'])
@login_required
def activar_emergencia():
    data = request.get_json()
    activar = data.get('activar', True)
    conn = get_db()
    conn.execute("UPDATE punto_acceso SET modo_emergencia=?, estado=?",
                 (1 if activar else 0, 'ABIERTO' if activar else 'CERRADO'))
    conn.commit()
    conn.close()
    msg = "🚨 MODO EMERGENCIA ACTIVADO — Todas las puertas abiertas" if activar else "✅ Modo normal restaurado"
    return jsonify({'success': True, 'mensaje': msg})

# ─────────────────────────────────────────────
# ALERTAS
# ─────────────────────────────────────────────

@app.route('/alertas')
@login_required
def alertas():
    conn = get_db()
    als = conn.execute("""SELECT a.*, pa.nombre as punto_nombre,
                          u.nombre||' '||u.apellido as operador_nombre,
                          uu.nombre||' '||uu.apellido as usuario_acceso
                          FROM alerta a
                          LEFT JOIN evento_acceso e ON a.id_evento=e.id_evento
                          LEFT JOIN punto_acceso pa ON e.id_punto=pa.id_punto
                          LEFT JOIN usuario u ON a.id_operador=u.id_usuario
                          LEFT JOIN usuario uu ON e.id_usuario=uu.id_usuario
                          ORDER BY a.timestamp_emision DESC""").fetchall()
    conn.close()
    return render_template('alertas.html', alertas=als)

@app.route('/api/atender_alerta/<int:aid>', methods=['POST'])
@login_required
def atender_alerta(aid):
    obs = request.get_json().get('observacion', '')
    conn = get_db()
    conn.execute("""UPDATE alerta SET estado='ATENDIDA', id_operador=?, observacion_cierre=?,
                    timestamp_emision=datetime('now') WHERE id_alerta=?""",
                 (session['user_id'], obs, aid))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ─────────────────────────────────────────────
# REPORTES
# ─────────────────────────────────────────────

@app.route('/reportes')
@login_required
def reportes():
    conn = get_db()
    puntos = conn.execute("SELECT * FROM punto_acceso").fetchall()
    conn.close()
    return render_template('reportes.html', puntos=puntos)

@app.route('/api/reporte_eventos')
@login_required
def reporte_eventos():
    fecha_ini = request.args.get('fecha_ini', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
    fecha_fin = request.args.get('fecha_fin', datetime.now().strftime('%Y-%m-%d'))
    resultado = request.args.get('resultado', '')
    id_punto = request.args.get('id_punto', '')

    query = """SELECT e.id_evento, e.timestamp, e.resultado, e.metodo_auth, e.observacion,
                      u.nombre||' '||u.apellido as usuario, pa.nombre as punto
               FROM evento_acceso e
               LEFT JOIN usuario u ON e.id_usuario=u.id_usuario
               LEFT JOIN punto_acceso pa ON e.id_punto=pa.id_punto
               WHERE DATE(e.timestamp) BETWEEN ? AND ?"""
    params = [fecha_ini, fecha_fin]
    if resultado:
        query += " AND e.resultado=?"; params.append(resultado)
    if id_punto:
        query += " AND e.id_punto=?"; params.append(id_punto)
    query += " ORDER BY e.timestamp DESC LIMIT 200"

    conn = get_db()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ─────────────────────────────────────────────
# VISITANTES
# ─────────────────────────────────────────────

@app.route('/visitantes')
@login_required
def visitantes():
    conn = get_db()
    vs = conn.execute("""SELECT v.*, u.nombre||' '||u.apellido as nombre_usuario,
                         a.nombre||' '||a.apellido as nombre_anfitrion,
                         c.codigo_rfid
                         FROM visitante v
                         JOIN usuario u ON v.id_usuario=u.id_usuario
                         JOIN usuario a ON v.id_anfitrion=a.id_usuario
                         LEFT JOIN credencial c ON c.id_usuario=u.id_usuario
                         ORDER BY v.fecha_inicio DESC""").fetchall()
    empleados = conn.execute("""SELECT id_usuario, nombre||' '||apellido as nombre
                                FROM usuario WHERE estado=1 AND rol_sistema!='visitante'""").fetchall()
    conn.close()
    return render_template('visitantes.html', visitantes=vs, empleados=empleados)

@app.route('/visitantes/crear', methods=['POST'])
@login_required
def crear_visitante():
    d = request.form
    pw_hash = hashlib.sha256("visitante123".encode()).hexdigest()
    try:
        conn = get_db()
        perfil_vis = conn.execute("SELECT id_perfil FROM perfil_acceso WHERE nombre_perfil='Visitante'").fetchone()
        conn.execute("""INSERT INTO usuario (nombre,apellido,email,documento,id_perfil,password_hash,rol_sistema)
                        VALUES (?,?,?,?,?,?,'visitante')""",
                     (d['nombre'], d['apellido'],
                      f"vis.{d['documento']}@smartcapital.co", d['documento'],
                      perfil_vis['id_perfil'], pw_hash))
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        rfid_temp = f"TEMP-{d['documento'][-4:]}-{uid:04d}"
        conn.execute("""INSERT INTO credencial (id_usuario, codigo_rfid, tipo_rfid, fecha_expiracion)
                        VALUES (?,?,?,?)""", (uid, rfid_temp, 'TEMP', d['fecha_fin']))
        conn.execute("""INSERT INTO visitante (id_usuario,empresa,motivo_visita,id_anfitrion,fecha_inicio,fecha_fin)
                        VALUES (?,?,?,?,?,?)""",
                     (uid, d.get('empresa',''), d.get('motivo',''),
                      d['anfitrion'], d['fecha_ini'], d['fecha_fin']))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'rfid_temporal': rfid_temp})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ─────────────────────────────────────────────
# PUNTOS DE ACCESO
# ─────────────────────────────────────────────

@app.route('/puntos')
@login_required
def puntos():
    conn = get_db()
    pts = conn.execute("""SELECT pa.*, z.nombre as zona_nombre, k.modelo as controlador_modelo
                          FROM punto_acceso pa
                          LEFT JOIN zona z ON pa.id_zona=z.id_zona
                          LEFT JOIN controlador k ON pa.id_controlador=k.id_controlador
                          ORDER BY pa.nombre""").fetchall()
    conn.close()
    return render_template('puntos.html', puntos=pts)

# ─────────────────────────────────────────────
# API STATS para dashboard chart
# ─────────────────────────────────────────────

@app.route('/api/stats_semana')
@login_required
def stats_semana():
    conn = get_db()
    rows = conn.execute("""
        SELECT DATE(timestamp) as dia, resultado, COUNT(*) as total
        FROM evento_acceso
        WHERE timestamp >= date('now', '-6 days')
        GROUP BY dia, resultado
        ORDER BY dia
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ─────────────────────────────────────────────
# INIT + RUN
# ─────────────────────────────────────────────

# Inicializar DB al importar (necesario para gunicorn)
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))
