from qoala.lang.parse import QoalaParser

def _make_qoala_program(server, events, data_qubits):
    node_name = f'qpu_{server}'
    peers = sorted({event['peer'] for event in events if event['peer'] is not None})
    epr_socket_for_peer = {peer: socket_id for socket_id, peer in enumerate(peers)}
    epr_socket_text = ', '.join((f'{epr_socket_for_peer[peer]} -> qpu_{peer}' for peer in peers))
    host_blocks = []
    subroutines = []
    requests = []
    metadata = {}
    data = sorted(data_qubits.get(server, set()))
    if data:
        uses = ', '.join((str(q) for q in data))
        netqasm_lines = []
        for register, q in enumerate(data):
            netqasm_lines.append(f'set Q{register} {q}')
            netqasm_lines.append(f'init Q{register}')
        netqasm_text = '\n    '.join(netqasm_lines)
        host_blocks.append('\n^initialise_qubits {type = QL}:\n    run_subroutine() : initialise_qubits_routine\n')
        subroutines.append(f'\nSUBROUTINE initialise_qubits_routine\n    params:\n    returns:\n    uses: {uses}\n    keeps: {uses}\n    request:\n  NETQASM_START\n    {netqasm_text}\n  NETQASM_END\n')
    for event in events:
        event_id = event['event_id']
        kind = event['kind']
        operation = event['operation']
        if kind == 'SINGLE':
            q = event['qubits'][0]
            block = f'ev_{event_id}_single'
            routine = f'routine_{event_id}_single'
            host_blocks.append(f'\n^{block} {{type = QL}}:\n    run_subroutine() : {routine}\n')
            subroutines.append(f'\nSUBROUTINE {routine}\n    params:\n    returns:\n    uses: {q}\n    keeps: {q}\n    request:\n  NETQASM_START\n    set Q0 {q}\n    h Q0\n  NETQASM_END\n')
            metadata[block] = {'event_id': event_id, 'type': 'SINGLE_GATE', 'operation': operation, 'qpu': server, 'peer': None, 'role': '', 'qubits': event['original_qubits']}
        elif kind == 'TWO':
            q0, q1 = event['qubits']
            block = f'ev_{event_id}_two'
            routine = f'routine_{event_id}_two'
            host_blocks.append(f'\n^{block} {{type = QL}}:\n    run_subroutine() : {routine}\n')
            subroutines.append(f'\nSUBROUTINE {routine}\n    params:\n    returns:\n    uses: {q0}, {q1}\n    keeps: {q0}, {q1}\n    request:\n  NETQASM_START\n    set Q0 {q0}\n    set Q1 {q1}\n    cnot Q0 Q1\n  NETQASM_END\n')
            metadata[block] = {'event_id': event_id, 'type': 'TWO_GATE', 'operation': operation, 'qpu': server, 'peer': None, 'role': '', 'qubits': event['original_qubits']}
        elif kind == 'STARTING_PROCESS':
            peer = event['peer']
            role = event['role']
            virt_id = event['qubits'][0]
            socket_id = epr_socket_for_peer[peer]
            block = f'ev_{event_id}_epr_ejpp_start'
            request_name = f'request_{event_id}_{server}_{peer}'
            host_blocks.append(f'\n^{block} {{type = QC}}:\n    run_request() : {request_name}\n')
            requests.append(f'\nREQUEST {request_name}\n    callback_type:\n    callback:\n    return_vars:\n    remote_id: {peer}\n    epr_socket_id: {socket_id}\n    num_pairs: 1\n    virt_ids: all {virt_id}\n    timeout: 1000000000000\n    fidelity: 1.0\n    typ: create_keep\n    role: {role}\n')
            metadata[block] = {'event_id': event_id, 'type': 'EJPP_START', 'operation': 'EPR + EJPP_Start', 'qpu': server, 'peer': peer, 'role': role, 'qubits': event['original_qubits']}
        elif kind == 'ENDING_PROCESS':
            peer = event['peer']
            role = event['role']
            virt_id = event['qubits'][0]
            block = f'ev_{event_id}_epr_end_{server}'
            routine = f'routine_{event_id}_end_{server}'
            host_blocks.append(f'\n^{block} {{type = QL}}:\n    run_subroutine() : {routine}\n')
            subroutines.append(f'\nSUBROUTINE {routine}\n    params:\n    returns:\n    uses: {virt_id}\n    keeps:\n    request:\n  NETQASM_START\n    set Q0 {virt_id}\n    x Q0\n  NETQASM_END\n')
            metadata[block] = {'event_id': event_id, 'type': 'EPR_END', 'operation': 'ending_process', 'qpu': server, 'peer': peer, 'role': role, 'qubits': event['original_qubits']}
        else:
            raise ValueError(f'Unsupported Qoala event: {kind}')
    text = f"\nMETA_START\n    name: {node_name}\n    parameters:\n    csockets:\n    epr_sockets: {epr_socket_text}\nMETA_END\n\n{''.join(host_blocks)}\n\n{''.join(subroutines)}\n\n{''.join(requests)}\n"
    program = QoalaParser(text).parse()
    return (program, metadata)