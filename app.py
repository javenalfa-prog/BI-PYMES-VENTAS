"""App principal - Business Intelligence y Reportes Ejecutivos (DaaS)."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.ingestion import load_sales, filter_valid_orders
from src.kpis import compute_kpis, summary_dict
from src.pdf_report import build_pdf
from src.whatsapp import send_whatsapp, ADMIN_WHATSAPP

OUTPUT_DIR = Path("reportes")
OUTPUT_DIR.mkdir(exist_ok=True)


def _money(v: float) -> str:
    return f"${v:,.2f}"


def _metric_card(label, value, subtitle=""):
    st.metric(label, value, delta=None, help=subtitle)


def main():
    st.set_page_config(
        page_title="BI DaaS - Reportes Ejecutivos",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # CSS de aspecto dashboard
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
        .kpi-card {background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px;
                   padding:1rem; text-align:center;}
        .kpi-title {font-size:0.85rem; color:#64748b; margin-bottom:0.25rem;}
        .kpi-value {font-size:1.5rem; font-weight:700; color:#1e293b;}
        .section-title {font-size:1.1rem; font-weight:700; color:#1f3864;
                        margin-top:1.5rem; margin-bottom:0.75rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("📊 Asistente BI Automatizado - Reportes Ejecutivos")
    st.caption("DaaS para restaurantes, cafeterías, ropa/accesorios, veterinarias y comercio general.")

    # ---------- Sidebar configuracion ----------
    with st.sidebar:
        st.header("⚙️ Configuración")
        negocio = st.text_input("Nombre del negocio", value="Mi Negocio")
        admin_whatsapp = st.text_input(
            "WhatsApp Administrador",
            value=ADMIN_WHATSAPP or "",
            help="Formato internacional, ej: +5215512345678",
        )
        monthly_target = st.number_input(
            "Objetivo de ventas mensual", min_value=0.0,
            value=float(os.getenv("MONTHLY_SALES_TARGET", 50000)), step=1000.0,
        )
        cost_ratio = st.number_input(
            "Coste directo estimado (si no hay columna de coste)", min_value=0.0, max_value=1.0,
            value=float(os.getenv("DEFAULT_COST_RATIO", 0.35)), step=0.05, format="%0.2f",
        )
        excluir = st.checkbox("Excluir órdenes canceladas/devueltas", value=True)
        st.divider()
        st.write("Gemini API Key se lee de `.env` (GEMINI_API_KEY).")

    # ---------- Carga de archivo ----------
    st.header("1️⃣ Cargar archivo de ventas")
    uploaded = st.file_uploader(
        "Sube CSV o Excel de ventas", type=["csv", "xlsx", "xls"],
        help="Columnas esperadas: Fecha, Producto, Cantidad, Precio Unitario, Total, Método de Pago, Código Cliente, Estado de la Orden.",
    )

    if uploaded is None:
        st.info("Sube un archivo para comenzar.")
        return

    try:
        df = load_sales(uploaded)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Error leyendo el archivo: {exc}")
        return

    if excluir:
        df = filter_valid_orders(df)

    st.success(f"Archivo cargado: {len(df)} órdenes válidas.")

    # ---------- Filtros (Dashboard) ----------
    with st.expander("🔎 Filtros del dashboard", expanded=True):
        fcol1, fcol2, fcol3 = st.columns(3)

        # Filtro por fechas (desde / hasta)
        with fcol1:
            fecha_min = df["fecha"].min().date()
            fecha_max = df["fecha"].max().date()
            f_ini = st.date_input("Fecha Desde", value=fecha_min, min_value=fecha_min, max_value=fecha_max)
            f_fin = st.date_input("Fecha Hasta", value=fecha_max, min_value=fecha_min, max_value=fecha_max)

        # Filtro por producto (incluye "Todos")
        with fcol2:
            productos = ["(Todos)"] + sorted(df["producto"].unique().tolist())
            prod_sel = st.multiselect("Producto(s)", options=productos, default=["(Todos)"])

        # Filtro por metodo de pago (incluye "Todos")
        with fcol3:
            pagos = ["(Todos)"] + sorted(df["metodo_pago"].unique().tolist())
            pago_sel = st.multiselect("Método de pago", options=pagos, default=["(Todos)"])

    # Aplicar filtros
    mask = (df["fecha"].dt.date >= f_ini) & (df["fecha"].dt.date <= f_fin)
    if prod_sel and "(Todos)" not in prod_sel:
        mask &= df["producto"].isin(prod_sel)
    if pago_sel and "(Todos)" not in pago_sel:
        mask &= df["metodo_pago"].isin(pago_sel)
    df_f = df.loc[mask].copy()

    st.info(f"Registros filtrados: {len(df_f)} de {len(df)}")

    with st.expander("Vista previa de datos filtrados"):
        st.dataframe(df_f.head(20), use_container_width=True)

    # ---------- Calcular KPIs ----------
    if st.button("🚀 Generar reporte ejecutivo", type="primary", use_container_width=True):
        with st.spinner("Calculando indicadores y generando PDF..."):
            kpis = compute_kpis(df_f, monthly_target=monthly_target, cost_ratio=cost_ratio)

        # ---------- Dashboard ----------
        st.header("2️⃣ Indicadores de Resultados")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            _metric_card("Facturación total", _money(kpis["total_ingresos"]))
        with col2:
            _metric_card("Transacciones", str(kpis["total_transacciones"]))
        with col3:
            _metric_card("Clientes únicos", str(kpis["clientes_unicos"]))
        with col4:
            _metric_card("Ticket promedio", _money(kpis["ticket_promedio"]))

        st.divider()

        # Fila de gráficos principales
        g1, g2 = st.columns(2)
        with g1:
            st.markdown('<div class="section-title">📈 Facturación por mes</div>', unsafe_allow_html=True)
            mensual = kpis["mensual"].set_index("periodo")["facturacion"]
            st.line_chart(mensual)

        with g2:
            st.markdown('<div class="section-title">🗓️ Ventas por año y mes</div>', unsafe_allow_html=True)
            pivot = kpis["ventas_por_anio_mes"]
            st.bar_chart(pivot)

        st.divider()

        # Fila productos y pago
        p1, p2 = st.columns(2)
        with p1:
            st.markdown('<div class="section-title">🏆 Top 5 productos</div>', unsafe_allow_html=True)
            st.dataframe(
                kpis["top5"][["producto", "ventas", "cantidad", "margen_pct"]],
                use_container_width=True, hide_index=True,
            )

        with p2:
            st.markdown('<div class="section-title">⬇️ 3 Artículos de menor rotación</div>', unsafe_allow_html=True)
            st.dataframe(
                kpis["bottom3"][["producto", "ventas", "cantidad", "margen_pct"]],
                use_container_width=True, hide_index=True,
            )

        st.divider()

        m1, m2 = st.columns(2)
        with m1:
            st.markdown('<div class="section-title">💳 Métodos de pago</div>', unsafe_allow_html=True)
            st.dataframe(kpis["metodo_pago"], use_container_width=True, hide_index=True)

        with m2:
            st.markdown('<div class="section-title">🎯 Cumplimiento de objetivo</div>', unsafe_allow_html=True)
            obj = kpis["objetivo"]
            st.write(f"Meta: {_money(obj['meta'])}")
            st.write(f"Último mes ({obj['ultimo_mes']}): {_money(obj['real_ultimo_mes'])}")
            st.write(f"Cumplimiento: {obj['cumplimiento_pct']:.1f}%")

        st.divider()

        # ---------- PDF ----------
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_name = f"Reporte_Ejecutivo_{negocio.replace(' ', '_')}_{ts}.pdf"
        pdf_path = OUTPUT_DIR / pdf_name
        build_pdf(kpis, str(pdf_path), negocio=negocio)

        with open(pdf_path, "rb") as f:
            st.download_button(
                "⬇️ Descargar reporte detallado (PDF)",
                f,
                file_name=pdf_name,
                mime="application/pdf",
                use_container_width=True,
            )

        # ---------- WhatsApp ----------
        st.header("3️⃣ Reporte ejecutivo por WhatsApp")
        sent = send_whatsapp(summary_dict(kpis), pdf_path=str(pdf_path), negocio=negocio)
        if sent:
            st.success("Reporte ejecutivo enviado/listo para WhatsApp del administrador.")
        else:
            st.error("No se pudo preparar el reporte de WhatsApp.")

        st.caption("Insights generados con Google Gemini (nivel gratuito de AI Studio).")


if __name__ == "__main__":
    main()
