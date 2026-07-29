import sys

from ..bridges.register_manager import Registers_Interface

class Syscall:

    __slots__ = ["registers", "rax", "rdi", "rsi", "rdx"]

    def __init__ (self, registers: Registers_Interface):
        self.registers = registers

        self.rax: int = -1
        self.rdi: int = -1      
        self.rsi: int = -1
        self.rdx: int = -1

    def dispatcher(self):
        code = self.rax
        match code:
            case 1:
                self.exit()
            case 3:
                self.read(self.rdi, self.rsi, self.rdx)
            case 4:
                self.write(self.rdi, self.rsi, self.rdx)
            case _:
                return

    def exit(self):
        sys.exit(0)

    def read(self, stream, buffer_ref, size):
        ...

    def write(self, stream, buffer_ref, size):
        ...