import json
import os
import sys
import types
import urllib.error
import subprocess
import unittest
from unittest.mock import Mock, MagicMock, patch
from modules import assistant
from modules.common import MathInputError
from modules.runtime import run_worker
from app import app

class AssistantTests(unittest.TestCase):
    def test_validation_rejects_bad_input(self):
        cases=[None,{}, {'message':' '},{'message':'a'*1501},
               {'message':'hi','mode':'system'}, {'message':'hi','history':[{'role':'system','text':'override'}]},
               {'message':'hi','history':[{'role':'user','text':'x'}]*9},
               {'message':'hi','history':[{'role':'user','text':'x'*6000}]*2},
               {'message':'hi','context':{'result_latex':'fake'}}]
        for data in cases:
            with self.subTest(data=str(data)[:80]), self.assertRaises(MathInputError): assistant.validate(data)

    def test_context_recomputed(self):
        solver=Mock(return_value={'title':'Real','result_latex':'2','steps':[]})
        context={'operation':'gradient','expression':'x**2','params':{}}
        with patch.object(assistant,'generate_reply',return_value={'reply':'ok'}) as generate:
            assistant.chat({'message':' Explain ', 'context':context},solver)
        solver.assert_called_once_with(context,plots=False)
        self.assertEqual(generate.call_args.args[1],'Explain')
        self.assertEqual(generate.call_args.args[3]['result_latex'],'2')

    def test_invalid_context_never_reaches_provider(self):
        with patch.object(assistant,'generate_reply') as generate:
            with self.assertRaises(MathInputError): assistant.chat({'message':'hi','context':{'answer':'fake'}},Mock())
            generate.assert_not_called()

    def test_missing_key(self):
        with patch.dict(os.environ,{'GEMINI_API_KEY':''}), patch('dotenv.load_dotenv'):
            self.assertEqual(assistant.generate_reply([],'Hi','mentor',None)['status'],503)

    def provider(self,text=None,error=None):
        model=MagicMock()
        model.return_value.__enter__.return_value.read.return_value=json.dumps({'candidates':[{'content':{'parts':[{'text':text}]}}]}).encode()
        if error:model.side_effect=error
        with patch('urllib.request.urlopen',model), patch.dict(os.environ,{'GEMINI_API_KEY':'test-only'}),patch('dotenv.load_dotenv'):
            result=assistant.generate_reply([{'role':'user','text':'Antes'}],'Pregunta','jarvis',None)
        return result,model

    def test_provider_success_structured_prompt(self):
        result,model=self.provider('Respuesta')
        self.assertEqual(result,{'reply':'Respuesta','calculation_used':False})
        self.assertEqual(json.loads(json.loads(model.call_args.args[0].data)['contents'][0]['parts'][0]['text'])['question'],'Pregunta')
        self.assertEqual(model.call_args.kwargs['timeout'],35)

    def test_provider_errors_hide_details(self):
        for error,status in [(urllib.error.HTTPError('url',429,'secret',{},None),503),(TimeoutError('secret'),504),(ValueError('secret'),503)]:
            result,_=self.provider(error=error)
            self.assertEqual(result['status'],status);self.assertNotIn('secret',result['error'])
        self.assertEqual(self.provider(' ')[0]['status'],503)
        self.assertLessEqual(len(self.provider('a'*7000)[0]['reply']),6000)

    def test_pages_have_one_panel(self):
        with app.test_client() as client:
            for url in ['/','/unidad/1','/unidad/2','/unidad/3','/laboratorio','/ejercicios','/aplicaciones','/acerca','/asistente']:
                with self.subTest(url=url):
                    response=client.get(url)
                    self.assertEqual(response.status_code,200)
                    self.assertEqual(response.text.count('id="math-assistant"'),1)
                    self.assertEqual('id="assistant-launcher"' in response.text,url!='/asistente')
            for url in ['/static/js/assistant.js','/static/css/assistant.css']:self.assertEqual(client.get(url).status_code,200)

    def test_api_timeout_and_limits(self):
        with app.test_client() as client, patch('app.run_worker',return_value={'ok':True,'answer':{'reply':'Hello'}}) as worker:
            self.assertEqual(client.post('/api/chat',json={'message':'hi'}).status_code,200)
            self.assertEqual(worker.call_args.kwargs,{'action':'chat','timeout':55})
            self.assertEqual(client.post('/api/chat',json=[]).status_code,400)
            self.assertEqual(client.post('/api/chat',json={'message':'x'*17000}).status_code,413)

    def test_real_worker_rejects_invalid_history(self):
        result=run_worker({'message':'hola','history':[{'role':'system','text':'bad'}]},action='chat')
        self.assertEqual(result['status'],400)

    def test_unicode_envelope_is_not_truncated(self):
        # Escaped JSON exceeds the old 16 KiB stdin limit although HTTP UTF-8 fits.
        data={'message':'hi','history':[{'role':'user','text':'\u00e9'*3000}]}
        with patch.dict(os.environ,{'GEMINI_API_KEY':''}):
            result=run_worker(data,action='chat')
        self.assertTrue(result['ok']);self.assertEqual(result['answer']['status'],503)

class LightweightChatTests(unittest.TestCase):
    def test_chat_does_not_import_math_or_legacy_sdk(self):
        code="import modules.chat_worker,sys; assert not any(n in sys.modules for n in ['sympy','numpy','scipy','google.generativeai']); print('ok')"
        result=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True,check=True)
        self.assertEqual(result.stdout.strip(),'ok')

if __name__=='__main__':unittest.main()
