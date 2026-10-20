"""Envio de reporte ejecutivo por WhatsApp.

Backends soportados (en orden de prioridad):
1. Twilio WhatsApp (requiere credenciales).
2. WhatsApp Cloud API de Meta (requiere token y phone_number_id).
3. Demo sin coste: guarda el mensaje en archivo y lo imprime por consola para
   copiarlo y pegarlo en WhatsApp Web / Business.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ADMIN_WHATSAPP = os.getenv("ADMIN_WHATSAPP", "")


def _build_message(kpis_summary: dict, negocio: str = "Mi Negocio") -> str:
    s = kpis_summary
    lines = [
        f"*Reporte Ejecutivo - {negocio}*",
        f"📅 {__import__('datetime').datetime.now().strftime('%d/%m/%Y')}",
        "",
        f"*💰 Facturación total:* {s['total_ingresos']:,.2f}",
        f"*🧾 Transacciones:* {s['total_transacciones']}",
        f"*👥 Clientes únicos:* {s['clientes_unicos']}",
        f"*🎫 Ticket promedio:* {s['ticket_promedio']:,.2f}",
        "",
        f"*🎯 Objetivo mensual:* {s['cumplimiento']['meta']:,.2f}",
        f"*📈 Cumplimiento último mes:* {s['cumplimiento']['cumplimiento_pct']:.1f}%",
        "",
        f"*🏆 Producto líder:* {s['top_producto'].get('producto','-')} "
        f"({s['top_producto'].get('ventas',0):,.2f})",
        f"*💳 Medio de pago principal:* {s['principal_pago'].get('metodo_pago','-')}",
        "",
        "_Reporte generado automáticamente por tu asistente BI DaaS (24/7)._",
        "_Adjunto encontrarás el reporte detallado en PDF._",
    ]
    return "\n".join(lines)


def _demo_send(to: str, message: str, pdf_path: str | None = None) -> bool:
    out = Path("whatsapp_demo.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"Para: {to}\n\n{message}\n")
        if pdf_path:
            f.write(f"\nArchivo PDF: {pdf_path}\n")
    print(f"[WHATSAPP DEMO] Mensaje listo en {out} (copiar y pegar en WhatsApp Web):")
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode(sys.stdout.encoding or "utf-8", errors="ignore").decode(sys.stdout.encoding or "utf-8", errors="ignore"))
    return True


def send_whatsapp(kpis_summary: dict, pdf_path: str | None = None, negocio: str = "Mi Negocio") -> bool:
    """Envía el reporte ejecutivo al administrador por WhatsApp."""
    to = ADMIN_WHATSAPP
    message = _build_message(kpis_summary, negocio)

    # 1. Twilio
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from = os.getenv("TWILIO_FROM")
    if account_sid and auth_token and twilio_from:
        try:
            from twilio.rest import Client  # type: ignore
            client = Client(account_sid, auth_token)
            client.messages.create(
                from_=f"whatsapp:{twilio_from}",
                body=message,
                to=f"whatsapp:{to}",
            )
            if pdf_path:
                client.messages.create(
                    from_=f"whatsapp:{twilio_from}",
                    media_url=[f"file://{pdf_path}"],
                    to=f"whatsapp:{to}",
                )
            print("[WHATSAPP] Enviado vía Twilio.")
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"[WHATSAPP] Error Twilio: {exc}")

    # 2. WhatsApp Cloud API (Meta)
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    if token and phone_id:
        try:
            import requests  # type: ignore
            url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message},
            }
            requests.post(url, headers=headers, json=payload, timeout=20)
            print("[WHATSAPP] Enviado vía WhatsApp Cloud API (Meta).")
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"[WHATSAPP] Error Meta Cloud API: {exc}")

    # 3. Demo sin credenciales
    return _demo_send(to, message, pdf_path)
