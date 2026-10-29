"""Evaluación aislada de respuestas: nunca evalúa código del usuario."""
import json
import re
import sys
from modules.common import safe_expr
import sympy as sp


def expression(value):
    if not isinstance(value, str) or len(value)>240:
        raise ValueError('Respuesta demasiado larga.')
    text=re.sub(r'\\(?:left|right)', '', value)
    text=re.sub(r'\\[,;! ]', '', text).replace('−','-')
    pos=0
    def read(nested=False, depth=0):
        nonlocal pos
        if depth>18:raise ValueError('Demasiado anidamiento.')
        result=''
        def group():
            nonlocal pos
            while pos<len(text) and text[pos].isspace():pos+=1
            if pos>=len(text) or text[pos]!='{':raise ValueError('Faltan llaves.')
            pos+=1
            return read(True,depth+1)
        while pos<len(text):
            ch=text[pos];pos+=1
            if ch=='}':
                if not nested:raise ValueError('Llave inesperada.')
                return result
            if ch=='{':result+='('+read(True,depth+1)+')';continue
            if ch!='\\':result+=ch;continue
            match=re.match(r'[A-Za-z]+',text[pos:])
            if not match:raise ValueError('Notación no admitida.')
            cmd=match.group();pos+=len(cmd)
            if cmd in ('frac','dfrac','tfrac'):
                top=group();bottom=group();result+='(('+top+')/('+bottom+'))'
            elif cmd=='sqrt':result+='sqrt('+group()+')'
            elif cmd in ('cdot','times'):result+='*'
            elif cmd=='div':result+='/'
            elif cmd in ('pi','sin','cos','tan','exp','log'):result+=cmd
            elif cmd=='ln':result+='log'
            else:raise ValueError('Notación no admitida.')
        if nested:raise ValueError('Llave sin cierre.')
        return result
    return safe_expr(read())


def grade(questions, answers):
    results={}
    for i,q in enumerate(questions):
        value=answers.get(str(i))
        if q.get('kind')!='written':
            results[str(i)]={'correct':value==q['correct'],'status':'auto'};continue
        raw=value.get('value','') if isinstance(value,dict) else ''
        if not raw.strip():
            results[str(i)]={'correct':False,'status':'blank'};continue
        try:
            actual=expression(raw);expected=expression(q['answer'])
            # Current exercises ask for exact scalar values. No decimal tolerance.
            if actual.free_symbols:raise ValueError('Se esperaba un valor numérico.')
            correct=sp.simplify(actual-expected)==0
            results[str(i)]={'correct':bool(correct),'status':'auto','latex':sp.latex(actual)}
        except Exception:
            results[str(i)]={'correct':None,'status':'review'}
    return results


if __name__=='__main__':
    payload=json.loads(sys.stdin.read(200000))
    if payload.get('action')=='validate':
        value=expression(payload['value'])
        if value.free_symbols:raise ValueError('La respuesta debe ser numérica.')
        print(json.dumps({'answer':str(value),'answer_latex':sp.latex(value)}))
    else:print(json.dumps(grade(payload['questions'],payload['answers'])))
