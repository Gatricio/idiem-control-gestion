import datetime
import pandas as pd
import streamlit as st
import database as db
from streamlit_oauth import OAuth2Component

st.set_page_config(
    page_title="IDIEM - Control de Gestión & KPI",
    page_icon="📊",
    layout="wide"
)

db.init_db()

st.markdown("""
    <style>
    .main-header { font-size:24px; font-weight:bold; color:#002855; margin-bottom:2px; }
    .sub-header { font-size:14px; color:#555; margin-bottom: 20px; }
    .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 4px solid #0056B3; }
    </style>
""", unsafe_allow_html=True)

# Autenticación Google OAuth
CLIENT_ID = st.secrets["google_oauth"]["client_id"]
CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
REDIRECT_URI = st.secrets["google_oauth"]["redirect_uri"]

oauth2 = OAuth2Component(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    authorize_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
    token_endpoint="https://oauth2.googleapis.com/token",
    refresh_token_endpoint="https://oauth2.googleapis.com/token",
    revoke_token_endpoint="https://oauth2.googleapis.com/revoke"
)

if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.markdown('<div class="main-header">IDIEM — UNIVERSIDAD DE CHILE</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">División de Ingeniería Contractual | Portal de Control de Gestión</div>', unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.subheader("🔒 Acceso Institucional")
        st.caption("Ingresa con tu cuenta de correo corporativa IDIEM / Universidad de Chile.")

        result = oauth2.authorize_button(
            name="Iniciar sesión con Google IDIEM",
            redirect_uri=REDIRECT_URI,
            scope="openid email profile",
            key="google_login",
            use_container_width=True
        )

        if result and "token" in result:
            import jwt
            id_token = result["token"]["id_token"]
            user_info = jwt.decode(id_token, options={"verify_signature": False})
            
            email_google = user_info.get("email", "").lower()
            nombre_google = user_info.get("name", "Usuario IDIEM")

            if email_google.endswith("@idiem.cl") or email_google.endswith("@uchile.cl"):
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id, nombre, email FROM usuarios WHERE email = ?", (email_google,))
                user_db = cursor.fetchone()

                if user_db:
                    st.session_state.user = dict(user_db)
                else:
                    cursor.execute("""
                        INSERT INTO usuarios (nombre, email)
                        VALUES (?, ?)
                    """, (nombre_google, email_google))
                    conn.commit()
                    cursor.execute("SELECT id, nombre, email FROM usuarios WHERE email = ?", (email_google,))
                    st.session_state.user = dict(cursor.fetchone())

                conn.close()
                st.rerun()
            else:
                st.error("⚠️ Acceso denegado: Solo se permiten cuentas corporativas @idiem.cl o @uchile.cl.")
    st.stop()

# Barra Lateral
usuario_actual = st.session_state.user

with st.sidebar:
    st.markdown(f"👤 **{usuario_actual['nombre']}**")
    st.caption(f"Email: {usuario_actual['email']}")
    st.markdown("---")
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.user = None
        st.rerun()

st.markdown('<div class="main-header">IDIEM — Control de Gestión de Ingeniería Contractual</div>', unsafe_allow_html=True)

# Pestañas Abiertas para Todos los Usuarios
tab_kpi, tab_gestion, tab_asignar, tab_timesheet = st.tabs([
    "📈 Cuadro de Mando & KPI",
    "➕ Crear / Editar Proyectos",
    "👥 Asignar Equipos & HH",
    "⏱️ Registro de Horas (Timesheet)"
])

conn = db.get_connection()

# ---------------------------------------------------------
# PESTAÑA 1: CUADRO DE MANDO & KPI
# ---------------------------------------------------------
with tab_kpi:
    st.subheader("Estado Global de Proyectos")

    df_proyectos = pd.read_sql_query("""
        SELECT p.id, p.codigo, p.nombre, p.cliente, u.nombre as responsable, p.presupuesto_uf, 
               p.hh_presupuestadas, p.fecha_inicio, p.fecha_fin, p.estado,
               COALESCE(SUM(r.hh_registradas), 0) as hh_ejecutadas
        FROM proyectos p
        LEFT JOIN usuarios u ON p.responsable_id = u.id
        LEFT JOIN registro_horas r ON p.id = r.proyecto_id
        GROUP BY p.id
    """, conn)

    if df_proyectos.empty:
        st.info("No hay proyectos registrados en el sistema.")
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
        m4.metric("Consumo HH Global", f"{total_hh_real:,.1f} HH", f"{avance_hh_pct:.1f}%")

        st.markdown("---")
        df_proyectos['Avance HH %'] = (df_proyectos['hh_ejecutadas'] / df_proyectos['hh_presupuestadas'] * 100).round(1)
        df_proyectos['HH Disponibles'] = df_proyectos['hh_presupuestadas'] - df_proyectos['hh_ejecutadas']

        st.dataframe(
            df_proyectos[['codigo', 'nombre', 'cliente', 'responsable', 'presupuesto_uf', 'hh_presupuestadas', 'hh_ejecutadas', 'HH Disponibles', 'Avance HH %', 'estado']],
            use_container_width=True
        )

        st.markdown("---")
        st.markdown("##### 🗑️ Eliminar Proyecto")
        dict_del_p = {f"{r['codigo']} - {r['nombre']}": r['id'] for _, r in df_proyectos.iterrows()}
        p_to_del = st.selectbox("Seleccionar Proyecto para Eliminar:", list(dict_del_p.keys()), key="del_p_select")
        if st.button("Eliminar Proyecto Seleccionado", type="secondary"):
            cursor = conn.cursor()
            p_id = dict_del_p[p_to_del]
            cursor.execute("DELETE FROM registro_horas WHERE proyecto_id = ?", (p_id,))
            cursor.execute("DELETE FROM asignaciones WHERE proyecto_id = ?", (p_id,))
            cursor.execute("DELETE FROM proyectos WHERE id = ?", (p_id,))
            conn.commit()
            st.success("Proyecto y sus registros eliminados correctamente.")
            st.rerun()

# ---------------------------------------------------------
# PESTAÑA 2: CREAR / EDITAR PROYECTOS
# ---------------------------------------------------------
with tab_gestion:
    st.subheader("Crear Nuevo Proyecto")
    with st.form("form_crear_proyecto"):
        col1, col2 = st.columns(2)
        with col1:
            cod_in = st.text_input("Código de Propuesta (PR.DIC):", placeholder="PR.DIC-2026-X")
            nom_in = st.text_input("Nombre del Proyecto/Peritaje:")
            cli_in = st.text_input("Cliente / Tribunal Arbitral:")
        with col2:
            uf_in = st.number_input("Presupuesto Total (UF):", min_value=1.0, value=100.0, step=10.0)
            hh_in = st.number_input("Horas Hombre Presupuestadas:", min_value=1, value=150)
            f_ini = st.date_input("Fecha Inicio:", value=datetime.date.today())
            f_fin = st.date_input("Fecha Estimada Término:", value=datetime.date.today() + datetime.timedelta(days=90))

        btn_crear = st.form_submit_button("Guardar Proyecto")

        if btn_crear:
            if cod_in.strip() and nom_in.strip() and cli_in.strip():
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO proyectos (codigo, nombre, cliente, responsable_id, presupuesto_uf, hh_presupuestadas, fecha_inicio, fecha_fin)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (cod_in.strip(), nom_in.strip(), cli_in.strip(), usuario_actual['id'], uf_in, hh_in, f_ini, f_fin))
                    conn.commit()
                    st.success(f"¡Proyecto '{cod_in}' registrado exitosamente!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al registrar proyecto: {e}")
            else:
                st.warning("Completa los campos obligatorios.")

# ---------------------------------------------------------
# PESTAÑA 3: ASIGNAR EQUIPOS & HH
# ---------------------------------------------------------
with tab_asignar:
    st.subheader("Asignación de Profesionales a Proyectos")

    proyectos_all = pd.read_sql_query("SELECT id, codigo, nombre FROM proyectos", conn)
    usuarios_all = pd.read_sql_query("SELECT id, nombre, email FROM usuarios", conn)

    if proyectos_all.empty:
        st.info("Primero debes registrar un proyecto.")
    elif usuarios_all.empty:
        st.info("No hay usuarios registrados en el sistema.")
    else:
        dict_proyectos = {f"{r['codigo']} - {r['nombre']}": r['id'] for _, r in proyectos_all.iterrows()}
        dict_usuarios = {f"{r['nombre']} ({r['email']})": r['id'] for _, r in usuarios_all.iterrows()}

        sel_p = st.selectbox("Seleccionar Proyecto:", list(dict_proyectos.keys()), key="asig_p")
        sel_u = st.selectbox("Seleccionar Profesional a Asignar:", list(dict_usuarios.keys()), key="asig_u")
        hh_asign = st.number_input("Horas Asignadas (HH):", min_value=1, value=40)

        if st.button("Guardar Asignación"):
            p_id = dict_proyectos[sel_p]
            u_id = dict_usuarios[sel_u]

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

# ---------------------------------------------------------
# PESTAÑA 4: REGISTRO DE HORAS (TIMESHEET)
# ---------------------------------------------------------
with tab_timesheet:
    st.subheader("Carga Diario / Semanal de Horas Hombre")

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
        st.info("No tienes asignaciones de horas activas. Puedes asignarte horas en la pestaña 'Asignar Equipos & HH'.")
    else:
        mis_asignaciones['HH Pendientes'] = mis_asignaciones['hh_asignadas'] - mis_asignaciones['hh_cargadas']
        st.dataframe(mis_asignaciones[['codigo', 'nombre', 'hh_asignadas', 'hh_cargadas', 'HH Pendientes']], use_container_width=True)

        st.markdown("---")
        st.markdown("#### Registrar Horas")

        dict_mis_p = {f"{r['codigo']} - {r['nombre']}": r['id'] for _, r in mis_asignaciones.iterrows()}

        with st.form("form_carga_hh"):
            p_sel_name = st.selectbox("Proyecto:", list(dict_mis_p.keys()))
            fecha_reg = st.date_input("Fecha de Trabajo:", value=datetime.date.today())
            hh_reg = st.number_input("Horas Trabajadas (HH):", min_value=0.5, max_value=12.0, value=2.0, step=0.5)
            act_reg = st.text_area("Descripción de la Actividad / Avance:", placeholder="Ej: Revisión de Libro de Obras...")

            btn_cargar = st.form_submit_button("Registrar Horas")

            if btn_cargar:
                if act_reg.strip():
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO registro_horas (proyecto_id, usuario_id, fecha, hh_registradas, actividad)
                        VALUES (?, ?, ?, ?, ?)
                    """, (dict_mis_p[p_sel_name], usuario_actual['id'], fecha_reg, hh_reg, act_reg.strip()))
                    conn.commit()
                    st.success("¡Horas registradas!")
                    st.rerun()
                else:
                    st.warning("Por favor describe la actividad.")

conn.close()
