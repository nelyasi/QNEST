import json
import netsquid as ns
from qoala.runtime.config import ProcNodeNetworkConfig
from qoala.runtime.program import ProgramInput
from qoala.util.runner import run_n_node_app
from src.qoala_events import _prepare_qoala_events
from src.qoala_program import _make_qoala_program
from src.qoala_nodes import _make_qoala_node, _scheduler_strategy
from src.qoala_schedule import _extract_qoala_schedule
from src.qoala_report import _print_full_schedule, _print_entanglement_schedule, _print_qpu_summary

def schedule_pytket_dqc_with_qoala(bridge_file, single_qubit_time, two_qubit_time, starting_process_time, ending_process_time, strategy='QOALA', print_output=True):
    strategy = strategy.upper()
    _scheduler_strategy(strategy)
    with open(bridge_file, 'r') as f:
        circuit_data = json.load(f)
    events = circuit_data['events']
    qubits_per_qpu = circuit_data['qubits_per_qpu']
    node_events, data_qubits, node_num_qubits = _prepare_qoala_events(events, qubits_per_qpu)
    used_servers = sorted(node_events.keys())
    programs = {}
    metadata = {}
    for server in used_servers:
        program, info = _make_qoala_program(server=server, events=node_events[server], data_qubits=data_qubits)
        node_name = f'qpu_{server}'
        programs[node_name] = program
        metadata[node_name] = info
    node_configs = []
    for server in used_servers:
        node_configs.append(_make_qoala_node(server=server, num_qubits=node_num_qubits[server], single_qubit_time=single_qubit_time, two_qubit_time=two_qubit_time, ending_process_time=ending_process_time, strategy=strategy))
    network_cfg = ProcNodeNetworkConfig.from_nodes_perfect_links(nodes=node_configs, link_duration=starting_process_time)
    program_inputs = {name: ProgramInput.empty() for name in programs}
    ns.sim_reset()
    qoala_result = run_n_node_app(num_iterations=1, programs=programs, program_inputs=program_inputs, network_cfg=network_cfg, linear=False)
    schedule = _extract_qoala_schedule(qoala_result, metadata)
    if print_output:
        _print_full_schedule(schedule, qoala_result, strategy)
        _print_entanglement_schedule(schedule)
        _print_qpu_summary(schedule)
    return {'strategy': strategy, 'schedule': schedule, 'total_execution_time_ns': qoala_result.total_duration, 'qoala_result': qoala_result, 'n_original_events': len(events), 'used_qpus': used_servers}