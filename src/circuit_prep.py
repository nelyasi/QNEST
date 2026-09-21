from pathlib import Path
from tempfile import TemporaryDirectory
from pytket_dqc.utils import DQCPass
from mqt.bench import BenchmarkLevel, get_benchmark
from qiskit import qasm2
from pytket.qasm import circuit_from_qasm
from pytket.circuit.display import render_circuit_jupyter

def clean_qasm_file(input_path, output_path):
    lines_to_keep = []
    with open(input_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith('creg '):
                continue
            if stripped.startswith('measure '):
                continue
            if stripped.startswith('barrier '):
                continue
            lines_to_keep.append(line)
    with open(output_path, 'w') as f:
        f.writelines(lines_to_keep)

def load_and_prepare_circuit_clean(qasm_path):
    qasm_path = Path(qasm_path)
    clean_dir = qasm_path.parent / '_cleaned'
    clean_dir.mkdir(exist_ok=True)
    cleaned_path = clean_dir / qasm_path.name
    original_circ = circuit_from_qasm(qasm_path)
    print('\n======================================')
    print('ORIGINAL CIRCUIT')
    print('======================================')
    render_circuit_jupyter(original_circ)
    clean_qasm_file(qasm_path, cleaned_path)
    circ = circuit_from_qasm(cleaned_path)
    print('\n======================================')
    print('CIRCUIT AFTER CLEANING')
    print('======================================')
    render_circuit_jupyter(circ)
    DQCPass().apply(circ)
    print('\n======================================')
    print('CIRCUIT AFTER DQCPass')
    print('======================================')
    render_circuit_jupyter(circ)
    return circ

def prepare_mqt_circuit(qiskit_circuit):
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        qasm_path = tmpdir / 'benchmark.qasm'
        qasm2.dump(qiskit_circuit, qasm_path)
        prepared_circuit = load_and_prepare_circuit_clean(qasm_path)
    return prepared_circuit