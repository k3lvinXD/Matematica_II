"""Voz Voice.ai seleccionada por el usuario; credenciales solo en servidor."""
import base64
import json
import os
import re
import urllib.error
import urllib.request
from .common import MathInputError

DEFAULT_VOICE = 'ca993c5a-dc17-4800-94fc-1cdcabe759fc'


def speech(data):
    text = data.get('text')
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 1200:
        raise MathInputError('La voz acepta entre 1 y 1200 caracteres por fragmento.')
    from dotenv import load_dotenv
    load_dotenv()
    key = os.getenv('VOICEAI_API_KEY', '').strip()
    if not key:
        return {'error': 'Falta configurar VOICEAI_API_KEY en el servidor.', 'status': 503}
    voice = os.getenv('VOICEAI_VOICE_ID', DEFAULT_VOICE).strip()
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', voice):
        return {'error': 'Revisa VOICEAI_VOICE_ID en el servidor.', 'status': 503}
    body = {'text': text.strip(), 'voice_id': voice, 'audio_format': 'mp3', 'language': 'es'}
    request = urllib.request.Request(
        'https://dev.voice.ai/api/v1/tts/speech',
        data=json.dumps(body).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Accept': 'audio/mpeg', 'Authorization': 'Bearer ' + key}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=18) as response:
            content_type=response.headers.get_content_type()
            audio=response.read(8_000_001)
        # MP3 with an ID3 tag or MPEG frame sync. Never play a JSON/HTML error body.
        is_mp3=audio.startswith(b'ID3') or (len(audio)>1 and audio[0]==0xff and audio[1]&0xe0==0xe0)
        if content_type not in ('audio/mpeg','audio/mp3','application/octet-stream') or not is_mp3 or not 16 <= len(audio) <= 8_000_000:
            raise ValueError('Respuesta de audio inválida')
        return {'audio':base64.b64encode(audio).decode('ascii'),'mime':'audio/mpeg'}
    except urllib.error.HTTPError as exc:
        if exc.code==403 and 'cloudflare' in exc.headers.get('Server','').lower() and 'text/html' in exc.headers.get('Content-Type','').lower():
            error='La protección de Voice.ai (Cloudflare) bloqueó la conexión del servidor. No se pudo comprobar la clave ni generar audio. Contacta con soporte de Voice.ai si persiste.'
        elif exc.code in (401,403):
            error='Voice.ai rechazó el acceso. Revisa la clave, los permisos y el acceso a esta voz.'
        elif exc.code==402:
            error='Voice.ai requiere créditos o un plan habilitado para generar esta voz. Revisa tu cuenta.'
        elif exc.code==422:
            error='Voice.ai no acepta esta configuración de voz o idioma. Comprueba que la voz permita español.'
        elif exc.code==404:
            error='La voz no está disponible para tu cuenta de Voice.ai. Comprueba que esté en tu biblioteca.'
        elif exc.code==429:
            error='Voice.ai no tiene cuota disponible o recibió demasiadas solicitudes. Intenta más tarde.'
        else:
            error='Voice.ai no pudo generar la voz. Intenta más tarde.'
        return {'error':error,'status':503}
    except Exception:
        return {'error':'No se pudo obtener el audio de Voice.ai. Intenta de nuevo.','status':503}
