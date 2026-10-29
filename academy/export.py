"""Exportación acotada en un proceso separado. PNG A4 a 150 ppp y PDF."""
import io
import json
import sys
import zipfile
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
from matplotlib.mathtext import math_to_image
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4

WIDTH,HEIGHT=1240,1754
FONT_DIR=Path(matplotlib.get_data_path())/'fonts'/'ttf'

def font(size,bold=False):
    return ImageFont.truetype(str(FONT_DIR/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')),size)

def pages(exam,course,questions):
    output=[];page=None;draw=None;y=0
    def paragraph(text,size=26,bold=False,max_width=1080):
        nonlocal y
        f=font(size,bold)
        # Wrap by character as well, so long titles cannot run off the page.
        for original in str(text).splitlines() or ['']:
            line=''
            for char in original:
                if draw.textlength(line+char,font=f)>max_width:
                    draw.text((80,y),line,font=f,fill='#152635');y+=size+12;line=''
                line+=char
            draw.text((80,y),line,font=f,fill='#152635');y+=size+12
    def start_page():
        nonlocal page,draw,y
        page=Image.new('RGB',(WIDTH,HEIGHT),'white');draw=ImageDraw.Draw(page);output.append(page);y=65
        paragraph('MATEMÁTICA II  /  EXAMEN',22,True)
        paragraph(exam['title'],32,True)
        paragraph(course['title'],22)
        paragraph(f"Duración: {exam['duration']} minutos    |    {len(questions)} ejercicios",22)
        paragraph('Nombre: ___________________________________   Fecha: ______________',22)
        draw.line((80,y+5,1160,y+5),fill='#7e919c',width=2);y+=30
    start_page()
    for i,q in enumerate(questions):
        formula=None
        if q.get('formula'):
            stream=io.BytesIO();math_to_image('$'+q['formula']+'$',stream,dpi=180,format='png',color='black')
            formula=Image.open(stream).convert('RGBA')
            if formula.width>1080:formula= formula.resize((1080,max(1,int(formula.height*1080/formula.width))))
        prompt=q['prompt'][:1500]
        estimate=(len(prompt)//65+2)*38+330+(formula.height if formula else 0)
        if y+estimate>HEIGHT-100 and y>400:start_page()
        paragraph(f'Ejercicio {i+1}',26,True);paragraph(prompt)
        if formula:
            page.paste(formula,(80,y+8),formula);y+=formula.height+35
        if q.get('kind')!='written':
            for j,option in enumerate(q.get('options',[])):paragraph(f"{'ABCD'[j]}. {option}",24)
        paragraph('Desarrollo y respuesta:',22)
        for _ in range(4):
            y+=48;draw.line((80,y,1160,y),fill='#d7dee2',width=1)
        y+=45
    for n,image in enumerate(output,1):
        ImageDraw.Draw(image).text((80,HEIGHT-65),f'Matemática II  |  Página {n} de {len(output)}',font=font(20),fill='#506472')
    return output

def export(exam,course,questions,kind):
    images=pages(exam,course,questions);out=io.BytesIO()
    if kind=='pdf':
        pdf=canvas.Canvas(out,pagesize=A4);pdf.setTitle(exam['title']);pdf.setAuthor('Matemática II')
        for image in images:
            pdf.drawImage(ImageReader(image),0,0,width=A4[0],height=A4[1]);pdf.showPage()
        pdf.save()
    elif kind=='images':
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
            for n,image in enumerate(images,1):
                buffer=io.BytesIO();image.save(buffer,format='PNG',dpi=(150,150));archive.writestr(f'examen-pagina-{n:02}.png',buffer.getvalue())
    else:raise ValueError('Formato inválido.')
    return out.getvalue()

if __name__=='__main__':
    request=json.loads(sys.stdin.read(200000))
    if not 1<=len(request['questions'])<=20:raise ValueError('Cantidad inválida.')
    sys.stdout.buffer.write(export(request['exam'],request['course'],request['questions'],request['kind']))
