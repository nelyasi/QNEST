def _print_full_schedule(schedule, qoala_result, strategy):
    print()
    print('=' * 165)
    print('QOALA DISTRIBUTED CIRCUIT EXECUTION SCHEDULE')
    print('=' * 165)
    print(f'Scheduling strategy   : {strategy}')
    print(f'Total execution time  : {qoala_result.total_duration:.0f} ns')
    unique_epr_events = {row['event'] for row in schedule if row['type'] == 'EJPP_START'}
    print(f'EPR pairs generated   : {len(unique_epr_events)}')
    print(f'Scheduled task records: {len(schedule)}')
    print('=' * 165)
    print(f"{'EV':>5} {'START(ns)':>12} {'END(ns)':>12} {'DUR(ns)':>10} {'QPU':>5} {'PEER':>7} {'TYPE':<18} {'OPERATION':<22} {'ROLE':<12} {'TASK':<26} QUBITS")
    print('-' * 165)
    for row in schedule:
        if row['peer'] is None:
            peer = '-'
        else:
            peer = f"QPU{row['peer']}"
        qubits = ', '.join(row['qubits'])
        print(f"{row['event']:>5} {row['start_ns']:>12.0f} {row['end_ns']:>12.0f} {row['duration_ns']:>10.0f} {row['qpu']:>5} {peer:>7} {row['type']:<18} {row['operation']:<22} {row['role']:<12} {row['task_class']:<26} {qubits}")
    print('=' * 165)

def _print_entanglement_schedule(schedule):
    print()
    print('=' * 125)
    print('ENTANGLEMENT TIMELINE')
    print('=' * 125)
    rows = [row for row in schedule if row['type'] in {'EJPP_START', 'EPR_END'}]
    if not rows:
        print('No entanglement events.')
        return
    print(f"{'EV':>5} {'START(ns)':>12} {'END(ns)':>12} {'DUR(ns)':>10} {'QPU':>5} {'PEER':>7} {'ACTION':<25} {'ROLE':<12}")
    print('-' * 125)
    for row in rows:
        if row['type'] == 'EJPP_START':
            action = 'EPR + EJPP START'
        else:
            action = 'ENDING PROCESS'
        if row['peer'] is None:
            peer = '-'
        else:
            peer = f"QPU{row['peer']}"
        print(f"{row['event']:>5} {row['start_ns']:>12.0f} {row['end_ns']:>12.0f} {row['duration_ns']:>10.0f} {row['qpu']:>5} {peer:>7} {action:<25} {row['role']:<12}")
    print('=' * 125)

def _print_qpu_summary(schedule):
    print()
    print('=' * 105)
    print('PER-QPU SUMMARY')
    print('=' * 105)
    qpus = sorted({row['qpu'] for row in schedule})
    print(f"{'QPU':>6} {'TASKS':>8} {'1Q':>8} {'2Q':>8} {'EPR START':>12} {'EPR END':>10} {'BUSY(ns)':>14} {'FIRST':>12} {'LAST':>12}")
    print('-' * 105)
    for qpu in qpus:
        rows = [row for row in schedule if row['qpu'] == qpu]
        one_q = sum((row['type'] == 'SINGLE_GATE' for row in rows))
        two_q = sum((row['type'] == 'TWO_GATE' for row in rows))
        epr_start = sum((row['type'] == 'EJPP_START' for row in rows))
        epr_end = sum((row['type'] == 'EPR_END' for row in rows))
        busy = sum((row['duration_ns'] for row in rows))
        first = min((row['start_ns'] for row in rows))
        last = max((row['end_ns'] for row in rows))
        print(f'{qpu:>6} {len(rows):>8} {one_q:>8} {two_q:>8} {epr_start:>12} {epr_end:>10} {busy:>14.0f} {first:>12.0f} {last:>12.0f}')
    print('=' * 105)