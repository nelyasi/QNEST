import numpy as np
import pandas as pd
try:
    from src.request_table import build_qoala_request_table
except Exception:
    build_qoala_request_table = None
_EPS = 1e-09
_MAX_BG_CYCLES = 10000000
REQUIRED_COLUMNS = ['Request k', 'QPU C (i)', 'QPU T (j)', 'QPU C Link (m)', 'QPU T Link (n)', 'Δt_w(k)^(C_m,T_n) [ns]', 't_D(k)^(C_m,T_n) [ns]']

def _materialise_seed(seed):
    if seed is None:
        return int(np.random.SeedSequence().entropy % 2 ** 63)
    return int(seed)

def _spawn_streams(seed):
    parent = np.random.SeedSequence(_materialise_seed(seed))
    child_bg, child_ap, child_swap = parent.spawn(3)
    return (np.random.default_rng(child_bg), np.random.default_rng(child_ap), np.random.default_rng(child_swap))

def _bootstrap_ci(values, n_boot=10000, alpha=0.05, rng=None):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return (np.nan, np.nan)
    if x.size == 1 or np.allclose(x, x[0]):
        return (float(x[0]), float(x[0]))
    rng = np.random.default_rng(0) if rng is None else rng
    idx = rng.integers(0, x.size, size=(n_boot, x.size))
    means = x[idx].mean(axis=1)
    lo, hi = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return (float(lo), float(hi))

def _get_request_table(qoala_result):
    if isinstance(qoala_result, pd.DataFrame):
        table = qoala_result.copy()
    else:
        if build_qoala_request_table is None:
            raise ImportError('build_qoala_request_table could not be imported and qoala_result is not a DataFrame.')
        table = build_qoala_request_table(qoala_result)
    missing = [c for c in REQUIRED_COLUMNS if c not in table.columns]
    if missing:
        raise KeyError('Request table is missing columns:\n' + '\n'.join(missing))
    return table

def _validate_request_table(table, strict=True):
    import warnings

    def _fail(msg):
        if strict:
            raise ValueError(msg)
        warnings.warn(msg + '  [strict_validation=False: continuing]', RuntimeWarning, stacklevel=3)
    if table.empty:
        return
    k = table['Request k']
    if k.duplicated().any():
        dupes = sorted(k[k.duplicated()].unique().tolist())
        _fail(f"Duplicate 'Request k' values: {dupes}. The HAMFA/AFA merge in compare_hamfa_vs_afa() joins on this key and would produce a cross product.")
    same_link = table['QPU C Link (m)'] == table['QPU T Link (n)']
    if same_link.any():
        bad = sorted(table.loc[same_link, 'Request k'].tolist())
        _fail(f'Requests {bad} have QPU C Link == QPU T Link. The two arms would alias the same memory state: one stored pair counted as both halves, its age doubled, and discarded twice. Fix the topology or split the link.')
    for col in ('Δt_w(k)^(C_m,T_n) [ns]', 't_D(k)^(C_m,T_n) [ns]'):
        vals = pd.to_numeric(table[col], errors='coerce')
        if vals.isna().any():
            _fail(f'Column {col!r} contains non-numeric or NaN entries.')
        if (vals < 0).any():
            _fail(f'Column {col!r} contains negative values.')

def _prepare_working_table(table):
    work = table.copy()
    work['_orig_pos'] = np.arange(len(work))
    work['_window_start_ns'] = work['t_D(k)^(C_m,T_n) [ns]'] - work['Δt_w(k)^(C_m,T_n) [ns]']
    return work.sort_values(by=['_window_start_ns', 'Request k']).reset_index(drop=True)

def _start_generation(state, start_time_ns, rng, p_link, t_trial_ns):
    if len(state['slots']) >= state['n_slots']:
        state['gen_start_ns'] = None
        state['gen_success_ns'] = None
        state['gen_trials'] = None
        return
    n_trials = int(rng.geometric(p_link))
    state['gen_start_ns'] = float(start_time_ns)
    state['gen_success_ns'] = float(start_time_ns) + n_trials * t_trial_ns
    state['gen_trials'] = n_trials
    state['bg_trials'] += n_trials

def _create_link_state(link_name, start_time_ns, rng, p_link, t_trial_ns, n_slots=1):
    state = {'link': link_name, 'available_from_ns': float(start_time_ns), 'n_slots': int(max(1, n_slots)), 'slots': [], 'gen_start_ns': None, 'gen_success_ns': None, 'gen_trials': None, 'bg_trials': 0}
    _start_generation(state, start_time_ns, rng, p_link, t_trial_ns)
    return state

def _advance_link_to(state, target_time_ns, rng, p_link, t_trial_ns, t_cut_ns, t_store_ns, stats=None):
    target_time_ns = float(target_time_ns)
    if target_time_ns < state['available_from_ns'] - _EPS:
        raise RuntimeError(f"Link {state['link']}: asked to advance to {target_time_ns} but it is busy until {state['available_from_ns']}.")
    for _ in range(_MAX_BG_CYCLES):
        t_gen = float(state['gen_success_ns']) if state['gen_success_ns'] is not None else np.inf
        t_exp = state['slots'][0] + t_store_ns if state['slots'] else np.inf
        nxt = min(t_gen, t_exp)
        if nxt > target_time_ns:
            return
        if t_gen <= t_exp:
            state['slots'].append(t_gen)
            state['slots'].sort()
            _start_generation(state, t_gen, rng, p_link, t_trial_ns)
        else:
            if stats is not None:
                if t_store_ns >= t_cut_ns - _EPS:
                    stats['passed_t_cut'] += 1
                else:
                    stats['stale_refreshed'] += 1
            state['slots'].pop(0)
            if state['gen_success_ns'] is None:
                _start_generation(state, t_exp, rng, p_link, t_trial_ns)
    raise RuntimeError(f"Background process on link {state['link']} exceeded {_MAX_BG_CYCLES} cycles reaching t={target_time_ns} ns.")

def _consume_pair(state, stored_at_ns, now_ns, rng, p_link, t_trial_ns):
    try:
        state['slots'].remove(stored_at_ns)
    except ValueError:
        if state['slots']:
            state['slots'].pop(0)
    if state['gen_success_ns'] is None:
        _start_generation(state, now_ns, rng, p_link, t_trial_ns)

def _oldest_pair(state):
    return state['slots'][0] if state['slots'] else None

def _trials_completed_between(state, start_ns, end_ns, t_trial_ns):
    gen_start = state.get('gen_start_ns')
    total = state.get('gen_trials')
    if gen_start is None or total is None:
        return 0

    def done(t):
        return int(min(total, max(0, np.floor((float(t) - gen_start) / t_trial_ns + 1e-12))))
    return int(max(0, done(end_ns) - done(start_ns)))

def simulate_hamfa_qsp(qoala_result, p_succ, time_per_trial_ns, t_cut_ns, delta_t_c_ns, F_I, F_T, alpha, seed=None, deadline_equal_is_blocked=True, background_start_ns=0.0, hedge_mode='race', fidelity_guard=True, kappa=1.0, early_refresh=True, preserve_unconsumed=True, dual_purpose=True, p_swap=1.0, verbose=True, p_succ_ap=None, strict_validation=True, link_serialization=False, retain_to_fidelity_floor=True, deadline_aware=True, deadline_aware_arbitration=True, conserve_entanglement=True, couple_to_afa_baseline=True, n_memory_slots=1, warm_start=True, warm_start_cycles=25.0, joint_budget_retention=True):
    p_succ = float(p_succ)
    p_ap = float(p_succ if p_succ_ap is None else p_succ_ap)
    time_per_trial_ns = float(time_per_trial_ns)
    t_cut_ns = float(t_cut_ns)
    delta_t_c_ns = float(delta_t_c_ns)
    F_I = float(F_I)
    F_T = float(F_T)
    alpha = float(alpha)
    background_start_ns = float(background_start_ns)
    kappa = float(kappa)
    p_swap = float(p_swap)
    if not 0.0 < p_succ <= 1.0:
        raise ValueError('p_succ must satisfy 0 < p_succ <= 1.')
    if not 0.0 < p_ap <= 1.0:
        raise ValueError('p_succ_ap must satisfy 0 < p_succ_ap <= 1.')
    if time_per_trial_ns <= 0.0:
        raise ValueError('time_per_trial_ns must be > 0.')
    if t_cut_ns <= 0.0:
        raise ValueError('t_cut_ns must be > 0.')
    if delta_t_c_ns <= 0.0:
        raise ValueError('delta_t_c_ns must be > 0.')
    if not 0.0 < F_I <= 1.0:
        raise ValueError('F_I must satisfy 0 < F_I <= 1.')
    if not 0.0 < F_T <= F_I:
        raise ValueError('F_T must satisfy 0 < F_T <= F_I.')
    if not 0.0 < alpha < 1.0:
        raise ValueError('alpha must satisfy 0 < alpha < 1.')
    if hedge_mode not in ('race', 'sequential', 'off'):
        raise ValueError("hedge_mode must be 'race', 'sequential' or 'off'.")
    if not 0.0 < p_swap <= 1.0:
        raise ValueError('p_swap must satisfy 0 < p_swap <= 1.')
    if kappa <= 0.0:
        raise ValueError('kappa must be > 0.')
    resolved_seed = _materialise_seed(seed)
    delta_tau_B_ns = float(-delta_t_c_ns * np.log(F_T / F_I))
    delta_tau_C_ns = float(-delta_t_c_ns * np.log(alpha))
    t_AP_expected_ns = float(time_per_trial_ns / p_ap)
    z = float(np.exp(-time_per_trial_ns / delta_t_c_ns))
    denom = 1.0 - (1.0 - p_ap) * z
    phi_ap = float(p_ap * z / denom) if denom > _EPS else float(p_ap * z / _EPS)
    phi_ap = min(max(phi_ap, 1e-300), 1.0)
    a_break_ns = float(-delta_t_c_ns * np.log(phi_ap))
    accept_age_ns = float(min(delta_tau_B_ns, kappa * a_break_ns)) if fidelity_guard else float(delta_tau_B_ns)
    accept_age_ns = max(accept_age_ns, 0.0)
    if retain_to_fidelity_floor:
        _floor = 0.5 * delta_tau_B_ns if joint_budget_retention else delta_tau_B_ns
        retention_ns = float(min(t_cut_ns, _floor))
    else:
        retention_ns = float(min(t_cut_ns, accept_age_ns))
    t_store_ns = retention_ns if early_refresh else t_cut_ns
    t_store_ns = max(t_store_ns, time_per_trial_ns * 0.001, _EPS)
    rng_bg, rng_ap, rng_swap = _spawn_streams(resolved_seed)
    stats = {'memory_assisted_successful': 0, 'memory_assisted_not_successful': 0, 'passed_t_cut': 0, 'stale_refreshed': 0, 'all_photonic_used': 0, 'swap_failures': 0, 'fidelity_gate_rejections': 0}
    request_table = _get_request_table(qoala_result)
    _validate_request_table(request_table, strict=strict_validation)
    if request_table.empty:
        summary = _empty_summary(p_succ, time_per_trial_ns, t_cut_ns, delta_t_c_ns, F_I, F_T, alpha, delta_tau_B_ns, delta_tau_C_ns, t_AP_expected_ns)
        summary['seed'] = resolved_seed
        if verbose:
            print('No HAMFA requests found.')
        return (request_table.copy(), summary)
    working_table = _prepare_working_table(request_table)
    n_requests = len(working_table)
    if couple_to_afa_baseline:
        ap_trials_stream = np.random.default_rng(resolved_seed).geometric(p_ap, size=n_requests).astype(int)
    else:
        ap_trials_stream = rng_ap.geometric(p_ap, size=n_requests).astype(int)
    all_links = set(working_table['QPU C Link (m)'].tolist())
    all_links.update(working_table['QPU T Link (n)'].tolist())
    burn_in_ns = float(warm_start_cycles) * (t_AP_expected_ns + t_store_ns) if warm_start else 0.0
    warm_start_trials = 0
    link_states = {}
    for name in sorted(all_links):
        st = _create_link_state(name, background_start_ns - burn_in_ns, rng_bg, p_succ, time_per_trial_ns, n_slots=n_memory_slots)
        if warm_start:
            _advance_link_to(st, background_start_ns, rng_bg, p_succ, time_per_trial_ns, t_cut_ns, t_store_ns, None)
            st['available_from_ns'] = float(background_start_ns)
            warm_start_trials += int(st['bg_trials'])
            st['bg_trials'] = 0
        link_states[name] = st
    _ws = working_table['_window_start_ns'].to_numpy(float)
    _lc = working_table['QPU C Link (m)'].tolist()
    _lt = working_table['QPU T Link (n)'].tolist()
    next_use_ns = np.full(n_requests, np.inf)
    for _i in range(n_requests):
        _pair = {_lc[_i], _lt[_i]}
        for _j in range(_i + 1, n_requests):
            if _pair & {_lc[_j], _lt[_j]}:
                next_use_ns[_i] = _ws[_j]
                break
    rows = []
    for idx, row in working_table.iterrows():
        request_k = int(row['Request k'])
        link_c = row['QPU C Link (m)']
        link_t = row['QPU T Link (n)']
        delta_t_w = float(row['Δt_w(k)^(C_m,T_n) [ns]'])
        t_D = float(row['t_D(k)^(C_m,T_n) [ns]'])
        window_start_ns = float(row['_window_start_ns'])
        state_c = link_states[link_c]
        state_t = link_states[link_t]
        if link_serialization:
            decision_time_ns = max(window_start_ns, state_c['available_from_ns'], state_t['available_from_ns'])
        else:
            decision_time_ns = window_start_ns
        _cut_before = stats['passed_t_cut']
        for st in (state_c, state_t):
            _advance_link_to(st, decision_time_ns, rng_bg, p_succ, time_per_trial_ns, t_cut_ns, t_store_ns, stats)
        passed_t_cut_here = stats['passed_t_cut'] > _cut_before
        ap_expected_finish = decision_time_ns + t_AP_expected_ns
        urgent = bool(deadline_aware and ap_expected_finish >= t_D)
        accept_age_k = delta_tau_B_ns if urgent else accept_age_ns

        def arm_status(st):
            stored_at = _oldest_pair(st)
            if stored_at is None:
                return (False, np.nan, np.nan, 0)
            remaining = stored_at + t_store_ns - decision_time_ns
            age = decision_time_ns - stored_at
            if remaining <= 0.0:
                return (False, age, remaining, 0)
            return (True, age, remaining, len(st['slots']))
        c_stored, c_age_ns, c_remaining_ns, c_lle_trials = arm_status(state_c)
        t_stored, t_age_ns, t_remaining_ns, t_lle_trials = arm_status(state_t)
        c_ok = bool(c_stored and c_age_ns <= accept_age_k + _EPS)
        t_ok = bool(t_stored and t_age_ns <= accept_age_k + _EPS)
        n_rejected = int(c_stored and (not c_ok)) + int(t_stored and (not t_ok))
        if c_ok and t_ok and (c_age_ns + t_age_ns > accept_age_k + _EPS):
            if c_age_ns >= t_age_ns:
                c_ok = False
            else:
                t_ok = False
            n_rejected += 1
        if c_stored and (not c_ok):
            _consume_pair(state_c, _oldest_pair(state_c), decision_time_ns, rng_bg, p_succ, time_per_trial_ns)
            c_age_ns = c_remaining_ns = np.nan
            c_lle_trials = 0
        if t_stored and (not t_ok):
            _consume_pair(state_t, _oldest_pair(state_t), decision_time_ns, rng_bg, p_succ, time_per_trial_ns)
            t_age_ns = t_remaining_ns = np.nan
            t_lle_trials = 0
        n_accepted = int(c_ok) + int(t_ok)
        if n_accepted == 2:
            hamfa_case = 'A'
        elif n_accepted == 1:
            hamfa_case = 'B'
        elif n_rejected >= 1:
            hamfa_case = 'C'
        else:
            hamfa_case = 'E'
        both_near_expiry = bool(c_ok and t_ok and (0.0 < min(c_remaining_ns, t_remaining_ns) <= delta_tau_C_ns))
        tau_p_max_ns = float(min(c_remaining_ns, t_remaining_ns)) if c_ok and t_ok else np.nan
        T_mem = np.inf
        a_eff_ns = 0.0
        if hedge_mode != 'off':
            if c_ok and t_ok:
                T_mem = decision_time_ns
                a_eff_ns = float(c_age_ns + t_age_ns)
            elif c_ok or t_ok:
                stored_state = state_c if c_ok else state_t
                missing_state = state_t if c_ok else state_c
                _S = missing_state['gen_success_ns']
                S = float(_S) if _S is not None else np.inf
                horizon = _oldest_pair(stored_state) + t_store_ns
                if S < horizon:
                    T_mem = S
                    a_eff_ns = float(S - float(_oldest_pair(stored_state)))
            else:
                _sc = state_c['gen_success_ns']
                _st = state_t['gen_success_ns']
                S_c = float(_sc) if _sc is not None else np.inf
                S_t = float(_st) if _st is not None else np.inf
                skew = abs(S_c - S_t)
                if np.isfinite(S_c) and np.isfinite(S_t) and (skew <= min(t_cut_ns, t_store_ns) + _EPS):
                    T_mem = max(S_c, S_t)
                    a_eff_ns = float(skew)
            if np.isfinite(T_mem) and a_eff_ns > accept_age_k + _EPS:
                stats['fidelity_gate_rejections'] += 1
                T_mem, a_eff_ns = (np.inf, 0.0)
            if np.isfinite(T_mem) and p_swap < 1.0:
                if rng_swap.random() > p_swap:
                    stats['swap_failures'] += 1
                    T_mem, a_eff_ns = (np.inf, 0.0)
        n_ap_full = int(ap_trials_stream[int(row['_orig_pos'])])
        T_ap_alone = window_start_ns + n_ap_full * time_per_trial_ns
        ap_alone_blocked = T_ap_alone >= t_D if deadline_equal_is_blocked else T_ap_alone > t_D
        T_ap_full = decision_time_ns + n_ap_full * time_per_trial_ns
        if hedge_mode == 'race':
            ap_start_ns = decision_time_ns
            if deadline_aware_arbitration:

                def _late(t):
                    return t >= t_D if deadline_equal_is_blocked else t > t_D
                mem_ok = bool(np.isfinite(T_mem)) and (not _late(T_mem))
                ap_ok = not _late(T_ap_full)
                _nu0 = float(next_use_ns[idx])
                hold_for_future = bool(conserve_entanglement and np.isfinite(_nu0) and (_nu0 - decision_time_ns <= delta_tau_B_ns))
                if mem_ok and (not ap_ok):
                    use_memory = True
                elif ap_ok and (not mem_ok):
                    use_memory = False
                elif mem_ok and ap_ok:
                    if hold_for_future:
                        use_memory = False
                    elif T_mem < T_ap_full - _EPS:
                        use_memory = True
                    elif T_ap_full < T_mem - _EPS:
                        use_memory = False
                    else:
                        use_memory = bool(a_eff_ns <= _EPS)
                else:
                    hold = bool(hold_for_future and np.isfinite(T_mem))
                    if hold:
                        use_memory = False
                    else:
                        use_memory = bool(np.isfinite(T_mem) and T_mem <= T_ap_full + _EPS)
            else:
                use_memory = bool(np.isfinite(T_mem) and T_mem <= T_ap_full + _EPS)
            completion_time_ns = float(T_mem if use_memory else T_ap_full)
        elif hedge_mode == 'sequential':
            wait_limit = accept_age_ns
            use_memory = bool(np.isfinite(T_mem) and T_mem <= decision_time_ns + wait_limit)
            if use_memory:
                completion_time_ns = float(T_mem)
                ap_start_ns = decision_time_ns
            else:
                ap_start_ns = decision_time_ns + wait_limit
                completion_time_ns = ap_start_ns + n_ap_full * time_per_trial_ns
        else:
            use_memory = False
            ap_start_ns = decision_time_ns
            completion_time_ns = float(T_ap_full)
        if use_memory:
            path_used = f'Memory SWAP (Case {hamfa_case})'
            elapsed = max(0.0, completion_time_ns - ap_start_ns)
            aborted = int(min(n_ap_full, np.floor(elapsed / time_per_trial_ns + 1e-12)))
            direct_ap_trials = 0 if dual_purpose else aborted
            aborted_ap_trials = aborted
            direct_ap_duration_ns = 0.0
            memory_wait_ns = max(0.0, completion_time_ns - decision_time_ns)
            memory_assisted_success = True
            memory_assisted_failed = False
            all_photonic_used = False
            F_del = float(F_I * np.exp(-a_eff_ns / delta_t_c_ns))
        else:
            path_used = f'All-Photonic (Case {hamfa_case})'
            direct_ap_trials = n_ap_full
            aborted_ap_trials = 0
            direct_ap_duration_ns = float(n_ap_full * time_per_trial_ns)
            memory_wait_ns = max(0.0, ap_start_ns - decision_time_ns)
            memory_assisted_success = False
            memory_assisted_failed = bool(hamfa_case in ('A', 'B', 'C'))
            all_photonic_used = True
            a_eff_ns = 0.0
            F_del = float(F_I)
        missing_arm_trials = 0
        if hamfa_case == 'B':
            missing_state = state_t if c_ok else state_c
            missing_arm_trials = _trials_completed_between(missing_state, decision_time_ns, completion_time_ns, time_per_trial_ns)
        if memory_assisted_success:
            stats['memory_assisted_successful'] += 1
        if memory_assisted_failed:
            stats['memory_assisted_not_successful'] += 1
        if all_photonic_used:
            stats['all_photonic_used'] += 1
        time_until_success_ns = completion_time_ns - window_start_ns
        punishment_time_ns = max(0.0, completion_time_ns - t_D)
        time_before_deadline_ns = max(0.0, t_D - completion_time_ns)
        blocked = ('Yes' if completion_time_ns >= t_D else 'No') if deadline_equal_is_blocked else 'Yes' if completion_time_ns > t_D else 'No'
        F_eff = float(F_del * np.exp(-max(0.0, time_until_success_ns) / delta_t_c_ns))
        rows.append({'Request k': request_k, 'QPU C (i)': row['QPU C (i)'], 'QPU T (j)': row['QPU T (j)'], 'QPU C Link (m)': link_c, 'QPU T Link (n)': link_t, 'Δt_w(k)^(C_m,T_n) [ns]': delta_t_w, 't_D(k)^(C_m,T_n) [ns]': t_D, 'Window start [ns]': window_start_ns, 'HAMFA decision time [ns]': decision_time_ns, 'HAMFA Case': hamfa_case, 'Path Used': path_used, 'C memory ready': 'Yes' if c_ok else 'No', 'T memory ready': 'Yes' if t_ok else 'No', 'C memory age [ns]': c_age_ns, 'T memory age [ns]': t_age_ns, 'C remaining lifetime [ns]': c_remaining_ns, 'T remaining lifetime [ns]': t_remaining_ns, 'C LLE generation trials': c_lle_trials, 'T LLE generation trials': t_lle_trials, 'Δτ_B [ns]': delta_tau_B_ns, 'Δτ_C [ns]': delta_tau_C_ns, 'Case B effective wait limit [ns]': accept_age_ns, 'τ_p^max [ns]': tau_p_max_ns, 'Both near expiry': 'Yes' if both_near_expiry else 'No', 'Expected AP time [ns]': t_AP_expected_ns, 'Missing-arm trials during request': missing_arm_trials, 'Memory wait duration [ns]': memory_wait_ns, 'Direct AP trials': direct_ap_trials, 'Direct AP duration [ns]': direct_ap_duration_ns, 'Total photonic trials during request': direct_ap_trials + (0 if dual_purpose else missing_arm_trials), 'Memory-assisted successful': 'Yes' if memory_assisted_success else 'No', 'Memory-assisted failed': 'Yes' if memory_assisted_failed else 'No', 'Passed t_cut during request': 'Yes' if passed_t_cut_here else 'No', 'All-photonic used': 'Yes' if all_photonic_used else 'No', 'Completion time [ns]': completion_time_ns, 'Time duration until success [ns]': time_until_success_ns, 'Δt_P(k)^(C_m,T_n) [ns]': punishment_time_ns, 'Blocked': blocked, 'Time before deadline [ns]': time_before_deadline_ns, 'Aborted AP trials': aborted_ap_trials, 'Effective pair age [ns]': a_eff_ns, 'Delivered fidelity F_del': F_del, 'Effective end-to-end fidelity F_eff': F_eff, 'AP variate N_AP': n_ap_full, 'AP-alone blocked': 'Yes' if ap_alone_blocked else 'No', 'Rescued by memory': 'Yes' if use_memory and blocked == 'No' and ap_alone_blocked else 'No'})
        if link_serialization:
            for st in (state_c, state_t):
                st['available_from_ns'] = completion_time_ns
        if use_memory:
            for st, ok in ((state_c, c_ok), (state_t, t_ok)):
                if ok and st['slots']:
                    _consume_pair(st, _oldest_pair(st), completion_time_ns, rng_bg, p_succ, time_per_trial_ns)
                else:
                    st['gen_start_ns'] = st['gen_success_ns'] = None
                    st['gen_trials'] = None
                    _start_generation(st, completion_time_ns, rng_bg, p_succ, time_per_trial_ns)
        elif not preserve_unconsumed:
            for st in (state_c, state_t):
                st['slots'].clear()
                st['gen_start_ns'] = st['gen_success_ns'] = None
                st['gen_trials'] = None
                _start_generation(st, completion_time_ns, rng_bg, p_succ, time_per_trial_ns)
    table = pd.DataFrame(rows).sort_values(by='Request k').reset_index(drop=True)
    table = table[[c for c in HAMFA_TABLE_COLUMNS if c in table.columns] + [c for c in table.columns if c not in HAMFA_TABLE_COLUMNS]]
    makespan_ns = float(table['Completion time [ns]'].max())
    for st in link_states.values():
        st['available_from_ns'] = min(st['available_from_ns'], makespan_ns)
        _advance_link_to(st, makespan_ns, rng_bg, p_succ, time_per_trial_ns, t_cut_ns, t_store_ns, stats)
    background_trials = int(sum((s['bg_trials'] for s in link_states.values())))
    summary = _build_summary(table=table, stats=stats, p_succ=p_succ, p_ap=p_ap, time_per_trial_ns=time_per_trial_ns, t_cut_ns=t_cut_ns, delta_t_c_ns=delta_t_c_ns, F_I=F_I, F_T=F_T, alpha=alpha, delta_tau_B_ns=delta_tau_B_ns, delta_tau_C_ns=delta_tau_C_ns, t_AP_expected_ns=t_AP_expected_ns, accept_age_ns=accept_age_ns, t_store_ns=t_store_ns, background_trials=background_trials, protocol='HAMFA-QSP' if hedge_mode == 'race' else f'HAMFA-QSP[{hedge_mode}]')
    summary.update({'seed': resolved_seed, 'fidelity_break_even_age_ns': a_break_ns, 'requests_rescued_by_memory': int((table['Rescued by memory'] == 'Yes').sum()), 'requests_ap_alone_would_block': int((table['AP-alone blocked'] == 'Yes').sum()), 'memory_rescue_rate': float((table['Rescued by memory'] == 'Yes').sum() / max(1, int((table['AP-alone blocked'] == 'Yes').sum()))), 'hedge_mode': hedge_mode, 'dual_purpose': dual_purpose, 'fidelity_guard': fidelity_guard, 'kappa': kappa, 'link_serialization': link_serialization, 'retain_to_fidelity_floor': retain_to_fidelity_floor, 'deadline_aware': deadline_aware, 'deadline_aware_arbitration': deadline_aware_arbitration, 'conserve_entanglement': conserve_entanglement, 'couple_to_afa_baseline': couple_to_afa_baseline, 'n_memory_slots': int(n_memory_slots), 'warm_start': warm_start, 'warm_start_trials': int(warm_start_trials), 'burn_in_ns': burn_in_ns, 'joint_budget_retention': joint_budget_retention, 'retention_ns': retention_ns, 'early_refresh': early_refresh, 'preserve_unconsumed': preserve_unconsumed, 'p_swap': p_swap, 'fidelity_gate_rejections': stats['fidelity_gate_rejections']})
    if verbose:
        _print_report(table, summary, 'HAMFA-QSP MONTE CARLO RESULTS')
    return (table, summary)
simulate_hamfa_qsp_v2 = simulate_hamfa_qsp
simulate_hamfa_qsp_v3 = simulate_hamfa_qsp

def simulate_afa_qsp(qoala_result, p_succ, time_per_trial_ns, t_cut_ns=None, delta_t_c_ns=None, F_I=1.0, F_T=None, alpha=None, seed=None, deadline_equal_is_blocked=True, background_start_ns=0.0, verbose=True, p_succ_ap=None, strict_validation=True, link_serialization=True, **_ignored):
    p_succ = float(p_succ)
    p_ap = float(p_succ if p_succ_ap is None else p_succ_ap)
    time_per_trial_ns = float(time_per_trial_ns)
    delta_t_c_ns = float(delta_t_c_ns) if delta_t_c_ns is not None else np.inf
    F_I = float(F_I)
    resolved_seed = _materialise_seed(seed)
    request_table = _get_request_table(qoala_result)
    _validate_request_table(request_table, strict=strict_validation)
    if request_table.empty:
        return (request_table.copy(), {'total_requests': 0, 'seed': resolved_seed})
    working_table = _prepare_working_table(request_table)
    n_requests = len(working_table)
    _rng_bg, rng_ap, _rng_swap = _spawn_streams(resolved_seed)
    ap_trials_stream = np.random.default_rng(resolved_seed).geometric(p_ap, size=n_requests).astype(int)
    all_links = set(working_table['QPU C Link (m)'].tolist())
    all_links.update(working_table['QPU T Link (n)'].tolist())
    available_from = {name: float(background_start_ns) for name in all_links}
    rows = []
    for idx, row in working_table.iterrows():
        link_c = row['QPU C Link (m)']
        link_t = row['QPU T Link (n)']
        t_D = float(row['t_D(k)^(C_m,T_n) [ns]'])
        window_start_ns = float(row['_window_start_ns'])
        decision_time_ns = max(window_start_ns, available_from[link_c], available_from[link_t]) if link_serialization else window_start_ns
        n_ap = int(ap_trials_stream[int(row['_orig_pos'])])
        completion_time_ns = decision_time_ns + n_ap * time_per_trial_ns
        time_until_success_ns = completion_time_ns - window_start_ns
        punishment_time_ns = max(0.0, completion_time_ns - t_D)
        blocked = ('Yes' if completion_time_ns >= t_D else 'No') if deadline_equal_is_blocked else 'Yes' if completion_time_ns > t_D else 'No'
        F_del = F_I
        F_eff = float(F_del * np.exp(-max(0.0, time_until_success_ns) / delta_t_c_ns))
        rows.append({'Request k': int(row['Request k']), 'QPU C (i)': row['QPU C (i)'], 'QPU T (j)': row['QPU T (j)'], 'QPU C Link (m)': link_c, 'QPU T Link (n)': link_t, 'Δt_w(k)^(C_m,T_n) [ns]': float(row['Δt_w(k)^(C_m,T_n) [ns]']), 't_D(k)^(C_m,T_n) [ns]': t_D, 'Window start [ns]': window_start_ns, 'HAMFA decision time [ns]': decision_time_ns, 'HAMFA Case': 'AP', 'Path Used': 'All-Photonic (AFA)', 'Direct AP trials': n_ap, 'Direct AP duration [ns]': float(n_ap * time_per_trial_ns), 'Total photonic trials during request': n_ap, 'Completion time [ns]': completion_time_ns, 'Time duration until success [ns]': time_until_success_ns, 'Δt_P(k)^(C_m,T_n) [ns]': punishment_time_ns, 'Blocked': blocked, 'Time before deadline [ns]': max(0.0, t_D - completion_time_ns), 'Delivered fidelity F_del': F_del, 'Effective end-to-end fidelity F_eff': F_eff, 'AP variate N_AP': n_ap})
        if link_serialization:
            available_from[link_c] = completion_time_ns
            available_from[link_t] = completion_time_ns
    table = pd.DataFrame(rows).sort_values(by='Request k').reset_index(drop=True)
    table = table[[c for c in AFA_TABLE_COLUMNS if c in table.columns] + [c for c in table.columns if c not in AFA_TABLE_COLUMNS]]
    summary = _build_summary(table=table, stats={'memory_assisted_successful': 0, 'memory_assisted_not_successful': 0, 'passed_t_cut': 0, 'stale_refreshed': 0, 'all_photonic_used': len(table), 'swap_failures': 0, 'fidelity_gate_rejections': 0}, p_succ=p_succ, p_ap=p_ap, time_per_trial_ns=time_per_trial_ns, t_cut_ns=float(t_cut_ns) if t_cut_ns is not None else np.nan, delta_t_c_ns=delta_t_c_ns, F_I=F_I, F_T=float(F_T) if F_T is not None else np.nan, alpha=float(alpha) if alpha is not None else np.nan, delta_tau_B_ns=np.nan, delta_tau_C_ns=np.nan, t_AP_expected_ns=time_per_trial_ns / p_ap, accept_age_ns=np.nan, t_store_ns=np.nan, background_trials=0, protocol='AFA-QSP')
    summary['seed'] = resolved_seed
    if verbose:
        _print_report(table, summary, 'AFA-QSP MONTE CARLO RESULTS', show_table=False)
    return (table, summary)

def validate_hamfa_run(table, summary, F_T=None, tol=1e-06):
    checks = {}
    if table.empty:
        return {'non_empty': False}
    comp = table['Completion time [ns]']
    dec = table['HAMFA decision time [ns]']
    win = table['Window start [ns]']
    checks['completion_after_decision'] = bool((comp >= dec - tol).all())
    checks['decision_after_window_start'] = bool((dec >= win - tol).all())
    checks['no_nan_completion'] = bool(comp.notna().all())
    checks['latency_non_negative'] = bool((table['Time duration until success [ns]'] >= -tol).all())
    checks['ages_non_negative'] = bool((table['Effective pair age [ns]'].fillna(0.0) >= -tol).all())
    checks['fidelity_in_unit_interval'] = bool(table['Delivered fidelity F_del'].between(0.0, 1.0 + tol).all())
    checks['F_eff_le_F_del'] = bool((table['Effective end-to-end fidelity F_eff'] <= table['Delivered fidelity F_del'] + tol).all())
    if F_T is not None:
        checks['delivered_fidelity_above_floor'] = bool((table['Delivered fidelity F_del'] >= float(F_T) - tol).all())
    if 'Effective pair age [ns]' in table and 'accept_age_ns' in summary:
        cap = summary['accept_age_ns']
        if np.isfinite(cap):
            served = table['Path Used'].str.startswith('Memory')
            checks['accepted_ages_within_bound'] = bool((table.loc[served, 'Effective pair age [ns]'] <= cap + 1e-06).all())
    if summary is not None and (not summary.get('link_serialization', True)):
        return checks
    ok = True
    for col in ('QPU C Link (m)', 'QPU T Link (n)'):
        for _link, grp in table.sort_values('HAMFA decision time [ns]').groupby(col):
            prev_end = -np.inf
            for _, r in grp.iterrows():
                if r['HAMFA decision time [ns]'] < prev_end - tol:
                    ok = False
                prev_end = max(prev_end, r['Completion time [ns]'])
    checks['link_exclusivity'] = ok
    return checks

def _empty_summary(p_succ, t_trial, t_cut, dtc, F_I, F_T, alpha, dB, dC, tAP):
    return {'p_succ': p_succ, 'time_per_trial_ns': t_trial, 't_cut_ns': t_cut, 'delta_t_c_ns': dtc, 'F_I': F_I, 'F_T': F_T, 'alpha': alpha, 'delta_tau_B_ns': dB, 'delta_tau_C_ns': dC, 'expected_AP_time_ns': tAP, 'total_requests': 0, 'memory_assisted_successful': 0, 'memory_assisted_not_successful': 0, 'passed_t_cut': 0, 'all_photonic_used': 0, 'total_blocked_requests': 0, 'total_punishment_time_ns': 0.0}

def _build_summary(table, stats, p_succ, time_per_trial_ns, t_cut_ns, delta_t_c_ns, F_I, F_T, alpha, delta_tau_B_ns, delta_tau_C_ns, t_AP_expected_ns, accept_age_ns, t_store_ns, background_trials, protocol, p_ap=None):
    p_ap = p_succ if p_ap is None else p_ap
    stats = dict(stats)
    stats.setdefault('fidelity_gate_rejections', 0)
    n = int(len(table))
    n_blocked = int((table['Blocked'] == 'Yes').sum())
    critical_trials = int(table['Total photonic trials during request'].sum())
    total_budget = critical_trials + int(background_trials)

    def case_count(c):
        return int((table['HAMFA Case'] == c).sum()) if 'HAMFA Case' in table else 0
    return {'p_succ': p_succ, 'p_succ_ap': p_ap, 'time_per_trial_ns': time_per_trial_ns, 't_cut_ns': t_cut_ns, 'delta_t_c_ns': delta_t_c_ns, 'F_I': F_I, 'F_T': F_T, 'alpha': alpha, 'delta_tau_B_ns': delta_tau_B_ns, 'delta_tau_C_ns': delta_tau_C_ns, 'expected_AP_time_ns': t_AP_expected_ns, 'total_requests': n, 'case_A_requests': case_count('A'), 'case_B_requests': case_count('B'), 'case_C_requests': case_count('C'), 'case_E_requests': case_count('E'), 'memory_assisted_successful': stats['memory_assisted_successful'], 'memory_assisted_not_successful': stats['memory_assisted_not_successful'], 'passed_t_cut': stats['passed_t_cut'], 'all_photonic_used': stats['all_photonic_used'], 'total_direct_AP_trials': int(table['Direct AP trials'].sum()), 'total_photonic_trials_during_requests': critical_trials, 'total_blocked_requests': n_blocked, 'total_punishment_time_ns': float(table['Δt_P(k)^(C_m,T_n) [ns]'].sum()), 'protocol': protocol, 'accept_age_ns': accept_age_ns, 't_store_ns': t_store_ns, 'stale_refreshed': stats['stale_refreshed'], 'swap_failures': stats['swap_failures'], 'background_trials': int(background_trials), 'total_photon_budget': total_budget, 'photon_budget_per_request': float(total_budget / n) if n else 0.0, 'P_on': float(1.0 - n_blocked / n) if n else 0.0, 'B_blocking': float(n_blocked / n) if n else 0.0, 'mean_completion_latency_ns': float(table['Time duration until success [ns]'].mean()), 'p95_completion_latency_ns': float(table['Time duration until success [ns]'].quantile(0.95)), 'makespan_ns': float(table['Completion time [ns]'].max()), 'mean_delivered_fidelity': float(table['Delivered fidelity F_del'].mean()), 'min_delivered_fidelity': float(table['Delivered fidelity F_del'].min()), 'mean_effective_fidelity': float(table['Effective end-to-end fidelity F_eff'].mean()), 'critical_path_trials_per_request': float(critical_trials / n) if n else 0.0, 'R_EG_critical_path': float(n / critical_trials) if critical_trials else np.inf}

def _print_report(table, summary, header, show_table=True):
    line = '=' * 60
    print(f'\n{line}\n{header}\n{line}\n')
    if show_table:
        with pd.option_context('display.max_columns', None, 'display.width', 250):
            print(table.to_string(index=False))
    print(f"\n{line}\n{summary['protocol']} SUMMARY  (seed={summary.get('seed')})\n{line}")
    fields = [('Total requests', 'total_requests', '{}'), ('Case A requests', 'case_A_requests', '{}'), ('Case B requests', 'case_B_requests', '{}'), ('Case C requests', 'case_C_requests', '{}'), ('Case E requests', 'case_E_requests', '{}'), ('Memory-assisted successful', 'memory_assisted_successful', '{}'), ('Memory-assisted not successful', 'memory_assisted_not_successful', '{}'), ('Fidelity-gate rejections', 'fidelity_gate_rejections', '{}'), ('Stored LLEs that passed t_cut', 'passed_t_cut', '{}'), ('Stale LLEs refreshed early', 'stale_refreshed', '{}'), ('All-photonic used', 'all_photonic_used', '{}'), ('Critical-path photonic trials', 'total_photonic_trials_during_requests', '{}'), ('Background LLE trials', 'background_trials', '{}'), ('TOTAL photon budget', 'total_photon_budget', '{}'), ('On-time delivery P_on', 'P_on', '{:.4f}'), ('Blocking probability B', 'B_blocking', '{:.4f}'), ('Mean latency [ns]', 'mean_completion_latency_ns', '{:.2f}'), ('p95 latency [ns]', 'p95_completion_latency_ns', '{:.2f}'), ('Makespan [ns]', 'makespan_ns', '{:.2f}'), ('Mean delivered fidelity', 'mean_delivered_fidelity', '{:.5f}'), ('Min delivered fidelity', 'min_delivered_fidelity', '{:.5f}'), ('Mean effective fidelity', 'mean_effective_fidelity', '{:.5f}'), ('TOTAL BLOCKED REQUESTS', 'total_blocked_requests', '{}'), ('TOTAL PUNISHMENT TIME [ns]', 'total_punishment_time_ns', '{:.2f}')]
    for label, key, fmt in fields:
        if key in summary:
            print(f'{label:<36}: ' + fmt.format(summary[key]))
    print(line + '\n')

def compare_hamfa_vs_afa(qoala_result, p_succ, time_per_trial_ns, t_cut_ns, delta_t_c_ns, F_I, F_T, alpha, seed=None, deadline_equal_is_blocked=True, background_start_ns=0.0, verbose=True, p_succ_ap=None, **hamfa_kwargs):
    resolved_seed = _materialise_seed(seed)
    common = dict(qoala_result=qoala_result, p_succ=p_succ, time_per_trial_ns=time_per_trial_ns, t_cut_ns=t_cut_ns, delta_t_c_ns=delta_t_c_ns, F_I=F_I, F_T=F_T, alpha=alpha, seed=resolved_seed, deadline_equal_is_blocked=deadline_equal_is_blocked, background_start_ns=background_start_ns, verbose=False, p_succ_ap=p_succ_ap)
    hamfa_table, hamfa_summary = simulate_hamfa_qsp(**common, **hamfa_kwargs)
    afa_table, afa_summary = simulate_afa_qsp(**common, link_serialization=hamfa_kwargs.get('link_serialization', False))
    merged = hamfa_table.merge(afa_table, on='Request k', suffixes=('_HAMFA', '_AFA'))
    if len(merged) != len(hamfa_table):
        raise RuntimeError("Merge changed row count; 'Request k' is not unique.")
    coupled = bool((merged['AP variate N_AP_HAMFA'] == merged['AP variate N_AP_AFA']).all())
    later = merged['Completion time [ns]_HAMFA'] > merged['Completion time [ns]_AFA'] + _EPS
    worse_pen = merged['Δt_P(k)^(C_m,T_n) [ns]_HAMFA'] > merged['Δt_P(k)^(C_m,T_n) [ns]_AFA'] + _EPS
    worse_blk = (merged['Blocked_HAMFA'] == 'Yes') & (merged['Blocked_AFA'] == 'No')
    more_ap = merged['Direct AP trials_HAMFA'] > merged['Direct AP trials_AFA']
    lat_delta = merged['Time duration until success [ns]_AFA'] - merged['Time duration until success [ns]_HAMFA']
    comparison = {'seed': resolved_seed, 'coupling_verified': coupled, 'requests': int(len(merged)), 'requests_where_HAMFA_is_later': int(later.sum()), 'requests_where_HAMFA_penalty_worse': int(worse_pen.sum()), 'requests_where_HAMFA_blocked_but_AFA_not': int(worse_blk.sum()), 'requests_where_HAMFA_used_more_AP_trials': int(more_ap.sum()), 'requests_strictly_improved': int((merged['Completion time [ns]_HAMFA'] < merged['Completion time [ns]_AFA'] - _EPS).sum()), 'mean_latency_reduction_ns': float(lat_delta.mean()), 'median_latency_reduction_ns': float(lat_delta.median()), 'pathwise_domination_holds': bool(coupled and later.sum() == 0 and (worse_pen.sum() == 0) and (worse_blk.sum() == 0) and (more_ap.sum() == 0)), 'metrics': {}}
    metric_spec = [('P_on', 'higher', 'hard'), ('B_blocking', 'lower', 'hard'), ('total_blocked_requests', 'lower', 'hard'), ('total_punishment_time_ns', 'lower', 'hard'), ('mean_completion_latency_ns', 'lower', 'hard'), ('p95_completion_latency_ns', 'lower', 'hard'), ('makespan_ns', 'lower', 'hard'), ('total_direct_AP_trials', 'lower', 'hard'), ('total_photonic_trials_during_requests', 'lower', 'hard'), ('critical_path_trials_per_request', 'lower', 'hard'), ('mean_effective_fidelity', 'higher', 'trade'), ('mean_delivered_fidelity', 'higher', 'capped'), ('total_photon_budget', 'lower', 'cost'), ('photon_budget_per_request', 'lower', 'cost')]
    construction_losses = []
    for key, direction, kind in metric_spec:
        a, f = (hamfa_summary[key], afa_summary[key])
        wins = a >= f - 1e-12 if direction == 'higher' else a <= f + 1e-12
        if kind == 'hard' and (not wins):
            construction_losses.append(key)
        if f:
            rel = float((a - f) / f) if direction == 'higher' else float((f - a) / f)
        else:
            rel = 0.0 if a == f else float('inf') * (1 if (a > f) == (direction == 'higher') else -1)
        comparison['metrics'][key] = {'HAMFA': a, 'AFA': f, 'better_or_equal': bool(wins), 'direction': direction, 'kind': kind, 'relative_gain': rel}
    comparison['hard_metric_losses'] = construction_losses
    comparison['all_hard_metrics_won'] = bool(not construction_losses)
    comparison['construction_invariant_losses'] = construction_losses
    comparison['all_construction_invariants_held'] = bool(not construction_losses)
    comparison['delivered_fidelity_above_floor'] = bool(float(hamfa_table['Delivered fidelity F_del'].min()) >= float(F_T) - 1e-12)
    comparison['photon_overhead_ratio'] = float(hamfa_summary['total_photon_budget'] / afa_summary['total_photon_budget']) if afa_summary['total_photon_budget'] else np.inf
    comparison['invariants'] = validate_hamfa_run(hamfa_table, hamfa_summary, F_T=F_T)
    comparison['background_trials'] = hamfa_summary['background_trials']
    if verbose:
        _print_comparison(comparison)
    return (hamfa_table, afa_table, comparison)

def _print_comparison(comparison):
    line = '=' * 88
    print(f"\n{line}\nHAMFA-QSP  vs  AFA-QSP   (coupled streams, seed={comparison['seed']})\n{line}")
    print(f"{'Metric':<44}{'HAMFA':>15}{'AFA':>15}{'':>6}")
    print('-' * 88)
    for key, d in comparison['metrics'].items():
        mark = {'capped': 'cap ', 'cost': 'cost', 'trade': 'trade'}.get(d['kind'], 'OK  ' if d['better_or_equal'] else 'FAIL')
        arrow = '^' if d['direction'] == 'higher' else 'v'
        print(f"{key + ' (' + arrow + ')':<44}{d['HAMFA']:>15.4f}{d['AFA']:>15.4f}   {mark}")
    print('-' * 88)
    print('OK   = construction invariant held (regression test, not a result)')
    print('cap  = a fresh photonic pair is F_I by definition; nothing beats it.')
    print('       Floor check (all delivered pairs >= F_T): ' + ('PASS' if comparison['delivered_fidelity_above_floor'] else 'FAIL'))
    print('cost = HAMFA is expected to lose here. This is what the latency')
    print(f"       gain is bought with. Overhead ratio: {comparison['photon_overhead_ratio']:.2f}x")
    print('-' * 88)
    print(f"Coupling verified (same N_AP)            : {comparison['coupling_verified']}")
    print(f"Requests                                 : {comparison['requests']}")
    print(f"Strictly improved by HAMFA               : {comparison['requests_strictly_improved']}")
    print(f"Mean latency reduction [ns]              : {comparison['mean_latency_reduction_ns']:.2f}")
    print(f"Median latency reduction [ns]            : {comparison['median_latency_reduction_ns']:.2f}")
    print(f"HAMFA later than AFA                     : {comparison['requests_where_HAMFA_is_later']}")
    print(f"HAMFA penalty worse                      : {comparison['requests_where_HAMFA_penalty_worse']}")
    print(f"HAMFA blocked where AFA was not          : {comparison['requests_where_HAMFA_blocked_but_AFA_not']}")
    print('-' * 88)
    bad = [k for k, v in comparison['invariants'].items() if not v]
    print('PHYSICAL INVARIANTS : ' + ('ALL PASS' if not bad else f'FAILED {bad}'))
    print('CONSTRUCTION CHECK  : ' + ('HOLDS' if comparison['pathwise_domination_holds'] else 'VIOLATED'))
    print(line + '\n')

def run_replications(qoala_result, p_succ, time_per_trial_ns, t_cut_ns, delta_t_c_ns, F_I, F_T, alpha, n_reps=30, base_seed=12345, metrics=('mean_completion_latency_ns', 'P_on', 'mean_effective_fidelity', 'total_punishment_time_ns', 'total_photon_budget'), verbose=True, **kwargs):
    seeds = [int(base_seed) + i for i in range(int(n_reps))]
    records, invariant_failures = ([], [])
    for s in seeds:
        _h, _a, cmp_ = compare_hamfa_vs_afa(qoala_result=qoala_result, p_succ=p_succ, time_per_trial_ns=time_per_trial_ns, t_cut_ns=t_cut_ns, delta_t_c_ns=delta_t_c_ns, F_I=F_I, F_T=F_T, alpha=alpha, seed=s, verbose=False, **kwargs)
        rec = {'seed': s, 'pathwise_ok': cmp_['pathwise_domination_holds'], 'strictly_improved': cmp_['requests_strictly_improved'], 'requests': cmp_['requests']}
        for m in metrics:
            rec[f'{m}_HAMFA'] = cmp_['metrics'][m]['HAMFA']
            rec[f'{m}_AFA'] = cmp_['metrics'][m]['AFA']
            rec[f'{m}_delta'] = cmp_['metrics'][m]['HAMFA'] - cmp_['metrics'][m]['AFA']
        records.append(rec)
        bad = [k for k, v in cmp_['invariants'].items() if not v]
        if bad:
            invariant_failures.append((s, bad))
    df = pd.DataFrame(records)
    boot_rng = np.random.default_rng(base_seed)
    stats = {'n_reps': len(seeds), 'pathwise_ok_fraction': float(df['pathwise_ok'].mean()), 'invariant_failures': invariant_failures, 'metrics': {}}
    for m in metrics:
        d = df[f'{m}_delta'].to_numpy(float)
        lo, hi = _bootstrap_ci(d, rng=boot_rng)
        base = df[f'{m}_AFA'].mean()
        stats['metrics'][m] = {'HAMFA_mean': float(df[f'{m}_HAMFA'].mean()), 'AFA_mean': float(base), 'mean_delta': float(d.mean()), 'std_delta': float(d.std(ddof=1)) if len(d) > 1 else 0.0, 'ci95_delta': (lo, hi), 'relative_delta': float(d.mean() / base) if base else np.nan, 'sign_test_fraction_negative': float((d < 0).mean()), 'ci_excludes_zero': bool(lo > 0 or hi < 0)}
    if verbose:
        line = '=' * 88
        print(f'\n{line}\nREPLICATED COMPARISON  ({len(seeds)} seeds, paired)\n{line}')
        print(f"{'Metric':<40}{'HAMFA':>13}{'AFA':>13}{'Δ mean':>13}{'95% CI on Δ':>0}")
        print('-' * 88)
        for m, d in stats['metrics'].items():
            lo, hi = d['ci95_delta']
            print(f"{m:<40}{d['HAMFA_mean']:>13.3f}{d['AFA_mean']:>13.3f}{d['mean_delta']:>13.3f}   [{lo:.3f}, {hi:.3f}]" + ('' if d['ci_excludes_zero'] else '   (n.s.)'))
        print('-' * 88)
        print(f"Construction invariants held in {stats['pathwise_ok_fraction'] * 100:.1f}% of seeds")
        if invariant_failures:
            print(f'PHYSICAL INVARIANT FAILURES: {invariant_failures}')
        else:
            print('Physical invariants: all seeds clean')
        print(line + '\n')
    return (df, stats)

def make_synthetic_request_table(n_requests=40, n_qpus=6, n_links=6, mean_gap_ns=4000.0, window_ns=6000.0, seed=7):
    rng = np.random.default_rng(seed)
    starts = np.cumsum(rng.exponential(mean_gap_ns, size=n_requests))
    rows = []
    for k in range(n_requests):
        i, j = rng.choice(n_qpus, size=2, replace=False)
        m, n = rng.choice(n_links, size=2, replace=False)
        w = float(window_ns * rng.uniform(0.6, 1.6))
        rows.append({'Request k': k, 'QPU C (i)': f'QPU{i}', 'QPU T (j)': f'QPU{j}', 'QPU C Link (m)': f'L{m}', 'QPU T Link (n)': f'L{n}', 'Δt_w(k)^(C_m,T_n) [ns]': w, 't_D(k)^(C_m,T_n) [ns]': float(starts[k]) + w})
    return pd.DataFrame(rows)
_hamfa_get_request_table = _get_request_table
_hamfa_prepare_working_table = _prepare_working_table
_hamfa_spawn_streams = _spawn_streams
_hamfa_start_generation = _start_generation
_hamfa_create_link_state = _create_link_state
_hamfa_advance_link_to = _advance_link_to
_hamfa_discard_and_restart = _start_generation
_hamfa_trials_completed_between = _trials_completed_between
_hamfa_empty_summary = _empty_summary
_hamfa_build_summary = _build_summary
_hamfa_print_report = _print_report
_hamfa_print_comparison = _print_comparison
HAMFA_TABLE_COLUMNS = ['Request k', 'QPU C (i)', 'QPU T (j)', 'QPU C Link (m)', 'QPU T Link (n)', 'Δt_w(k)^(C_m,T_n) [ns]', 't_D(k)^(C_m,T_n) [ns]', 'Window start [ns]', 'HAMFA decision time [ns]', 'HAMFA Case', 'Path Used', 'C memory ready', 'T memory ready', 'C memory age [ns]', 'T memory age [ns]', 'C remaining lifetime [ns]', 'T remaining lifetime [ns]', 'C LLE generation trials', 'T LLE generation trials', 'Δτ_B [ns]', 'Δτ_C [ns]', 'Case B effective wait limit [ns]', 'τ_p^max [ns]', 'Both near expiry', 'Expected AP time [ns]', 'Missing-arm trials during request', 'Memory wait duration [ns]', 'Direct AP trials', 'Direct AP duration [ns]', 'Total photonic trials during request', 'Memory-assisted successful', 'Memory-assisted failed', 'Passed t_cut during request', 'All-photonic used', 'Completion time [ns]', 'Time duration until success [ns]', 'Δt_P(k)^(C_m,T_n) [ns]', 'Blocked', 'Time before deadline [ns]', 'Aborted AP trials', 'Effective pair age [ns]', 'Delivered fidelity F_del', 'Effective end-to-end fidelity F_eff', 'AP variate N_AP', 'AP-alone blocked', 'Rescued by memory']
AFA_TABLE_COLUMNS = ['Request k', 'QPU C (i)', 'QPU T (j)', 'QPU C Link (m)', 'QPU T Link (n)', 'Δt_w(k)^(C_m,T_n) [ns]', 't_D(k)^(C_m,T_n) [ns]', 'Window start [ns]', 'HAMFA decision time [ns]', 'HAMFA Case', 'Path Used', 'Direct AP trials', 'Direct AP duration [ns]', 'Total photonic trials during request', 'Completion time [ns]', 'Time duration until success [ns]', 'Δt_P(k)^(C_m,T_n) [ns]', 'Blocked', 'Time before deadline [ns]', 'Delivered fidelity F_del', 'Effective end-to-end fidelity F_eff', 'AP variate N_AP']
SUMMARY_KEYS = ['p_succ', 'time_per_trial_ns', 't_cut_ns', 'delta_t_c_ns', 'F_I', 'F_T', 'alpha', 'delta_tau_B_ns', 'delta_tau_C_ns', 'expected_AP_time_ns', 'total_requests', 'case_A_requests', 'case_B_requests', 'case_C_requests', 'case_E_requests', 'memory_assisted_successful', 'memory_assisted_not_successful', 'passed_t_cut', 'all_photonic_used', 'total_direct_AP_trials', 'total_photonic_trials_during_requests', 'total_blocked_requests', 'total_punishment_time_ns', 'protocol', 'accept_age_ns', 't_store_ns', 'stale_refreshed', 'swap_failures', 'background_trials', 'P_on', 'B_blocking', 'mean_completion_latency_ns', 'makespan_ns', 'mean_delivered_fidelity', 'mean_effective_fidelity', 'critical_path_trials_per_request', 'R_EG_critical_path', 'fidelity_break_even_age_ns', 'hedge_mode', 'dual_purpose', 'fidelity_guard', 'kappa']
COMPARISON_KEYS = ['requests', 'requests_where_HAMFA_is_later', 'requests_where_HAMFA_penalty_worse', 'requests_where_HAMFA_blocked_but_AFA_not', 'requests_where_HAMFA_used_more_AP_trials', 'requests_strictly_improved', 'pathwise_domination_holds', 'metrics', 'hard_metric_losses', 'all_hard_metrics_won', 'delivered_fidelity_above_floor', 'background_trials']

def assert_output_schema(hamfa_table=None, afa_table=None, summary=None, comparison=None, exact_order=False):
    problems = []

    def _cols(df, expected, label):
        missing = [c for c in expected if c not in df.columns]
        if missing:
            problems.append(f'{label}: missing columns {missing}')
        elif exact_order and list(df.columns)[:len(expected)] != expected:
            problems.append(f'{label}: column order changed')
    if hamfa_table is not None and (not hamfa_table.empty):
        _cols(hamfa_table, HAMFA_TABLE_COLUMNS, 'HAMFA table')
    if afa_table is not None and (not afa_table.empty):
        _cols(afa_table, AFA_TABLE_COLUMNS, 'AFA table')
    if summary is not None and summary.get('total_requests', 0):
        missing = [k for k in SUMMARY_KEYS if k not in summary]
        if missing:
            problems.append(f'summary: missing keys {missing}')
    if comparison is not None:
        missing = [k for k in COMPARISON_KEYS if k not in comparison]
        if missing:
            problems.append(f'comparison: missing keys {missing}')
    if problems:
        raise AssertionError('Output schema regression:\n  - ' + '\n  - '.join(problems))
    return True

def diagnose_blocking(hamfa_table, afa_table, hamfa_summary=None, deadline_equal_is_blocked=True, verbose=True):
    m = hamfa_table.merge(afa_table, on='Request k', suffixes=('_H', '_A'))
    t_D = m['t_D(k)^(C_m,T_n) [ns]_H']
    dec_H = m['HAMFA decision time [ns]_H']

    def _blocked(t):
        return t >= t_D if deadline_equal_is_blocked else t > t_D
    blk_A = _blocked(m['Completion time [ns]_A'])
    blk_H = _blocked(m['Completion time [ns]_H'])
    unsavable = _blocked(dec_H)
    afa_blocked = int(blk_A.sum())
    hamfa_blocked = int(blk_H.sum())
    rescued = int((blk_A & ~blk_H).sum())
    regressed = int((~blk_A & blk_H).sum())
    blocked_unsavable = int((blk_A & unsavable).sum())
    savable = afa_blocked - blocked_unsavable
    missed = int((blk_A & ~blk_H & False).sum()) or savable - rescued
    still = blk_A & blk_H & ~unsavable
    shortfall = (m.loc[still, 'Completion time [ns]_H'] - t_D[still]).astype(float)
    used_mem = hamfa_table['Path Used'].str.startswith('Memory')
    cases = hamfa_table['HAMFA Case'].value_counts().to_dict()
    out = {'requests': int(len(m)), 'afa_blocked': afa_blocked, 'hamfa_blocked': hamfa_blocked, 'rescued_by_hamfa': rescued, 'regressed': regressed, 'blocked_but_unsavable': blocked_unsavable, 'blocked_and_savable': savable, 'savable_but_missed': max(0, savable - rescued), 'capture_rate': float(rescued / savable) if savable else float('nan'), 'memory_hit_rate': float(used_mem.mean()), 'case_counts': cases, 'median_shortfall_ns': float(shortfall.median()) if len(shortfall) else 0.0, 'max_shortfall_ns': float(shortfall.max()) if len(shortfall) else 0.0}
    if hamfa_summary is not None:
        out['accept_age_ns'] = hamfa_summary.get('accept_age_ns')
        out['expected_AP_time_ns'] = hamfa_summary.get('expected_AP_time_ns')
        out['fidelity_gate_rejections'] = hamfa_summary.get('fidelity_gate_rejections')
        out['swap_failures'] = hamfa_summary.get('swap_failures')
    if verbose:
        line = '=' * 72
        print(f'\n{line}\nWHY BLOCKING DID (NOT) FALL\n{line}')
        print(f"Requests                              : {out['requests']}")
        print(f'Blocked under AFA                     : {afa_blocked}')
        print(f'Blocked under HAMFA                   : {hamfa_blocked}')
        print(f'  rescued by HAMFA                    : {rescued}')
        print(f'  regressed (must be 0)               : {regressed}')
        print('-' * 72)
        print(f'Of the {afa_blocked} AFA-blocked requests:')
        print(f'  UNSAVABLE (link busy past t_D)      : {blocked_unsavable}   <- contention, not protocol')
        print(f'  savable in principle                : {savable}')
        print(f'    rescued                           : {rescued}')
        print(f"    still missed                      : {out['savable_but_missed']}")
        if savable:
            print(f"  CAPTURE RATE                        : {out['capture_rate'] * 100:.1f}%")
        print('-' * 72)
        print(f"Memory hit rate                       : {out['memory_hit_rate'] * 100:.1f}% of requests")
        print(f'Case counts (A=both stored, E=neither) : {cases}')
        if hamfa_summary is not None:
            print(f"Acceptance window accept_age          : {out['accept_age_ns']:.1f} ns")
            print(f"Expected all-photonic time E[T_AP]    : {out['expected_AP_time_ns']:.1f} ns")
            print(f"Fidelity-gate rejections              : {out['fidelity_gate_rejections']}")
        if len(shortfall):
            print(f"Median shortfall on missed savable    : {out['median_shortfall_ns']:.1f} ns")
        print(line + '\n')
    return out