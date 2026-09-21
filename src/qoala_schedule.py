from collections import defaultdict
from src.qoala_events import _unique_preserve

def _extract_raw_qoala_schedule(qoala_result, metadata):
    schedule = []
    for node_name, stats in qoala_result.statistics.items():
        node_metadata = metadata[node_name]
        shared_ptr_to_block = {}
        cpu_tasks = stats._cpu_tasks_executed
        for _, cpu_task in cpu_tasks.items():
            if hasattr(cpu_task, 'shared_ptr') and hasattr(cpu_task, 'block_name'):
                shared_ptr_to_block[cpu_task.shared_ptr] = cpu_task.block_name
        qpu_tasks = stats._qpu_tasks_executed
        starts = stats._qpu_task_starts
        ends = stats._qpu_task_ends
        for task_id, task in qpu_tasks.items():
            block_name = None
            if hasattr(task, 'block_name'):
                block_name = task.block_name
            elif hasattr(task, 'shared_ptr'):
                block_name = shared_ptr_to_block.get(task.shared_ptr)
            if block_name is None:
                continue
            if block_name not in node_metadata:
                continue
            if task_id not in starts:
                continue
            if task_id not in ends:
                continue
            info = node_metadata[block_name]
            start = starts[task_id]
            end = ends[task_id]
            schedule.append({'event': info['event_id'], 'qpu': info['qpu'], 'peer': info['peer'], 'role': info['role'], 'type': info['type'], 'operation': info['operation'], 'qubits': info['qubits'], 'start_ns': start, 'end_ns': end, 'duration_ns': end - start, 'task_id': task_id, 'task_class': task.__class__.__name__, 'block_name': block_name})
    schedule.sort(key=lambda x: (x['start_ns'], x['end_ns'], x['event'], x['qpu']))
    return schedule

def _collapse_distributed_protocol_blocks(raw_schedule):
    normal_rows = []
    distributed_groups = defaultdict(list)
    for row in raw_schedule:
        if row['type'] in {'EJPP_START', 'EPR_END'}:
            key = (row['type'], row['event'])
            distributed_groups[key].append(dict(row))
        else:
            normal_rows.append(dict(row))
    logical_rows = list(normal_rows)
    for (event_type, event_id), rows in distributed_groups.items():
        rows = sorted(rows, key=lambda r: (r['start_ns'], r['qpu']))
        if event_type == 'EJPP_START':
            source_candidates = [row for row in rows if row.get('role') == 'create']
        else:
            source_candidates = [row for row in rows if row.get('role') == 'source']
        if source_candidates:
            representative = dict(source_candidates[0])
        else:
            representative = dict(rows[0])
        merged_qubits = _unique_preserve((q for row in rows for q in row.get('qubits', [])))
        participating_qpus = sorted({row['qpu'] for row in rows if row.get('qpu') is not None})
        source_qpu = representative['qpu']
        other_qpus = [qpu for qpu in participating_qpus if qpu != source_qpu]
        if other_qpus:
            peer = other_qpus[0]
        else:
            peer = representative.get('peer')
        if event_type == 'EJPP_START':
            start_ns = min((float(row['start_ns']) for row in rows))
            end_ns = max((float(row['end_ns']) for row in rows))
            duration_ns = end_ns - start_ns
            operation = 'EPR + EJPP_Start'
            task_class = 'DistributedEJPPStart'
            block_name = f'logical_ejpp_start_{event_id}'
        else:
            start_ns = max((float(row['start_ns']) for row in rows))
            duration_ns = max((float(row['duration_ns']) for row in rows))
            end_ns = start_ns + duration_ns
            operation = 'ending_process'
            task_class = 'DistributedEndingProcess'
            block_name = f'logical_ending_process_{event_id}'
        representative.update({'event': event_id, 'qpu': source_qpu, 'peer': peer, 'role': 'distributed', 'type': event_type, 'operation': operation, 'qubits': merged_qubits, 'start_ns': start_ns, 'end_ns': end_ns, 'duration_ns': duration_ns, 'task_class': task_class, 'block_name': block_name})
        logical_rows.append(representative)
    logical_rows.sort(key=lambda row: (row['start_ns'], row['end_ns'], row['event'], row['qpu']))
    return logical_rows

def _enforce_ending_dependencies(schedule):
    rows = [dict(row) for row in schedule]
    rows.sort(key=lambda row: (row['event'], row['start_ns'], row['qpu']))
    qubit_ready = defaultdict(float)
    corrected = []
    for row in rows:
        qubits = list(row.get('qubits', []))
        original_start = float(row['start_ns'])
        original_end = float(row['end_ns'])
        duration = float(row.get('duration_ns', original_end - original_start))
        if row['type'] == 'EPR_END':
            dependency_ready = max((qubit_ready[q] for q in qubits), default=0.0)
            corrected_start = max(original_start, dependency_ready)
            corrected_end = corrected_start + duration
            row['start_ns'] = corrected_start
            row['end_ns'] = corrected_end
            row['duration_ns'] = duration
        for q in qubits:
            qubit_ready[q] = max(qubit_ready[q], float(row['end_ns']))
        corrected.append(row)
    corrected.sort(key=lambda row: (row['start_ns'], row['end_ns'], row['event'], row['qpu']))
    return corrected

def _extract_qoala_schedule(qoala_result, metadata):
    raw_schedule = _extract_raw_qoala_schedule(qoala_result, metadata)
    schedule = _collapse_distributed_protocol_blocks(raw_schedule)
    schedule = _enforce_ending_dependencies(schedule)
    return schedule