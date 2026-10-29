import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import insert,select,update
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import mssql
from werkzeug.security import generate_password_hash
from app import app
from academy.database import metadata,make_engine,users,courses,enrollments,exams,attempts
from academy.generator import generate,TOPICS

class AcademyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.password_hash=generate_password_hash('UnaClaveLarga123!')
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.previous_engine=app.extensions['academy_engine'];self.previous_secret=app.secret_key
        app.config.update(TESTING=True,SECRET_KEY='test-secret-only-32-characters-long',ACADEMY_DATABASE_URL='sqlite:///'+str(Path(self.temp.name)/'test.db'))
        self.engine=make_engine(app);metadata.create_all(self.engine);app.extensions['academy_engine']=self.engine
        self.client=app.test_client()
        with self.engine.begin() as db:
            for uid,role in [(1,'teacher'),(2,'teacher'),(3,'student'),(4,'student')]:
                db.execute(insert(users).values(id=uid,name=f'Persona {uid}',email=f'user{uid}@example.com',password_hash=self.password_hash,role=role,teacher_requested=0,auth_version=1))
            db.execute(insert(courses).values(id=1,teacher_id=1,title='Curso A',join_code='CODE123'))
            db.execute(insert(enrollments).values(course_id=1,student_id=3))
    def tearDown(self):
        self.engine.dispose();app.extensions['academy_engine']=self.previous_engine;app.secret_key=self.previous_secret;app.config.pop('ACADEMY_DATABASE_URL',None);self.temp.cleanup()
    def identity(self,uid):
        with self.client.session_transaction() as s:s.clear();s['uid']=uid;s['auth_version']=1;s['csrf']='token'
    def post(self,url,data=None):return self.client.post(url,data={'csrf_token':'token',**(data or {})})
    def exam(self,state='published'):
        questions=[{'prompt':'¿Cuánto es dos más dos?','options':['1','4','6','8'],'correct':1,'explanation':'SOLUCION_PRIVADA: dos más dos es cuatro.'}]
        with self.engine.begin() as db:
            return db.execute(insert(exams).values(course_id=1,title='Examen',topic='partial',difficulty='basic',duration=5,state=state,questions_json=json.dumps(questions),created_at=int(time.time()))).inserted_primary_key[0]
    def attempt(self,exam_id,deadline=None):
        with self.engine.begin() as db:
            return db.execute(insert(attempts).values(exam_id=exam_id,student_id=3,started_at=int(time.time()),deadline=deadline or int(time.time())+300,answers_json='{}')).inserted_primary_key[0]

    def test_registration_does_not_grant_teacher_role(self):
        self.client.get('/aula/registro')
        with self.client.session_transaction() as s:token=s['csrf']
        response=self.client.post('/aula/registro',data={'csrf_token':token,'name':'Docente','email':'nuevo@example.com','password':'NuevaClave12345','confirm':'NuevaClave12345','role':'teacher','teacher_request':'yes'})
        self.assertEqual(response.status_code,302)
        with self.engine.connect() as db:
            user=db.execute(select(users).where(users.c.email=='nuevo@example.com')).mappings().one()
            self.assertEqual(user['role'],'student');self.assertEqual(user['teacher_requested'],1);self.assertNotEqual(user['password_hash'],'NuevaClave12345')

    def test_csrf_and_roles(self):
        self.identity(3)
        self.assertEqual(self.client.post('/aula/cursos',data={'title':'Ataque'}).status_code,400)
        self.assertEqual(self.post('/aula/cursos',{'title':'No permitido'}).status_code,403)
        self.assertEqual(self.post('/aula/salir').status_code,302)
        self.assertEqual(self.client.get('/aula/').status_code,302)

    def test_teacher_cli_revokes_old_session(self):
        self.identity(3)
        result=app.test_cli_runner().invoke(args=['authorize-teacher','user3@example.com'])
        self.assertEqual(result.exit_code,0,result.output)
        self.assertEqual(self.client.get('/aula/').status_code,302)
        with self.engine.connect() as db:self.assertEqual(db.execute(select(users.c.role).where(users.c.id==3)).scalar(),'teacher')

    def test_login_and_throttling(self):
        self.client.get('/aula/ingresar')
        with self.client.session_transaction() as s:s['csrf']='token'
        for _ in range(8):self.assertEqual(self.post('/aula/ingresar',{'email':'user3@example.com','password':'wrong'}).status_code,401)
        self.assertEqual(self.post('/aula/ingresar',{'email':'user3@example.com','password':'UnaClaveLarga123!'}).status_code,429)
        good=app.test_client();good.get('/aula/ingresar')
        with good.session_transaction() as s:token=s['csrf']
        self.assertEqual(good.post('/aula/ingresar',data={'csrf_token':token,'email':'user1@example.com','password':'UnaClaveLarga123!'}).status_code,302)
        self.assertEqual(good.get('/aula/').status_code,200)

    def test_course_ownership_and_enrollment(self):
        self.identity(4);self.assertEqual(self.client.get('/aula/cursos/1').status_code,403)
        self.assertEqual(self.post('/aula/inscribirse',{'code':'CODE123'}).status_code,302)
        self.assertEqual(self.post('/aula/inscribirse',{'code':'CODE123'}).status_code,302)
        self.assertEqual(self.client.get('/aula/cursos/1').status_code,200)
        self.identity(2);self.assertEqual(self.client.get('/aula/cursos/1').status_code,403)

    def test_generate_review_publish(self):
        self.identity(1)
        response=self.post('/aula/cursos/1/generar',{'title':'Parciales','topic':'partial','difficulty':'medium','count':'3','duration':'15'})
        self.assertEqual(response.status_code,302)
        exam_id=int(response.location.split('/')[-1]);page=self.client.get(response.location);self.assertEqual(page.status_code,200)
        self.assertIn('Revisé todas',page.text)
        self.assertEqual(self.post(f'/aula/examenes/{exam_id}/publicar').status_code,400)
        self.assertEqual(self.post(f'/aula/examenes/{exam_id}/publicar',{'reviewed':'yes'}).status_code,302)
        self.assertEqual(self.post(f'/aula/examenes/{exam_id}/preguntas/0',{}).status_code,409)

    def test_draft_and_answer_leak_prevented(self):
        exam_id=self.exam('draft');self.identity(3)
        self.assertEqual(self.client.get(f'/aula/examenes/{exam_id}').status_code,404)
        with self.engine.begin() as db:db.execute(update(exams).where(exams.c.id==exam_id).values(state='published'))
        attempt_id=self.attempt(exam_id)
        page=self.client.get(f'/aula/intentos/{attempt_id}')
        self.assertEqual(page.status_code,200);self.assertNotIn('SOLUCION_PRIVADA',page.text);self.assertNotIn('math-assistant',page.text)
        self.identity(4);self.assertEqual(self.client.get(f'/aula/intentos/{attempt_id}').status_code,404)

    def test_single_attempt_and_grading_release(self):
        exam_id=self.exam();self.identity(3)
        first=self.post(f'/aula/examenes/{exam_id}/iniciar');second=self.post(f'/aula/examenes/{exam_id}/iniciar')
        self.assertEqual(first.location,second.location)
        response=self.post(first.location,{'q0':'1','action':'submit','score':'999'})
        self.assertEqual(response.status_code,302)
        page=self.client.get(first.location);self.assertNotIn('SOLUCION_PRIVADA',page.text);self.assertNotIn('Resultado:',page.text)
        self.assertEqual(self.post(first.location,{'q0':'0','action':'submit'}).status_code,409)
        self.identity(1);self.assertEqual(self.post(f'/aula/examenes/{exam_id}/cerrar').status_code,302)
        self.identity(3);page=self.client.get(first.location)
        self.assertIn('SOLUCION_PRIVADA',page.text);self.assertIn('1/1',page.text)

    def test_timeout_ignores_late_answers(self):
        exam_id=self.exam();attempt_id=self.attempt(exam_id,deadline=int(time.time())-1);self.identity(3)
        response=self.post(f'/aula/intentos/{attempt_id}',{'q0':'1','action':'submit'})
        self.assertEqual(response.status_code,302)
        with self.engine.connect() as db:
            row=db.execute(select(attempts).where(attempts.c.id==attempt_id)).mappings().one()
            self.assertEqual(row['score'],0);self.assertIsNotNone(row['submitted_at'])

    def test_close_uses_saved_answers(self):
        exam_id=self.exam();attempt_id=self.attempt(exam_id);self.identity(3)
        response=self.client.post(f'/aula/intentos/{attempt_id}',data={'csrf_token':'token','q0':'1','action':'save'},headers={'X-Autosave':'1'})
        self.assertTrue(response.json['saved'])
        self.identity(1);self.post(f'/aula/examenes/{exam_id}/cerrar')
        self.assertEqual(self.client.get(f'/aula/examenes/{exam_id}/resultados').status_code,200)
        self.assertIn('Elegida por el estudiante',self.client.get(f'/aula/entregas/{attempt_id}').text)
        self.identity(3);self.assertIn('1/1',self.client.get(f'/aula/intentos/{attempt_id}').text)

    def test_other_teacher_cannot_access_or_publish(self):
        exam_id=self.exam('draft');self.identity(2)
        for url in [f'/aula/examenes/{exam_id}',f'/aula/examenes/{exam_id}/resultados']:
            self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.post(f'/aula/examenes/{exam_id}/publicar',{'reviewed':'yes'}).status_code,403)

    def test_schema_compiles_for_sql_server(self):
        for table in metadata.sorted_tables:
            ddl=str(CreateTable(table).compile(dialect=mssql.dialect()))
            self.assertIn('CREATE TABLE',ddl)
        self.assertIn('NVARCHAR(max)',str(CreateTable(exams).compile(dialect=mssql.dialect())))

    def test_templates_generate_unique_exact_options(self):
        for topic in TOPICS:
            for level in ['basic','medium','advanced']:
                questions=generate(topic,level,20,seed=42)
                self.assertEqual(len({(q['prompt'],q['formula']) for q in questions}),20)
                for q in questions:
                    self.assertEqual(q['kind'],'written');self.assertTrue(q['formula']);self.assertTrue(q['answer_latex']);self.assertTrue(q['explanation'])

if __name__=='__main__':unittest.main()
