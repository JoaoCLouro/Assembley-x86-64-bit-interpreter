"""
Fixtures for tests/integration/ -- full .asm-file-to-Interpreter_x86
integration tests, run end-to-end through a subprocess.

Deliberately does NOT do `from conftest import PROJECT_ROOT` -- since
this file is itself also named conftest.py, pytest/Python resolves a
bare `conftest` import to this very module (partially initialized at
that point), not to the project-root conftest.py, causing a circular
ImportError. Root discovery is duplicated here (same walk-up-to-
pyproject.toml logic as the root conftest) rather than importing it, to
sidestep the name collision entirely.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _find_project_root(start_dir: str) -> str:
    current = start_dir
    while True:
        if os.path.isfile(os.path.join(current, "pyproject.toml")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise RuntimeError(
                f"Could not find a 'pyproject.toml' above {start_dir} -- "
                "is this test file still somewhere inside the project tree?"
            )
        current = parent


PROJECT_ROOT = _find_project_root(os.path.dirname(os.path.abspath(__file__)))

_SRC_ROOT = os.path.join(PROJECT_ROOT, "interpreter", "_src")
_LIBREG_PATH = os.path.join(_SRC_ROOT, "lib", "libreg.so")
_LIBMMU_PATH = os.path.join(_SRC_ROOT, "lib", "libmmu.so")
_LIBSCL_PATH = os.path.join(_SRC_ROOT, "lib", "libscl.so")
LIBS_PRESENT = (
    os.path.exists(_LIBREG_PATH)
    and os.path.exists(_LIBMMU_PATH)
    and os.path.exists(_LIBSCL_PATH)
)

ASM_DIR = Path(PROJECT_ROOT) / "tests" / "asm_files"
RUNNER = Path(__file__).parent / "_runner.py"


class AsmResult:
    """Wraps the outcome of running one .asm file through the interpreter."""

    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.raw_stdout = stdout
        self.stderr = stderr

        self.program_output = stdout
        self.state = None

        marker = "__STATE__"
        idx = stdout.find(marker)
        if idx != -1:
            self.program_output = stdout[:idx]
            json_part = stdout[idx + len(marker):].strip().splitlines()[0]
            self.state = json.loads(json_part)

    @property
    def registers(self) -> dict:
        assert self.state is not None, (
            f"No state was captured (process may have crashed before "
            f"reaching the exit syscall). stderr:\n{self.stderr}"
        )
        return self.state


@pytest.fixture
def run_asm():
    """
    Returns a callable: run_asm("filename.asm") -> AsmResult
    Runs the given file (resolved relative to tests/asm_files/) through
    the interpreter in a fresh subprocess and captures its state + stdout.
    """

    def _run(asm_filename: str, timeout: float = 10.0) -> AsmResult:
        asm_path = ASM_DIR / asm_filename
        assert asm_path.exists(), f"Missing test asm file: {asm_path}"

        proc = subprocess.run(
            [sys.executable, str(RUNNER), str(asm_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=PROJECT_ROOT,
        )
        return AsmResult(proc.returncode, proc.stdout, proc.stderr)

    return _run