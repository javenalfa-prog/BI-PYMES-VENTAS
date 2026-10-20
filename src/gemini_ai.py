"""Insights automáticos con Google Gemini (AI Studio, nivel gratuito)."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def generate_insights(kpis_summary: dict) -> str:
    """Devuelve recomendaciones ejecutivas. Si no hay API key, usa plantilla."""
    if not GEMINI_API_KEY:
        return _template_insights(kpis_summary)

    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = (
            "Eres un consultor de Business Intelligence para PYMES (restaurantes, "
            "cafeterías, comercios de ropa, veterinarias). Analiza estos indicadores y "
            "redacta en español un reporte ejecutivo corto con: (1) conclusión principal, "
            "(2) 3 oportunidades de mejora concretas, (3) 1 alerta de riesgo si aplica. "
            "Sé directo, usa viñetas y no inventes datos. Indicadores:\n"
            + str(kpis_summary)
        )
        resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return resp.text or _template_insights(kpis_summary)
    except Exception as exc:  # noqa: BLE001
        return f"_Insights IA no disponibles ({exc})._\n\n{_template_insights(kpis_summary)}"


def _template_insights(s: dict) -> str:
    lines = [
        "Conclusión: el negocio mantiene un flujo de ventas con un ticket promedio de "
        f"{s['ticket_promedio']:,.2f} y {s['total_transacciones']} transacciones.",
        "Oportunidades:",
        f"- Impulsar el producto líder '{s['top_producto'].get('producto','-')}'.",
        "- Revisar precios de productos con bajo margen de beneficio.",
        f"- Aprovechar el medio de pago principal '{s['principal_pago'].get('metodo_pago','-')}'.",
        f"- Cerrar brecha de objetivo: cumplimiento del {s['cumplimiento']['cumplimiento_pct']:.1f}%.",
        "Alerta: vigilar productos de menor rotación para evitar stock inmovilizado.",
    ]
    return "\n".join(lines)
