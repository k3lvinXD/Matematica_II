"""Catálogo ligero compartido por formularios y generador."""
TOPIC_GROUPS={
    'Unidad 1 · Cálculo diferencial':{
        'partials':'Derivadas parciales', 'gradient':'Gradiente en un punto',
        'directional':'Derivada direccional', 'tangent':'Plano tangente y recta normal',
        'extrema':'Máximos, mínimos y silla', 'lagrange':'Multiplicadores de Lagrange',
        'exact':'Diferencial exacta y potencial', 'chain':'Regla de la cadena',
        'jacobian':'Jacobiano', 'limit':'Límite univariable'},
    'Unidad 2 · Integración':{
        'double_integral':'Integral doble cartesiana', 'triple_integral':'Integral triple',
        'polar':'Integrales polares', 'surface_area':'Área de una superficie',
        'mass_center':'Masa y centro de masa'},
    'Unidad 3 · Análisis vectorial':{
        'vector_curve':'Trayectoria espacial: velocidad y aceleración',
        'vector_field':'Campo vectorial 2D', 'divergence':'Divergencia',
        'curl':'Rotacional', 'laplacian':'Laplaciano', 'line_integral':'Integral de línea',
        'conservative':'Campo conservativo', 'green':'Teorema de Green'}
}
TOPICS={key:label for group in TOPIC_GROUPS.values() for key,label in group.items()}
ALIASES={'partial':'partials','double':'double_integral'}
