"""Plantillas de Matemática II; respuestas exactas, sin IA ni eval de entradas."""
import random
import sympy as sp

from .catalog import TOPICS, ALIASES
DIFFICULTIES={'basic':'Básica','medium':'Media','advanced':'Avanzada'}

def generate(topic,difficulty,count,seed=None):
    topic=ALIASES.get(topic,topic)
    if topic not in TOPICS or difficulty not in DIFFICULTIES or not 1<=count<=20:
        raise ValueError('Tema, dificultad o cantidad inválidos.')
    if topic not in {'partials','gradient','double_integral','divergence','directional'}:
        from .extra_generator import generate_extra
        return generate_extra(topic,difficulty,count,seed)
    topic={'partials':'partial','double_integral':'double'}.get(topic,topic)
    rng=random.Random(seed);x,y,z=sp.symbols('x y z');questions=[];seen=set()
    power={'basic':2,'medium':3,'advanced':4}[difficulty]
    while len(questions)<count:
        a,b,c=[rng.randint(1,7) for _ in range(3)];u,v=rng.randint(1,3),rng.randint(1,3)
        f=a*x**power+b*x*y+c*y**2
        if topic=='partial':
            expr=sp.diff(f,x);result=expr.subs({x:u,y:v})
            prompt=f'Para f(x,y) = {f}, calcula la derivada parcial respecto de x en ({u},{v}).'
            formula=rf'f(x,y)={sp.latex(f)}'; instruction=f'Calcula la derivada parcial respecto de x en ({u}, {v}).'
            explanation=f'df/dx = {expr}. Sustituyendo x={u}, y={v}, se obtiene {result}.'
        elif topic=='gradient':
            dx,dy=sp.diff(f,x),sp.diff(f,y);result=dy.subs({x:u,y:v})
            prompt=f'Para f(x,y) = {f}, ¿cuál es la componente y del gradiente en ({u},{v})?'
            formula=rf'f(x,y)={sp.latex(f)}'; instruction=f'Calcula la componente y del gradiente en ({u}, {v}).'
            explanation=f'Gradiente = ({dx}, {dy}). La componente y evaluada vale {result}.'
        elif topic=='double':
            f=a*x**(power-1)+b*y+c;result=sp.integrate(f,(x,0,u),(y,0,v))
            prompt=f'Calcula la integral doble de {f} sobre el rectángulo 0 ≤ x ≤ {u}, 0 ≤ y ≤ {v}.'
            formula=rf'\int_0^{{{v}}}\int_0^{{{u}}} \left({sp.latex(f)}\right)\,dx\,dy'; instruction='Evalúa la integral doble indicada.'
            explanation=f'Integrando primero en x: {sp.integrate(f,(x,0,u))}. Integrando después en y resulta {result}.'
        elif topic=='divergence':
            field=(a*x**power,b*y**power,c*z**power);expr=sum(sp.diff(f,t) for f,t in zip(field,(x,y,z)));result=expr.subs({x:u,y:v,z:1})
            prompt=f'Calcula la divergencia de F = {field} en ({u},{v},1).'
            formula=r'F(x,y,z)=\left('+','.join(sp.latex(item) for item in field)+r'\right)'; instruction=f'Calcula la divergencia en ({u}, {v}, 1).'
            explanation=f'div F = {expr}; en el punto indicado vale {result}.'
        else:
            direction=rng.choice([(sp.Rational(3,5),sp.Rational(4,5)),(sp.Rational(4,5),sp.Rational(-3,5))]);dx,dy=sp.diff(f,x),sp.diff(f,y)
            result=sp.simplify((dx*direction[0]+dy*direction[1]).subs({x:u,y:v}))
            prompt=f'Para f(x,y) = {f}, calcula la derivada direccional en ({u},{v}) en la dirección unitaria {direction}.'
            formula=rf'f(x,y)={sp.latex(f)}'; instruction=f'Calcula la derivada direccional en ({u}, {v}) con el vector unitario indicado.'
            formula+=r',\quad u=\left('+','.join(sp.latex(item) for item in direction)+r'\right)'
            explanation=f'Gradiente = ({dx}, {dy}). Producto escalar con el vector unitario en el punto: {result}.'
        if prompt in seen:continue
        seen.add(prompt)
        questions.append({'kind':'written','prompt':instruction,'formula':formula,
                          'answer':str(result),'answer_latex':sp.latex(result),
                          'explanation':{'partial':'Deriva respecto de x manteniendo y constante; después sustituye el punto.', 'gradient':'Deriva respecto de y y evalúa en el punto para obtener la componente solicitada.', 'double':'Integra primero respecto de x con sus límites y después respecto de y.', 'divergence':'Suma la derivada de cada componente respecto de su coordenada y evalúa en el punto.', 'directional':'Calcula el gradiente en el punto y su producto escalar con el vector unitario.'}[topic]})
    return questions

if __name__=='__main__':
    import sys,json
    request=json.loads(sys.stdin.read(3000))
    print(json.dumps(generate(request['topic'],request['difficulty'],request['count']),ensure_ascii=True))
