import base64
import json
import os
import unittest
import urllib.error
from unittest.mock import patch
from modules.speech import speech, DEFAULT_VOICE
from modules.common import MathInputError
from app import app

class SpeechTests(unittest.TestCase):
    def test_validation(self):
        for text in [None,'',' ','x'*1201,25]:
            with self.subTest(text=str(text)[:20]),self.assertRaises(MathInputError):speech({'text':text})

    def test_missing_key_does_not_contact_provider(self):
        with patch.dict(os.environ,{'VOICEAI_API_KEY':''}),patch('dotenv.load_dotenv'),patch('urllib.request.urlopen') as call:
            self.assertEqual(speech({'text':'Hola'})['status'],503);call.assert_not_called()

    def test_selected_voice_and_mp3(self):
        audio=b'ID3'+b'\0'*100
        with patch.dict(os.environ,{'VOICEAI_API_KEY':'test-key','VOICEAI_VOICE_ID':DEFAULT_VOICE}),patch('dotenv.load_dotenv'),patch('urllib.request.urlopen') as call:
            response=call.return_value.__enter__.return_value
            response.headers.get_content_type.return_value='audio/mpeg';response.read.return_value=audio
            result=speech({'text':'La derivada es dos equis.'})
        request=call.call_args.args[0]
        self.assertEqual(request.full_url,'https://dev.voice.ai/api/v1/tts/speech');self.assertNotIn('test-key',request.full_url)
        body=json.loads(request.data);self.assertEqual(body['voice_id'],DEFAULT_VOICE);self.assertEqual(body['language'],'es');self.assertEqual(body['audio_format'],'mp3');self.assertEqual(request.get_header('Authorization'),'Bearer test-key')
        self.assertEqual(body['text'],'La derivada es dos equis.');self.assertNotIn('language_code',body)
        self.assertEqual(result['mime'],'audio/mpeg');self.assertEqual(base64.b64decode(result['audio']),audio)
        self.assertEqual(call.call_args.kwargs['timeout'],18)

    def test_errors_do_not_expose_response(self):
        for status in [401,402,403,404,422,429,500]:
            with patch.dict(os.environ,{'VOICEAI_API_KEY':'test-key'}),patch('dotenv.load_dotenv'),patch('urllib.request.urlopen',side_effect=urllib.error.HTTPError('url',status,'secret',{},None)):
                result=speech({'text':'Hola'})
            self.assertEqual(result['status'],503);self.assertNotIn('secret',result['error'])

    def test_cloudflare_block_is_not_reported_as_bad_key(self):
        error=urllib.error.HTTPError('url',403,'blocked',{'Server':'cloudflare','Content-Type':'text/html'},None)
        with patch.dict(os.environ,{'VOICEAI_API_KEY':'test-key'}),patch('dotenv.load_dotenv'),patch('urllib.request.urlopen',side_effect=error):
            result=speech({'text':'Hola'})
        self.assertIn('Cloudflare',result['error']);self.assertIn('No se pudo comprobar',result['error'])

    def test_rejects_non_audio_and_bad_voice_id(self):
        with patch.dict(os.environ,{'VOICEAI_API_KEY':'test-key'}),patch('dotenv.load_dotenv'),patch('urllib.request.urlopen') as call:
            response=call.return_value.__enter__.return_value
            response.headers.get_content_type.return_value='text/html';response.read.return_value=b'<html>bad</html>'
            self.assertEqual(speech({'text':'Hola'})['status'],503)
        with patch.dict(os.environ,{'VOICEAI_API_KEY':'test-key','VOICEAI_VOICE_ID':'../../other'}),patch('dotenv.load_dotenv'),patch('urllib.request.urlopen') as call:
            self.assertEqual(speech({'text':'Hola'})['status'],503);call.assert_not_called()

    def test_api_and_assets(self):
        with app.test_client() as client,patch('app.run_worker',return_value={'ok':True,'answer':{'audio':'test','mime':'audio/mpeg'}}) as worker:
            response=client.post('/api/speech',json={'text':'Hola'})
            self.assertEqual(response.status_code,200);self.assertEqual(response.headers['Cache-Control'],'no-store')
            self.assertEqual(worker.call_args.kwargs,{'action':'speech','timeout':24})
            self.assertEqual(client.post('/api/speech',json=[]).status_code,400)
            html=client.get('/asistente').text
            self.assertIn('Español latinoamericano · navegador',html);self.assertIn('value="orb" selected',html);self.assertNotIn('Cuphead',html);self.assertIn('jarvis-core-7',html)


if __name__=='__main__':unittest.main()
