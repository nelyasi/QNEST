import numpy as np
import pandas as pd
from src.request_table import build_qoala_request_table

def simulate_afa_qsp(qoala_result, p_succ, time_per_trial_ns, seed=None):
    p_succ = float(p_succ)
    time_per_trial_ns = float(time_per_trial_ns)
    if not 0.0 < p_succ <= 1.0:
        raise ValueError('p_succ must satisfy 0 < p_succ <= 1.')
    if time_per_trial_ns <= 0.0:
        raise ValueError('time_per_trial_ns must be greater than zero.')
    request_table = build_qoala_request_table(qoala_result)
    rng = np.random.default_rng(seed)
    afa_rows = []
    for _, row in request_table.iterrows():
        request_k = int(row['Request k'])
        qpu_c = row['QPU C (i)']
        qpu_t = row['QPU T (j)']
        link_m = row['QPU C Link (m)']
        link_n = row['QPU T Link (n)']
        delta_t_w = float(row['Δt_w(k)^(C_m,T_n) [ns]'])
        t_D = float(row['t_D(k)^(C_m,T_n) [ns]'])
        if delta_t_w < 0:
            raise ValueError(f'Request {request_k} has negative Δt_w.')
        afa_start_time = t_D - delta_t_w
        number_of_trials = int(rng.geometric(p_succ))
        time_until_success = number_of_trials * time_per_trial_ns
        success_time = afa_start_time + time_until_success
        if success_time >= t_D:
            blocked = 'Yes'
        else:
            blocked = 'No'
        delta_t_P = max(0.0, success_time - t_D)
        time_before_deadline = max(0.0, t_D - success_time)
        afa_rows.append({'Request k': request_k, 'QPU C (i)': qpu_c, 'QPU T (j)': qpu_t, 'QPU C Link (m)': link_m, 'QPU T Link (n)': link_n, 'Δt_w(k)^(C_m,T_n) [ns]': delta_t_w, 't_D(k)^(C_m,T_n) [ns]': t_D, 'Δt_P(k)^(C_m,T_n) [ns]': delta_t_P, 'Number of trials': number_of_trials, 'Time duration until success [ns]': time_until_success, 'Blocked': blocked, 'Time before deadline [ns]': time_before_deadline})
    afa_table = pd.DataFrame(afa_rows, columns=['Request k', 'QPU C (i)', 'QPU T (j)', 'QPU C Link (m)', 'QPU T Link (n)', 'Δt_w(k)^(C_m,T_n) [ns]', 't_D(k)^(C_m,T_n) [ns]', 'Δt_P(k)^(C_m,T_n) [ns]', 'Number of trials', 'Time duration until success [ns]', 'Blocked', 'Time before deadline [ns]'])
    total_punishment_time = float(afa_table['Δt_P(k)^(C_m,T_n) [ns]'].sum())
    total_blocked_requests = int((afa_table['Blocked'] == 'Yes').sum())
    summary = {'p_succ': p_succ, 'time_per_trial_ns': time_per_trial_ns, 'total_requests': len(afa_table), 'total_blocked_requests': total_blocked_requests, 'total_punishment_time_ns': total_punishment_time}
    print('\n============================================================')
    print('AFA-QSP MONTE CARLO RESULTS')
    print('============================================================\n')
    print(afa_table.to_string(index=False))
    print('\n============================================================')
    print('AFA-QSP SUMMARY')
    print('============================================================')
    print(f'Success probability per trial : {p_succ}')
    print(f'Time per trial               : {time_per_trial_ns} ns')
    print(f'Total requests               : {len(afa_table)}')
    print(f'Total blocked requests       : {total_blocked_requests}')
    print(f'Total punishment time        : {total_punishment_time} ns')
    print('============================================================\n')
    return (afa_table, summary)