import hashlib,json,re,random,unittest
from pathlib import Path
import sympy as s
from sqlalchemy import select,update
import test_academy as fixtures
from academy.catalog import TOPICS,TOPIC_GROUPS
from academy.generator import generate
from academy.grading import expression
from academy.database import attempts,exams

class TopicMathTests(unittest.TestCase):
    def test_catalog_matches_every_calculator(self):
        operations=set()
        for path in Path('templates').glob('*.html'):
            operations.update(re.findall(r"calculator\('[^']*',\s*'[^']*',\s*'([^']+)'",path.read_text(encoding='utf-8')))
        self.assertEqual(set(TOPICS),operations)
        self.assertEqual(len(TOPICS),23)
    def test_new_answers_against_independent_symbolic_calculation(self):
        x,y,z,t=s.symbols('x y z t',real=True)
        for difficulty,p in [('basic',2),('medium',3),('advanced',4)]:
            rng=random.Random(42);a,b,c=[rng.randint(1,8) for _ in range(3)];u,v,w=[rng.randint(1,4) for _ in range(3)]
            f=a*x**p+b*y*y+c*x*y;point={x:u,y:v,z:w}
            density=a*x**(p-1)+b;mass=s.integrate(density,(x,0,u),(y,0,v))
            expected={
              'tangent':f.subs(point)+w if p==4 else (f.subs(point)+s.diff(f,x).subs(point)+s.diff(f,y).subs(point)),
              'extrema':-4*a*b if p==4 else c,
              'lagrange':(u+p-2)*s.sqrt(a*a+b*b),
              'exact':(a*x**p*y+b*x+c*y*y).subs(point),
              'conservative':(a*x**p*y+b*x+c*y*y).subs(point),
              'chain':s.diff(f.subs({x:t**(p-1),y:b*t+c}),t).subs(t,u),
              'jacobian':s.det(s.Matrix([a*x**(p-1)+b*y,c*x*y+y**p]).jacobian([x,y])).subs(point),
              'limit':s.limit((x**p-u**p)/(x-u)+a*x+b,x,u),
              'triple_integral':s.integrate(a*x**(p-1)+b*y+c*z,(x,0,u),(y,0,v),(z,0,w)),
              'polar':s.integrate((a*x**(2*(p-1))+b)*x,(x,0,u))*2*s.pi,
              'surface_area':u*v*s.sqrt(1+a*a+b*b),
              'mass_center':mass if p==2 else s.integrate(x*density,(x,0,u),(y,0,v))/mass,
              'vector_curve':a*p*u**(p-1) if p==2 else a*p*(p-1)*u**(p-2) if p==3 else s.sqrt((a*p*u**(p-1))**2+(2*b*u)**2+c*c),
              'vector_field':s.sqrt((a*u**(p-1)+b*v)**2+(c*u-b*v)**2),
              'curl':b*p*u**(p-1)-a*p*v**(p-1),
              'laplacian':sum(s.diff(a*x**p+b*y**p+c*z**p,k,2) for k in (x,y,z)).subs(point),
              'line_integral':s.integrate(a*t**p+(b*t+c)*p*t**(p-1),(t,0,u)),
              'green':s.integrate(s.diff(b*x**(p-1)+c,x)-s.diff(-a*y**(p-1),y),(x,0,u),(y,0,v))}
            for topic,value in expected.items():
                q=generate(topic,difficulty,1,seed=42)[0]
                self.assertEqual(s.simplify(expression(q['answer'])-value),0,(topic,difficulty))
                self.assertEqual(s.simplify(expression(q['answer_latex'])-value),0,(topic,'latex'))
    def test_legacy_topic_identifiers_still_work(self):
        for old,new in [('partial','partials'),('double','double_integral')]:self.assertEqual(generate(old,'basic',2,3),generate(new,'basic',2,3))

class FeedbackTests(fixtures.AcademyTests):
    def setUp(self):
        super().setUp();self.exam_id=self.exam();self.attempt_id=self.attempt(self.exam_id);self.identity(3)
        self.post(f'/aula/intentos/{self.attempt_id}',{'q0':'1','action':'submit'})
        self.url=f'/aula/entregas/{self.attempt_id}/comentarios'
    def version(self):
        with self.engine.connect() as db:
            answers=json.loads(db.execute(select(attempts.c.answers_json).where(attempts.c.id==self.attempt_id)).scalar())
        return hashlib.sha256(json.dumps(answers.get('_feedback',{}),sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    def data(self,**kw):return {'feedback_version':self.version(),'general':'Revisa tus unidades.','comment0':'Buen procedimiento.',**kw}
    def test_permissions_csrf_and_submission(self):
        self.assertEqual(self.post(self.url,self.data()).status_code,403)
        self.identity(2);self.assertEqual(self.post(self.url,self.data()).status_code,403)
        self.identity(1);self.assertEqual(self.client.post(self.url,data=self.data()).status_code,400)
        with self.engine.begin() as db:db.execute(update(attempts).where(attempts.c.id==self.attempt_id).values(submitted_at=None))
        self.assertEqual(self.post(self.url,self.data()).status_code,409)
    def test_comment_release_edit_delete_and_escaping(self):
        self.identity(1);old=self.data(general='<script>alert(1)</script>COMENTARIO_PRIVADO');self.assertEqual(self.post(self.url,old).status_code,302)
        review=self.client.get(f'/aula/entregas/{self.attempt_id}');self.assertIn('&lt;script&gt;',review.text);self.assertNotIn('<script>alert',review.text)
        self.assertEqual(self.post(self.url,old).status_code,409)
        self.identity(3);self.assertNotIn('COMENTARIO_PRIVADO',self.client.get(f'/aula/intentos/{self.attempt_id}').text)
        self.identity(1);self.post(f'/aula/examenes/{self.exam_id}/cerrar')
        self.identity(3);page=self.client.get(f'/aula/intentos/{self.attempt_id}');self.assertIn('COMENTARIO_PRIVADO',page.text);self.assertIn('Buen procedimiento.',page.text)
        self.identity(1);self.assertEqual(self.post(self.url,self.data(general='',comment0='')).status_code,302)
        with self.engine.connect() as db:self.assertEqual(db.execute(select(attempts.c.score).where(attempts.c.id==self.attempt_id)).scalar(),1)
        self.identity(3);self.assertNotIn('COMENTARIO_PRIVADO',self.client.get(f'/aula/intentos/{self.attempt_id}').text)
    def test_length_and_grade_changes_preserve_comments(self):
        self.identity(1);self.assertEqual(self.post(self.url,self.data(general='x'*3001)).status_code,400)
        self.assertEqual(self.post(self.url,self.data(comment0='x'*1501)).status_code,400)
        self.post(self.url,self.data());self.post(f'/aula/entregas/{self.attempt_id}/calificar/0',{'correct':'0'})
        self.assertIn('Buen procedimiento.',self.client.get(f'/aula/entregas/{self.attempt_id}').text)

for name in vars(fixtures.AcademyTests):
    if name.startswith('test_') and name not in FeedbackTests.__dict__:setattr(FeedbackTests,name,None)
