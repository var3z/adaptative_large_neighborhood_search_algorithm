#-------------------------------------------------------------------------------
# En este modulo se define el modelo de la red de cercanias de Madrid contemplando
# los 800 pares origen-destino admisibles.
#-------------------------------------------------------------------------------
from __future__ import division
from pyomo.environ import *
from sys import *

"""
Tipo de modelo
"""
model = AbstractModel()

"""
Conjuntos
"""
model.N = Set()                   #nodos
model.W = Set()                   #pares origen-destino
model.L = Set()                   #lineas
model.ST = Set()                  #RangeSet de segmentos compartidos || (i,j) ? E: sum(a[i,j,l] for l in model.L) > 1
model.V = Set()                   #Frecuencias permitidas 2,3,4,5,6,10,12,15,20 trenes/hora
model.TET = Set()                 #Conjunto de coeficientes tetha
model.T = Set()                   #set 1..N, siendo N el numero maximo de vias compartidas


"""
Datos
"""
model.gamma = Param(model.L)                   #Longitud de la linea L
model.d = Param(model.N, model.N)              #Distancia del enlace (i,j)
model.tetha = Param(model.TET)                 #Coeficientes monetarios
model.tethafr = Param(model.V, model.V)        #Matriz de compatibilidad de headways

model.v = Param()                              #Velocidad de funcionamiento
model.C = Param()                              #Capacidad del vagon
model.NVmax = Param()                          #Vagones maximos por tren
model.NVmin = Param()                          #Vagones minimos por tren
model.Vmax = Param()                           #frecuencia maxima
model.sft = Param()                            #tiempo ventana de seguridad
model.dwt = Param()                            #Tiempo de espera en estacion

model.ckm_loc= Param()                         #Coste variable de operacion de la linea (eur por Km plaza y hora) dependiente de la capacidad  y frecuencia
model.ckm_carr= Param()                        #Coste variable de operacion de la linea (eur por Km plaza y hora) dependiente de la capacidad  y frecuencia
model.Horizonte= Param()                       #Horizonte para computar costes de compra de rolling stocks medido en anios
model.cost_loc= Param()                        #Coste de compra de una locomotora por 10E6
model.cost_carr= Param()                       #Coste de compra de un vagon por 10E6
model.factorg = Param()                        #Factor de escala de la demanda

model.a = Param(model.N, model.N, model.L,default=0)    #matriz de incidencia. a[i,j,l]=1 si la linea l pasa por el arco i,j
model.b = Param(model.N, model.L)              			#matriz de incidencia. b[i,l]=1 si la linea l para en el nodo i

#COnjuntos auxiliares para datos

model.CT = Set()                               			#Cabecera Tabla
model.CTr = Set()                              			#Cabecera Tracks
model.tabla = Param(model.W,model.CT)          			#tabla del tipo [w wo wd g[w]]
model.tracks = Param(model.ST,model.CTr)       			#tabla del tipo [segmento    nodo-orig-segmento  nodo-fin-segmento    numero-de-vias]
model.ijw = Param(model.N,model.N,model.W, default=0)   #Tabla de pares validos

#Conjuntos auxiliares para el modelo

def indexNNW_rule(model):
    indices=[]
    for w in model.W:
        for i in model.N:
            for j in model.N:
                if model.ijw[i,j,w]==1:
                    indices.append((i,j,w))
    return indices
model.NNW = Set(dimen=3, initialize=indexNNW_rule)  #Indices simplificados - indices de las variables no nulas y pares-nodos permitidos (w=800)


"""
Variables
"""
model.f = Var(model.NNW, model.L, within=NonNegativeIntegers)                       #flujo de pasajeros que circulan en la linea l, por el arco i,j, con un par origen-destino w
model.fo = Var(model.W, model.L, within=NonNegativeIntegers)                        #flujo de pasajeros desde cada origen
model.fd = Var(model.W, model.L, within=NonNegativeIntegers)                        #flujo de pasajeros hacia cada destino
model.trans = Var(model.N,model.W, model.L, model.L, within=NonNegativeIntegers)    #flujo con par origen-destino w, transbordando en el nodo i, de la linea l a lp
model.beta = Var(model.L, model.V, within=Boolean)                                  #vble auxiliar. beta[l,v]=1 si la linea l circula con la frecuencia v
model.delta = Var(model.ST, model.L, model.T, within=Boolean)                       #vble auxiliar. delta[s,l,t]=1 si el track t del segmento compartido s, esta asignado a la linea l
model.h = Var(model.W,within=NonNegativeIntegers)                                   #variables de holguras
model.fr = Var(model.L, within=NonNegativeIntegers)                                 #frecuencia para cada linea l
model.frs = Var(model.ST, model.L, model.T, within=NonNegativeIntegers)             #frecuencia que lleva la linea l en el track t del segmeto compartido s
model.u = Var(model.W, within=NonNegativeReals)

#variables de depuracion
model.flujoarco = Var(model.N,model.N, within=NonNegativeReals)
model.capacidadarco = Var(model.N,model.N, within=NonNegativeReals)
model.FO1 = Var(within=NonNegativeReals)
model.FO2 = Var(within=NonNegativeReals)
model.FO3 = Var(within=NonNegativeReals)
model.FO4 = Var(within=NonNegativeReals)
model.FO5 = Var(within=NonNegativeReals)
model.FO6 = Var(within=NonNegativeReals)
model.FO7 = Var(within=NonNegativeReals)
model.FO8 = Var(within=NonNegativeReals)

#Variables modificadas por ALNS, se pasan como datos parametrizados
model.hd = Param(model.L,mutable=True, within=NonNegativeIntegers)                   #headways para cada linea l
model.nv = Param(model.L,mutable=True, within=NonNegativeIntegers)                   #numero de vagones de la linea l
model.ALNS = Var(model.ST,model.T,model.L,model.L, within=Boolean)
model.ALNS2 = Var(model.ST,model.T, within=Boolean)
model.M = Param(mutable=True)
model.M2 = Param(mutable=True)


"""
Restricciones
"""

#1 // flujo de salida desde cada origen "wo" igual a demanda del par origen destino "w"
def resd1_rule(model,w):
    wo=model.tabla[w,'wo']
    expr=0
    for l in model.L:
            if model.b[wo,l]==1:
                expr += model.fo[w,l]
    if expr!=0:
        return (expr + model.h[w]==model.tabla[w,'g']*model.factorg)
    else:
        return Constraint.Skip
model.restr1 = Constraint(model.W,rule=resd1_rule)

#2 // flujo de llegada a cada destino "wd" igual a demanda del par origen destino "w"
def resd2_rule(model,w):
    wd=model.tabla[w,'wd']
    expr=0
    for l in model.L:
            if model.b[wd,l]==1:
                expr += model.fd[w,l]
    if expr!=0:
        return (expr + model.h[w]==model.tabla[w,'g']*model.factorg)
    else:
        return Constraint.Skip
model.restr2 = Constraint(model.W,rule=resd2_rule)

#3 // conservacion del flujo teniendo en cuenta transbordos
def resd3_rule(model,i,w,l):
    wo=model.tabla[w,'wo']
    wd=model.tabla[w,'wd']
    expr1=expr2=expr3=expr4=0
    if i!=wo and i!=wd:
        for j in model.N:
            if model.a[i,j,l]==1 and model.ijw[i,j,w]==1:
                    expr3+=model.f[i,j,w,l]
        for k in model.N:
            if model.a[k,i,l]==1 and model.ijw[k,i,w]==1:
                    expr1+=model.f[k,i,w,l]
        for lp in model.L:
            if l!=lp and model.b[i,lp]==1 and model.b[i,l]==1:
                expr2+=model.trans[i,w,lp,l]
                expr4+=model.trans[i,w,l,lp]
    if (expr2+expr3)!=0 and (expr1+expr4)!=0:
            return (expr1+expr2==expr3+expr4)
    else:
        return Constraint.Skip
model.restr3 = Constraint(model.N,model.W,model.L, rule=resd3_rule)

#4 // flujo de transporte nulo si y[i,j,w,l]==0
#se elimina model.y[i,j,w,l] del termino derecho de la desigualdad
def resd4_rule(model,i,j,w,l):
    if model.a[i,j,l]==1 and model.ijw[i,j,w]==1:
        return (model.f[i,j,w,l]<=model.tabla[w,'g']*model.factorg)
    else:
        return Constraint.Skip
model.restr4 = Constraint(model.NNW,model.L,rule=resd4_rule)

#5a // flujo saliente de cada nodo origen
def resd5_rule(model,w,l):
    wo=model.tabla[w,'wo']
    expr=0
    for j in model.N:
        if model.b[j,l]==1 and model.ijw[wo,j,w]==1:
                expr+=model.f[wo,j,w,l]
    if expr!=0:
        return (expr==model.fo[w,l])
    else:
        return Constraint.Skip
model.restr5 = Constraint(model.W,model.L,rule=resd5_rule)

#5b // flujo entrante en cada nodo destino
def resd5b_rule(model,w,l):
    wd=model.tabla[w,'wd']
    expr=0
    for i in model.N:
        if model.a[i,wd,l]==1 and model.ijw[i,wd,w]==1:
                expr+=model.f[i,wd,w,l]
    if expr!=0:
        return (expr==model.fd[w,l])
    else:
        return Constraint.Skip
model.restr5b = Constraint(model.W,model.L,rule=resd5b_rule)

#6 // Promedio tiempo viaje
def resd6_rule(model,w):
    expr1=expr2=expr3=0
    wo=model.tabla[w,'wo']
    for l in model.L:
        for i in model.N:
            for j in model.N:
                if model.a[i,j,l]==1 and model.ijw[i,j,w]==1:
                    expr1+=(60/model.v)*model.d[i,j]*model.f[i,j,w,l]
            for lp in model.L:
                if lp!=l and model.b[i,lp]==1 and model.b[i,l]==1:
                    expr3+=0.5*model.trans[i,w,l,lp]*model.hd[lp]
        expr2+=0.5*model.fo[w,l]*model.hd[l]
    return (model.u[w]==expr1+expr2+expr3)
model.restr6 = Constraint(model.W,rule=resd6_rule)

#7 // relacion entre frecuencias y headways
def resd7_rule(model,l):
    return (model.fr[l]*model.hd[l]==60)
model.restr7 = Constraint(model.L, rule=resd7_rule)

#8a // asignacion de frecuencia a cada linea
def resd8a_rule(model,l):
    return (model.fr[l]==sum(v*model.beta[l,v] for v in model.V))
model.restr8a = Constraint(model.L, rule=resd8a_rule)

#8b // solo una frecuencia es admisible por linea
def resd8b_rule(model,l):
    return (1==sum(model.beta[l,v] for v in model.V))
model.restr8b = Constraint(model.L, rule=resd8b_rule)

#9 // asignacion de via t en el segmento compartido s a la linea l
def resd9_rule(model,s,l):
    si=model.tracks[s,'si']
    sf=model.tracks[s,'sf']
    if model.a[si,sf,l]==1:
        vias=range(1,model.tracks[s,'vias']+1)
        return (1==sum(model.delta[s,l,t] for t in vias))
    else:
        return Constraint.Skip
model.restr9 = Constraint(model.ST,model.L, rule=resd9_rule)

#10 // asignacion de frecuencias en segmentos compartidos
def resd10_rule(model,s,l):
    si=model.tracks[s,'si']
    sf=model.tracks[s,'sf']
    if model.a[si,sf,l]==1:
        vias=range(1,model.tracks[s,'vias']+1)
        return (model.fr[l]==sum(model.frs[s,l,t] for t in vias))
    else:
        return Constraint.Skip
model.restr10 = Constraint(model.ST,model.L, rule=resd10_rule)

#11 // las frecuencias en segmentos compartidos son menores o igual a la frecuencia maxima
def resd11_rule(model,s,l,t):
    si=model.tracks[s,'si']
    sf=model.tracks[s,'sf']
    if t>model.tracks[s,'vias']:
        return Constraint.Skip
    if model.a[si,sf,l]==1:
        return (model.frs[s,l,t]<=model.Vmax*model.delta[s,l,t])
    else:
        return Constraint.Skip
model.restr11 = Constraint(model.ST,model.L, model.T, rule=resd11_rule)

#12 // safety time and dwell time
def resd12_rule(model,s,t):
    si=model.tracks[s,'si']
    sf=model.tracks[s,'sf']
    if t>model.tracks[s,'vias']:
        return Constraint.Skip
    expr=0
    for l in model.L:
        if model.a[si,sf,l]==1:
            expr+=model.frs[s,l,t]
    if expr!=0:
        return (expr*(model.sft + model.dwt)<=60 + 420 * model.ALNS2[s,t])
    else:
        return Constraint.Skip
model.restr12 = Constraint(model.ST, model.T, rule=resd12_rule)

#13 // Multiplicidad
def resd13_rule(model,s,l,lp,v,vp,t):
    if t>model.tracks[s,'vias']:
        return Constraint.Skip
    vias=range(1,model.tracks[s,'vias']+1)
    si=model.tracks[s,'si']
    sf=model.tracks[s,'sf']
    if l<lp and v<=vp and model.a[si,sf,l]==1 and model.a[si,sf,lp]==1:
        return (model.delta[s,l,t] + model.delta[s,lp,t] <= 3 + model.tethafr[v,vp] - (model.beta[l,v] + model.beta[lp,vp]) + model.ALNS[s,t,l,lp])
    else:
        return Constraint.Skip
model.restr13 = Constraint(model.ST,model.L,model.L,model.V,model.V, model.T, rule=resd13_rule)

#14 // el flujo de cada linea es inferior a la capacidad de los vagones de dicha linea
def resd14_rule(model,i,j,l):
    expr=0
    for w in model.W:
        if model.a[i,j,l]==1 and model.ijw[i,j,w]==1:
            expr+=model.f[i,j,w,l]
    if expr!=0:
        return (expr<=(2+model.nv[l])*model.C*model.fr[l])
    else:
        return Constraint.Skip
model.restr14 = Constraint(model.N, model.N, model.L, rule=resd14_rule)

#Ecuaciones de depuracion
def depura1_rule(model,i,j):
    expr=0
    for l in model.L:
        for w in model.W:
            if model.ijw[i,j,w]==1 and model.a[i,j,l]==1:
                expr+=model.f[i,j,w,l]
    if expr!=0:
            return (model.flujoarco[i,j]==expr)
    else:
            return Constraint.Skip
model.restr15 = Constraint(model.N, model.N, rule=depura1_rule)

def depura2_rule(model,i,j):
    expr=0
    for l in model.L:
            if model.a[i,j,l]==1:
                expr+=(2+model.nv[l])*model.C*model.fr[l]
    if expr!=0:
        return (model.capacidadarco[i,j]==expr)
    else:
        return Constraint.Skip
model.restr16 = Constraint(model.N, model.N, rule=depura2_rule)

"""
Funcion Objetivo
"""
#penalizacion por demanda no atendida
def depura3_rule(model):
    return (model.FO6==sum(5000000*model.h[w] for w in model.W))
model.restr17 = Constraint(rule=depura3_rule)

#penalizacion por transbordo
def depura4_rule(model):
    expr=0
    for l in model.L:
        for lp in model.L:
            for w in model.W:
                for i in model.N:
                    if model.b[i,l]==1 and model.b[i,lp]==1:
                            expr+=model.trans[i,w,l,lp]
    return (model.FO2==model.tetha[2]*expr)
model.restr18 = Constraint(rule=depura4_rule)

#Coste operacion por distancia recorrida
def depura5_rule(model):
    return(model.FO3==sum(1.2*model.gamma[l]*model.fr[l]*(model.ckm_loc+model.ckm_carr*(model.nv[l]+1)) for l in model.L))
model.restr19 = Constraint(rule=depura5_rule)

#Coste operacion por tiempo trenes
def depura6_rule(model):
    return(model.FO4==model.tetha[4]*sum(1.2*model.gamma[l]*model.fr[l]/model.v for l in model.L))
model.restr20 = Constraint(rule=depura6_rule)

#Coste de adquisicion
def depura7_rule(model):
    return(model.FO5==(1000000/(model.Horizonte*365*24))*sum(1.2*model.gamma[l]*(model.fr[l]/model.v)*(2*model.cost_loc + model.nv[l]*model.cost_carr) for l in model.L))
model.restr21 = Constraint(rule=depura7_rule)

#Tiempos de viaje
def depura8_rule(model):
    return(model.FO1==model.tetha[1]*sum(model.u[w] for w in model.W))
model.restr22 = Constraint(rule=depura8_rule)

#Variables ALNS
def depura9_rule(model):
    return(model.FO7==model.M2*(sum(sum(model.ALNS2[s,t] for s in model.ST) for t in model.T)))
#model.restr23 = Constraint(rule=depura9_rule)

def depura10_rule(model):
    return(model.FO8==model.M*sum(sum(sum(sum(model.ALNS[s,t,l,lp] for s in model.ST) for t in model.T) for l in model.L) for lp in model.L))
model.restr24 = Constraint(rule=depura10_rule)

#FO
def obj_rule(model):
    return (model.FO1+model.FO2+model.FO3+model.FO4+model.FO5+model.FO6+model.FO7+model.FO8)
model.obj = Objective(rule=obj_rule)