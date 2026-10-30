"""Esquema común a SQLite (desarrollo) y SQL Server (producción)."""
import os
from pathlib import Path
from sqlalchemy import (MetaData, Table, Column, Integer, BigInteger, Unicode, UnicodeText,
                        ForeignKey, UniqueConstraint, create_engine, event)
from sqlalchemy.engine import URL
from sqlalchemy.dialects.mssql import NVARCHAR

LONG_TEXT=UnicodeText().with_variant(NVARCHAR(None), "mssql")

metadata=MetaData()
users=Table('academic_users',metadata,
    Column('id',Integer,primary_key=True),Column('name',Unicode(100),nullable=False),
    Column('email',Unicode(254),nullable=False,unique=True),Column('password_hash',Unicode(512),nullable=False),
    Column('role',Unicode(20),nullable=False),Column('teacher_requested',Integer,nullable=False,default=0),
    Column('auth_version',Integer,nullable=False,default=1))
courses=Table('academic_courses',metadata,
    Column('id',Integer,primary_key=True),Column('teacher_id',ForeignKey(users.c.id),nullable=False),
    Column('title',Unicode(120),nullable=False),Column('join_code',Unicode(24),nullable=False,unique=True))
enrollments=Table('academic_enrollments',metadata,
    Column('id',Integer,primary_key=True),Column('course_id',ForeignKey(courses.c.id),nullable=False),
    Column('student_id',ForeignKey(users.c.id),nullable=False),UniqueConstraint('course_id','student_id'))
exams=Table('academic_exams',metadata,
    Column('id',Integer,primary_key=True),Column('course_id',ForeignKey(courses.c.id),nullable=False),
    Column('title',Unicode(160),nullable=False),Column('topic',Unicode(40),nullable=False),
    Column('difficulty',Unicode(20),nullable=False),Column('duration',Integer,nullable=False),
    Column('state',Unicode(20),nullable=False),Column('questions_json',LONG_TEXT,nullable=False),
    Column('created_at',BigInteger,nullable=False))
attempts=Table('academic_attempts',metadata,
    Column('id',Integer,primary_key=True),Column('exam_id',ForeignKey(exams.c.id),nullable=False),
    Column('student_id',ForeignKey(users.c.id),nullable=False),Column('started_at',BigInteger,nullable=False),
    Column('deadline',BigInteger,nullable=False),Column('submitted_at',BigInteger),
    Column('answers_json',LONG_TEXT,nullable=False),Column('score',Integer),
    UniqueConstraint('exam_id','student_id'))
login_limits=Table('academic_login_limits',metadata,
    Column('key',Unicode(64),primary_key=True),Column('failures',Integer,nullable=False),
    Column('expires',BigInteger,nullable=False))

def make_engine(app):
    connection=app.config.get('ACADEMY_ODBC_CONNECTION') or os.getenv('ACADEMY_ODBC_CONNECTION')
    url=app.config.get('ACADEMY_DATABASE_URL') or os.getenv('ACADEMY_DATABASE_URL')
    if connection:
        target=URL.create('mssql+pyodbc',query={'odbc_connect':connection})
    elif url:
        target=url
    else:
        target='sqlite:///'+str(Path(app.instance_path)/'academia.sqlite3')
    engine=create_engine(target,pool_pre_ping=True,hide_parameters=True,
                         connect_args={'timeout':15} if str(target).startswith('sqlite') else {})
    if engine.dialect.name=='sqlite':
        @event.listens_for(engine,'connect')
        def configure_sqlite(dbapi_connection, record):
            dbapi_connection.execute('PRAGMA foreign_keys=ON')
    if engine.dialect.name not in ('sqlite','mssql','postgresql'):
        engine.dispose()
        raise ValueError('Usa SQLite, SQL Server o PostgreSQL para el aula.')
    return engine
