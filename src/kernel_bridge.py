from pathlib import Path
from queue import Empty
import atexit
import json
from IPython import get_ipython
from IPython.display import display
from jupyter_client.manager import start_new_kernel
from src.config import COMPILER, PROJECT_ROOT, PYTKET_KERNEL_NAME, SWITCHSIM

class PersistentKernelBridge:

    def __init__(self, kernel_name, cwd):
        self.kernel_name = kernel_name
        self.cwd = Path(cwd)
        self.km = None
        self.kc = None
        self.start()

    def start(self):
        if self.km is not None:
            try:
                if self.km.is_alive():
                    return
            except Exception:
                pass
        print(f'Starting secondary kernel: {self.kernel_name}')
        self.km, self.kc = start_new_kernel(kernel_name=self.kernel_name, cwd=str(self.cwd))
        self.initialize()
        print(f'✓ {self.kernel_name} kernel ready')

    def initialize(self):
        code = f'\nimport sys\nfrom pathlib import Path\n\nSWITCHSIM = Path({str(SWITCHSIM)!r})\nCOMPILER = Path({str(COMPILER)!r})\nPROJECT_ROOT = Path({str(PROJECT_ROOT)!r})\n\nif str(COMPILER) not in sys.path:\n    sys.path.insert(0, str(COMPILER))\n\n# Make `from src...` importable inside the pytket_dqc kernel too.\nif str(PROJECT_ROOT) not in sys.path:\n    sys.path.insert(0, str(PROJECT_ROOT))\n'
        self.execute(code, show_output=False)

    def ensure_alive(self):
        if self.km is None:
            self.start()
            return
        try:
            alive = self.km.is_alive()
        except Exception:
            alive = False
        if not alive:
            print('pytket kernel died — restarting automatically...')
            self.start()

    def execute(self, code, show_output=True, timeout=3600):
        self.ensure_alive()
        msg_id = self.kc.execute(code, allow_stdin=False, stop_on_error=True)
        remote_error = None
        while True:
            try:
                msg = self.kc.get_iopub_msg(timeout=timeout)
            except Empty:
                raise TimeoutError(f'{self.kernel_name} did not finish within {timeout} seconds.')
            parent_id = msg.get('parent_header', {}).get('msg_id')
            if parent_id != msg_id:
                continue
            msg_type = msg['header']['msg_type']
            content = msg['content']
            if msg_type == 'stream':
                if show_output:
                    print(content.get('text', ''), end='')
            elif msg_type in ('display_data', 'execute_result'):
                if show_output:
                    data = content.get('data', {})
                    metadata = content.get('metadata', {})
                    if data:
                        display(data, raw=True, metadata=metadata)
            elif msg_type == 'error':
                traceback_lines = content.get('traceback', [])
                if show_output:
                    print('\n'.join(traceback_lines))
                remote_error = (content.get('ename', 'RemoteError'), content.get('evalue', ''))
            elif msg_type == 'status':
                if content.get('execution_state') == 'idle':
                    break
        if remote_error:
            name, value = remote_error
            raise RuntimeError(f'{self.kernel_name}: {name}: {value}')

    def restart(self):
        print('Restarting pytket kernel...')
        if self.km is not None:
            try:
                self.kc.stop_channels()
            except Exception:
                pass
            try:
                self.km.shutdown_kernel(now=True)
            except Exception:
                pass
        self.km = None
        self.kc = None
        self.start()

    def shutdown(self):
        if self.km is None:
            return
        try:
            self.kc.stop_channels()
        except Exception:
            pass
        try:
            self.km.shutdown_kernel(now=True)
        except Exception:
            pass
        self.km = None
        self.kc = None
PYTKET = None

def start_bridge(register_magics=True, quiet=False):
    global PYTKET
    if PYTKET is None:
        PYTKET = PersistentKernelBridge(PYTKET_KERNEL_NAME, PROJECT_ROOT)
    ip = get_ipython()
    if register_magics and ip is not None:

        def pytket_magic(line, cell):
            PYTKET.execute(cell)
        ip.register_magic_function(pytket_magic, magic_kind='cell', magic_name='pytket')

        def pytket_restart(line):
            PYTKET.restart()
        ip.register_magic_function(pytket_restart, magic_kind='line', magic_name='pytket_restart')
    atexit.register(PYTKET.shutdown)
    if not quiet:
        print()
        print('========================================')
        print(' QNEST dual-kernel system READY')
        print('========================================')
        print('Main process  → Qoala / NetSquid')
        print('pytket_dqc    → circuit + distribution')
        if register_magics and ip is not None:
            print('%%pytket / %pytket_restart magics registered')
        print('========================================')
    return PYTKET