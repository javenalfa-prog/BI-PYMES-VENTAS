"""Calculo de indicadores de resultados financieros y generales."""

from __future__ import annotations

import pandas as pd


def _period_frame(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    df = df.copy()
    df["periodo"] = df["fecha"].dt.to_period(freq).astype(str)
    g = (
        df.groupby("periodo")
        .agg(facturacion=("total", "sum"), transacciones=("total", "size"))
        .reset_index()
    )
    g["ticket_promedio"] = g["facturacion"] / g["transacciones"]
    return g


def compute_kpis(df: pd.DataFrame, monthly_target: float, cost_ratio: float) -> dict:
    """Calcula todos los indicadores requeridos."""
    kpis: dict = {}

    # --- 1. Nivel de facturación por períodos ---
    kpis["diario"] = _period_frame(df, "D")
    kpis["mensual"] = _period_frame(df, "M")
    kpis["trimestral"] = _period_frame(df, "Q")
    kpis["anual"] = _period_frame(df, "Y")

    total_ingresos = float(df["total"].sum())
    total_transacciones = int(len(df))
    clientes_unicos = int(df["cliente"].nunique()) if "cliente" in df.columns else 0

    # --- 2. Ticket promedio ---
    kpis["ticket_promedio"] = total_ingresos / total_transacciones if total_transacciones else 0.0
    kpis["total_ingresos"] = total_ingresos
    kpis["total_transacciones"] = total_transacciones
    kpis["clientes_unicos"] = clientes_unicos

    # --- 3. Margen de beneficio por producto ---
    prod = (
        df.groupby("producto")
        .agg(
            ventas=("total", "sum"),
            cantidad=("cantidad", "sum"),
            transacciones=("total", "size"),
        )
        .reset_index()
    )
    # Coste estimado: columna costo_unitario si existe, sinon ratio sobre ventas
    if "costo_unitario" in df.columns:
        costo = (
            df.groupby("producto").apply(
                lambda g: float((g["costo_unitario"] * g["cantidad"]).sum()),
                include_groups=False,
            )
            .reset_index(name="coste_total")
        )
        prod = prod.merge(costo, on="producto", how="left")
        prod["coste_total"] = prod["coste_total"].fillna(prod["ventas"] * cost_ratio)
    else:
        prod["coste_total"] = prod["ventas"] * cost_ratio

    prod["beneficio"] = prod["ventas"] - prod["coste_total"]
    prod["margen_pct"] = (prod["beneficio"] / prod["ventas"] * 100).where(
        prod["ventas"] > 0, 0
    )
    prod = prod.sort_values("ventas", ascending=False).reset_index(drop=True)
    kpis["productos"] = prod

    # --- 4. Cumplimiento de objetivos (mensual vs meta) ---
    mensual = kpis["mensual"].copy()
    mensual["meta"] = monthly_target
    mensual["cumplimiento_pct"] = (
        mensual["facturacion"] / monthly_target * 100
    ) if monthly_target else 0.0
    ultimo = mensual.iloc[-1] if len(mensual) else None
    kpis["objetivo"] = {
        "meta": monthly_target,
        "ultimo_mes": str(ultimo["periodo"]) if ultimo is not None else None,
        "real_ultimo_mes": float(ultimo["facturacion"]) if ultimo is not None else 0.0,
        "cumplimiento_pct": float(ultimo["cumplimiento_pct"]) if ultimo is not None else 0.0,
        "mensual": mensual,
    }

    # --- 5. Ventas por producto (top 5 y menor rotacion) ---
    kpis["top5"] = prod.head(5)
    kpis["bottom5"] = prod.tail(5).sort_values("ventas", ascending=True)

    # Estacionalidad de articulos por dia/semana/mes
    df2 = df.copy()
    df2["dia_semana"] = df2["fecha"].dt.day_name()
    df2["mes"] = df2["fecha"].dt.month
    df2["dia_mes"] = df2["fecha"].dt.day

    kpis["estacionalidad_dia"] = (
        df2.groupby("dia_semana")["total"].sum().reindex(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        )
    )
    kpis["estacionalidad_mes"] = df2.groupby("mes")["total"].sum().sort_index()

    # --- 6. Principal metodo de pago ---
    pago = (
        df.groupby("metodo_pago")["total"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    pago["participacion_pct"] = pago["total"] / total_ingresos * 100 if total_ingresos else 0
    kpis["metodo_pago"] = pago

    return kpis


def summary_dict(kpis: dict) -> dict:
    """Resumen plano para enviar a la IA y al reporte de WhatsApp."""
    return {
        "total_ingresos": round(kpis["total_ingresos"], 2),
        "total_transacciones": kpis["total_transacciones"],
        "clientes_unicos": kpis["clientes_unicos"],
        "ticket_promedio": round(kpis["ticket_promedio"], 2),
        "top_producto": kpis["productos"].iloc[0].to_dict() if len(kpis["productos"]) else {},
        "cumplimiento": kpis["objetivo"],
        "principal_pago": (
            kpis["metodo_pago"].iloc[0].to_dict() if len(kpis["metodo_pago"]) else {}
        ),
        "periodos": {
            "mensual": kpis["mensual"].to_dict("records"),
        },
    }
