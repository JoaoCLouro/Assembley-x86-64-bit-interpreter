import sys
import re

from ...exit_codes import ExitCode

from . import patter_matching_helpers as PM

from ..helpers.my_types import LabelMap
class Operand:
    __slots__ = [
        "expression",
        "type",
        "address",
        "size",
        "is_high",
        "is_signed",
        "valid",
    ]

    def __init__(self) -> None:
        """
        Initializes the parameters of the operand.
        """
        self.valid: bool = False  # Information validity flag for usability
        self.expression: str = ""
        self.type: int = 0  # OpType enum (e.g., REGISTER, MEMORY, IMMEDIATE)
        self.address: int = 0  # Virtual address or register index (long long)
        self.size: int = 0  # Size in bytes (1, 2, 4, 8)
        self.is_high: int = 0  # Flag for high register access (e.g., AH, BH)
        self.is_signed: int = 0  # Flag for signed register/operand operations

    def set(self, expression: str, op_type: int, address: int, size: int, is_high: int = 0, is_signed: int = 0) -> None:
        """
        Sets the parameters of the operand.
        Sets validity to True and enables use of this Operand info.

        :param expression: Unprocessed expression of the operand
        :type expression: str
        :param op_type: Type of the operand (OpType enum integer)
        :type op_type: int
        :param address: Virtual address for memory or register index
        :type address: int
        :param size: Number of bytes to use (1, 2, 4, 8)
        :type size: int
        :param is_high: High register byte indicator (0 or 1)
        :type is_high: int
        :param is_signed: Signed operand indicator (0 or 1)
        :type is_signed: int
        """
        self.valid = True
        self.expression = expression
        self.type = op_type
        self.address = address
        self.size = size
        self.is_high = is_high
        self.is_signed = is_signed

    def clear(self) -> None:
        """
        Sets the validity parameter to False to signal not current/usable information.
        """
        self.valid = False

    def is_valid(self) -> bool:
        """
        Returns the usability status of this Operand object.

        :return: True if the operand can be used, False otherwise.
        :rtype: bool
        """
        return self.valid

        


class Instruction_Parser:
    
    __slots__ = ("op1","op2","line", "labels", "rip", "expected_op_count")

    def __init__ (self, op1: Operand, op2: Operand, labels: LabelMap, expected_op_count: int = 0, line: list[str]=[]):
        self.op1: Operand = op1
        self.op2: Operand = op2
        self.labels = labels
        self.line = line
        self.expected_op_count = expected_op_count
        self.rip: int = -1 # Reset immediately before any call to parser
    

    def parse(self) -> None:
        if not self.validate_instruction_line(self.line):
            raise SyntaxError (f"Invalid instruction declaration syntax at line {self.rip}.")    
        self.parse_operands(self.line[1:])


    def parse_operands(self, line: list [str]) -> None:
        operand_info: list[str] = self.get_operand_info(line) 

    def get_operand_info(self, line: list[str]) -> list[str]:
        """
        Dynamically parses the operand declarations of an instruction.\n
        Tries to match size key words and skips over the expected operand, if it finds one else raises an exception. Also tries to match unspecified sized operands and tries to get their size (if register).
        If doesn't match either a size keyword or an operand format raises a SyntaxError.\n
        Returns pairs of sizes and operand expressions used in the declaration as list elements (always 4 elements but the sizes could be '""')
            
        :param line: Line of code in which the operands are declared without the instruction previously removed
        :type line: list[str]
        :return: List os size and operand expression pairs always following the format: [size;op2;size;op1]
        :rtype: list[str]
        :raises SyntaxError: If comes across an invalid syntax format for assembly x86-64bit code
        :raises ValueError: If comes across a software bug (Unexpected but preventive)
        """
        ret_list: list[str] = ["", "", "", ""]
        max_ret_value: int = 3 
        last_idx: int = len(line) - 1
        size_directives = PM.SIZE_DIRECTIVES
        operand_re = re.compile(fr'^({PM.OPERAND_PATTERN})$')
    
        i = 0
        while i < len(line):
            token = line[i]
            size = size_directives.get(token)
    
            if size is not None:
                if i == last_idx or not operand_re.match(line[i + 1]):
                    raise SyntaxError(f"INVALID SYNTAX FORMAT AT LINE {self.rip}!")
                if max_ret_value <= 1:
                    raise ValueError("Program parsing ran into a problem! Aborting execution ...")
                ret_list[max_ret_value] = line[i + 1]
                ret_list[max_ret_value - 1] = str(size)
                max_ret_value -= 2
                i += 2
    
            elif operand_re.match(token):
                if max_ret_value <= 1:
                    raise ValueError("Program parsing ran into a problem! Aborting execution ...")
                ret_list[max_ret_value] = token
                if self.is_register(token):
                    try:
                        ret_list[max_ret_value - 1] = str(self.get_register_size(token, self.rip))
                    except SyntaxError as e:
                        print(e)
                        sys.exit(ExitCode.INVALID_INSTRUCTION_SYNTAX)
                else:
                    ret_list[max_ret_value - 1] = ""
                max_ret_value -= 2
                i += 1
    
            else:
                raise ValueError("Program parsing ran into a problem! Aborting execution ...")
        return ret_list

        

    # ----------------------------
    # General validation methods
    # ----------------------------
    
    def validate_instruction_line(self, line: list[str]) -> bool:
        """
        Validates the operands of the current instruction based on the number of operands provided in the line.\n
        Primary syntax validator

        :param line: List of strings representing the instruction line
        :type line: list[str]
        :return: True if the instruction is format is valid, false otherwise
        :rtype: bool
        """
        instruction_length: int = len(line)

        if instruction_length == 1:
        # One element code line means a no explicit operand so set both to a Null value
            self.op1.clear()
            self.op2.clear()
            return True
            
        elif instruction_length > 5:
            # instructions with more than 5 elements means it is most definitely wrong syntax
            self.op1.clear()
            self.op2.clear()
            return False
        
        else:
            try:
                return self.match_instruction_format(line[1:]) == self.expected_op_count
            except SyntaxError:
                return False

              


    # --------------------------
    # Pattern Matching Methods
    # --------------------------

    def match_instruction_format(self, instruction: list[str]) -> int:
        """
        Checks whether the operand declaration portion of an instruction (instruction removed) matches
        one of the supported formats:\n
        - size_dir, op1
        - op1
        - size_dir, op1, size_dir, op2
        - op1, op2
        - size_dir, op1, op2
        - op1, size_dir, op2

        :param instruction: Line of code containing only the operand declarations (without instruction in use)
        :type instruction: list[str]
        :return: The number of operands found (1 or 2) if the tokens match a supported operand declaration format
        :rtype: int
        :raises SyntaxError: If the tokens don't match any supported operand declaration format
        """

        # Patterns to Match
        size = fr'(?:{"|".join(re.escape(k) for k in PM.SIZE_DIRECTIVES.keys())})'
        op = fr'(?:{PM.OPERAND_PATTERN})'
        # Precompiled PM for faster comparisons
        one_operand_pattern = re.compile(fr'^(?:{size},{op}|{op})$')
        two_operand_pattern = re.compile(
            fr'^(?:{size},{op},{size},{op}|{op},{op}|{size},{op},{op}|{op},{size},{op})$'
        )

        joined = ",".join(instruction)
        if one_operand_pattern.fullmatch(joined):
            return 1
        if two_operand_pattern.fullmatch(joined):
            return 2
        raise SyntaxError

    # -----------------------------
    # Operand Attributes Fetching
    # -----------------------------

    @staticmethod
    def get_operand_type(operand: str, rip: int) -> int:
        """
        Determines the type of the given operand expression.

        :param operand: Operand expression to classify
        :type operand: str
        :param rip: Current instruction line number, used for error reporting
        :type rip: int
        :return: 0 for memory, 1 for register, 2 for immediate (numeric literal, character/string literal, or label/constant)
        :rtype: int
        :raises SyntaxError: If the operand doesn't match any supported operand type
        """
        if Instruction_Parser.is_memory(operand):
            return 0
        if Instruction_Parser.is_register(operand):
            return 1
        if Instruction_Parser.is_immediate(operand):
            return 2
        raise SyntaxError(f"INVALID SYNTAX FORMAT AT LINE {rip}!")


    @staticmethod
    def get_register_size(register: str, rip: int) -> int:
        """
        Determines the size, in bytes, of the given register based on its declared name.\n
        General-purpose:\n
        64-bit: rax, rbx, rcx, rdx, rsp, rbp, rsi, rdi, rip, r8-r15 -> 8\n
        32-bit: eax, ebx, ecx, edx, esp, ebp, esi, edi, eip, r8d-r15d -> 4\n
        16-bit: ax, bx, cx, dx, sp, bp, si, di, ip, r8w-r15w -> 2\n
        8-bit:  al/ah, bl/bh, cl/ch, dl/dh, r8b-r15b (or r8l-r15l, per this ISA's own convention) -> 1\n
        FPU/vector:\n
        xmm0-15 -> 16\n
        ymm0-15 -> 32
        :param register: Register expression to size (without a leading '%', per existing PM.*_REGISTERS_PATTERN matching)
        :type register: str
        :param rip: Current instruction line number, used for error reporting. Optional.
        :type rip: int
        :return: The register's size in bytes (1, 2, 4, 8, 16, or 32)
        :rtype: int
        :raises SyntaxError: If the register name doesn't match any supported register format
        """
        # FPU/vector registers
        if Instruction_Parser.is_fpu_register(register):
            if register.startswith('ymm'):
                return 32
            return 16  # xmm

        if not Instruction_Parser.is_general_purpose_register(register):
            location = f" AT LINE {rip}" if rip is not None else ""
            raise SyntaxError(f"INVALID SYNTAX FORMAT{location}!")

        # 8-bit high/low byte registers: al, ah, bl, bh, cl, ch, dl, dh
        if re.fullmatch(r'[abcd][hl]', register):
            return 1

        # r8-r15 extended registers with explicit size suffix
        match = re.fullmatch(r'r(?:[89]|1[0-5])([bdlw]?)', register)
        if match:
            suffix = match.group(1)
            return {"": 8, "b": 1, "l": 1, "w": 2, "d": 4}[suffix]

        # rip is 8 bytes, eip is 4 bytes, ip is 2 bytes (no byte-sized ip variant exists)
        if register in ("rip", "eip", "ip"):
            return {"rip": 8, "eip": 4, "ip": 2}[register]

        # Standard [er]?xx / [er]?p / [er]?i forms: rax/eax/ax, rsp/esp/sp, rsi/esi/si, etc.
        if register.startswith('r'):
            return 8
        if register.startswith('e'):
            return 4
        return 2

    # -----------------
    # Type Validation
    # -----------------
    
    # -- / Memory / --
    @staticmethod
    def is_memory(operand: str) -> bool:
        """
        Checks whether the given operand expression is a memory addressing declaration (direct, base, or indexed).

        :param operand: Operand expression to check
        :type operand: str
        :return: True if operand matches a supported memory addressing format, False otherwise
        :rtype: bool
        """
        return bool(re.fullmatch(PM.MEMORY_ADDRESSING_PATTERN, operand))

    @staticmethod
    def is_direct_memory(operand: str) -> bool:
        """
        Checks whether the given operand expression is a direct or base memory addressing declaration.

        :param operand: Operand expression to check
        :type operand: str
        :return: True if operand matches the direct/base addressing format, False otherwise
        :rtype: bool
        """
        return bool(re.fullmatch(PM.DIRECT_AND_BASE_ADDRESSING_PATTERN, operand))

    @staticmethod
    def is_indexed_memory(operand: str) -> bool:
        """
        Checks whether the given operand expression is an indexed memory addressing declaration.

        :param operand: Operand expression to check
        :type operand: str
        :return: True if operand matches the indexed addressing format, False otherwise
        :rtype: bool
        """
        return bool(re.fullmatch(PM.INDEXED_ADDRESSING_PATTERN, operand))


    # -- / Immediate / --
    @staticmethod
    def is_immediate(operand: str) -> bool:
        """
        Checks whether the given operand expression is an immediate-class operand: a numeric/character literal,
        or a constant/label reference (both resolve to a value known at assemble/link time rather than at runtime
        from a register or memory location).

        :param operand: Operand expression to check
        :type operand: str
        :return: True if operand matches either the numeric literal format or the label/constant format
        :rtype: bool
        """
        return Instruction_Parser.is_number(operand) or Instruction_Parser.is_label(operand)

    @staticmethod
    def is_number(operand: str) -> bool:
        """
        Checks whether the given operand expression is a numeric literal (any supported base/representation)
        or a quoted character/string literal.

        :param operand: Operand expression to check
        :type operand: str
        :return: True if operand matches the numeric/character literal format, False otherwise
        :rtype: bool
        """
        return bool(re.fullmatch(PM.IMMEDIATE_VALUE_PATTERN, operand))

    @staticmethod
    def is_label(operand: str) -> bool:
        """
        Checks whether the given operand expression is a constant/label reference (bare identifier, not a numeric
        literal or quoted string).

        :param operand: Operand expression to check
        :type operand: str
        :return: True if operand matches the constant/label naming format, False otherwise
        :rtype: bool
        """
        return bool(re.fullmatch(PM.CONSTANTS_AND_LABELS_PATTERN, operand))


    # -- / Register / --
    @staticmethod
    def is_register(operand: str) -> bool:
        """
        Checks whether the given operand expression is a register of any supported kind (general-purpose or FPU).

        :param operand: Operand expression to check
        :type operand: str
        :return: True if operand matches any supported register format, False otherwise
        :rtype: bool
        """
        return Instruction_Parser.is_general_purpose_register(operand) or Instruction_Parser.is_fpu_register(operand)

    @staticmethod
    def is_general_purpose_register(operand: str) -> bool:
        """
        Checks whether the given operand expression is a general-purpose register (8/16/32/64-bit, including
        high/low byte registers and r8-r15 extended registers).

        :param operand: Operand expression to check
        :type operand: str
        :return: True if operand matches the general-purpose register format, False otherwise
        :rtype: bool
        """
        return bool(re.fullmatch(PM.GENERAL_PURPOSE_REGISTERS_PATTERN, operand))

    @staticmethod
    def is_fpu_register(operand: str) -> bool:
        """
        Checks whether the given operand expression is an FPU/vector register (xmm0-15 or ymm0-15).

        :param operand: Operand expression to check
        :type operand: str
        :return: True if operand matches the FPU/vector register format, False otherwise
        :rtype: bool
        """
        return bool(re.fullmatch(PM.FPU_REGISTERS_PATTERN, operand))