#!/bin/bash

# You can control number of threads used by Qiskit
export OMP_NUM_THREADS=1

# Total number of bitstrings for each calculation
N=8192

## Schrödinger cat states from research paper

echo 'Calculating Schrödinger cat states...'

# z-basis
python3 ./cats.py -n ${N} --qbits 16

# random basis
python3 ./cats.py -n ${N} --qbits 16 --basis random

## Dicke states from research paper

echo 'Calculating Dicke states...'

# different values of D parameter
for d in {1..8}
do
    python3 ./dicke.py -n ${N} --qbits 16 -D ${d}
    python3 ./dicke.py -n ${N} --qbits 16 -D ${d} --basis random
done

## Chaotic states

echo 'Calculating chaotic states...'

python3 ./chaotic.py -n ${N} --depth 19
python3 ./chaotic.py -n ${N} --depth 19 --basis random