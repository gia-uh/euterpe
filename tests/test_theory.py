import subprocess
import sys


def test_theory_imports_no_audio():
    code = "import euterpe.theory, sys; print('euterpe.sound' in sys.modules)"
    assert subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip() == "False"
