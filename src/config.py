from pathlib import Path
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
GUI_DIR = PROJECT_ROOT / 'GUI'
GUI_DIR.mkdir(exist_ok=True)
import os
SWITCHSIM = Path(os.environ.get('QNEST_SWITCHSIM', str(PROJECT_ROOT))).expanduser().resolve()
COMPILER = Path(os.environ.get('QNEST_COMPILER', str(SWITCHSIM / 'Compiler'))).expanduser().resolve()
PYTKET_KERNEL_NAME = 'pytket_dqc'
BRIDGE_FILE = '/tmp/pytket_qoala_events.json'
GANTT_TIMED_FILE = GUI_DIR / 'qoala_timed.html'
GANTT_SCHEDULE_FILE = GUI_DIR / 'qoala_schedule.html'