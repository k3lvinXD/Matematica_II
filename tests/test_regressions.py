import json
import subprocess
import unittest
from unittest.mock import patch
import sympy as sp
from app import app
from modules.common import MathInputError, safe_expr, x, y, z, make_surface
from modules.worker import solve, dispatch


class ParserTests(unittest.TestCase):
    def test_exact_decimals(self):
        self.assertEqual(safe_expr('0.1+0.2'), sp.Rational(3,10))

    def test_existing_notation(self):
        for text, expected in [('2xsin(x)',2*x*sp.sin(x)), ('xy',x*y),
                               ('sqrt(x^2+1)',sp.sqrt(x*x+1)), ('log(x)',sp.log(x)),
                               ('x/y',x/y), ('(x+1)(y+1)',(x+1)*(y+1)),
                               ('sin x',sp.sin(x)), ('x^-2',x**-2),
                               ('asin(x)',sp.asin(x)), ('abs(x)',sp.Abs(x))]:
            with self.subTest(text=text): self.assertEqual(safe_expr(text),expected)

    def test_rejected_inputs(self):
        for text in ['1/0','0/0','sqrt(-1)','log(0)','x.__class__','__import__(x)',
                     '[x]','sin(x,y)','x^99999','9^9^9','sin('*25+'x'+')'*25, 'x'*241]:
            with self.subTest(text=text), self.assertRaises(MathInputError): safe_expr(text)


class EngineTests(unittest.TestCase):
    def result(self, operation, expression, params=None):
        return solve(dict(operation=operation,expression=expression,params=params or {}))

    def test_family(self):
        answer=self.result('extrema','x^2')
        self.assertNotIn('None',json.dumps(answer))
        self.assertIn('y',answer['result_latex'])
        self.assertTrue(any('Familia' in step['title'] for step in answer['steps']))

    def test_constant_family(self):
        self.assertNotIn('None',json.dumps(self.result('extrema','7')))

    def test_isolated_minimum(self):
        self.assertTrue(any('Mínimo local' in step.get('note','') for step in self.result('extrema','x^2+y^2')['steps']))

    def test_gradient_at_point(self):
        self.assertEqual(self.result('gradient','x^2+y^2',{'x0':'1','y0':'2'})['result_latex'],sp.latex(sp.Matrix([2,4])))

    def test_graph_cannot_break_calculation(self):
        with patch('modules.common.sp.lambdify',side_effect=RuntimeError('plot broken')):
            answer=self.result('partials','x*z')
        self.assertIsNone(answer['plot'])
        self.assertIn('z',answer['result_latex'])

    def test_plot_failures_are_messages(self):
        self.assertEqual(make_surface(x*z)['kind'],'message')
        with patch('modules.common.sp.lambdify',side_effect=RuntimeError('plot broken')):
            self.assertEqual(make_surface(x)['kind'],'message')

    def test_plot_json_is_finite(self):
        data=make_surface(1/x)
        self.assertIn(None,data['z'][0])
        json.dumps(data,allow_nan=False)

    def test_divergence_3d(self):
        self.assertEqual(self.result('divergence','x,y,z')['result_latex'],'3')
        with self.assertRaises(MathInputError): self.result('divergence','x,y,z',{'dimensions':'2'})
        with self.assertRaises(MathInputError): self.result('divergence','x,z',{'dimensions':'2'})

    def test_integral_both_orders(self):
        for params in [dict(xmin='0',xmax='1-y',ymin='0',ymax='1'),dict(order='yx',xmin='0',xmax='1',ymin='0',ymax='1-x')]:
            answer=self.result('double_integral','1',params)
            self.assertEqual(answer['result_latex'],sp.latex(sp.Rational(1,2)))
            self.assertEqual(answer['steps'][2]['latex'],'0')

    def test_invalid_regions(self):
        for params in [dict(xmin='2',xmax='1'),dict(ymin='1',ymax='0'),dict(xmax='x'),dict(ymax='x'),dict(xmax='y-1')]:
            with self.subTest(params=params),self.assertRaises(MathInputError): self.result('double_integral','1',params)

    def test_invalid_point(self):
        for operation in ['gradient', 'tangent', 'directional']:
            with self.subTest(operation=operation), self.assertRaises(MathInputError):
                self.result(operation, '1/x', {'x0':'0','y0':'0'})
        with self.assertRaises(MathInputError): self.result('gradient','x^2',{'x0':'x'})

    def test_ai_not_configured(self):
        with patch('dotenv.load_dotenv'), patch.dict('os.environ', {'GEMINI_API_KEY': ''}):
            answer = dispatch('explain', {'operation':'gradient','expression':'x^2+y^2'})
        self.assertEqual(answer['status'],503)

    def test_polar_jacobian(self):
        self.assertEqual(self.result('polar','1',dict(rmin='0',rmax='1',thetamin='0',thetamax='2*pi'))['result_latex'],sp.latex(sp.pi))

    def test_all_existing_operations(self):
        cases={'partials':'x^2+y^2','gradient':'x^2+y^2','directional':'x^2+y^2',
               'tangent':'x^2+y^2','extrema':'x^2+y^2','lagrange':'x*y','exact':'2*x*y,x^2',
               'chain':'x^2+y^2','jacobian':'x^2-y,x+y^2','limit':'sin(x)/x',
               'double_integral':'x*y','triple_integral':'x+y+z','polar':'x^2+y^2',
               'surface_area':'x+y','mass_center':'1+x+y','vector_curve':'cos(t),sin(t),t/3',
               'vector_field':'-y,x','divergence':'x,y','curl':'-y,x','laplacian':'x^2+y^2+z^2',
               'line_integral':'y,x','conservative':'2*x*y,x^2','green':'-y,x'}
        for operation,expression in cases.items():
            with self.subTest(operation=operation):
                answer=self.result(operation,expression)
                self.assertIn('result_latex',answer)
                json.dumps(answer,allow_nan=False)

    def test_params_and_unknown_operations(self):
        for data in [dict(operation='gradient',expression='x',params=[]),dict(operation='unknown',expression='x'),dict(operation='gradient',expression=[]),dict(operation='gradient',expression='x',params={'x0':{}})]:
            with self.assertRaises(MathInputError): solve(data)

    def test_exercise_does_not_reveal_solution(self):
        answer=dispatch('exercise',dict(exercise_id='u1-basic',answer='0'))
        self.assertFalse(answer['correct']); self.assertNotIn('solution',answer)


class ApiTests(unittest.TestCase):
    def setUp(self): self.client=app.test_client()

    def test_pages(self):
        for path in ['/','/unidad/1','/unidad/2','/unidad/3','/laboratorio','/ejercicios','/aplicaciones','/acerca','/static/js/main.js']:
            with self.subTest(path=path):
                response=self.client.get(path)
                self.assertEqual(response.status_code,200)
                response.close()

    def test_bad_json(self):
        for endpoint in ['/api/calculate','/api/plot','/api/explain','/api/plot/surface','/api/exercise/u1-basic']:
            for body in [None,[],1,'text']:
                self.assertEqual(self.client.post(endpoint,json=body).status_code,400)

    def test_request_size(self):
        self.assertEqual(self.client.post('/api/calculate',json={'expression':'x'*17000}).status_code,413)

    def test_real_calculate_without_ai(self):
        response=self.client.post('/api/calculate',json={'operation':'gradient','expression':'x^2+y^2','params':{'x0':'1','y0':'2'}})
        self.assertEqual(response.status_code,200,response.get_data(as_text=True))
        self.assertIsNone(response.json['plot'])
        self.assertNotIn('ai_explanation',response.json)

    def test_real_graph_and_exercise(self):
        response=self.client.post('/api/plot',json={'operation':'divergence','expression':'x,y,z'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['kind'],'message')
        response=self.client.post('/api/exercise/u2-basic',json={'answer':'1'})
        self.assertTrue(response.json['correct'])
        self.assertEqual(self.client.post('/api/exercise/missing',json={'answer':'1'}).status_code,404)

    def test_timeout_and_hidden_error(self):
        with patch('app.run_worker',side_effect=subprocess.TimeoutExpired('worker',12)):
            self.assertEqual(self.client.post('/api/calculate',json={}).status_code,504)
        with patch('app.run_worker',side_effect=RuntimeError('secret')):
            response=self.client.post('/api/calculate',json={})
            self.assertEqual(response.status_code,500)
            self.assertNotIn('secret',response.get_data(as_text=True))

    def test_busy(self):
        with patch('app.SLOTS') as slots:
            slots.acquire.return_value=False
            self.assertEqual(self.client.post('/api/calculate',json={}).status_code,503)
            slots.release.assert_not_called()

    def test_real_worker_timeout(self):
        from modules.runtime import run_worker
        with self.assertRaises(subprocess.TimeoutExpired): run_worker({}, timeout=0.001)


if __name__=='__main__': unittest.main()
