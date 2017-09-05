# ALNS
ALNS Algorithm which optimise MINLP railroad network models (applied to Madrid's network)

## ALNS.py
This file contains Python code in order to create an "Adaptatipe Large Neighborhood Search" algorithm which can manage a "Mixed Integer Non Linear Programming" model. This kind of model, doesn't have an exact solution, so should be solved with metaheuristic algorithm such as this one.

## madridALNS.py
This file is the Madrid short-distance railroad model. With the aid of Pyomo (https://github.com/Pyomo) the whole model is developed.

## madridALNS.dat
This file contains data for fill the model: real distances, conections (tracks) between nodes (stations), railroad lines, times, wagons, etc.

## plantilla.xlsx
This is an Excel template. Only for results.
