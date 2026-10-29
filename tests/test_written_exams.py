import json,unittest,io,zipfile
from sqlalchemy import insert,select,update
import test_academy as fixtures
from academy.database import exams,attempts
from academy.generator import generate
from academy.grading import expression,grade

class WrittenTests(fixtures.AcademyTests):
    # Reuse fixture helpers without repeating the parent test methods.
    def written_exam(self):
        exam_id=self.exam();q=generate('partial','basic',1,seed=12)[0]
        q['answer']='3/5';q['answer_latex']=r'\frac{3}{5}'
        with self.engine.begin() as db:db.execute(update(exams).where(exams.c.id==exam_id).values(questions_json=json.dumps([q])))
        return exam_id,q
    def test_written_submit_review_and_override(self):
        exam_id,q=self.written_exam();attempt_id=self.attempt(exam_id);self.identity(3)
        page=self.client.get(f'/aula/intentos/{attempt_id}')
        self.assertIn('data-answer-input',page.text);self.assertNotIn('answer_latex',page.text);self.assertNotIn(r'\frac{3}{5}',page.text)
        response=self.post(f'/aula/intentos/{attempt_id}',{'q0':r'\frac{6}{10}','work0':'Derivé y sustituí.','action':'submit','score':'99'})
        self.assertEqual(response.status_code,302)
        with self.engine.connect() as db:
            attempt=db.execute(select(attempts).where(attempts.c.id==attempt_id)).mappings().one()
            self.assertEqual(attempt['score'],1);self.assertEqual(json.loads(attempt['answers_json'])['0']['work'],'Derivé y sustituí.')
        self.identity(2);self.assertEqual(self.post(f'/aula/entregas/{attempt_id}/calificar/0',{'correct':'0'}).status_code,403)
        self.identity(1);page=self.client.get(f'/aula/entregas/{attempt_id}');self.assertEqual(page.status_code,200);self.assertIn('Correcto',page.text)
        self.assertEqual(self.post(f'/aula/entregas/{attempt_id}/calificar/0',{'correct':'0'}).status_code,302)
        with self.engine.connect() as db:self.assertEqual(db.execute(select(attempts.c.score).where(attempts.c.id==attempt_id)).scalar(),0)
    def test_unrecognized_answer_needs_review(self):
        exam_id,q=self.written_exam();attempt_id=self.attempt(exam_id);self.identity(3)
        self.post(f'/aula/intentos/{attempt_id}',{'q0':r'\badcommand{1}','action':'submit'})
        with self.engine.connect() as db:
            saved=json.loads(db.execute(select(attempts.c.answers_json).where(attempts.c.id==attempt_id)).scalar())
            self.assertEqual(saved['_grading']['0']['status'],'review')
    def test_export_authorization_and_content(self):
        exam_id,q=self.written_exam();self.identity(3)
        self.assertEqual(self.client.get(f'/aula/examenes/{exam_id}/exportar/pdf').status_code,403)
        self.identity(2);self.assertEqual(self.client.get(f'/aula/examenes/{exam_id}/exportar/images').status_code,403)
        self.identity(1)
        response=self.client.get(f'/aula/examenes/{exam_id}/exportar/pdf');self.assertEqual(response.status_code,200);self.assertTrue(response.data.startswith(b'%PDF'))
        response=self.client.get(f'/aula/examenes/{exam_id}/exportar/images');self.assertEqual(response.status_code,200)
        with zipfile.ZipFile(io.BytesIO(response.data)) as z:self.assertEqual(z.namelist(),['examen-pagina-01.png'])
    def test_exact_equivalence_and_malicious_input(self):
        q={'kind':'written','answer':'3/5'}
        for raw in [r'\frac{6}{10}','0.6','3/5']:
            self.assertTrue(grade([q],{'0':{'value':raw}})['0']['correct'])
        self.assertFalse(grade([q],{'0':{'value':'0.6001'}})['0']['correct'])
        for raw in ["__import__('os').system('whoami')",'1/0','9^99999',r'\href{evil}{1}']:
            self.assertIsNone(grade([q],{'0':{'value':raw}})['0']['correct'])
    def test_regeneration_requires_draft_and_explicit_replace(self):
        exam_id=self.exam('draft');self.identity(1)
        self.assertEqual(self.post(f'/aula/examenes/{exam_id}/regenerar').status_code,400)
        self.assertEqual(self.post(f'/aula/examenes/{exam_id}/regenerar',{'replace':'yes'}).status_code,302)
        with self.engine.connect() as db:self.assertEqual(json.loads(db.execute(select(exams.c.questions_json).where(exams.c.id==exam_id)).scalar())[0]['kind'],'written')
        self.post(f'/aula/examenes/{exam_id}/publicar',{'reviewed':'yes'})
        self.assertEqual(self.post(f'/aula/examenes/{exam_id}/regenerar',{'replace':'yes'}).status_code,409)

    def test_written_edit_and_render(self):
        exam_id,q=self.written_exam()
        with self.engine.begin() as db:db.execute(update(exams).where(exams.c.id==exam_id).values(state='draft'))
        self.identity(1);self.assertEqual(self.client.get(f'/aula/examenes/{exam_id}').status_code,200)
        response=self.post(f'/aula/examenes/{exam_id}/preguntas/0',{'prompt':'Resuelve.','formula':r'f(x)=x^2','answer':r'\frac{4}{2}','explanation':'Derivar y evaluar.'})
        self.assertEqual(response.status_code,302)
        with self.engine.connect() as db:self.assertEqual(json.loads(db.execute(select(exams.c.questions_json).where(exams.c.id==exam_id)).scalar())[0]['answer'],'2')

# Parent suite is run independently by unittest discovery.
for name in list(vars(fixtures.AcademyTests)):
    if name.startswith('test_') and name not in WrittenTests.__dict__:setattr(WrittenTests,name,None)
