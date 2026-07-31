"""
Helper script run as a subprocess by the integration test suite.

Why a subprocess at all: the simulated `exit` syscall calls sys.exit(0)
on the REAL host process (see assembly_specs.md, section "exit (60)") --
it does not just stop the simulated program's loop. If we ran
Interpreter_x86 in-process, any test program ending in the exit syscall
would kill the pytest process itself. Running each program in a
subprocess isolates that sys.exit() call to a throwaway child.

Why Control_Unit.run is also wrapped here: exit(60) raises SystemExit
from deep inside Control_Unit.run() (via Syscall.syscall()), called from
Interpreter_x86.__init__ before that constructor ever returns. That means
this script's own code never regains control to read state - the process
would just terminate with no output. To recover the state anyway,
Control_Unit.run is wrapped so we hold a reference to the live
Control_Unit instance (which has the registers/memory) the moment run()
starts, and sys.exit is replaced with a wrapper that reads state off that
instance and prints it before re-raising the real exit.

This script relies on the project already being pip-installed in
editable mode (see the root conftest.py) for `bridges`, `FUs`, `helpers`,
and `parsing` to be importable as top-level packages. However, that
editable install's .pth file only points at `interpreter/_src`, not at
the project root itself -- so `import interpreter` (the top-level
package) is NOT made importable by the editable install alone. It only
worked in ad-hoc testing (e.g. `python -c "import interpreter"`) because
Python's `-c` mode adds the current working directory to sys.path.
Running this file as a script does not get that same CWD entry (Python
adds the script's own directory instead), so PROJECT_ROOT is inserted
onto sys.path explicitly below to make `import interpreter` reliable
regardless of how this script is invoked or what the caller's CWD is.

Protocol:
    python _runner.py <asm_file_path>

On success, prints a line to stdout of the form:
    __STATE__<json>
containing the interpreter's state dict (Control_Unit.get_state("all")).
Any output the program itself wrote to stdout (e.g. via the `write`
syscall) appears before that marker line, since it's written during
execution, prior to the exit syscall firing.
"""
import json
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _find_project_root(start_dir: str) -> str:
    current = start_dir
    while True:
        if os.path.isfile(os.path.join(current, "pyproject.toml")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise RuntimeError(
                f"Could not find a 'pyproject.toml' above {start_dir}"
            )
        current = parent


_PROJECT_ROOT = _find_project_root(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from interpreter._src.parsing.control_unit import Control_Unit
from interpreter import Interpreter

_cpu_holder: dict = {"cpu": None}
_real_exit = sys.exit
_real_run = Control_Unit.run


def _wrapped_run(self):
    _cpu_holder["cpu"] = self
    return _real_run(self)


def _intercepting_exit(code=0):
    cpu = _cpu_holder.get("cpu")
    if cpu is not None:
        try:
            state = cpu.get_state("all")
            sys.stdout.write("__STATE__" + json.dumps(state) + "\n")
            sys.stdout.flush()
        except Exception:
            # If state can't be read for any reason, still let the real
            # exit happen - the test will see it via the marker's absence.
            pass
    _real_exit(code)


def main() -> None:
    asm_path = sys.argv[1]
    Control_Unit.run = _wrapped_run
    sys.exit = _intercepting_exit

    # NOTE: Interpreter.__init__ does `if not args: args = _get_args()`,
    # which treats an empty list the same as None and falls back to an
    # interactive input() prompt - fatal in a non-interactive subprocess.
    # None of the test .asm files read argv, so a harmless non-empty
    # placeholder list avoids that prompt without affecting behavior.
    interp = Interpreter(file_name=asm_path, args=["_"])
    # Only reached if the program did NOT call the exit(60) syscall path.
    state = interp.get_state("all")
    sys.stdout.write("__STATE__" + json.dumps(state) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()