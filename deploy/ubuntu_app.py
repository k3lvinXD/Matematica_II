"""Entrada exclusiva del servidor local; no modifica la instalación Windows."""
import os
from app import app

if os.getenv('ACADEMY_LOCAL_HTTP') == '1':
    # Solo para una LAN de confianza. Para Internet se exige HTTPS y valor 0.
    app.config['SESSION_COOKIE_SECURE'] = False
