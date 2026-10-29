"""Proceso de chat ligero; SymPy se carga solo si hay un ejercicio adjunto."""
import json
import sys
from .assistant import chat
from .errors import MathInputError

def solve_context(data, plots=False):
    from .worker import solve
    return solve(data, plots=plots)

def main():
    try:
        request=json.loads(sys.stdin.read(131073))
        answer=chat(request['data'],solve_context)
        response={'ok':True,'answer':answer}
    except MathInputError as exc:
        response={'ok':False,'error':str(exc),'status':400}
    except Exception:
        response={'ok':False,'error':'No se pudo completar la consulta del chat.','status':500}
    print(json.dumps(response,ensure_ascii=True,allow_nan=False))

if __name__=='__main__':main()
