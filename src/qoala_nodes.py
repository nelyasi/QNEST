from qoala.runtime.config import LatenciesConfig, NtfConfig, ProcNodeConfig, TopologyConfigBuilder

def _scheduler_strategy(strategy):
    strategy = strategy.upper()
    strategies = {'QOALA': {'determ_sched': True, 'use_deadlines': True, 'fcfs': False, 'prio_epr': False, 'is_predictable': False}, 'FCFS': {'determ_sched': True, 'use_deadlines': False, 'fcfs': True, 'prio_epr': False, 'is_predictable': False}, 'EPR_PRIORITY': {'determ_sched': True, 'use_deadlines': False, 'fcfs': False, 'prio_epr': True, 'is_predictable': False}, 'RANDOM': {'determ_sched': False, 'use_deadlines': False, 'fcfs': False, 'prio_epr': False, 'is_predictable': False}}
    if strategy not in strategies:
        raise ValueError('Unknown strategy. Choose one of:\nQOALA\nFCFS\nEPR_PRIORITY\nRANDOM')
    return strategies[strategy]

def _make_qoala_node(server, num_qubits, single_qubit_time, two_qubit_time, ending_process_time, strategy):
    sched = _scheduler_strategy(strategy)
    topology = TopologyConfigBuilder().num_qubits(num_qubits).uniform_topology().no_decoherence().default_generic_gates().zero_gate_durations().perfect_gate_fidelities().all_comm_gates_duration(single_qubit_time).all_mem_gates_duration(single_qubit_time).comm_gate_duration('INSTR_INIT', 0).mem_gate_duration('INSTR_INIT', 0).comm_gate_duration('INSTR_X', ending_process_time).mem_gate_duration('INSTR_X', ending_process_time).all_two_gates_duration(two_qubit_time).build()
    return ProcNodeConfig(node_name=f'qpu_{server}', node_id=server, topology=topology, latencies=LatenciesConfig(host_instr_time=0, qnos_instr_time=0, host_peer_latency=0, internal_sched_latency=0), ntf=NtfConfig.from_cls_name('GenericNtf'), determ_sched=sched['determ_sched'], use_deadlines=sched['use_deadlines'], fcfs=sched['fcfs'], prio_epr=sched['prio_epr'], is_predictable=sched['is_predictable'])