import ctypes
import os

from ..bridges.register_manager import Registers_Interface
from ..bridges.data_memory import Data_Memory


class Syscall:
    """
    Resolves and executes syscalls triggered during instruction execution.
    Called from the control_unit via the `syscall()` entry point, which reads
    the syscall number and arguments straight from the register bridge, then
    dispatches to the matching handler.\n
    Handlers that move data (read/write) go through the Data_Memory bridge to
    translate simulated addresses into real bytes, then hand those bytes to
    the compiled C module (libscl.so) which performs the actual host I/O
    against real stdin/stdout/stderr. The C module has no notion of virtual
    addresses or paging — it only ever sees plain byte buffers.

    :param registers: Register bridge used to read syscall number/arguments
    :type registers: Registers_Interface
    :param memory: Memory bridge used to translate simulated addresses to/from bytes
    :type memory: Data_Memory
    """

    # Simulated file descriptors currently supported
    STDIN: int = 0
    STDOUT: int = 1
    STDERR: int = 2

    __slots__ = ["registers", "memory", "lib"]

    def __init__(self, registers: Registers_Interface, memory: Data_Memory):
        self.registers = registers
        self.memory = memory

        # C lib initializer
        # lib/ lives at the project root, one directory up from this file (bridges/)
        _base_dir = os.path.dirname(os.path.abspath(__file__))
        _project_root = os.path.dirname(_base_dir)
        _lib_path = os.path.join(_project_root, "lib", "libscl.so")
        self.lib = ctypes.CDLL(_lib_path)

        # Setup C types as usable types in python
        # Matches execution/include/syscall.h:
        #   int64_t sys_read(int fd, uint8_t *buffer, size_t size)
        #   int64_t sys_write(int fd, const uint8_t *buffer, size_t size)
        self.lib.sys_read.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_size_t
        ]
        self.lib.sys_read.restype = ctypes.c_int64
        self.lib.sys_write.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_size_t
        ]
        self.lib.sys_write.restype = ctypes.c_int64

    def syscall(self) -> None:
        """
        Main entry point called by the control_unit when a syscall instruction
        is executed. Reads the syscall number from rax and its arguments from
        rdi/rsi/rdx, then dispatches to the matching handler.\n
        Unrecognized syscall numbers are ignored (no-op), matching x86-64 Linux
        convention of leaving unknown behavior to the caller.
        """
        code: int = self.registers.read_reg('rax')
        rdi: int = self.registers.read_reg('rdi')
        rsi: int = self.registers.read_reg('rsi')
        rdx: int = self.registers.read_reg('rdx')

        match code:
            case 1:
                self.exit()
            case 3:
                self.read(rdi, rsi, rdx)
            case 4:
                self.write(rdi, rsi, rdx)
            case _:
                return

    def exit(self) -> None:
        """
        Terminates the simulator process immediately.
        """
        import sys
        sys.exit(0)

    def read(self, fd: int, addr: int, size: int) -> int:
        """
        Reads up to `size` bytes from the real stream mapped to `fd` (0/1/2)
        and writes the result into simulated memory at `addr`.

        :param fd: Simulated file descriptor (0 = stdin, 1 = stdout, 2 = stderr)
        :type fd: int
        :param addr: Simulated memory address to write the read bytes into
        :type addr: int
        :param size: Number of bytes to read
        :type size: int
        :return: Number of bytes actually read, or -1 on error/unsupported fd
        :rtype: int
        """
        buffer = (ctypes.c_uint8 * size)()
        read_count = self.lib.sys_read(fd, buffer, size)

        if read_count <= 0:
            return read_count

        data = bytes(buffer[:read_count])
        # Pad to the requested size so write_bytes' size check is satisfied;
        # only the first read_count bytes are meaningful.
        if len(data) < size:
            data = data.ljust(size, b'\x00')
        self.memory.write_bytes(addr, data, size)
        return read_count

    def write(self, fd: int, addr: int, size: int) -> int:
        """
        Reads `size` bytes from simulated memory at `addr` and writes them to
        the real stream mapped to `fd` (0/1/2).

        :param fd: Simulated file descriptor (0 = stdin, 1 = stdout, 2 = stderr)
        :type fd: int
        :param addr: Simulated memory address to read the bytes from
        :type addr: int
        :param size: Number of bytes to write
        :type size: int
        :return: Number of bytes actually written, or -1 on error/unsupported fd
        :rtype: int
        """
        data = self.memory.read_bytes(addr, size)
        buffer = (ctypes.c_uint8 * size).from_buffer_copy(data)
        return self.lib.sys_write(fd, buffer, size)