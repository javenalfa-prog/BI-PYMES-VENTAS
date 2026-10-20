"""Generacion del reporte detallado en PDF con graficos."""

from __future__ import annotations

import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak,
)

from src.kpis import summary_dict


_MONEY = "${:,.2f}"


def _fig_to_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _line_chart(period_df, y_col, title, color="#1f77b4"):
    fig, ax = plt.subplots(figsize=(9, 3.2))
    ax.plot(period_df["periodo"], period_df[y_col], marker="o", color=color, linewidth=2)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_ylabel("Monto")
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return _fig_to_bytes(fig)


def _bar_chart(df, x_col, y_col, title, color="#2ca02c", top=None):
    data = df.head(top) if top else df
    fig, ax = plt.subplots(figsize=(9, 3.2))
    ax.bar(range(len(data)), data[y_col], color=color)
    ax.set_xticks(range(len(data)))
    ax.set_xticklabels(data[x_col], rotation=45, ha="right", fontsize=7)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_ylabel(y_col)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return _fig_to_bytes(fig)


def _bar_chart_anio_mes(pivot_df, title):
    """Gráfico de barras agrupadas: filas=año, columnas=meses."""
    import numpy as np

    meses = list(pivot_df.columns)
    anios = [str(a) for a in pivot_df.index]
    x = np.arange(len(meses))
    width = 0.8 / max(len(anios), 1)

    fig, ax = plt.subplots(figsize=(9, 3.6))
    colors_ = plt.cm.tab10.colors
    for i, anio in enumerate(anios):
        valores = pivot_df.loc[int(anio)].values if int(anio) in pivot_df.index else np.zeros(len(meses))
        ax.bar(x + i * width, valores, width=width, label=anio, color=colors_[i % len(colors_)])

    ax.set_xticks(x + width * (len(anios) - 1) / 2)
    ax.set_xticklabels(meses, fontsize=8)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_ylabel("Ventas")
    ax.legend(title="Año", fontsize=7, title_fontsize=8, loc="upper left", bbox_to_anchor=(1, 1))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return _fig_to_bytes(fig)


def _pie_chart(df, value_col, label_col, title):
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    ax.pie(
        df[value_col],
        labels=df[label_col],
        autopct="%1.1f%%",
        startangle=90,
        textprops={"fontsize": 7},
    )
    ax.set_title(title, fontsize=11, fontweight="bold")
    fig.tight_layout()
    return _fig_to_bytes(fig)


def build_pdf(kpis: dict, out_path: str, negocio: str = "Mi Negocio") -> str:
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16, textColor=colors.HexColor("#1f3864"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#1f3864"))
    normal = styles["Normal"]

    doc = BaseDocTemplate(out_path, pagesize=A4,
                          leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                          topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                          title=f"Reporte Ejecutivo - {negocio}",
                          author="BI DaaS")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame])])

    story = []

    # ---------- Cabecera ----------
    story.append(Paragraph(f"Reporte de Inteligencia de Negocio - {negocio}", h1))
    story.append(Paragraph(
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} &nbsp;|&nbsp; DaaS Automatizado", normal))
    story.append(Spacer(1, 0.4 * cm))

    # ---------- Resumen ejecutivo ----------
    story.append(Paragraph("Resumen Ejecutivo", h2))
    s = summary_dict(kpis)
    resumen_data = [
        ["Indicador", "Valor"],
        ["Facturación total", _MONEY.format(s["total_ingresos"])],
        ["Transacciones", str(s["total_transacciones"])],
        ["Clientes únicos", str(s["clientes_unicos"])],
        ["Ticket promedio", _MONEY.format(s["ticket_promedio"])],
        ["Meta mensual", _MONEY.format(s["cumplimiento"]["meta"])],
        ["Cumplimiento último mes", f"{s['cumplimiento']['cumplimiento_pct']:.1f}%"],
    ]
    t = Table(resumen_data, colWidths=[7 * cm, 4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3864")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef2f7")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    # ---------- Facturacion por periodos ----------
    story.append(Paragraph("Facturación por Períodos", h2))
    for freq, label, color in [
        ("mensual", "Mensual", "#1f77b4"),
        ("trimestral", "Trimestral", "#ff7f0e"),
        ("anual", "Anual", "#2ca02c"),
    ]:
        dfp = kpis[freq]
        story.append(Paragraph(f"{label}", ParagraphStyle("sub", parent=normal, fontSize=10, spaceAfter=2)))
        story.append(Image(io.BytesIO(_line_chart(dfp, "facturacion", f"Facturación {label}", color)), width=17 * cm, height=6 * cm))
        story.append(Spacer(1, 0.3 * cm))

    story.append(PageBreak())

    # ---------- Productos ----------
    story.append(Paragraph("Análisis por Producto", h2))
    prod = kpis["productos"]
    top = prod.head(8)
    story.append(Paragraph("Top 8 productos por ventas", ParagraphStyle("sub", parent=normal, fontSize=10, spaceAfter=2)))
    story.append(Image(io.BytesIO(_bar_chart(top, "producto", "ventas", "Top productos", "#2ca02c")), width=17 * cm, height=6 * cm))
    story.append(Spacer(1, 0.3 * cm))

    prod_table_data = [["Producto", "Ventas", "Unidades", "Margen %"]]
    for _, r in prod.head(10).iterrows():
        prod_table_data.append([
            str(r["producto"])[:28],
            _MONEY.format(r["ventas"]),
            str(int(r["cantidad"])),
            f"{r['margen_pct']:.1f}%",
        ])
    pt = Table(prod_table_data, colWidths=[5 * cm, 3.5 * cm, 2.5 * cm, 2.5 * cm])
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3864")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(pt)
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("Estacionalidad por Día de la Semana", ParagraphStyle("sub", parent=normal, fontSize=10, spaceAfter=2)))
    ed = kpis["estacionalidad_dia"].reset_index().rename(columns={"dia_semana": "dia"})
    story.append(Image(io.BytesIO(_bar_chart(
        ed, "dia", "total",
        "Ventas por día", "#9467bd")), width=17 * cm, height=5 * cm))

    # ---------- Ventas por Año x Mes ----------
    story.append(Paragraph("Ventas por Año y Mes (12 meses)", h2))
    pivot = kpis["ventas_por_anio_mes"]
    story.append(
        Image(
            io.BytesIO(_bar_chart_anio_mes(pivot, "Ventas por año y mes")),
            width=17 * cm,
            height=6.5 * cm,
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    # ---------- Menor rotación ----------
    story.append(Paragraph("Artículos de Menor Rotación (Top 3)", h2))
    bottom = kpis["bottom3"]
    bot_data = [["Producto", "Ventas", "Unidades", "Margen %"]]
    for _, r in bottom.iterrows():
        bot_data.append([
            str(r["producto"])[:28],
            _MONEY.format(r["ventas"]),
            str(int(r["cantidad"])),
            f"{r['margen_pct']:.1f}%",
        ])
    bt = Table(bot_data, colWidths=[5 * cm, 3.5 * cm, 2.5 * cm, 2.5 * cm])
    bt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7f1d1d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fdecea")]),
    ]))
    story.append(bt)
    story.append(Spacer(1, 0.4 * cm))

    story.append(PageBreak())

    # ---------- Metodos de pago y objetivo ----------
    story.append(Paragraph("Métodos de Pago y Cumplimiento de Objetivos", h2))
    pago = kpis["metodo_pago"]
    story.append(Paragraph("Participación por método de pago", ParagraphStyle("sub", parent=normal, fontSize=10, spaceAfter=2)))
    story.append(Image(io.BytesIO(_pie_chart(pago, "total", "metodo_pago", "Métodos de pago")), width=12 * cm, height=7 * cm))
    story.append(Spacer(1, 0.4 * cm))

    obj = kpis["objetivo"]
    mensual = obj["mensual"]
    story.append(Paragraph("Cumplimiento de objetivo mensual", ParagraphStyle("sub", parent=normal, fontSize=10, spaceAfter=2)))
    story.append(Image(io.BytesIO(_line_chart(mensual, "cumplimiento_pct", "Cumplimiento de meta (%)", "#d62728")), width=17 * cm, height=6 * cm))
    story.append(Spacer(1, 0.3 * cm))

    # ---------- Insights IA ----------
    story.append(PageBreak())
    story.append(Paragraph("Insights Automatizados (IA)", h2))
    from src.gemini_ai import generate_insights
    texto = generate_insights(summary_dict(kpis))
    story.append(Paragraph(texto.replace("\n", "<br/>"), normal))

    doc.build(story)
    return out_path

