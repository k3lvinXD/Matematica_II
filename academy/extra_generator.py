"""Ejercicios escalares exactos de las demás operaciones de las calculadoras."""
import random
import sympy as s

def generate_extra(topic,difficulty,count,seed=None):
    rng=random.Random(seed);x,y,z,t=s.symbols('x y z t',real=True)
    power={'basic':2,'medium':3,'advanced':4}[difficulty]
    questions=[];seen=set()
    L=s.latex
    vector=lambda items:r'\left('+','.join(L(i) for i in items)+r'\right)'
    for _ in range(2000):
        a,b,c=[rng.randint(1,8) for _ in range(3)];u,v,w=[rng.randint(1,4) for _ in range(3)]
        f=a*x**power+b*y**2+c*x*y
        point={x:u,y:v,z:w,t:u}
        if topic=='tangent':
            if difficulty=='advanced':
                # A fixed normal direction makes its parameterization unambiguous.
                result=f.subs(point)+w
                prompt=f'La recta normal se parametriza desde el punto de la superficie con x={u}, y={v}, usando la dirección (-fx,-fy,1). Calcula su coordenada z para el parámetro s={w}.'
                note='La componente z de esa parametrización es el valor de la superficie en el punto más s.'
            else:
                tangent=f.subs(point)+s.diff(f,x).subs(point)*(x-u)+s.diff(f,y).subs(point)*(y-v)
                result=tangent.subs({x:u+1,y:v+1})
                prompt=f'Construye el plano tangente en x={u}, y={v} y calcula su altura para x={u+1}, y={v+1}.'
                note='Usa el valor de la función y sus dos derivadas parciales en el punto de tangencia.'
            formula='z='+L(f)
        elif topic=='extrema':
            sign=-1 if difficulty=='medium' else 1
            f=sign*a*(x-u)**2+(b if difficulty!='medium' else -b)*(y-v)**2+c
            if difficulty=='advanced':
                f=a*(x-u)**2-b*(y-v)**2+c;result=-4*a*b
                prompt=f'Encuentra y clasifica el punto crítico. Escribe como respuesta el determinante de la Hessiana en ({u}, {v}).'
                note='El determinante negativo de la Hessiana indica un punto de silla.'
            else:
                result=c;prompt='Encuentra el punto crítico y clasifícalo en el procedimiento. Escribe el valor '+('máximo' if sign<0 else 'mínimo')+' de la función.'
                note='Anula las dos derivadas. La Hessiana definida positiva indica mínimo; definida negativa, máximo.'
            formula='f(x,y)='+L(f)
        elif topic=='lagrange':
            radius=u+(power-2);result=radius*s.sqrt(a*a+b*b)
            formula='f(x,y)='+L(a*x+b*y)+r',\quad x^2+y^2='+L(radius**2)
            prompt='Usa multiplicadores de Lagrange para obtener el máximo de la función bajo la restricción indicada.'
            note='Iguala el gradiente de la función a un múltiplo del gradiente de la restricción y compara los candidatos.'
        elif topic in ('exact','conservative'):
            potential=a*x**power*y+b*x+c*y**2
            P,Q=s.diff(potential,x),s.diff(potential,y)
            formula=(L(P)+r'\,dx+\left('+L(Q)+r'\right)\,dy') if topic=='exact' else 'F(x,y)='+vector((P,Q))
            result=potential.subs(point)
            prompt=(f'Comprueba que la diferencial es exacta y encuentra un potencial con valor cero en (0,0). Escribe su valor en ({u}, {v}).' if topic=='exact' else f'Comprueba que el campo es conservativo y calcula el trabajo desde (0,0) hasta ({u}, {v}).')
            note='Las derivadas cruzadas coinciden. Integra una componente, ajusta la función de la otra variable y usa la diferencia de potencial.'
        elif topic=='chain':
            xt=t**(power-1);yt=b*t+c
            result=s.diff(f.subs({x:xt,y:yt}),t).subs(t,u)
            formula='f(x,y)='+L(f)+r',\quad x(t)='+L(xt)+r',\quad y(t)='+L(yt)
            prompt=f'Aplica la regla de la cadena para calcular df/dt en t={u}.'
            note='Suma la derivada parcial respecto de x multiplicada por dx/dt y la parcial respecto de y multiplicada por dy/dt.'
        elif topic=='jacobian':
            U=a*x**(power-1)+b*y;V=c*x*y+y**power
            result=s.det(s.Matrix([U,V]).jacobian([x,y])).subs(point)
            formula='u(x,y)='+L(U)+r',\quad v(x,y)='+L(V)
            prompt=f'Calcula el determinante jacobiano de (u,v) respecto de (x,y) en ({u}, {v}).'
            note='Forma la matriz de derivadas parciales y calcula su determinante en el punto.'
        elif topic=='limit':
            expr=(x**power-u**power)/(x-u)+a*x+b;result=power*u**(power-1)+a*u+b
            formula=rf'\lim_{{x\to {u}}}\left({L(expr)}\right)'
            prompt='Evalúa el límite indicado.'
            note='Factoriza la diferencia de potencias, cancela el factor común y evalúa la expresión continua resultante.'
        elif topic=='triple_integral':
            f=a*x**(power-1)+b*y+c*z;result=s.Rational(a*v*w*u**power,power)+s.Rational(b*u*w*v*v,2)+s.Rational(c*u*v*w*w,2)
            formula=rf'\int_0^{{{w}}}\int_0^{{{v}}}\int_0^{{{u}}}\left({L(f)}\right)\,dx\,dy\,dz'
            prompt='Evalúa la integral triple sobre la caja indicada.'
            note='Integra sucesivamente en x, y y z, aplicando los límites en cada etapa.'
        elif topic=='polar':
            n=power-1;f=a*(x*x+y*y)**n+b
            result=s.pi*(s.Rational(a*u**(2*n+2),n+1)+b*u*u)
            formula='f(x,y)='+L(f)+r',\quad x^2+y^2\leq '+L(u*u)
            prompt='Integra la función sobre el disco indicado usando coordenadas polares.'
            note='Sustituye la suma de cuadrados por el radio al cuadrado, multiplica por el jacobiano r e integra una vuelta completa.'
        elif topic=='surface_area':
            f=a*x+b*y+c;result=u*v*s.sqrt(1+a*a+b*b)
            formula='z='+L(f)+rf',\quad 0\leq x\leq {u},\quad 0\leq y\leq {v}'
            prompt='Calcula el área de la superficie sobre el rectángulo indicado.'
            note='Integra la raíz de uno más los cuadrados de las dos derivadas parciales sobre la región.'
        elif topic=='mass_center':
            density=a*x**(power-1)+b
            mass=v*(s.Rational(a*u**power,power)+b*u)
            if difficulty=='basic':
                result=mass;prompt='Calcula la masa total de la lámina con la densidad indicada.'
            else:
                moment=v*(s.Rational(a*u**(power+1),power+1)+s.Rational(b*u*u,2))
                result=moment/mass;prompt='Calcula la coordenada x del centro de masa de la lámina.'
            formula=r'\rho(x,y)='+L(density)+rf',\quad 0\leq x\leq {u},\quad 0\leq y\leq {v}'
            note='Integra la densidad para obtener la masa. Para la coordenada x, divide el momento (la integral de x multiplicada por la densidad) entre la masa.'
        elif topic=='vector_curve':
            curve=(a*t**power,b*t**2,c*t)
            if difficulty=='basic':result=s.diff(curve[0],t).subs(t,u);prompt=f'Calcula la componente x de la velocidad en t={u}.'
            elif difficulty=='medium':result=s.diff(curve[0],t,2).subs(t,u);prompt=f'Calcula la componente x de la aceleración en t={u}.'
            else:result=s.sqrt(sum(s.diff(k,t).subs(t,u)**2 for k in curve));prompt=f'Calcula la rapidez de la trayectoria en t={u}.'
            formula='r(t)='+vector(curve);note='Deriva la trayectoria para obtener la velocidad y otra vez para la aceleración. La rapidez es la norma de la velocidad.'
        elif topic=='vector_field':
            P=a*x**(power-1)+b*y;Q=c*x-b*y
            result=s.sqrt(P.subs(point)**2+Q.subs(point)**2)
            formula='F(x,y)='+vector((P,Q));prompt=f'Evalúa el campo en ({u}, {v}) y escribe su magnitud.'
            note='Evalúa ambas componentes y calcula la raíz de la suma de sus cuadrados.'
        elif topic=='curl':
            P=a*y**power;Q=b*x**power
            result=(s.diff(Q,x)-s.diff(P,y)).subs(point)
            if difficulty=='advanced':
                formula='F(x,y,z)='+vector((P,Q,c*z));prompt=f'Calcula la componente z del rotacional 3D en ({u}, {v}, {w}).'
            else:
                formula='F(x,y)='+vector((P,Q));prompt=f'Calcula el rotacional escalar del campo 2D en ({u}, {v}).'
            note='Resta la derivada de P respecto de y de la derivada de Q respecto de x.'
        elif topic=='laplacian':
            f=a*x**power+b*y**power+c*z**power
            result=sum(s.diff(f,k,2) for k in (x,y,z)).subs(point)
            formula='f(x,y,z)='+L(f);prompt=f'Calcula el laplaciano en ({u}, {v}, {w}).'
            note='Suma las segundas derivadas puras respecto de x, y y z y evalúa en el punto.'
        elif topic=='line_integral':
            P=a*y;Q=b*x+c;xt=t;yt=t**power
            result=s.Rational((a+b*power)*u**(power+1),power+1)+c*u**power
            formula='F(x,y)='+vector((P,Q))+r',\quad r(t)='+vector((xt,yt))+rf',\quad 0\leq t\leq {u}'
            prompt='Calcula el trabajo del campo a lo largo de la curva con la orientación indicada.'
            note='Sustituye la curva en el campo, calcula su producto escalar con la derivada de la curva e integra en t.'
        elif topic=='green':
            P=-a*y**(power-1);Q=b*x**(power-1)+c
            result=b*v*u**(power-1)+a*u*v**(power-1)
            formula='F(x,y)='+vector((P,Q))+rf',\quad 0\leq x\leq {u},\quad 0\leq y\leq {v}'
            prompt='Usa el teorema de Green para calcular la circulación sobre el borde del rectángulo en sentido antihorario.'
            note='Integra sobre el rectángulo la derivada de Q respecto de x menos la derivada de P respecto de y.'
        else:raise ValueError('Tema sin generador.')
        key=(prompt,formula)
        if key in seen:continue
        seen.add(key);result=s.simplify(result)
        questions.append({'kind':'written','prompt':prompt,'formula':formula,'answer':str(result),'answer_latex':L(result),'explanation':note})
        if len(questions)==count:return questions
    raise ValueError('No se pudieron generar suficientes ejercicios distintos.')
