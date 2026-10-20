"""Ingesta y normalización de archivos de ventas (CSV / Excel)."""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

import pandas as pd


def _strip_accents(text: str) -> str:
    if not isinstance(text, str):
        return text
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [_strip_accents(str(c)) for c in df.columns]
    return df


# Alias aceptados (espanol e ingles) -> nombre canonico
_COLUMN_ALIASES = {
    "fecha": "fecha",
    "date": "fecha",
    "orden": "orden",
    "# orden": "orden",
    "order": "orden",
    "order id": "orden",
    "codigo cliente": "cliente",
    "cod cliente": "cliente",
    "customer": "cliente",
    "customer code": "cliente",
    "producto": "producto",
    "product": "producto",
    "cantidad": "cantidad",
    "qty": "cantidad",
    "quantity": "cantidad",
    "precio unitario": "precio_unitario",
    "precio unitario ": "precio_unitario",
    "unit price": "precio_unitario",
    "total": "total",
    "metodo de pago": "metodo_pago",
    "metodo de pago ": "metodo_pago",
    "payment method": "metodo_pago",
    "estado de la orden": "estado",
    "order status": "estado",
    "status": "estado",
    "costo unitario": "costo_unitario",
    "unit cost": "costo_unitario",
}


def _map_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {}
    for col in df.columns:
        key = _strip_accents(col)
        if key in _COLUMN_ALIASES:
            mapping[col] = _COLUMN_ALIASES[key]
    df = df.rename(columns=mapping)
    return df


def load_sales(file) -> pd.DataFrame:
    """Carga un archivo CSV o Excel y devuelve un DataFrame normalizado."""
    name = getattr(file, "name", "") or ""
    if name.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(file)
    else:
        df = pd.read_csv(file)

    df = _normalize_columns(df)
    df = _map_columns(df)

    required = ["fecha", "producto", "cantidad", "precio_unitario", "total", "metodo_pago"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            "Faltan columnas requeridas: "
            + ", ".join(missing)
            + ". Columnas detectadas: " + ", ".join(map(str, df.columns))
        )

    # Tipos
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)
    df["precio_unitario"] = pd.to_numeric(df["precio_unitario"], errors="coerce").fillna(0)
    df["total"] = pd.to_numeric(df["total"], errors="coerce").fillna(0)

    if "cliente" in df.columns:
        df["cliente"] = df["cliente"].astype(str).fillna("Desconocido")
    if "metodo_pago" in df.columns:
        df["metodo_pago"] = df["metodo_pago"].astype(str).fillna("No especificado")
    if "estado" in df.columns:
        df["estado"] = df["estado"].astype(str).fillna("Sin estado")
    if "producto" in df.columns:
        df["producto"] = df["producto"].astype(str).fillna("Sin producto")

    # Recalcular total si falta pero hay precio y cantidad
    mask = df["total"].isna() | (df["total"] == 0)
    df.loc[mask, "total"] = df.loc[mask, "cantidad"] * df.loc[mask, "precio_unitario"]

    df = df.dropna(subset=["fecha"]).sort_values("fecha").reset_index(drop=True)
    return df


def filter_valid_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Descarta ordenes canceladas/Devueltas si existe columna estado."""
    if "estado" not in df.columns:
        return df
    excluir = {"cancelled", "cancelada", "cancelado", "returned", "devuelto", "reembolsado", "refunded"}
    mask = ~df["estado"].str.lower().str.strip().isin(excluir)
    return df[mask].reset_index(drop=True)

