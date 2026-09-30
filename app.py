import datetime
import pandas as pd
import streamlit as st
import database as db

st.set_page_config(
    page_title="IDIEM - Control de Gestión & KPI",
    page_icon="📊",
    layout="wide"
)

# Inicializar Base de Datos
db.init_db()

# Estilos corporativos IDIEM
st.markdown("""
    <style>
    .main-header { font-size:24px; font-weight:bold; color:#002855; margin-bottom:2px; }
    .sub-header { font-size:14px; color:#555; margin-bottom: 20px; }
    .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 4px solid #0056B3; }
    </style>
""", unsafe_allow_html=True)

# Autenticación / Login
if "user" not in st.session_state:
    st.session_state.user = None

def login(email, password):
    conn = db.get_connection()
    cursor = conn.cursor()
    pwd_hash = db.hash_password(password)
    cursor.execute("SELECT id, nombre, email, rol FROM usuarios WHERE email = ? AND password_hash = ?", (email, pwd_hash))
    user = cursor.fetchone()
    conn.close()
    if user:
        st.session_state.user = dict(user)
        st.rerun()
    else:
        st.error("Credenciales incorrectas.")

if not st.session_state.user:
    st.markdown('<div class="main-header">IDIEM — UNIVERSIDAD DE CHILE</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">División de Ingeniería Contractual | Portal de Control de Gestión</div>', unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.subheader("🔒 Iniciar Sesión")
        email_in = st.text_input("Correo Institucional:")
        pwd_in = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar al Sistema", use_container_width=True):
            login(email_in, pwd_in)

        st.caption("👥 **Cuentas Demo:**")
        st.caption("• **Gerencia:** gerencia@idiem.cl / gerencia123")
        st.caption("• **Jefe de Proyecto:** jp.patricio@idiem.cl / jp123")
        st.caption("• **Profesional:** carlos.prof@idiem.cl / prof123")
    st.stop()

# Barra lateral
usuario_actual = st.session_state.user

with st.sidebar:
    st.markdown(f"👤 **{usuario_actual['nombre']}**")
    st.caption(f"Rol: **{usuario_actual['rol']}**")
    st.caption(f"Email: {usuario_actual['email']}")
    st.markdown("---")
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.user = None
        st.rerun()

st.markdown('<div class="main-header">IDIEM — Control de Gestión de Ingeniería Contractual</div>', unsafe_allow_html=True)
st.caption(f"Panel Operativo | Perfil Activo: {usuario_actual['rol']}")

# VISTA 1: GERENCIA
if usuario_actual['rol'] == "Gerencia":
    st.subheader("📈 Cuadro de Mando Ejecutivo (KPI Gerenciales)")

    conn = db.get_connection()

    df_proyectos = pd.read_sql_query("""
        SELECT p.id, p.codigo, p.nombre, p.cliente, u.nombre as jp, p.presupuesto_uf, 
               p.hh_presupuestadas, p.fecha_inicio, p.fecha_fin, p.estado,
               COALESCE(SUM(r.hh_registradas), 0) as hh_ejecutadas
        FROM proyectos p
        LEFT JOIN usuarios u ON p.jp_id = u.id
        LEFT JOIN registro_horas r ON p.id = r.proyecto_id
        GROUP BY p.id
    """, conn)

    conn.close()

    if df_proyectos.empty:
        st.info("No hay proyectos registrados aún en la base de datos.")
    else:
        total_proyectos = len(df_proyectos)
        total_uf = df_proyectos['presupuesto_uf'].sum()
        total_hh_plan = df_proyectos['hh_presupuestadas'].sum()
        total_hh_real = df_proyectos['hh_ejecutadas'].sum()
        avance_hh_pct = (total_hh_real / total_hh_plan * 100) if total_hh_plan > 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Proyectos Activos", f"{total_proyectos}")
        m2.metric("Monto Cartera Total", f"UF {total_uf:,.1f}")
        m3.metric("HH Presupuestadas", f"{total_hh_plan:,.0f} HH")
        m4.metric("Consumo HH Global", f"{total_hh_real:,.1f} HH", f"{avance_hh_pct:.1f}% del Total")

        st.markdown("---")
        st.markdown("### 🔍 Estado Detallado por Proyecto")

        df_proyectos['Avance HH %'] = (df_proyectos['hh_ejecutadas'] / df_proyectos['hh_presupuestadas'] * 100).round(1)
        df_proyectos['HH Disponibles'] = df_proyectos['hh_presupuestadas'] - df_proyectos['hh_ejecutadas']

        st.dataframe(
            df_proyectos[['codigo', 'nombre', 'cliente', 'jp', 'presupuesto_uf', 'hh_presupuestadas', 'hh_ejecutadas', 'HH Disponibles', 'Avance HH %', 'estado']],
            use_container_width=True
        )

# VISTA 2: JEFE DE PROYECTO
elif usuario_actual['rol'] == "Jefe de Proyecto":
    tab_mis_proyectos, tab_crear, tab_asignar = st.tabs([
        "📊 Mis Proyectos & Avance",
        "➕ Crear Nuevo Proyecto",
        "👥 Asignar Equipo & HH"
    ])

    conn = db.get_connection()

    with tab_mis_proyectos:
        st.subheader("Proyectos Bajo mi Gestión")
        df_mis_p = pd.read_sql_query("""
            SELECT p.id, p.codigo, p.nombre, p.cliente, p.presupuesto_uf, p.hh_presupuestadas,
                   COALESCE(SUM(r.hh_registradas), 0) as hh_ejecutadas
            FROM proyectos p
            LEFT JOIN registro_horas r ON p.id = r.proyecto_id
            WHERE p.jp_id = ?
            GROUP BY p.id
        """, conn, params=(usuario_actual['id'],))

        if df_mis_p.empty:
            st.info("No tienes proyectos asignados como Jefe de Proyecto.")
        else:
            df_mis_p['HH Restantes'] = df_mis_p['hh_presupuestadas'] - df_mis_p['hh_ejecutadas']
            df_mis_p['% Consumido'] = (df_mis_p['hh_ejecutadas'] / df_mis_p['hh_presupuestadas'] * 100).round(1)
            st.dataframe(df_mis_p, use_container_width=True)

    with tab_crear:
        st.subheader("Ingreso de Nuevo Proyecto al Sistema")
        with st.form("form_crear_proyecto"):
            col1, col2 = st.columns(2)
            with col1:
                cod_in = st.text_input("Código de Propuesta (PR.DIC):", placeholder="PR.DIC-2026-X")
                nom_in = st.text_input("Nombre Oficial del Proyecto/Peritaje:")
                cli_in = st.text_input("Cliente / Tribunal Arbitral:")
            with col2:
                uf_in = st.number_input("Presupuesto Total (UF):", min_value=1.0, value=100.0, step=10.0)
                hh_in = st.number_input("Horas Hombre Totales Presupuestadas:", min_value=1, value=150)
                f_ini = st.date_input("Fecha Inicio:", value=datetime.date.today())
                f_fin = st.date_input("Fecha Estimada Término:", value=datetime.date.today() + datetime.timedelta(days=90))

            btn_crear = st.form_submit_button("Guardar y Registrar Proyecto")

            if btn_crear:
                if cod_in.strip() and nom_in.strip() and cli_in.strip():
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO proyectos (codigo, nombre, cliente, jp_id, presupuesto_uf, hh_presupuestadas, fecha_inicio, fecha_fin)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (cod_in.strip(), nom_in.strip(), cli_in.strip(), usuario_actual['id'], uf_in, hh_in, f_ini, f_fin))
                        conn.commit()
                        st.success(f"¡Proyecto '{cod_in}' registrado exitosamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar proyecto: {e}")
                else:
                    st.warning("Por favor completa todos los campos requeridos.")

    with tab_asignar:
        st.subheader("Asignación de Profesionales a Proyectos")

        proyectos_jp = pd.read_sql_query("SELECT id, codigo, nombre FROM proyectos WHERE jp_id = ?", conn, params=(usuario_actual['id'],))
        profesionales = pd.read_sql_query("SELECT id, nombre, email FROM usuarios WHERE rol = 'Profesional'", conn)

        if proyectos_jp.empty:
            st.info("Primero debes crear un proyecto para asignarle profesionales.")
        elif profesionales.empty:
            st.info("No hay profesionales registrados en el sistema.")
        else:
            dict_proyectos = {f"{r['codigo']} - {r['nombre']}": r['id'] for _, r in proyectos_jp.iterrows()}
            dict_profesional = {f"{r['nombre']} ({r['email']})": r['id'] for _, r in profesionales.iterrows()}

            sel_p = st.selectbox("Seleccionar Proyecto:", list(dict_proyectos.keys()))
            sel_prof = st.selectbox("Seleccionar Profesional de Asesoría:", list(dict_profesional.keys()))
            hh_asign = st.number_input("Horas Asignadas para el Período/Mes:", min_value=1, value=40)

            if st.button("Asignar Profesional al Proyecto"):
                p_id = dict_proyectos[sel_p]
                u_id = dict_profesional[sel_prof]

                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO asignaciones (proyecto_id, usuario_id, hh_asignadas)
                        VALUES (?, ?, ?)
                        ON CONFLICT(proyecto_id, usuario_id) DO UPDATE SET hh_asignadas = ?
                    """, (p_id, u_id, hh_asign, hh_asign))
                    conn.commit()
                    st.success("¡Asignación guardada correctamente!")
                except Exception as e:
                    st.error(f"Error en la asignación: {e}")

    conn.close()

# VISTA 3: PROFESIONAL
elif usuario_actual['rol'] == "Profesional":
    st.subheader("⏱️ Registro Diario / Semanal de Horas Hombre (Timesheet)")

    conn = db.get_connection()

    mis_asignaciones = pd.read_sql_query("""
        SELECT p.id, p.codigo, p.nombre, a.hh_asignadas,
               COALESCE(SUM(r.hh_registradas), 0) as hh_cargadas
        FROM asignaciones a
        JOIN proyectos p ON a.proyecto_id = p.id
        LEFT JOIN registro_horas r ON p.id = r.proyecto_id AND r.usuario_id = a.usuario_id
        WHERE a.usuario_id = ?
        GROUP BY p.id
    """, conn, params=(usuario_actual['id'],))

    if mis_asignaciones.empty:
        st.info("No tienes proyectos asignados actualmente.")
    else:
        st.markdown("#### Mis Asignaciones Activas")
        mis_asignaciones['HH Pendientes'] = mis_asignaciones['hh_asignadas'] - mis_asignaciones['hh_cargadas']
        st.dataframe(mis_asignaciones[['codigo', 'nombre', 'hh_asignadas', 'hh_cargadas', 'HH Pendientes']], use_container_width=True)

        st.markdown("---")
        st.markdown("#### Cargar Horas Trabajadas")

        dict_mis_p = {f"{r['codigo']} - {r['nombre']}": r['id'] for _, r in mis_asignaciones.iterrows()}

        with st.form("form_carga_hh"):
            p_sel_name = st.selectbox("Proyecto:", list(dict_mis_p.keys()))
            fecha_reg = st.date_input("Fecha de Trabajo:", value=datetime.date.today())
            hh_reg = st.number_input("Horas Trabajadas (HH):", min_value=0.5, max_value=12.0, value=2.0, step=0.5)
            act_reg = st.text_area("Descripción de la Actividad / Avance:", placeholder="Ej: Revisión de Libro de Obras...")

            btn_cargar = st.form_submit_button("Registrar Horas en el Proyecto")

            if btn_cargar:
                if act_reg.strip():
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO registro_horas (proyecto_id, usuario_id, fecha, hh_registradas, actividad)
                        VALUES (?, ?, ?, ?, ?)
                    """, (dict_mis_p[p_sel_name], usuario_actual['id'], fecha_reg, hh_reg, act_reg.strip()))
                    conn.commit()
                    st.success("¡Horas registradas correctamente!")
                    st.rerun()
                else:
                    st.warning("Por favor describe la actividad realizada.")

    conn.close()
