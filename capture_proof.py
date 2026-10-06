"""Start a clean local instance, capture curl output, then stop it."""
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path

root = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as directory:
    env = dict(os.environ, CALLS_DB=str(Path(directory) / 'calls.db'))
    with open(root / 'server_output.txt', 'w') as logs:
        process = subprocess.Popen(['python', str(root / 'app.py')], env=env,
                                   stdout=logs, stderr=logs)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError('Server exited; inspect server_output.txt')
                try:
                    with socket.create_connection(('127.0.0.1', 8000), timeout=.1):
                        break
                except OSError:
                    time.sleep(.05)
            else:
                raise RuntimeError('Server did not start')
            with open(root / 'proof.txt', 'w') as output:
                subprocess.run(['bash', str(root / 'proof.sh')],
                               stdout=output, stderr=subprocess.STDOUT, check=True)
        finally:
            process.terminate()
            process.wait(timeout=5)
print((root / 'proof.txt').read_text())
