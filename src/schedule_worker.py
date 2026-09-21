import argparse
import json
from pathlib import Path
import traceback
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def _json_default(value):
    if hasattr(value, 'item'):
        try:
            return value.item()
        except Exception:
            pass
    if hasattr(value, 'tolist'):
        try:
            return value.tolist()
        except Exception:
            pass
    if isinstance(value, set):
        return sorted(value, key=str)
    return str(value)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bridge-file', required=True)
    parser.add_argument('--result-file', required=True)
    parser.add_argument('--single-qubit-time', required=True, type=float)
    parser.add_argument('--two-qubit-time', required=True, type=float)
    parser.add_argument('--starting-process-time', required=True, type=float)
    parser.add_argument('--ending-process-time', required=True, type=float)
    parser.add_argument('--strategy', default='QOALA')
    args = parser.parse_args()
    try:
        from src.scheduler import schedule_pytket_dqc_with_qoala
        result = schedule_pytket_dqc_with_qoala(bridge_file=args.bridge_file, single_qubit_time=args.single_qubit_time, two_qubit_time=args.two_qubit_time, starting_process_time=args.starting_process_time, ending_process_time=args.ending_process_time, strategy=args.strategy, print_output=False)
        public_result = {'strategy': result.get('strategy', args.strategy), 'schedule': result.get('schedule', []), 'total_execution_time_ns': result.get('total_execution_time_ns', 0), 'n_original_events': result.get('n_original_events', 0), 'used_qpus': result.get('used_qpus', [])}
        out = Path(args.result_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(public_result, indent=2, default=_json_default), encoding='utf-8')
        print(f"[OK] Qoala/NetSquid child process completed: {float(public_result['total_execution_time_ns']):,.0f} ns")
        return 0
    except Exception:
        traceback.print_exc()
        return 1
if __name__ == '__main__':
    raise SystemExit(main())