from collections import defaultdict
from pytket.circuit import Circuit, Qubit, CustomGateDef, OpType
from pytket_dqc.utils.circuit_analysis import is_link_qubit, get_server_id
from pytket_dqc.utils.gateset import is_start_proc, is_end_proc

def _make_display_gate(name, n_qubits):
    definition = Circuit(n_qubits)
    return CustomGateDef.define(name, definition, [])
_EJPP_START = _make_display_gate('EPR + EJPP_Start', 3)

def make_explicit_ejpp_representation(dist_circ, n_qpus):
    commands = list(dist_circ.get_commands())
    existing_link_indices = defaultdict(list)
    for q in dist_circ.qubits:
        if is_link_qubit(q):
            try:
                server = get_server_id(q)
                index = int(q.index[0])
                existing_link_indices[server].append(index)
            except Exception:
                pass
    first_source_link_slot = {}
    for server in range(n_qpus):
        existing = existing_link_indices.get(server, [])
        if existing:
            first_source_link_slot[server] = max(existing) + 1
        else:
            first_source_link_slot[server] = 0
    next_link_slot = {server: first_source_link_slot[server] for server in range(n_qpus)}
    free_link_slots = defaultdict(list)
    start_assignment = {}
    active_assignment = {}
    for command_index, cmd in enumerate(commands):
        if is_start_proc(cmd):
            source_qubit = cmd.qubits[0]
            remote_link_qubit = cmd.qubits[1]
            source_is_processing = not is_link_qubit(source_qubit)
            remote_is_link = is_link_qubit(remote_link_qubit)
            if source_is_processing and remote_is_link:
                server = get_server_id(source_qubit)
                if free_link_slots[server]:
                    slot = free_link_slots[server].pop(0)
                else:
                    slot = next_link_slot[server]
                    next_link_slot[server] += 1
                source_link_qubit = Qubit(f'server_{server}_link_register', slot)
                assignment = {'processing_qubit': source_qubit, 'source_link_qubit': source_link_qubit, 'remote_link_qubit': remote_link_qubit, 'server': server, 'slot': slot, 'start_command': command_index, 'end_command': None}
                start_assignment[command_index] = assignment
                active_assignment[remote_link_qubit] = assignment
                continue
        if is_end_proc(cmd):
            remote_link_qubit = cmd.qubits[0]
            home_qubit = cmd.qubits[1]
            assignment = active_assignment.get(remote_link_qubit)
            if assignment is not None:
                processing_qubit = assignment['processing_qubit']
                if home_qubit == processing_qubit:
                    assignment['end_command'] = command_index
                    server = assignment['server']
                    slot = assignment['slot']
                    free_link_slots[server].append(slot)
                    free_link_slots[server].sort()
                    del active_assignment[remote_link_qubit]
    representation_circ = Circuit()
    for q in dist_circ.qubits:
        representation_circ.add_qubit(q)
    for b in dist_circ.bits:
        representation_circ.add_bit(b)
    all_source_link_qubits = set()
    for assignment in start_assignment.values():
        all_source_link_qubits.add(assignment['source_link_qubit'])
    for source_link_qubit in sorted(all_source_link_qubits, key=str):
        if source_link_qubit not in representation_circ.qubits:
            representation_circ.add_qubit(source_link_qubit)
    active_source_links = {}
    link_map = []

    def copy_original_command(cmd):
        if cmd.op.type == OpType.Barrier:
            representation_circ.add_barrier(list(cmd.qubits))
        else:
            representation_circ.add_gate(cmd.op, list(cmd.args))
    for command_index, cmd in enumerate(commands):
        if command_index in start_assignment:
            assignment = start_assignment[command_index]
            processing_qubit = assignment['processing_qubit']
            source_link_qubit = assignment['source_link_qubit']
            remote_link_qubit = assignment['remote_link_qubit']
            server = assignment['server']
            slot = assignment['slot']
            representation_circ.add_custom_gate(_EJPP_START, [], [processing_qubit, source_link_qubit, remote_link_qubit])
            active_source_links[remote_link_qubit] = assignment
            link_map.append({'processing_qubit': str(processing_qubit), 'source_link_qubit': str(source_link_qubit), 'remote_link_qubit': str(remote_link_qubit), 'source_qpu': server, 'link_slot': slot, 'start_command': command_index, 'end_command': assignment['end_command']})
            continue
        if is_end_proc(cmd):
            remote_link_qubit = cmd.qubits[0]
            home_qubit = cmd.qubits[1]
            assignment = active_source_links.get(remote_link_qubit)
            if assignment is not None:
                processing_qubit = assignment['processing_qubit']
                if home_qubit == processing_qubit:
                    copy_original_command(cmd)
                    del active_source_links[remote_link_qubit]
                    continue
        copy_original_command(cmd)
    source_link_required = {}
    for server in range(n_qpus):
        source_link_required[server] = next_link_slot[server] - first_source_link_slot[server]
    return (representation_circ, source_link_required, link_map)