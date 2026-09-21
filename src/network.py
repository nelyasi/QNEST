from pytket_dqc.networks import NISQNetwork

def build_network(n_qpus=7, qubits_per_qpu=1, print_output=True):
    links = [[i, j] for i in range(n_qpus) for j in range(i + 1, n_qpus)]
    server_qubits = {qpu: list(range(qpu * qubits_per_qpu, (qpu + 1) * qubits_per_qpu)) for qpu in range(n_qpus)}
    network = NISQNetwork(links, server_qubits)
    if print_output:
        print('\n======================================')
        print('NETWORK')
        print('======================================')
        print('Number of QPUs:', n_qpus)
        print('Qubits per QPU:', qubits_per_qpu)
        print('Total physical computation qubits:', n_qpus * qubits_per_qpu)
        print('Number of inter-QPU links:', len(links))
    return (network, links, server_qubits)

def build_network_from_gui(graph, qubits_per_qpu=10, print_output=True):
    if not isinstance(graph, dict):
        raise TypeError("graph must be a dict with 'nodes' and 'links'.")
    nodes = list(graph.get('nodes', []))
    links_raw = list(graph.get('links', []))
    qpu_nodes = [n for n in nodes if str(n.get('kind', '')).upper() == 'QPU']
    if len(qpu_nodes) < 2:
        raise ValueError('The QNEST network needs at least two QPU nodes before distribution.')
    try:
        qubits_per_qpu = int(qubits_per_qpu)
    except Exception as exc:
        raise ValueError('qubits_per_qpu must be an integer.') from exc
    if qubits_per_qpu < 1:
        raise ValueError('qubits_per_qpu must be >= 1.')

    def _qpu_key(node):
        label = str(node.get('label', ''))
        import re
        m = re.search('(\\d+)$', label)
        return (0, int(m.group(1))) if m else (1, str(node.get('id', label)))
    qpu_nodes = sorted(qpu_nodes, key=_qpu_key)
    qpu_map = {str(node['id']): idx for idx, node in enumerate(qpu_nodes)}
    adjacency = {str(node['id']): set() for node in nodes if 'id' in node}
    for link in links_raw:
        a = str(link.get('src', ''))
        b = str(link.get('dst', ''))
        if a in adjacency and b in adjacency and (a != b):
            adjacency[a].add(b)
            adjacency[b].add(a)
    qpu_ids = set(qpu_map)
    dqc_links_set = set()
    collapsed_paths = []
    from collections import deque
    for src_id, src_server in qpu_map.items():
        queue = deque([(src_id, [src_id])])
        visited = {src_id}
        while queue:
            current, path = queue.popleft()
            for nxt in adjacency.get(current, ()):
                if nxt in visited:
                    continue
                visited.add(nxt)
                new_path = path + [nxt]
                if nxt in qpu_ids:
                    dst_server = qpu_map[nxt]
                    if src_server != dst_server:
                        pair = tuple(sorted((src_server, dst_server)))
                        if pair not in dqc_links_set:
                            dqc_links_set.add(pair)
                            collapsed_paths.append({'servers': list(pair), 'gui_path': new_path})
                    continue
                queue.append((nxt, new_path))
    if not dqc_links_set:
        raise ValueError('No QPU-to-QPU connectivity was found. Link QPUs directly or through BS/PBS/Switch/BSM components in the Designer.')
    dqc_links = [list(pair) for pair in sorted(dqc_links_set)]
    server_qubits = {server: list(range(server * qubits_per_qpu, (server + 1) * qubits_per_qpu)) for server in range(len(qpu_nodes))}
    network = NISQNetwork(dqc_links, server_qubits)
    metadata = {'n_qpus': len(qpu_nodes), 'qubits_per_qpu': qubits_per_qpu, 'qpu_id_to_server': qpu_map, 'server_to_qpu': {str(server): {'id': node.get('id'), 'label': node.get('label', node.get('id'))} for server, node in enumerate(qpu_nodes)}, 'dqc_links': dqc_links, 'collapsed_optical_paths': collapsed_paths}
    if print_output:
        print('\n======================================')
        print('QNEST GUI NETWORK -> PYTKET-DQC')
        print('======================================')
        print('QPU servers:', len(qpu_nodes))
        print('Qubits per QPU:', qubits_per_qpu)
        print('Logical DQC links:', len(dqc_links))
    return (network, dqc_links, server_qubits, qpu_map, metadata)