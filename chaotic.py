import pickle
from argparse import ArgumentParser
from copy import deepcopy
from qiskit import Aer, execute
from qiskit import QuantumCircuit
from qiskit.circuit.library import YGate
import numpy as np


class ChaoticChain:

    def __init__(self, total_qbits, chaotic_patterns):

        self.total_qbits = total_qbits
        self.chaotic_patterns = deepcopy(chaotic_patterns)
        self.total_patterns = len(chaotic_patterns)
        self.layers = []
        self.pattern_id = 0

        self.single_sites = []
        for pattern in self.chaotic_patterns:
            sites = []
            for i in range(self.total_qbits):
                for pair in pattern:
                    if i in pair:
                        break
                else:
                    sites.append(i)
            self.single_sites.append(sites[:])

        self.circuit = QuantumCircuit(self.total_qbits, self.total_qbits) if total_qbits else None

    def append(self, gate):

        for i in range(self.total_qbits):
            getattr(self.circuit, gate)(i)

        self.layers.append([gate]*self.total_qbits)

    def add_random_single_gate_layer(self, gates, tracked_layer=None):

        self.layers.append([None]*self.total_qbits)

        if tracked_layer is None:
            for qidx in range(self.total_qbits):
                gate_name = np.random.choice(gates)
                if gate_name == 'sy':
                    self.circuit.append(YGate().power(0.5), [qidx])
                else:
                    getattr(self.circuit, gate_name)(qidx)
                if not (self.layers[-1][qidx] is None):
                    raise RuntimeError('Internal error!')
                self.layers[-1][qidx] = gate_name
        else:
            for qidx in range(self.total_qbits):
                excluded_gate = self.layers[tracked_layer][qidx]
                avail_gates = [gate for gate in gates if gate != excluded_gate]
                gate_name = np.random.choice(avail_gates)
                if gate_name == 'sy':
                    self.circuit.append(YGate().power(0.5), [qidx])
                else:
                    getattr(self.circuit, gate_name)(qidx)
                if not (self.layers[-1][qidx] is None):
                    raise RuntimeError('Internal error!')
                self.layers[-1][qidx] = gate_name

    def grow(self, gates, increment=1, barrier=False, track=True):
        
        tracked_layer = -3 if track else None

        for idx in range(increment):

            self.add_random_single_gate_layer(gates, tracked_layer)

            self.layers.append([None]*self.total_qbits)

            pattern = self.chaotic_patterns[self.pattern_id]
            for control, target in pattern:
                self.circuit.cz(control, target)
                if not (self.layers[-1][control] is None) or not (self.layers[-1][target] is None):
                    raise RuntimeError('Internal error!')
                self.layers[-1][control] = '{0}'.format(self.pattern_id)
                self.layers[-1][target] = '{0}'.format(self.pattern_id)

            if self.pattern_id == self.total_patterns-1:
                self.pattern_id = 0
            else:
                self.pattern_id += 1

            if barrier:
                self.circuit.barrier()
            

    def get_circuit(self, measure=True):

        if measure:
            res = self.circuit.copy()
            res.measure_all()
            return res
        else:
            return self.circuit.copy()


    def write(self, fn):

        circ = self.circuit
        self.circuit = None
        with open(fn, 'wb') as f:
            pickle.dump(self, f)
        self.circuit = circ
    
    def read(self, fn, layers=0):

        with open(fn, 'rb') as f:
            obj = pickle.load(f)
            self.total_qbits = obj.total_qbits
            self.chaotic_patterns = deepcopy(obj.chaotic_patterns)
            self.pattern_id = obj.pattern_id
            self.total_patterns = len(self.chaotic_patterns)
            self.layers = deepcopy(obj.layers)
            if layers:
                self.layers = self.layers[:layers]
            self.single_sites = deepcopy(obj.single_sites)

        self.circuit = QuantumCircuit(self.total_qbits, self.total_qbits)

        for layer in self.layers:

            pattern_idx = None
            for gate in layer:
                if gate is None:
                    continue
                if gate.isnumeric():
                    pattern_idx = int(gate)
                    break
            
            if not (pattern_idx is None):
                pattern = self.chaotic_patterns[pattern_idx]
                for control, target in pattern:
                    self.circuit.cz(control, target)

            for qidx, gate in enumerate(layer):
                
                if gate is None or gate.isnumeric():
                    continue

                if gate == 'sy':
                    self.circuit.append(YGate().power(0.5), [qidx])
                else:
                    getattr(self.circuit, gate)(qidx)



def get_parameters():

    p = ArgumentParser()

    p.add_argument('-n', '--niter', type=int, default=8192, help='Number of generated configurations (default: 8192).')
    p.add_argument('--basis', default='z', choices=('z', 'random'), help='Measurement basis (default: z).')
    p.add_argument('--depth', type=int, default=19, help='Depth of the chaotic chain (default: 19).')
    p.add_argument('--save', default='', help='Generate chain, save it and exit.')
    p.add_argument('--load', default='', help='Load chain from file and continue calculation.')

    return p.parse_args()


def get_random_basis(niter):

    th = np.ndarray((niter,), dtype=float)
    ph = np.ndarray((niter,), dtype=float)
    la = np.ndarray((niter,), dtype=float)

    total = 0
    while total != niter:
        t, p, l = np.random.random((3,))
        t = np.arccos(2*t-1)
        p = 2*np.pi*p
        l = 2*np.pi*l
        if (t <= np.pi/2 and t >= 0 and p <= np.pi/2 and p >= 0 and l <= np.pi/2 and l >= 0):
            th[total] = t
            ph[total] = p
            la[total] = l
            total += 1

    return th, ph, la


def main():

    p = get_parameters()

    simulator = Aer.get_backend('qasm_simulator')

    # calculation parameters used in paper
    # total qbits and possible qbit pairs for CX gates
    total_qbits = 16
    chaotic_patterns = [
        [[0,1],[6,7],[8,9],[14,15]],
        [[2,3],[4,5],[10,11],[12,13]],
        [[5,9],[7,11]],
        [[4,8],[6,10]],
        [[1,2],[9,10]],
        [[5,6],[13,14]],
        [[1,5],[3,7],[8,12],[10,14]],
        [[0,4],[2,6],[9,13],[11,15]]
    ]
    gates = ['sx', 'sy', 't']

    # output file name template
    tmpl = 'chaotic'
    tmpl += '.{0}'.format(p.basis)
    tmpl += '.depth={0}.dat'.format(p.depth)

    if not p.load:

        chaos = ChaoticChain(total_qbits, chaotic_patterns)

        chaos.append('reset')
        chaos.grow(gates, track=False)

        for i in range(p.depth-1):
            chaos.grow(gates)

        if p.save:
            chaos.write(p.save)
            exit(0)
        
    else:

        chaos = ChaoticChain(0,[])
        chaos.read(p.load)

        total_qbits = chaos.total_qbits

    chaotic_circuit = chaos.get_circuit(False)

    if p.basis == 'random':
        th, ph, la = get_random_basis(p.niter)

    with open(tmpl, 'w') as ffz:

        for it in range(p.niter):
            
            circ = chaotic_circuit.copy()

            if p.basis == 'random':
                for i in range(total_qbits):
                    circ.u(th[it], ph[it], la[it], i)

            circ.barrier()

            for i in range(total_qbits):
                circ.measure(i, i)

            job = execute(circ, backend=simulator, shots=1)

            result = job.result()
            counts = result.get_counts(circ)

            for bits in counts:
                ffz.write(bits)


if __name__ == '__main__':
    main()
