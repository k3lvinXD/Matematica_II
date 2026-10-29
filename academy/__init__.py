"""Aula: cuentas, cursos y exámenes. Todos los permisos se verifican en servidor."""
import io
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import time
import threading
from functools import wraps
from pathlib import Path
import click
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for, send_file
from sqlalchemy import select, insert, update, and_, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash
from .database import metadata, make_engine, users, courses, enrollments, exams, attempts, login_limits

bp=Blueprint('academy',__name__,url_prefix='/aula')
EXPORT_SLOT=threading.BoundedSemaphore(1)
from .catalog import TOPICS, TOPIC_GROUPS, ALIASES
LEVELS={'basic':'Básica','medium':'Media','advanced':'Avanzada'}

def csrf_token():
    if 'csrf' not in session:session['csrf']=secrets.token_urlsafe(32)
    return session['csrf']

def one(query):return g.db.execute(query).mappings().first()
def rows(query):return g.db.execute(query).mappings().all()
def now():return int(time.time())
def integer(name,low,high):
    try:value=int(request.form.get(name,''))
    except (ValueError,TypeError):abort(400,description='Revisa los campos numéricos.')
    if not low<=value<=high:abort(400,description='Un valor está fuera del intervalo permitido.')
    return value

def textfield(name,limit):
    value=request.form.get(name,'').strip()
    if not 1<=len(value)<=limit:abort(400,description='Completa los campos y respeta su longitud máxima.')
    return value

def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args,**kwargs):
            if not g.user:return redirect(url_for('academy.login'))
            if role and g.user['role']!=role:abort(403,description='No tienes permisos para esta acción.')
            return fn(*args,**kwargs)
        return wrapper
    return decorator

def course_access(course_id,teacher=False):
    course=one(select(courses).where(courses.c.id==course_id))
    if not course:abort(404)
    owns=course['teacher_id']==g.user['id'] and g.user['role']=='teacher'
    if teacher and not owns:abort(403)
    if not owns and not one(select(enrollments.c.id).where(enrollments.c.course_id==course_id,enrollments.c.student_id==g.user['id'])):abort(403)
    return course

def exam_access(exam_id,teacher=False):
    exam=one(select(exams).where(exams.c.id==exam_id))
    if not exam:abort(404)
    course=course_access(exam['course_id'],teacher)
    if not teacher and g.user['role']=='student' and exam['state']=='draft':abort(404)
    return exam,course

def own_attempt(attempt_id):
    attempt=one(select(attempts).where(attempts.c.id==attempt_id,attempts.c.student_id==g.user['id']))
    if not attempt:abort(404)
    exam,course=exam_access(attempt['exam_id'])
    return attempt,exam,course

def math_job(payload):
    run=subprocess.run([sys.executable,'-B','-m','academy.grading'],input=json.dumps(payload),text=True,encoding='utf-8',capture_output=True,timeout=12,check=True,cwd=Path(__file__).resolve().parent.parent,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    return json.loads(run.stdout)


def grade_answers(questions,answers):
    if not any(q.get('kind')=='written' for q in questions):
        return {str(i):{'correct':answers.get(str(i))==q['correct'],'status':'auto'} for i,q in enumerate(questions)}
    try:return math_job({'questions':questions,'answers':answers})
    except (subprocess.SubprocessError,ValueError):
        return {str(i):{'correct':None,'status':'review'} for i in range(len(questions))}


def finalize(attempt,exam,answers=None):
    saved=json.loads(attempt['answers_json']) if answers is None else answers
    questions=json.loads(exam['questions_json'])
    saved['_grading']=grade_answers(questions,saved)
    score=sum(item.get('correct') is True for item in saved['_grading'].values())
    g.db.execute(update(attempts).where(attempts.c.id==attempt['id'],attempts.c.submitted_at.is_(None)).values(
        answers_json=json.dumps(saved),score=score,submitted_at=now()))
    g.db.commit()

@bp.before_request
def prepare_request():
    if current_app.extensions.get('academy_error'):
        return render_template('academy/error.html',message=current_app.extensions['academy_error']),503
    if request.method=='POST':
        sent=request.form.get('csrf_token','') or request.headers.get('X-CSRF-Token','')
        if not session.get('csrf') or not secrets.compare_digest(session['csrf'],sent):
            abort(400,description='La sesión del formulario expiró. Recarga la página e inténtalo de nuevo.')

@bp.route('/registro',methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=textfield('name',100);email=textfield('email',254).lower()
        password=request.form.get('password','')
        if not re.fullmatch(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',email):abort(400,description='Introduce un correo válido.')
        if not 12<=len(password)<=128 or password!=request.form.get('confirm'):abort(400,description='Usa una contraseña de 12 a 128 caracteres y confírmala correctamente.')
        try:
            g.db.execute(insert(users).values(name=name,email=email,password_hash=generate_password_hash(password),role='student',teacher_requested=int(request.form.get('teacher_request')=='yes'),auth_version=1));g.db.commit()
        except IntegrityError:
            g.db.rollback();flash('No se pudo registrar ese correo. Si ya tienes una cuenta, inicia sesión.','warning');return redirect(url_for('academy.register'))
        flash('Cuenta creada. Ya puedes iniciar sesión. Las solicitudes de profesor requieren autorización.','success')
        return redirect(url_for('academy.login'))
    return render_template('academy/auth.html',register=True)

@bp.route('/ingresar',methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form.get('email','').strip().lower()[:254];password=request.form.get('password','')
        if len(password)>128:abort(400)
        key=hashlib.sha256((email+'|'+(request.remote_addr or '')).encode()).hexdigest()
        limit=one(select(login_limits).where(login_limits.c.key==key))
        if limit and limit['expires']>now() and limit['failures']>=8:
            return render_template('academy/error.html',message='Demasiados intentos. Espera 15 minutos antes de volver a iniciar sesión.'),429
        user=one(select(users).where(users.c.email==email))
        valid=check_password_hash(user['password_hash'],password) if user else check_password_hash(current_app.extensions['academy_dummy_hash'],password)
        if not user or not valid:
            if limit:
                values={'failures':login_limits.c.failures+1} if limit['expires']>now() else {'failures':1,'expires':now()+900}
                g.db.execute(update(login_limits).where(login_limits.c.key==key).values(**values))
            else:g.db.execute(insert(login_limits).values(key=key,failures=1,expires=now()+900))
            g.db.commit();flash('Correo o contraseña incorrectos.','danger');return render_template('academy/auth.html',register=False),401
        if limit:g.db.execute(update(login_limits).where(login_limits.c.key==key).values(failures=0,expires=now()))
        g.db.commit();session.clear();session.permanent=True;session['uid']=user['id'];session['auth_version']=user['auth_version']
        return redirect(url_for('academy.dashboard'))
    return render_template('academy/auth.html',register=False)

@bp.post('/salir')
def logout():
    session.clear();return redirect(url_for('index'))

@bp.get('/')
@login_required()
def dashboard():
    if g.user['role']=='teacher':query=select(courses).where(courses.c.teacher_id==g.user['id'])
    else:query=select(courses).join(enrollments).where(enrollments.c.student_id==g.user['id'])
    return render_template('academy/dashboard.html',courses=rows(query.order_by(courses.c.id.desc())))

@bp.post('/cursos')
@login_required('teacher')
def create_course():
    result=g.db.execute(insert(courses).values(title=textfield('title',120),teacher_id=g.user['id'],join_code=secrets.token_hex(5).upper()))
    course_id=result.inserted_primary_key[0];g.db.commit();return redirect(url_for('academy.course_page',course_id=course_id))

@bp.post('/inscribirse')
@login_required('student')
def join_course():
    code=request.form.get('code','').strip().upper()[:24]
    course=one(select(courses).where(courses.c.join_code==code))
    if not course:abort(400,description='Código de curso incorrecto.')
    try:g.db.execute(insert(enrollments).values(course_id=course['id'],student_id=g.user['id']));g.db.commit()
    except IntegrityError:g.db.rollback()
    return redirect(url_for('academy.course_page',course_id=course['id']))

@bp.get('/cursos/<int:course_id>')
@login_required()
def course_page(course_id):
    course=course_access(course_id);query=select(exams).where(exams.c.course_id==course_id)
    if g.user['role']=='student':query=query.where(exams.c.state!='draft')
    students=rows(select(users.c.name,users.c.email).join(enrollments).where(enrollments.c.course_id==course_id)) if g.user['role']=='teacher' else []
    return render_template('academy/course.html',course=course,exams=rows(query.order_by(exams.c.id.desc())),students=students,topics=TOPICS,topic_groups=TOPIC_GROUPS,levels=LEVELS)

@bp.post('/cursos/<int:course_id>/generar')
@login_required('teacher')
def generate_exam(course_id):
    course_access(course_id,True);title=textfield('title',160);topic=ALIASES.get(request.form.get('topic'),request.form.get('topic'));difficulty=request.form.get('difficulty');count=integer('count',1,20);duration=integer('duration',5,180)
    if topic not in TOPICS or difficulty not in LEVELS:abort(400)
    # Bounded process prevents a generator from blocking all web threads indefinitely.
    try:
        run=subprocess.run([sys.executable,'-B','-m','academy.generator'],input=json.dumps({'topic':topic,'difficulty':difficulty,'count':count}),text=True,encoding='utf-8',capture_output=True,timeout=15,check=True,cwd=Path(__file__).resolve().parent.parent,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        questions=json.loads(run.stdout)
    except (subprocess.SubprocessError,ValueError):abort(503,description='No se pudo generar el examen a tiempo. Prueba con menos preguntas.')
    result=g.db.execute(insert(exams).values(course_id=course_id,title=title,topic=topic,difficulty=difficulty,duration=duration,state='draft',questions_json=json.dumps(questions,ensure_ascii=False),created_at=now()))
    exam_id=result.inserted_primary_key[0];g.db.commit();return redirect(url_for('academy.exam_page',exam_id=exam_id))

@bp.get('/examenes/<int:exam_id>')
@login_required()
def exam_page(exam_id):
    exam,course=exam_access(exam_id)
    if g.user['role']=='teacher':
        questions=json.loads(exam['questions_json'])
        return render_template('academy/exam_teacher.html',exam=exam,course=course,questions=questions)
    attempt=one(select(attempts).where(attempts.c.exam_id==exam_id,attempts.c.student_id==g.user['id']))
    return render_template('academy/exam_student.html',exam=exam,course=course,attempt=attempt)

@bp.post('/examenes/<int:exam_id>/preguntas/<int:index>')
@login_required('teacher')
def edit_question(exam_id,index):
    exam,course=exam_access(exam_id,True)
    if exam['state']!='draft':abort(409,description='Solo se pueden editar los borradores.')
    questions=json.loads(exam['questions_json'])
    if index>=len(questions):abort(404)
    if questions[index].get('kind')=='written':
        formula=textfield('formula',300)
        if re.search(r'\\(?:href|url|html|style|class|cssId|includegraphics|require|newcommand|def)\b',formula):abort(400,description='Usa solamente notación matemática.')
        try:solution=math_job({'action':'validate','value':textfield('answer',240)})
        except (subprocess.SubprocessError,ValueError):abort(400,description='Escribe una respuesta numérica exacta válida: por ejemplo 3/5 o una fracción del teclado.')
        questions[index]={'kind':'written','prompt':textfield('prompt',700),'formula':formula,**solution,'explanation':textfield('explanation',1500)}
    else:
        options=[textfield('option'+str(i),180) for i in range(4)]
        if len(set(options))!=4:abort(400,description='Las cuatro opciones deben ser distintas.')
        questions[index]={'prompt':textfield('prompt',1500),'options':options,'correct':integer('correct',0,3),'explanation':textfield('explanation',1500)}
    changed=g.db.execute(update(exams).where(exams.c.id==exam_id,exams.c.state=='draft',exams.c.questions_json==exam['questions_json']).values(questions_json=json.dumps(questions,ensure_ascii=False)))
    if changed.rowcount!=1:abort(409,description='El examen cambió en otra ventana. Recarga antes de editar.')
    g.db.commit();flash('Ejercicio guardado. Revisa también su solución.','success');return redirect(url_for('academy.exam_page',exam_id=exam_id))

@bp.post('/examenes/<int:exam_id>/regenerar')
@login_required('teacher')
def regenerate_exam(exam_id):
    exam,course=exam_access(exam_id,True)
    if exam['state']!='draft':abort(409,description='Solo se pueden regenerar borradores.')
    if request.form.get('replace')!='yes':abort(400,description='Confirma que deseas reemplazar los ejercicios del borrador.')
    try:
        run=subprocess.run([sys.executable,'-B','-m','academy.generator'],input=json.dumps({'topic':exam['topic'],'difficulty':exam['difficulty'],'count':len(json.loads(exam['questions_json']))}),text=True,encoding='utf-8',capture_output=True,timeout=15,check=True,cwd=Path(__file__).resolve().parent.parent,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        questions=json.loads(run.stdout)
    except (subprocess.SubprocessError,ValueError):abort(503,description='No se pudo regenerar el examen. Inténtalo de nuevo.')
    changed=g.db.execute(update(exams).where(exams.c.id==exam_id,exams.c.state=='draft',exams.c.questions_json==exam['questions_json']).values(questions_json=json.dumps(questions,ensure_ascii=False)))
    if changed.rowcount!=1:abort(409,description='El borrador cambió en otra ventana. Recarga.')
    g.db.commit();flash('Borrador reemplazado por ejercicios nuevos. Revísalos antes de publicar.','success')
    return redirect(url_for('academy.exam_page',exam_id=exam_id))

@bp.post('/examenes/<int:exam_id>/publicar')
@login_required('teacher')
def publish_exam(exam_id):
    exam,course=exam_access(exam_id,True)
    if request.form.get('reviewed')!='yes':abort(400,description='Confirma que revisaste las preguntas y sus soluciones.')
    if exam['state']!='draft':abort(409)
    g.db.execute(update(exams).where(exams.c.id==exam_id,exams.c.state=='draft').values(state='published'));g.db.commit()
    flash('Examen publicado. Las soluciones se mostrarán a los estudiantes cuando lo cierres.','success');return redirect(url_for('academy.exam_page',exam_id=exam_id))

@bp.post('/examenes/<int:exam_id>/cerrar')
@login_required('teacher')
def close_exam(exam_id):
    exam,course=exam_access(exam_id,True)
    if exam['state']!='published':abort(409)
    g.db.execute(update(exams).where(exams.c.id==exam_id,exams.c.state=='published').values(state='closed'));g.db.commit()
    # Pending attempts are finalized from their last server-side save when read.
    flash('Examen cerrado. Los estudiantes ya pueden consultar su nota y las soluciones.','success');return redirect(url_for('academy.results',exam_id=exam_id))

@bp.post('/examenes/<int:exam_id>/iniciar')
@login_required('student')
def start_exam(exam_id):
    exam,course=exam_access(exam_id)
    existing=one(select(attempts).where(attempts.c.exam_id==exam_id,attempts.c.student_id==g.user['id']))
    if existing:return redirect(url_for('academy.take_exam',attempt_id=existing['id']))
    if exam['state']!='published':abort(409,description='El examen no está abierto.')
    started=now()
    try:
        result=g.db.execute(insert(attempts).values(exam_id=exam_id,student_id=g.user['id'],started_at=started,deadline=started+exam['duration']*60,answers_json='{}'))
        attempt_id=result.inserted_primary_key[0];g.db.commit()
    except IntegrityError:
        g.db.rollback();attempt_id=one(select(attempts.c.id).where(attempts.c.exam_id==exam_id,attempts.c.student_id==g.user['id']))['id']
    return redirect(url_for('academy.take_exam',attempt_id=attempt_id))

@bp.route('/intentos/<int:attempt_id>',methods=['GET','POST'])
@login_required('student')
def take_exam(attempt_id):
    attempt,exam,course=own_attempt(attempt_id);questions=json.loads(exam['questions_json'])
    if attempt['submitted_at'] is None and (now()>=attempt['deadline'] or exam['state']=='closed'):
        finalize(attempt,exam);return redirect(url_for('academy.take_exam',attempt_id=attempt_id))
    if request.method=='POST':
        if attempt['submitted_at'] is not None:abort(409,description='El intento ya fue entregado.')
        answers={}
        for i in range(len(questions)):
            value=request.form.get('q'+str(i))
            if questions[i].get('kind')=='written':
                work=request.form.get('work'+str(i),'').strip()
                if len(value or '')>240 or len(work)>3000:abort(400,description='Respuesta o procedimiento demasiado largo.')
                answers[str(i)]={'value':(value or '').strip(),'work':work}
            elif value is not None:
                if value not in ('0','1','2','3'):abort(400)
                answers[str(i)]=int(value)
        # Guard deadline and state again in SQL; a stale form cannot reopen an attempt.
        changed=g.db.execute(update(attempts).where(attempts.c.id==attempt_id,attempts.c.submitted_at.is_(None),attempts.c.deadline>now(),attempts.c.exam_id.in_(select(exams.c.id).where(exams.c.state=='published'))).values(answers_json=json.dumps(answers)))
        if changed.rowcount!=1:abort(409,description='El examen terminó. Recarga para ver el estado de tu entrega.')
        g.db.commit()
        if request.form.get('action')=='submit':
            attempt=one(select(attempts).where(attempts.c.id==attempt_id));finalize(attempt,exam,answers)
        if request.headers.get('X-Autosave')=='1':return {'saved':True,'server_time':now()}
        flash('Respuestas guardadas.' if request.form.get('action')!='submit' else 'Examen entregado.','success')
        return redirect(url_for('academy.take_exam',attempt_id=attempt_id))
    # Before closing the exam, never serialize correct answers or explanations to students.
    released=exam['state']=='closed' and attempt['submitted_at'] is not None
    public=[{k:q[k] for k in ('kind','prompt','formula','options') if k in q} for q in questions] if not released else questions
    return render_template('academy/take.html',exam=exam,course=course,attempt=attempt,questions=public,answers={k:v for k,v in json.loads(attempt['answers_json']).items() if released or k not in ('_grading','_feedback')},released=released,remaining=max(0,attempt['deadline']-now()))

@bp.get('/examenes/<int:exam_id>/resultados')
@login_required('teacher')
def results(exam_id):
    exam,course=exam_access(exam_id,True)
    pending=rows(select(attempts).where(attempts.c.exam_id==exam_id,attempts.c.submitted_at.is_(None)))
    for attempt in pending:
        if now()>=attempt['deadline'] or exam['state']=='closed':finalize(attempt,exam)
    entries=rows(select(attempts,users.c.name,users.c.email).join(users,users.c.id==attempts.c.student_id).where(attempts.c.exam_id==exam_id))
    entries=[dict(item,pending=sum(v.get('correct') is None for v in json.loads(item['answers_json']).get('_grading',{}).values())) for item in entries]
    return render_template('academy/results.html',exam=exam,course=course,entries=entries,count=len(json.loads(exam['questions_json'])))

@bp.get('/entregas/<int:attempt_id>')
@login_required('teacher')
def review_attempt(attempt_id):
    attempt=one(select(attempts).where(attempts.c.id==attempt_id))
    if not attempt:abort(404)
    exam,course=exam_access(attempt['exam_id'],True)
    if attempt['submitted_at'] is None and (now()>=attempt['deadline'] or exam['state']=='closed'):
        finalize(attempt,exam);attempt=one(select(attempts).where(attempts.c.id==attempt_id))
    student=one(select(users.c.name,users.c.email).where(users.c.id==attempt['student_id']))
    feedback=json.loads(attempt['answers_json']).get('_feedback',{})
    feedback_version=hashlib.sha256(json.dumps(feedback,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return render_template('academy/review.html',feedback=feedback,feedback_version=feedback_version,attempt=attempt,exam=exam,student=student,questions=json.loads(exam['questions_json']),answers=json.loads(attempt['answers_json']))

@bp.post('/entregas/<int:attempt_id>/calificar/<int:index>')
@login_required('teacher')
def mark_answer(attempt_id,index):
    attempt=one(select(attempts).where(attempts.c.id==attempt_id))
    if not attempt:abort(404)
    exam,course=exam_access(attempt['exam_id'],True)
    if attempt['submitted_at'] is None:abort(409,description='La entrega debe estar finalizada.')
    questions=json.loads(exam['questions_json'])
    if index>=len(questions):abort(404)
    answers=json.loads(attempt['answers_json'])
    if '_grading' not in answers:answers['_grading']=grade_answers(questions,answers)
    grading=answers['_grading']
    grading[str(index)]={'correct':bool(integer('correct',0,1)),'status':'teacher'}
    changed=g.db.execute(update(attempts).where(attempts.c.id==attempt_id,attempts.c.answers_json==attempt['answers_json']).values(answers_json=json.dumps(answers),score=sum(v.get('correct') is True for v in grading.values())))
    if changed.rowcount!=1:abort(409,description='La entrega cambió. Recarga la página.')
    g.db.commit();flash('Calificación actualizada.','success')
    return redirect(url_for('academy.review_attempt',attempt_id=attempt_id))

@bp.post('/entregas/<int:attempt_id>/comentarios')
@login_required('teacher')
def save_feedback(attempt_id):
    attempt=one(select(attempts).where(attempts.c.id==attempt_id))
    if not attempt:abort(404)
    exam,course=exam_access(attempt['exam_id'],True)
    if attempt['submitted_at'] is None:abort(409,description='Solo puedes comentar entregas finalizadas.')
    questions=json.loads(exam['questions_json'])
    feedback={'general':request.form.get('general','').strip(),'exercises':{}}
    if len(feedback['general'])>3000:abort(400,description='El comentario general admite hasta 3000 caracteres.')
    for i in range(len(questions)):
        comment=request.form.get('comment'+str(i),'').strip()
        if len(comment)>1500:abort(400,description='Cada comentario admite hasta 1500 caracteres.')
        if comment:feedback['exercises'][str(i)]=comment
    # Reject edits from an old browser form before replacing feedback.
    answers=json.loads(attempt['answers_json'])
    previous=json.dumps(answers.get('_feedback',{}),sort_keys=True,ensure_ascii=False)
    if request.form.get('feedback_version')!=hashlib.sha256(previous.encode()).hexdigest():
        abort(409,description='Los comentarios cambiaron en otra ventana. Recarga antes de guardar.')
    answers['_feedback']=feedback
    changed=g.db.execute(update(attempts).where(attempts.c.id==attempt_id,attempts.c.answers_json==attempt['answers_json']).values(answers_json=json.dumps(answers)))
    if changed.rowcount!=1:abort(409,description='La entrega cambió. Recarga antes de guardar.')
    g.db.commit();flash('Comentarios guardados. El estudiante los verá cuando cierres el examen.','success')
    return redirect(url_for('academy.review_attempt',attempt_id=attempt_id))

@bp.get('/examenes/<int:exam_id>/exportar/<kind>')
@login_required('teacher')
def export_exam(exam_id,kind):
    exam,course=exam_access(exam_id,True)
    if kind not in ('pdf','images'):abort(404)
    # Export gets only public exercise content, never answers or student data.
    questions=[{k:q[k] for k in ('kind','prompt','formula','options') if k in q} for q in json.loads(exam['questions_json'])]
    payload={'exam':{'title':exam['title'],'duration':exam['duration']},'course':{'title':course['title']},'questions':questions,'kind':kind}
    if not EXPORT_SLOT.acquire(blocking=False):abort(429,description='Hay otra exportación en curso. Inténtalo de nuevo en unos segundos.')
    try:
        run=subprocess.run([sys.executable,'-B','-m','academy.export'],input=json.dumps(payload).encode('utf-8'),capture_output=True,timeout=30,check=True,cwd=Path(__file__).resolve().parent.parent,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    except subprocess.SubprocessError:
        abort(503,description='No se pudo exportar. Revisa las fórmulas del borrador y las dependencias de PDF e imagen.')
    finally:EXPORT_SLOT.release()
    extension='pdf' if kind=='pdf' else 'zip'
    response=send_file(io.BytesIO(run.stdout),mimetype='application/pdf' if kind=='pdf' else 'application/zip',as_attachment=True,download_name=f'examen-{exam_id}.{extension}')
    response.headers['Cache-Control']='private, no-store'
    return response


def init_app(app):
    from datetime import timedelta
    from dotenv import load_dotenv
    load_dotenv()
    production=bool(os.getenv('RENDER') or os.getenv('ACADEMY_PRODUCTION')=='1')
    configured=app.config.get('SECRET_KEY') or os.getenv('SECRET_KEY')
    if production and (not configured or len(configured)<32 or not (os.getenv('ACADEMY_DATABASE_URL') or os.getenv('ACADEMY_ODBC_CONNECTION') or app.config.get('ACADEMY_DATABASE_URL') or app.config.get('ACADEMY_ODBC_CONNECTION'))):
        app.extensions['academy_error']='El aula necesita SECRET_KEY de al menos 32 caracteres y una base de datos persistente configuradas en el servidor.'
    if not configured and not production:
        folder=Path(app.instance_path);folder.mkdir(parents=True,exist_ok=True);path=folder/'session.key'
        try:
            with path.open('x',encoding='utf-8') as f:f.write(secrets.token_hex(32))
        except FileExistsError:pass
        configured=path.read_text(encoding='utf-8').strip()
    app.config.update(SECRET_KEY=configured,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',
                      SESSION_COOKIE_SECURE=production,PERMANENT_SESSION_LIFETIME=timedelta(hours=8))
    app.extensions['academy_dummy_hash']=generate_password_hash(secrets.token_urlsafe(20))
    if not app.extensions.get('academy_error'):
        Path(app.instance_path).mkdir(parents=True,exist_ok=True)
        engine=make_engine(app);app.extensions['academy_engine']=engine
        # Existing SQL Server installations are initialized explicitly by CLI.
        if engine.dialect.name=='sqlite':metadata.create_all(engine)
    app.register_blueprint(bp)
    app.jinja_env.globals['csrf_token']=csrf_token
    @app.before_request
    def academic_session():
        g.user=None;g.db=None
        engine=app.extensions.get('academy_engine')
        if engine is None:return
        if request.blueprint=='academy' or session.get('uid'):
            g.db=engine.connect()
            if session.get('uid'):
                user=one(select(users).where(users.c.id==session['uid']))
                if user and user['auth_version']==session.get('auth_version'):g.user=user
                else:session.clear()
    @app.teardown_request
    def close_db(error):
        if getattr(g,'db',None) is not None:g.db.close()
    @app.context_processor
    def account_context():return {'academic_user':getattr(g,'user',None),'academic_enabled':not app.extensions.get('academy_error')}
    @app.errorhandler(SQLAlchemyError)
    def db_error(error):
        if getattr(g,'db',None) is not None:g.db.rollback()
        app.logger.error('academic_database_failure type=%s',type(error).__name__)
        return render_template('academy/error.html',message='El aula no pudo acceder a su base de datos. Revisa la conexión y la inicialización.'),503
    @app.cli.command('init-academy')
    def init_database():
        engine=app.extensions.get('academy_engine')
        if engine is None:raise click.ClickException('Configura SECRET_KEY y la conexión del aula primero.')
        metadata.create_all(engine);click.echo('Tablas del aula creadas/verificadas.')
    @app.cli.command('authorize-teacher')
    @click.argument('email')
    def authorize(email):
        with app.extensions['academy_engine'].begin() as db:
            result=db.execute(update(users).where(users.c.email==email.strip().lower()).values(role='teacher',teacher_requested=0,auth_version=users.c.auth_version+1))
            if result.rowcount!=1:raise click.ClickException('Registra primero esa cuenta en la página.')
        click.echo('Profesor autorizado. Debe volver a iniciar sesión.')
    @app.cli.command('reset-academy-password')
    @click.argument('email')
    @click.password_option(confirmation_prompt=True)
    def reset_password(email,password):
        if not 12<=len(password)<=128:raise click.ClickException('Usa entre 12 y 128 caracteres.')
        with app.extensions['academy_engine'].begin() as db:
            result=db.execute(update(users).where(users.c.email==email.strip().lower()).values(password_hash=generate_password_hash(password),auth_version=users.c.auth_version+1))
            if result.rowcount!=1:raise click.ClickException('Cuenta no encontrada.')
        click.echo('Contraseña actualizada; las sesiones anteriores dejan de ser válidas.')
