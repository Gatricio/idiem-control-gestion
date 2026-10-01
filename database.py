import sqlite3

DB_NAME = "gestion_idiem.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Verificar si la tabla proyectos usa la columna antigua jp_id
    cursor.execute("PRAGMA table_info(proyectos)")
    columns = [col[1] for col in cursor.fetchall()]

    # Si la tabla existe con el esquema viejo, la eliminamos para actualizar el esquema
    if "jp_id" in columns:
        cursor.execute("DROP TABLE IF EXISTS registro_horas")
        cursor.execute("DROP TABLE IF EXISTS asignaciones")
        cursor.execute("DROP TABLE IF EXISTS proyectos")
        cursor.execute("DROP TABLE IF EXISTS usuarios")

    # Tabla Usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        )
    """)

    # Tabla Proyectos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proyectos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            cliente TEXT NOT NULL,
            responsable_id INTEGER NOT NULL,
            presupuesto_uf REAL NOT NULL,
            hh_presupuestadas INTEGER NOT NULL,
            fecha_inicio DATE NOT NULL,
            fecha_fin DATE NOT NULL,
            estado TEXT NOT NULL DEFAULT 'En Ejecución',
            FOREIGN KEY (responsable_id) REFERENCES usuarios (id)
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

    # Tabla Registro de Horas
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
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada correctamente.")
