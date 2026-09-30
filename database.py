import sqlite3
import hashlib

DB_NAME = "gestion_idiem.db"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla Usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('Gerencia', 'Jefe de Proyecto', 'Profesional'))
        )
    """)

    # Tabla Proyectos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proyectos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            cliente TEXT NOT NULL,
            jp_id INTEGER NOT NULL,
            presupuesto_uf REAL NOT NULL,
            hh_presupuestadas INTEGER NOT NULL,
            fecha_inicio DATE NOT NULL,
            fecha_fin DATE NOT NULL,
            estado TEXT NOT NULL DEFAULT 'En Ejecución',
            FOREIGN KEY (jp_id) REFERENCES usuarios (id)
        )
    """)

    # Tabla Asignaciones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asignaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proyecto_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            hh_asignadas INTEGER NOT NULL,
            FOREIGN KEY (proyecto_id) REFERENCES proyectos (id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
            UNIQUE(proyecto_id, usuario_id)
        )
    """)

    # Tabla Registro de Horas (Timesheet)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registro_horas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proyecto_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            fecha DATE NOT NULL,
            hh_registradas REAL NOT NULL,
            actividad TEXT NOT NULL,
            FOREIGN KEY (proyecto_id) REFERENCES proyectos (id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    """)

    conn.commit()

    # Usuarios demo por defecto
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        usuarios_demo = [
            ("Director Gerencia", "gerencia@idiem.cl", hash_password("gerencia123"), "Gerencia"),
            ("Ing. Patricio Alday (JP)", "jp.patricio@idiem.cl", hash_password("jp123"), "Jefe de Proyecto"),
            ("Ing. Maria Paz (JP)", "jp.maria@idiem.cl", hash_password("jp123"), "Jefe de Proyecto"),
            ("Carlos Perez (Asesor)", "carlos.prof@idiem.cl", hash_password("prof123"), "Profesional"),
            ("Andrea Gomez (Asesor)", "andrea.prof@idiem.cl", hash_password("prof123"), "Profesional"),
            ("Felipe Soto (Asesor)", "felipe.prof@idiem.cl", hash_password("prof123"), "Profesional")
        ]
        cursor.executemany("INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (?, ?, ?, ?)", usuarios_demo)
        conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada correctamente.")
