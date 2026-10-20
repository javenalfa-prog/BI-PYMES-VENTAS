# App de Business Intelligence y Reportes Ejecutivos (DaaS)
# Para PYMES: restaurantes, cafeterías, ropa/accesorios, veterinarias y comercio general.

## Cómo ejecutar (inversión cero)

1. Crear entorno e instalar dependencias:
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   pip install -r requirements.txt

2. Copiar configuración:
   copy .env.example .env
   # Editar .env con tu GEMINI_API_KEY y ADMIN_WHATSAPP

3. Ejecutar la app:
   streamlit run app.py

## Funcionamiento
- Sube un archivo de ventas (CSV o Excel) con columnas: Fecha, Producto, Cantidad,
  Precio Unitario, Total, Método de Pago, Código Cliente, Estado de la Orden.
- La app calcula los indicadores financieros y genera:
  * Reporte detallado en PDF (descargable).
  * Reporte ejecutivo por WhatsApp al administrador.
- Usa Google Gemini (nivel gratuito) para generar insights automáticos.

## Backends de WhatsApp (coste cero)
- Demo/sin credenciales: guarda el mensaje y lo imprime por consola (listo para copiar y pegar en WhatsApp Web).
- Twilio o WhatsApp Cloud API (Meta): configurar credenciales en .env para envío automático.
