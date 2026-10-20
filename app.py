"""App principal - Business Intelligence y Reportes Ejecutivos (DaaS)."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.ingestion import load_sales, filter_valid_orders
from src.kpis import compute_kpis
from src.pdf_report import build_pdf
from src.whatsapp import send_whatsapp, ADMIN_WHATSAPP

OUTPUT_DIR = Path("reportes")
OUTPUT_DIR.mkdir(exist_ok=True)


def _money(v: float) -> str:
    return f"${v:,.2f}"


def _metric_card(label, value, subtitle=""):
    st.metric(label, value, delta=None, help=subtitle)


def main():
    st.set_page_config(page_title="BI DaaS - Reportes Ejecutivos", page_icon="📊", layout="wide")

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
            "Objetivo de ventas mensual", min_value=0.0, value=float(os.getenv("MONTHLY_SALES_TARGET", 50000)), step=1000.0
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
    with st.expander("Vista previa de datos"):
        st.dataframe(df.head(20), use_container_width=True)

    # ---------- Calcular KPIs ----------
    if st.button("🚀 Generar reporte ejecutivo", type="primary", use_container_width=True):
        with st.spinner("Calculando indicadores y generando PDF..."):
            kpis = compute_kpis(df, monthly_target=monthly_target, cost_ratio=cost_ratio)

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

        st.subheader("Facturación por mes")
        st.line_chart(kpis["mensual"].set_index("periodo")["facturacion"])

        st.subheader("Top 5 productos")
        st.dataframe(kpis["top5"][["producto", "ventas", "cantidad", "margen_pct"]], use_container_width=True, hide_index=True)

        st.subheader("Métodos de pago")
        st.dataframe(kpis["metodo_pago"], use_container_width=True, hide_index=True)

        st.subheader("Cumplimiento de objetivo")
        obj = kpis["objetivo"]
        st.write(f"Meta: {_money(obj['meta'])} | Último mes ({obj['ultimo_mes']}): {_money(obj['real_ultimo_mes'])} | "
                 f"Cumplimiento: {obj['cumplimiento_pct']:.1f}%")

        # ---------- PDF ----------
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_name = f"Reporte_Ejecutivo_{negocio.replace(' ', '_')}_{ts}.pdf"
        pdf_path = OUTPUT_DIR / pdf_name
        build_pdf(kpis, str(pdf_path), negocio=negocio)

        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Descargar reporte detallado (PDF)", f, file_name=pdf_name, mime="application/pdf", use_container_width=True)

        # ---------- WhatsApp ----------
        st.header("3️⃣ Reporte ejecutivo por WhatsApp")
        from src.kpis import summary_dict
        sent = send_whatsapp(summary_dict(kpis), pdf_path=str(pdf_path), negocio=negocio)
        if sent:
            st.success("Reporte ejecutivo enviado/listo para WhatsApp del administrador.")
        else:
            st.error("No se pudo preparar el reporte de WhatsApp.")

        st.caption("Insights generados con Google Gemini (nivel gratuito de AI Studio).")


if __name__ == "__main__":
    main()
