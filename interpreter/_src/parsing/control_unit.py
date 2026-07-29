import sys
from ..helpers.my_types import DataSectionInfo, BssSectionInfo, LabelMap, ConstantMap, FU

from ..bridges.data_memory import Data_Memory
from ..bridges.syscall import Syscall

from .patter_matching_helpers import INSTRUCTIONS
from .segment_mapper import Segment_Mapper
from .instruction_parser import Instruction_Parser, Operand

from ..FUs.data_path import Data_Path
from ..FUs.alu import ALU
from ..FUs.fpu import FPU

from interpreter.exit_codes import ExitCode


class Control_Unit:
    """
    Control Unit class responsible for fetching instructions, decoding them, validating operands, and dispatching execution to the appropriate functional units (CPU, Data Path, ALU, FPU).
    It also manages the state of the CPU, including registers, flags, and the instruction pointer (RIP).
    The Control Unit interacts with the Data Memory, Segment Mapper, and the functional units to execute instructions and update the CPU state accordingly.

    Attributes:
        # TO DO
    """

    __slots__ = ["registers", "memory", "data_path", "alu", "fpu", "syscall", "rip", 
                 "text_section", "rodata_section", "data_section", "bss_section", "labels", "constants", 
                 "finished", 
                 "current_fu", "current_instruction", "op1", "op2", "instruction_parser"]

    def __init__ (self,loader: Segment_Mapper, debugging:bool = False) -> None:
        # Initialize Control Unit with memory, segment mapper, functional units and registers (general purpose, fpu and flags)
        self.registers = loader.registers
        self.memory: Data_Memory = loader.memory
        self.data_path: Data_Path = Data_Path(self.registers, self.memory, loader.labels)
        self.syscall: Syscall = Syscall(self.registers, self.memory)
        self.alu: ALU = ALU(self.registers, self.memory)
        self.fpu: FPU = FPU(self.registers, self.memory)

        # Useful registers and flags attributes
        self.rip: int = loader.rip  # Instruction Pointer initialized from Segment Mapper
        # Turns debugging on
        if debugging:
            self.registers.Exch_trap_flag()

        # Parsed sections from segment_mapper
        self.text_section: list[list[str]] = loader.memory_list
        self.rodata_section: DataSectionInfo = loader.rodata_segment
        self.data_section: DataSectionInfo = loader.data_segment
        self.bss_section: BssSectionInfo = loader.bss_segment
        self.labels: LabelMap = loader.labels
        self.constants: ConstantMap = loader.constants

        # Helper instances for the execution
        self.finished: bool = False
        self.current_fu: str = "cpu" # (cpu/data_path/alu/fpu)
        self.current_instruction: str = ""
        self.op1: Operand = Operand()
        self.op2: Operand = Operand()
        self.instruction_parser: Instruction_Parser = Instruction_Parser(self.op1, self.op2, self.labels, self.constants, self.rodata_section, self.data_section, self.bss_section, self.registers)


    #---------------------------------
    # Cycle execution methods
    #---------------------------------

    def run(self) -> None:
        self.rip += 1
        # Improve this loop to enable debugging features
        while not self.finished:
            # Debugging feature: Trap flag verification. If the trap flag is raised, execute the trap flag command and halt execution before executing the instruction in the current line.
            if self.registers.read_trap_flag() == 1:
                # Should allow for gdb command actions
                self.execute_state_command()
            try:
                self.step()
            except Exception as e:
                print(f"CPU Exception at line {self.rip}: {e}")
                self.finished = True
    
    def step(self) -> None:
        try:
            # 1. Gets the instruction, operands and functional unit in use and verifies it's compatibility it the operator count of the instruction
            if self.rip < len(self.text_section):
                self.fetch()
            else:
                print("NO VALID EXIT WAS VALID TO THE PROGRAM.\n Forcing program's exit...")
                sys.exit(100)
            # current_instruction will only be 'None' if rip points to a label in .text (which should be skipped)
            if self.current_instruction != None:
                # 2. Verifies if the instruction-operand set is valid and triggers the execution of the instruction in the respective functional unit
                self.execute(self.current_instruction)
                # 3. Increases rip 
            self.rip += 1
        except ValueError as e:
            print(e)
            sys.exit(1) 

    # -------------------------------
    # Main Logic Implementation
    # -------------------------------

    def fetch(self) -> None:
        """
        Fetches the current instruction and its operands from the text section based on the instruction pointer (RIP).\n
        Sets the current instruction and current functional unit in use and validates and sets the operands and its size.
        Raises a ValueError if the instruction is invalid or if the operands are invalid.        
        
        :return: None
        :rtype: None
        :raises ValueError: If the instruction is invalid or if the operands are invalid.
        """
        line: list[str] = self.text_section[self.rip]

        # Means parsing failed to filter out empty lines and potentially comments too
        if not line:
            sys.exit(ExitCode.SOFTWARE_ERROR)
        
        # Verifies if the line is a label declaration and skips it if so
        if len(line) == 1 and line[0] in self.labels:
            return 
        
        # Verifies if the line is an instruction and sets the instruction, f.u. in use and operand info needed for execution (size, type, value, address)
        elif self.is_valid_instruction(line[0]):
            self.current_instruction = line[0]
            self.instruction_parser.line = line
            self.instruction_parser.rip = self.rip
            try:
                self.instruction_parser.parse()
            except SyntaxError as e:
                print(e)
                sys.exit(ExitCode.INVALID_INSTRUCTION_SYNTAX)
            except ValueError as e:
                print(e)
                sys.exit(ExitCode.INVALID_INSTRUCTION_SYNTAX)

            # Verifies if the number of operands registered are compatible with the instructions documentation in the valid_instructions json file    
            if self.valid_operand_count():
                return
            else:
                # If incompatible reset all info to a Null value and raise an exception
                self.op1.clear()
                self.op2.clear()
                print(f"INVALID OPERAND COUNT FOR INSTRUCTION AT LINE {self.rip}. Exiting program...")
                sys.exit(ExitCode.INVALID_INSTRUCTION_SYNTAX)
        
        # If the instruction wasn't found, raise an exception
        else:
            raise ValueError(f"INVALID INSTRUCTION AT LINE {self.rip}!")
    
    def execute(self, instruction: str) -> None:
        """
        Transfers executions to the class with the functional unit responsible for the instruction
        in the current instruction in this class's respective instance
        and retrieves the result of the operation if any and the flags state that resulted from the operation.
        
        """
        if self.current_fu == "cpu":
            # Calls syscall decoder methods
            # cpu should always just refer to the syscall operation
            error_code = self.syscall.syscall()
            if error_code == -1:
                sys.exit(ExitCode.INVALID_SYSCALL)
        else:
            current_fu: FU = self.get_current_fu()
            if self.current_fu == "data_path" and instruction == "call":
                current_fu.load_rip(self.rip)   # type: ignore
            current_fu.load_values(instruction, self.op1, self.op2)
            try:
                ret = current_fu.execute()      # type: ignore ONLY FOR JUMPS, CALL'S AND RET
                self.rip = ret if ret != None else self.rip
            except RuntimeError:
                sys.exit(ExitCode.INVALID_INSTRUCTION_SYNTAX)



    # ----------------------------------------
    # Execution Helpers
    # ----------------------------------------

    def is_valid_instruction(self, instruction: str) -> bool:
        """
        Verifies if a given instruction is supported by the program and if so sets the current functional unit in use.\n
        Enables syscall's and function calls methods taken care by this class.

        :param instruction: Instruction in verification
        :type instruction: str
        :return: True if the instruction is present in the valid_instructions.json file
        :rtype: bool
        """

        if instruction == "syscall":
            self.current_fu = "cpu"
            return True
        
        for functional_units in INSTRUCTIONS.keys():
            if instruction in INSTRUCTIONS[functional_units]:
                self.current_fu = functional_units
                return True

        return False

    def get_current_fu(self) -> FU:
        """
        Returns the object to the current functional unit in use

        :return: Functional unit object at use
        :rtype: FU (Type Alias for all functional unit types)
        """
        # 'cpu' is safely ignored as at this point it would already be taken care of 
        if self.current_fu == "data_path":
            return self.data_path
        elif self.current_fu == "alu":
            return self.alu
        elif self.current_fu == "fpu":
            return self.fpu
        else:
            raise ValueError("NO FUNCTIONAL UNIT FOUND.\n Exiting program...")
        
    def valid_operand_count(self) -> bool:
        """
        Verifies if the current operand count is valid for the current instruction

        :return: True if the current operand count is valid for the current instruction
        :rtype: bool
        """
        return INSTRUCTIONS[self.current_fu][self.current_instruction] == (self.op1.is_valid() + self.op2.is_valid())     


    # -------------------------
    # DEBUGGING METHODS
    # -------------------------
    def execute_state_command(self) -> None:
        """
        Cyclically asks for user input to execute commands to print the state of the program in execution.\n
        Commands are:\n
        - 'registers': prints the state of the registers
        - 'memory': prints the state of the memory
        - 'data': prints the state of the data section
        - 'rodata': prints the state of the rodata section
        - 'bss': prints the state of the bss section
        - 'constants': prints the state of the constants declared
        - 'rip': prints the current value of the rip register
        - 'fu': prints the current functional unit in use
        - 'help': prints the list of commands available
        - 'step' : executes the instruction at the current rip and updates the state of the program accordingly (to be used to execute step by step)
        - 'exit': exits the program and stops execution
        If an invalid command is given it will print an error message and ask for a new command.
        """
        while True: # Transform into a case switch 
            command: str = input("Enter a command to print the state of the program or 'help' to see the list of commands available: ")
            if command == "registers":
                # self.print_registers()
                pass
            elif command == "memory":
                # self.print_memory()
                pass
            elif command == "data":
                # self.print_data_section()
                pass
            elif command == "rodata":
                # self.print_rodata_section()
                pass
            elif command == "bss":
                # self.print_bss_section()
                pass
            elif command == "constants":
                # self.print_constants()
                pass
            elif command == "rip":
                print(f"Current value of rip: {self.rip}")
            elif command == "fu":
                print(f"Current functional unit in use: {self.current_fu}")
            elif command == "help":
                print("List of commands available:\n- 'registers': prints the state of the registers\n- 'memory': prints the state of the memory\n- 'data': prints the state of the data section\n- 'rodata': prints the state of the rodata section\n- 'bss': prints the state of the bss section\n- 'constants': prints the state of the constants declared\n- 'rip': prints the current value of the rip register\n- 'fu': prints the current functional unit in use\n- 'help': prints this list of commands available\n- 'exit': exits the program and stops execution")
            elif command == "step":
                return
            elif command == "exit":
                print("Exiting program and stopping execution...")
                sys.exit(0)
            else:
                print("Invalid command! Enter 'help' to see the list of commands available.")    