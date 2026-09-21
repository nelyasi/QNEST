import json
import re
from pytket import OpType
from src.config import BRIDGE_FILE

def export_distributed_circuit_for_qoala(dist_circ, qubits_per_qpu, filename=BRIDGE_FILE):
    events = []

    def parse_qubit(q):
        text = str(q)
        server_match = re.search('server_(\\d+)', text)
        index_match = re.search('\\[(\\d+)\\]', text)
        if server_match is None or index_match is None:
            raise ValueError(f'Cannot understand distributed qubit: {text}')
        return {'name': text, 'server': int(server_match.group(1)), 'index': int(index_match.group(1)), 'is_link': '_link_register' in text}
    for event_id, cmd in enumerate(dist_circ.get_commands()):
        qubits = [parse_qubit(q) for q in cmd.qubits]
        if cmd.op.type == OpType.CustomGate:
            operation = cmd.op.get_name()
        else:
            operation = cmd.op.type.name
        if operation.startswith('starting_process'):
            kind = 'STARTING_PROCESS'
        elif operation.startswith('ending_process'):
            kind = 'ENDING_PROCESS'
        elif len(qubits) == 1:
            kind = 'SINGLE'
        elif len(qubits) == 2:
            kind = 'TWO'
        else:
            raise ValueError(f'Unsupported operation: {cmd}')
        events.append({'id': event_id, 'kind': kind, 'operation': operation, 'qubits': qubits})
    data = {'qubits_per_qpu': qubits_per_qpu, 'events': events}
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f'Exported {len(events)} operations')
    print(f'Saved to: {filename}')
    return filename