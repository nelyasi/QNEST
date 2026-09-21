from pytket.circuit.display import render_circuit_jupyter
from pytket_dqc.distributors import PartitioningAnnealing, PartitioningHeterogeneous, PartitioningHeterogeneousEmbedding, CoverEmbedding, CoverEmbeddingSteiner, CoverEmbeddingSteinerDetached
DISTRIBUTION_METHODS = {'PartitioningAnnealing': PartitioningAnnealing, 'PartitioningHeterogeneous': PartitioningHeterogeneous, 'PartitioningHeterogeneousEmbedding': PartitioningHeterogeneousEmbedding, 'CoverEmbedding': CoverEmbedding, 'CoverEmbeddingSteiner': CoverEmbeddingSteiner, 'CoverEmbeddingSteinerDetached': CoverEmbeddingSteinerDetached}

def get_distributor(distribution_method):
    if distribution_method not in DISTRIBUTION_METHODS:
        available = '\n'.join((f'  - {method}' for method in DISTRIBUTION_METHODS))
        raise ValueError(f'Unknown distribution_method: {distribution_method!r}.\nChoose one of the 6 available methods:\n{available}')
    return DISTRIBUTION_METHODS[distribution_method]()
from pytket_dqc.utils.circuit_analysis import ebit_cost, ebit_memory_required
from src.ejpp_representation import make_explicit_ejpp_representation
from src.analysis_hooks import analyse_ebits, extract_placement, compute_circuit_depth

def show_input_circuit(output_circuit):
    circ = output_circuit.copy()
    print('======================================')
    print('INPUT CIRCUIT FOR DISTRIBUTION')
    print('======================================')
    print('Type:', type(circ))
    print('Qubits:', circ.n_qubits)
    print('Gates:', circ.n_gates)
    print('Depth:', circ.depth())
    render_circuit_jupyter(circ)
    return circ

def distribute_circuit(circ, network, n_qpus, seed=1, name='ghz', distribution_method='PartitioningAnnealing'):
    distributor = get_distributor(distribution_method)
    print('\n======================================')
    print('DISTRIBUTION METHOD')
    print('======================================')
    print(distribution_method)
    try:
        dist = distributor.distribute(circ, network, seed=seed)
        print('\n======================================')
        print('DISTRIBUTION SUCCESSFUL')
        print('======================================')
        print('Distribution valid:', dist.is_valid())
        dist_circ = dist.to_pytket_circuit(satisfy_bound=True, allow_update=False)
        representation_circ, source_link_required, link_map = make_explicit_ejpp_representation(dist_circ, n_qpus)
        print('\n======================================')
        print('DISTRIBUTED CIRCUIT')
        print('======================================')
        print('Type:', type(dist_circ))
        print('Qubits:', dist_circ.n_qubits)
        print('Gates:', dist_circ.n_gates)
        print('Depth:', dist_circ.depth())
        print('\n======================================')
        print('EXPLICIT EJPP LINK RESOURCES')
        print('======================================')
        for server in range(n_qpus):
            required = source_link_required.get(server, 0)
            print(f'QPU {server}: {required} additional source link qubit(s)')
        print('\n======================================')
        print('CORRECTED EJPP CIRCUIT REPRESENTATION')
        print('======================================')
        print('Representation qubits:', representation_circ.n_qubits)
        print('Representation gates:', representation_circ.n_gates)
        render_circuit_jupyter(representation_circ)
        builtin_ebits = ebit_cost(dist_circ)
        ebit_memory = ebit_memory_required(dist_circ)
        print('\n======================================')
        print('EBIT INFORMATION')
        print('======================================')
        print('Total ebits consumed:', builtin_ebits)
        print('Ebit memory required per QPU:')
        for server, memory in sorted(ebit_memory.items()):
            print(f'  QPU {server}: {memory}')
        print('\n======================================')
        print('EXPLICIT EJPP LINK CHANNELS')
        print('======================================')
        if link_map:
            for i, channel in enumerate(link_map, start=1):
                print(f'Link channel {i}:')
                print('  Processing qubit:', channel['processing_qubit'])
                print('  Source link qubit:', channel['source_link_qubit'])
                print('  Remote link qubit:', channel['remote_link_qubit'])
                print('  Source QPU:', channel['source_qpu'])
                print('  Link slot:', channel['link_slot'])
                print('  Start command:', channel['start_command'])
                print('  End command:', channel['end_command'])
                print()
        else:
            print('No processing-qubit -> remote-link EJPP starts required expansion.')
        ebit_info = analyse_ebits(dist_circ)
        placement = extract_placement(dist, circ.n_qubits)
        distributed_depth = compute_circuit_depth(dist_circ, ebit_info['count'])
        result = {'name': name, 'distribution_method': distribution_method, 'original_circuit': circ, 'distribution': dist, 'distributed_circuit': dist_circ, 'representation_circuit': representation_circ, 'source_link_qubits_required': source_link_required, 'link_map': link_map, 'n_qubits': circ.n_qubits, 'n_gates_original': circ.n_gates, 'depth_original': circ.depth(), 'n_qubits_distributed': dist_circ.n_qubits, 'n_gates_distributed': dist_circ.n_gates, 'depth_distributed_pytket': dist_circ.depth(), 'n_qubits_representation': representation_circ.n_qubits, 'n_gates_representation': representation_circ.n_gates, 'distributed_depth': distributed_depth, 'ebits': ebit_info['count'], 'ebit_info': ebit_info, 'ebits_builtin': builtin_ebits, 'ebit_memory': ebit_memory, 'placement': placement}
        print('\n======================================')
        print('SUMMARY')
        print('======================================')
        print(f'Original qubits:       {circ.n_qubits}')
        print(f'Original gates:        {circ.n_gates}')
        print(f'Original depth:        {circ.depth()}')
        print()
        print(f'Distributed qubits:    {dist_circ.n_qubits}')
        print(f'Distributed gates:     {dist_circ.n_gates}')
        print(f'Distributed depth:     {distributed_depth}')
        print()
        print(f'Representation qubits: {representation_circ.n_qubits}')
        print(f'Representation gates:  {representation_circ.n_gates}')
        print()
        print(f"Ebits (your function): {ebit_info['count']}")
        print(f'Ebits (pytket-dqc):    {builtin_ebits}')
        print()
        print('Additional source link qubits:')
        for server in range(n_qpus):
            print(f'  QPU {server}: {source_link_required.get(server, 0)}')
        print()
        print('Placement:')
        print(placement)
    except Exception as e:
        print('\n======================================')
        print('DISTRIBUTION FAILED')
        print('======================================')
        print('Error type:', type(e).__name__)
        print('Error:', e)
        result = {'name': name, 'distribution_method': distribution_method, 'error_type': type(e).__name__, 'error': str(e)}
        _partial = locals()
        for _result_key, _local_name in (('distribution', 'dist'), ('distributed_circuit', 'dist_circ'), ('representation_circuit', 'representation_circ'), ('source_link_qubits_required', 'source_link_required'), ('link_map', 'link_map'), ('ebits_builtin', 'builtin_ebits'), ('ebit_memory', 'ebit_memory')):
            if _local_name in _partial:
                result[_result_key] = _partial[_local_name]
    return result