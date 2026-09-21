import re
import pandas as pd

def _parse_qubit_name(qname):
    match = re.fullmatch('server_(\\d+)(_link_register)?\\[(\\d+)\\]', qname)
    if match is None:
        raise ValueError(f'Unsupported qubit name: {qname}')
    server_number = int(match.group(1))
    return {'name': qname, 'server': server_number, 'server_name': f'server_{server_number}', 'index': int(match.group(3)), 'is_link': match.group(2) is not None}

def _is_link_qubit(qname):
    return '_link_register' in qname

def _unique_keep_order(values):
    output = []
    seen = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output

def _find_matching_ending_process(start_row, end_rows, source_link, target_link):
    start_time = float(start_row['start_ns'])
    candidates = []
    for end_row in end_rows:
        end_start = float(end_row['start_ns'])
        if end_start < start_time:
            continue
        end_qubits = set(end_row.get('qubits', []))
        if source_link in end_qubits and target_link in end_qubits:
            candidates.append(end_row)
            continue
        if target_link in end_qubits:
            candidates.append(end_row)
    if not candidates:
        raise ValueError(f"\nCould not find matching ending_process.\nStart event : {start_row.get('event')}\nSource link : {source_link}\nTarget link : {target_link}")
    candidates.sort(key=lambda row: (float(row['start_ns']), float(row['end_ns'])))
    return candidates[0]

def _extract_ejpp_sessions(schedule):
    start_rows = [row for row in schedule if row.get('type') in {'EJPP_START', 'EPR_GENERATION'}]
    end_rows = [row for row in schedule if row.get('type') == 'EPR_END']
    start_rows.sort(key=lambda row: (float(row['start_ns']), row.get('event', -1)))
    sessions = []
    for start_row in start_rows:
        qubits = _unique_keep_order(start_row.get('qubits', []))
        processing_qubits = [q for q in qubits if not _is_link_qubit(q)]
        link_qubits = [q for q in qubits if _is_link_qubit(q)]
        if len(processing_qubits) != 1:
            raise ValueError(f'\nEJPP_START must contain exactly one processing qubit.\n{start_row}')
        if len(link_qubits) != 2:
            raise ValueError(f'\nEJPP_START must contain exactly two link-register qubits.\n{start_row}')
        control_qubit = processing_qubits[0]
        control_info = _parse_qubit_name(control_qubit)
        control_qpu_number = control_info['server']
        control_qpu_name = control_info['server_name']
        source_links = [q for q in link_qubits if _parse_qubit_name(q)['server'] == control_qpu_number]
        target_links = [q for q in link_qubits if _parse_qubit_name(q)['server'] != control_qpu_number]
        if len(source_links) != 1:
            raise ValueError(f'\nCould not identify exactly one control-side link qubit.\n{start_row}')
        if len(target_links) != 1:
            raise ValueError(f'\nCould not identify exactly one target-side link qubit.\n{start_row}')
        source_link = source_links[0]
        target_link = target_links[0]
        target_info = _parse_qubit_name(target_link)
        target_qpu_number = target_info['server']
        target_qpu_name = target_info['server_name']
        end_row = _find_matching_ending_process(start_row=start_row, end_rows=end_rows, source_link=source_link, target_link=target_link)
        sessions.append({'start_event': start_row.get('event'), 'control_qubit': control_qubit, 'control_qpu_number': control_qpu_number, 'control_qpu_name': control_qpu_name, 'target_qpu_number': target_qpu_number, 'target_qpu_name': target_qpu_name, 'source_link': source_link, 'target_link': target_link, 'start_ns': float(start_row['start_ns']), 'end_start_ns': float(end_row['start_ns']), 'release_ns': float(end_row['end_ns'])})
    return sessions

def _add_joint_link_free_windows(sessions):
    sessions = sorted(sessions, key=lambda session: (session['start_ns'], session['start_event']))
    busy_intervals = {}
    for session in sessions:
        for link in [session['source_link'], session['target_link']]:
            if link not in busy_intervals:
                busy_intervals[link] = []
            busy_intervals[link].append((session['start_ns'], session['release_ns']))
    for session in sessions:
        t_D = session['start_ns']
        source_link = session['source_link']
        target_link = session['target_link']
        source_previous_releases = [end for start, end in busy_intervals.get(source_link, []) if end <= t_D]
        target_previous_releases = [end for start, end in busy_intervals.get(target_link, []) if end <= t_D]
        last_source_release = max(source_previous_releases) if source_previous_releases else 0.0
        last_target_release = max(target_previous_releases) if target_previous_releases else 0.0
        joint_free_start = max(last_source_release, last_target_release)
        delta_t_w = t_D - joint_free_start
        if delta_t_w < 0:
            delta_t_w = 0.0
        session['joint_free_start_ns'] = joint_free_start
        session['delta_t_w_ns'] = delta_t_w
    return sessions

def _find_remote_gate_requests(schedule, session):
    target_qpu_number = session['target_qpu_number']
    target_link = session['target_link']
    start_time = session['start_ns']
    ending_start = session['end_start_ns']
    requests = []
    for row in schedule:
        if row.get('type') != 'TWO_GATE':
            continue
        row_start = float(row['start_ns'])
        if row_start < start_time:
            continue
        if row_start >= ending_start:
            continue
        qubits = list(row.get('qubits', []))
        if target_link not in qubits:
            continue
        target_processing_qubits = []
        for qname in qubits:
            info = _parse_qubit_name(qname)
            if not info['is_link'] and info['server'] == target_qpu_number:
                target_processing_qubits.append(qname)
        if not target_processing_qubits:
            continue
        requests.append({'original_event': row.get('event'), 'operation': row.get('operation'), 'remote_gate_start_ns': row_start, 'remote_gate_end_ns': float(row['end_ns']), 'target_qubit': target_processing_qubits[0], 'row': row})
    unique_requests = {}
    for request in requests:
        key = request['original_event']
        if key not in unique_requests:
            unique_requests[key] = request
    return list(unique_requests.values())

def build_qoala_request_table(qoala_result):
    if not isinstance(qoala_result, dict):
        raise TypeError('Expected the result dictionary returned by schedule_pytket_dqc_with_qoala().')
    if 'schedule' not in qoala_result:
        raise KeyError('Qoala result does not contain "schedule".')
    schedule = list(qoala_result['schedule'])
    sessions = _extract_ejpp_sessions(schedule)
    sessions = _add_joint_link_free_windows(sessions)
    raw_table_rows = []
    for session in sessions:
        requests = _find_remote_gate_requests(schedule, session)
        for request in requests:
            raw_table_rows.append({'_remote_gate_start_ns': request['remote_gate_start_ns'], '_original_event': request['original_event'], 'QPU C (i)': session['control_qpu_name'], 'QPU T (j)': session['target_qpu_name'], 'QPU C Link (m)': session['source_link'], 'QPU T Link (n)': session['target_link'], 'Δt_w(k)^(C_m,T_n) [ns]': session['delta_t_w_ns'], 't_D(k)^(C_m,T_n) [ns]': session['start_ns'], 'Δt_P(k)^(C_m,T_n) [ns]': 0.0})
    raw_table_rows.sort(key=lambda row: (row['_remote_gate_start_ns'], row['_original_event'] if row['_original_event'] is not None else float('inf')))
    table_rows = []
    for k, row in enumerate(raw_table_rows):
        table_rows.append({'Request k': k, 'QPU C (i)': row['QPU C (i)'], 'QPU T (j)': row['QPU T (j)'], 'QPU C Link (m)': row['QPU C Link (m)'], 'QPU T Link (n)': row['QPU T Link (n)'], 'Δt_w(k)^(C_m,T_n) [ns]': row['Δt_w(k)^(C_m,T_n) [ns]'], 't_D(k)^(C_m,T_n) [ns]': row['t_D(k)^(C_m,T_n) [ns]'], 'Δt_P(k)^(C_m,T_n) [ns]': row['Δt_P(k)^(C_m,T_n) [ns]']})
    request_table = pd.DataFrame(table_rows, columns=['Request k', 'QPU C (i)', 'QPU T (j)', 'QPU C Link (m)', 'QPU T Link (n)', 'Δt_w(k)^(C_m,T_n) [ns]', 't_D(k)^(C_m,T_n) [ns]', 'Δt_P(k)^(C_m,T_n) [ns]'])
    return request_table