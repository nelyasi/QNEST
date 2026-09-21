from collections import defaultdict

def _virtual_qubit_id(q, qubits_per_qpu):
    if q['is_link']:
        return qubits_per_qpu + q['index']
    return q['index']

def _make_link_qubit_description(server, index):
    return {'name': f'server_{server}_link_register[{index}]', 'server': server, 'index': index, 'is_link': True}

def _is_start_event(kind, operation):
    if kind in {'STARTING_PROCESS', 'EJPP_START'}:
        return True
    op = str(operation).lower().replace(' ', '')
    return 'starting_process' in op or 'startingprocess' in op or 'ejpp_start' in op or ('ejppstart' in op)

def _unique_preserve(values):
    out = []
    seen = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out

def _prepare_qoala_events(events, qubits_per_qpu):
    node_events = defaultdict(list)
    data_qubits = defaultdict(set)
    virtual_qubits = defaultdict(set)
    existing_link_indices = defaultdict(set)
    all_servers = set()
    for event in events:
        for q in event['qubits']:
            server = q['server']
            all_servers.add(server)
            virt = _virtual_qubit_id(q, qubits_per_qpu)
            virtual_qubits[server].add(virt)
            if q['is_link']:
                existing_link_indices[server].add(q['index'])
            else:
                data_qubits[server].add(virt)
    next_source_link_slot = {}
    for server in all_servers:
        existing = existing_link_indices.get(server, set())
        if existing:
            next_source_link_slot[server] = max(existing) + 1
        else:
            next_source_link_slot[server] = 0
    free_source_link_slots = defaultdict(list)
    active_eprs = {}
    active_source_links = set()
    for event in sorted(events, key=lambda x: x['id']):
        event_id = event['id']
        kind = event['kind']
        operation = event['operation']
        qubits = event['qubits']
        if kind == 'SINGLE':
            if len(qubits) != 1:
                raise ValueError(f'Invalid SINGLE event:\n{event}')
            q = qubits[0]
            server = q['server']
            virt = _virtual_qubit_id(q, qubits_per_qpu)
            node_events[server].append({'event_id': event_id, 'kind': 'SINGLE', 'operation': operation, 'qubits': [virt], 'original_qubits': [q['name']], 'peer': None, 'role': ''})
        elif kind == 'TWO':
            if len(qubits) != 2:
                raise ValueError(f'Invalid TWO event:\n{event}')
            q0 = qubits[0]
            q1 = qubits[1]
            server0 = q0['server']
            server1 = q1['server']
            if server0 != server1:
                raise ValueError(f'Found a normal 2-qubit gate between different QPUs:\n{event}')
            v0 = _virtual_qubit_id(q0, qubits_per_qpu)
            v1 = _virtual_qubit_id(q1, qubits_per_qpu)
            node_events[server0].append({'event_id': event_id, 'kind': 'TWO', 'operation': operation, 'qubits': [v0, v1], 'original_qubits': [q0['name'], q1['name']], 'peer': None, 'role': ''})
        elif _is_start_event(kind, operation):
            synthesized_source_link = False
            if len(qubits) == 2:
                processing_qubits = [q for q in qubits if not q['is_link']]
                link_qubits = [q for q in qubits if q['is_link']]
                if len(processing_qubits) != 1:
                    raise ValueError(f'Legacy starting_process must contain exactly one processing qubit:\n{event}')
                if len(link_qubits) != 1:
                    raise ValueError(f'Legacy starting_process must contain exactly one remote link qubit:\n{event}')
                processing_q = processing_qubits[0]
                remote_link_q = link_qubits[0]
                source = processing_q['server']
                target = remote_link_q['server']
                if source == target:
                    raise ValueError(f'starting_process must connect different QPUs:\n{event}')
                if free_source_link_slots[source]:
                    source_slot = free_source_link_slots[source].pop(0)
                else:
                    if source not in next_source_link_slot:
                        existing = existing_link_indices.get(source, set())
                        if existing:
                            next_source_link_slot[source] = max(existing) + 1
                        else:
                            next_source_link_slot[source] = 0
                    source_slot = next_source_link_slot[source]
                    next_source_link_slot[source] += 1
                source_link_q = _make_link_qubit_description(source, source_slot)
                synthesized_source_link = True
            elif len(qubits) == 3:
                processing_qubits = [q for q in qubits if not q['is_link']]
                link_qubits = [q for q in qubits if q['is_link']]
                if len(processing_qubits) != 1:
                    raise ValueError(f'EPR + EJPP_Start requires exactly one processing qubit:\n{event}')
                if len(link_qubits) != 2:
                    raise ValueError(f'EPR + EJPP_Start requires exactly two link-register qubits:\n{event}')
                processing_q = processing_qubits[0]
                source = processing_q['server']
                source_links = [q for q in link_qubits if q['server'] == source]
                remote_links = [q for q in link_qubits if q['server'] != source]
                if len(source_links) != 1:
                    raise ValueError(f'Could not identify exactly one source-side link qubit:\n{event}')
                if len(remote_links) != 1:
                    raise ValueError(f'Could not identify exactly one remote-side link qubit:\n{event}')
                source_link_q = source_links[0]
                remote_link_q = remote_links[0]
                source_slot = source_link_q['index']
                target = remote_link_q['server']
                if source == target:
                    raise ValueError(f'EPR + EJPP_Start must connect different QPUs:\n{event}')
            else:
                raise ValueError(f'EPR + EJPP_Start must contain:\n\n2 qubits:\n    processing + remote link\n\nor\n\n3 qubits:\n    processing + source link + remote link\n\nReceived:\n{event}')
            processing_virt = _virtual_qubit_id(processing_q, qubits_per_qpu)
            source_virt = _virtual_qubit_id(source_link_q, qubits_per_qpu)
            target_virt = _virtual_qubit_id(remote_link_q, qubits_per_qpu)
            virtual_qubits[source].add(processing_virt)
            virtual_qubits[source].add(source_virt)
            virtual_qubits[target].add(target_virt)
            remote_link_name = remote_link_q['name']
            source_link_name = source_link_q['name']
            if remote_link_name in active_eprs:
                raise ValueError(f'Remote link qubit is already occupied by an active EJPP:\n{remote_link_name}\nEvent:\n{event}')
            if source_link_name in active_source_links:
                raise ValueError(f'Source link qubit is already occupied by an active EJPP:\n{source_link_name}\nEvent:\n{event}')
            active_source_links.add(source_link_name)
            protocol_qubits = [processing_q['name'], source_link_q['name'], remote_link_q['name']]
            active_eprs[remote_link_name] = {'source': source, 'target': target, 'processing_virt': processing_virt, 'source_virt': source_virt, 'target_virt': target_virt, 'source_slot': source_slot, 'synthesized_source_link': synthesized_source_link, 'processing_name': processing_q['name'], 'source_link_name': source_link_name, 'remote_link_name': remote_link_name, 'protocol_qubits': protocol_qubits}
            node_events[source].append({'event_id': event_id, 'kind': 'STARTING_PROCESS', 'operation': 'EPR + EJPP_Start', 'qubits': [source_virt], 'original_qubits': protocol_qubits, 'peer': target, 'role': 'create'})
            node_events[target].append({'event_id': event_id, 'kind': 'STARTING_PROCESS', 'operation': 'EPR + EJPP_Start', 'qubits': [target_virt], 'original_qubits': protocol_qubits, 'peer': source, 'role': 'receive'})
        elif kind == 'ENDING_PROCESS':
            if len(qubits) != 2:
                raise ValueError(f'Invalid ending_process:\n{event}')
            matching_links = [q['name'] for q in qubits if q['name'] in active_eprs]
            if len(matching_links) != 1:
                raise ValueError(f'Could not find exactly one matching EPR + EJPP_Start for:\n{event}\n\nActive remote links:\n{list(active_eprs.keys())}')
            link_name = matching_links[0]
            epr = active_eprs.pop(link_name)
            source = epr['source']
            target = epr['target']
            active_source_links.discard(epr['source_link_name'])
            if epr['synthesized_source_link']:
                free_source_link_slots[source].append(epr['source_slot'])
                free_source_link_slots[source].sort()
            protocol_qubits = list(epr['protocol_qubits'])
            node_events[source].append({'event_id': event_id, 'kind': 'ENDING_PROCESS', 'operation': 'ending_process', 'qubits': [epr['source_virt']], 'original_qubits': protocol_qubits, 'peer': target, 'role': 'source'})
            node_events[target].append({'event_id': event_id, 'kind': 'ENDING_PROCESS', 'operation': 'ending_process', 'qubits': [epr['target_virt']], 'original_qubits': protocol_qubits, 'peer': source, 'role': 'remote'})
        else:
            raise ValueError(f'Unsupported event kind: {kind}')
    if active_eprs:
        raise ValueError(f'Some starting_process operations do not have matching ending_process operations.\nStill active: {list(active_eprs.keys())}')
    node_num_qubits = {}
    for server in node_events.keys():
        ids = virtual_qubits.get(server, set())
        if ids:
            node_num_qubits[server] = max(ids) + 1
        else:
            node_num_qubits[server] = 1
    return (node_events, data_qubits, node_num_qubits)