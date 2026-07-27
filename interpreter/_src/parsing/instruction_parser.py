import sys
import re

from ...exit_codes import ExitCode
from . import patter_matching_helpers as PM

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
    
    __slots__ = ("op1","op2","line", "rip", "expected_op_count")

    def __init__ (self, op1: Operand, op2: Operand, expected_op_count: int = 0, line: list[str]=[]):
        self.op1: Operand = op1
        self.op2: Operand = op2
        self.line = line
        self.expected_op_count = expected_op_count
        self.rip: int = -1 # Reset immediately before any call to parser
    

    def parse(self) -> None:
        try:
            self.validate_instruction_line(self.line)
            self.set_operand_type(self.line)
            self.set_operand_value_and_address(self.line)
        except SyntaxError as e:    # validate Operands
            raise SyntaxError(e)
        
        except ValueError as e:     # Operand setting
            raise SyntaxError(e)

    # -----------------------------------
    # General validation methods
    # -----------------------------------
    
    def validate_instruction_line(self, line: list[str]) -> None:
        """
        Validates the operands of the current instruction based on the number of operands provided in the line.\n
        Sets the operand attributes accordingly or raises a ValueError if the operands are invalid.

        :param line: List of strings representing the instruction line
        :type line: list[str]
        :raises SyntaxError: If the operands are invalid for the current instruction, including invalid syntax or invalid operand sets
        """
        instruction_length: int = len(line)

        if instruction_length == 1:
        # One element code line means a no explicit operand so set both to a Null value
            self.op1.clear()
            self.op2.clear()
            return
            
        elif instruction_length > 5:
            # instructions with more than 5 elements means it is most definitely wrong syntax
            self.op1.clear()
            self.op2.clear()
            raise SyntaxError
        
        else:
            # If none of the above cases are triggered try to parse the operands and sizes
            try:
                operand_info: list[str] = self.get_operand_info(line[1:]) 
                self.parse_operand_info(operand_info)
            except ValueError as e:
                print(e)
                sys.exit(ExitCode.SOFTWARE_ERROR)
            except SyntaxError as e:
                print(e)
                sys.exit(ExitCode.INVALID_INSTRUCTION_SYNTAX)
              

    #---------------------------
    # Operand setting methods
    #---------------------------

    def set_operand(self, operand: str, expression: str, type: str, value: bytes, size: int) -> None:
        """
        Automates the operand 

        :param operand: Expression for which operand(s) to update (op1/op2)
        :type operand: str
        :param expression: Unaltered expression used to refer to the operand in the line of code
        :type expression: str
        :param type: Type of operand (register/ memory/ immediate)
        :type type: str
        :param value: Value of the operand
        :type value: str
        :param size: Number of bytes used by the operand(s)
        :type size: int
        """
        getattr(self, operand).set(expression, type, value, size)

    def set_operand_type(self, line: list[str]) -> None:
        """
        Attribute a type to the operand type attributes based on the operand expression
        
        :param line: List of strings representing the instruction line
        :type line: list[str]
        :raises ValueError: If an invalid label is found during operand type determination
        """
        # For each of the attributes that hold the operands expression, if they are not None get their type
        if self.op1 != None:
            try:
                self.op1_type = self.determine_operand_type(self.op1)
            except ValueError as e:
                raise ValueError(e)
        if self.op2 != None:
            try:
                self.op2_type = self.determine_operand_type(self.op2)
            except ValueError as e:
                raise ValueError(e)
    
    def set_operand_value_and_address(self, line: list[str]) -> None:
        """
        Attribute a value and address to the operand value and address attributes based on the operand expression and type
        
        :param line: List of strings representing the instruction line
        :type line: list[str]
        :raises ValueError: If an invalid label is found during operand value or address determination
        """
        # For each of the attributes that hold the operands expression, if they are not None get their address (if it is a memory reference) and value
        operation_size: int = self.get_operation_size()
        if self.op1 != None:
            try:
                op1_info: tuple[bytes, int | None]= self.determine_operand_value_and_address(self.op1, self.op1_type, self.op1_size, operation_size, self.memory)
                self.set_operand_value("op1", op1_info[0])  
                self.set_operand_address("op1", op1_info[1])
            except ValueError as e:
                raise ValueError(e)
        if self.op2 != None:
            try:
                op2_info: tuple[bytes, int | None]= self.determine_operand_value_and_address(self.op2, self.op2_type, self.op1_size, operation_size, self.memory)
                self.set_operand_value("op2", op2_info[0])      
                self.set_operand_address("op2", op2_info[1])    
            except ValueError as e:
                raise ValueError(e)

    def set_operand_value(self, operand:str, value: bytes) -> None:
        """
        Attribute a value to the operand value attributes

        :param operand: Expression for the operand to update (both/op1/op2)
        :type operand: str
        :param value: Value of the operand (must be calculated)
        :type value: int
        :raises ValueError: If an invalid operand identifier is used
        :raises SyntaxError: If any operator value with an invalid type (non byte) is passed to the execution of this method
        """
        if not isinstance(value, bytes):
            raise SyntaxError("\n   Software bug detected.\nInvalid type for operator value. Values should always be bytes!")
        if operand == "both":
            self.op1_value = value
            self.op2_value = value
        elif operand == "op1":
            self.op1_value = value
        elif operand == "op2":
            self.op2_value = value
        else:
            raise ValueError(f"INVALID OPERAND IDENTIFIER {operand} USED. IT SHOULD BE EITHER 'both'/'op1'/'op2'!")
        
    def set_operand_address(self, operand:str, address: int | None) -> None:
        """
        Attribute an address to the operand address attributes

        :param operand: Expression for the operand to update (both/op1/op2)
        :type operand: str
        :param address: Address of the operand (must be calculated, None if not a memory operand)
        :type address: int | None
        :raises ValueError: If an invalid operand identifier is used
        """
        if operand == "both":
            self.op1_address = address
            self.op2_address = address
        elif operand == "op1":
            self.op1_address = address
        elif operand == "op2":
            self.op2_address = address
        else:
            raise ValueError(f"INVALID OPERAND IDENTIFIER {operand} USED. IT SHOULD BE EITHER 'both'/'op1'/'op2'!")

    #------------------------
    # Operand Determination
    #------------------------

    def determine_operand_type(self, operand: str) -> str:
        """
        Determines the operand type based on its expression by going through the possible operand types and verifying if the expression matches any of them.        

        :param operand: Expression for the operand to determine the type
        :type operand: str
        :return: Description of the operand type (either 'direct memory'/'base memory'/'indexed memory'/'address'/'register'/'constant'/'immediate')
        :rtype: str
        :raises ValueError: If an invalid label is found during operand type determination or if the operand does not match any valid type
        """
        try:
            if self.verify_memory_addressing(operand, PM.DIRECT_AND_BASE_ADDRESSING_PATTERN):
                return 'direct memory'
            elif self.verify_memory_addressing(operand,PM.DIRECT_AND_BASE_ADDRESSING_PATTERN, 2):
                return 'base memory'
            elif self.verify_memory_addressing(operand, PM.INDEXED_ADDRESSING_PATTERN, 2):
                return 'indexed memory'
            elif self.is_address(operand):
                return 'address'
            elif self.is_register(operand):
                return 'register'
            elif self.is_constant(operand):
                return 'constant'
            elif self.is_immediate_value(operand):
                return 'immediate'
            else:
                # should never happen
                raise ValueError(f"UNABLE TO DETERMINE OPERAND TYPE FOR {operand} AT LINE {self.rip}!")
        except ValueError as e:
            print(e)
            sys.exit(ExitCode.INVALID_INSTRUCTION_SYNTAX)
    
    ### RETURN OF BYTES MUST BE DEALT WITH

    def determine_operand_value_and_address(self, operand: str, operand_type: str | None, operand_size: int, operation_size: int, memory: Data_Memory) -> tuple[bytes, int|None]:
        """
        Determines the operand value and address based on its expression and type by going through the possible operand types and calculating the value and address accordingly.        

        :param operand: Expression for the operand to determine the value and address
        :type operand: str
        :param operand_type: Type of the operand to determine the value and address
        :type operand_type: str | None
        :param operand_size: Number of bytes that the operand uses (1, 2, 4, 8)
        :type operand_size: int
        :param operation_size: Size of the current operation to be executed (size of the biggest dominant operator)
        :type operation_size: int
        :param memory: Data memory instance to retrieve values from memory operands
        :type memory: Data_Memory
        :return: Tuple containing the operand value and address (address is None if not a memory operand)
        :rtype: tuple[bytes, int | None]
        :raises ValueError: If an invalid label is found during operand value or address determination or if the operand type is invalid
        """
        value: bytes = b"0"
        address: int | None = None 

        if operand_type == 'direct memory' or operand_type == 'base memory' or operand_type == 'indexed memory':
            address = self.calculate_memory_address(operand)
            value = memory.read_bytes(address, operand_size)  
        elif operand_type == 'address':
            if re.match(PM.CONSTANTS_AND_LABELS_PATTERN, operand):
                try:
                    value = self.get_label_address(operand).to_bytes(8, byteorder="little")
                except ValueError as e:
                    raise ValueError(e)
            else:
                # should never happen
                raise ValueError(f"INVALID ADDRESS OPERAND {operand} AT LINE {self.rip}!")
        elif operand_type == 'register':
            value = self.registers.read_reg(operand).to_bytes(operand_size, byteorder="little")
        elif operand_type == 'constant':
            value  = self.get_encoded_value(self.constants[operand]['value']).to_bytes(operation_size, byteorder="little")
        elif operand_type == 'immediate':
            value  = self.get_encoded_value(operand).to_bytes(operation_size, byteorder="little")
        else:
            # should never happen
            raise ValueError(f"INVALID OPERAND TYPE {operand_type} AT LINE {self.rip}!")
        return (value, address)


    #----------------------
    # Operand capture
    #----------------------

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
        max_ret_value: int = 3  # 4 list elements
        last_idx: int = len(line) - 1
        size_directives = PM.SIZE_DIRECTIVES
        operand_re = re.compile(fr'^({PM.OPERAND_PATTERN})$')  # precompiled, module/class level

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
                        ret_list[max_ret_value - 1] = str(self.get_register_size(token))
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

    def get_operand(self, operand: str) -> list[str]:
        """
        Retrieves the operand expression and size if valid.\n
        Goes through all the possible operand types and verifies if the given operand matches any of them. Else will raise an error.
        Acts as a dispatcher to the specific operand type verifiers.
        
        :param operand: Expression for the operand to retrieve 
        :type operand: str
        :return: List containing the operand expression and its size if valid, otherwise an empty list
        :rtype: list[str]
        :raises ValueError: If the operand is invalid or if an invalid label is found during size retrieval
        """
        ret: list[str] = []

        try: 
            condition: bool = self.is_memory_addressing(operand) or self.is_address(operand) or self.is_register(operand) or self.is_constant(operand) or self.is_immediate_value(operand)
        except ValueError as e:
            raise ValueError(e)
        if condition:
            ret.append(operand)
            try:
                size: int = self.get_label_size(operand)
            except ValueError as e:
                raise ValueError(e)
            ret.append(str(size))
        return ret
    
    def get_operation_size(self) -> int:
        """
        Returns the size of the current operation to be executed, meaning the size of the biggest of the operands.\n
        Will always return the biggest of the sizes in the current execution context.
        To be used in contexts of constants or immediate value parsing where size is not specified but needed for byte transformations of integer values.
    
        
        :return: The size of the biggest operand in the current instruction
        :rtype: int
        """
        return self.op1_size if self.op1_size > self.op2_size else self.op2_size
    
    def get_register_size(self, register: str) -> int:
        """
        Returns the size of a register as a number of bytes it takes (1-8)
        
        :param register: Register expression
        :type register: str
        :return: Size in number of bytes of the given register
        :rtype: int
        :raises SyntaxError: If no register match happen (Fail safe mechanism)
        """
        register = register.lower()

        if register.startswith('r') and (register.endswith('x') or register[len(register) - 1].isdigit()):
            return 8
        elif register.startswith('e') or register.endswith('d'):
            return 4
        elif register.endswith('x') or register.endswith('i') or register.endswith('w'):
            return 2
        elif register.endswith('h') or register.endswith('l') or register.endswith('b'):
            return 1
        else:
            raise SyntaxError(f"INVALID REGISTER '{register}' FOUND!")
    
    def get_labels(self, expressions: str) -> list[str]:
        """
        Extracts all labels from a given expression list by order.

        :param expression: Expression in verification
        :type expression: str
        :return: List of labels found in the expression in order of appearance 
        or ['Invalid'] if an invalid label-like element is found
        :rtype: list[str]
        """
        labels: list[str] = []
        found_labels: list[str] = re.findall(PM.CONSTANTS_AND_LABELS_PATTERN, expressions)
        for item in found_labels:
            if not (Segment_Mapper._exists_in_section(item, self.data_section) or Segment_Mapper._exists_in_section(item, self.rodata_section) or Segment_Mapper._exists_in_section(item, self.bss_section)):
                    return ['Invalid']
            else:
                labels.append(item)
        return labels

    def get_label_size(self, label: str) -> int:
        """
        Gets the size of a given label from the data/bss/rodata sections

        :param label: Label in verification
        :type label: str
        :return: Size of the label in bytes
        :rtype: int
        :raises ValueError: If the label is not found in any section
        """
        if Segment_Mapper._exists_in_section(label, self.data_section):
            return self.data_section[label]['size'] # type: ignore  
        elif Segment_Mapper._exists_in_section(label, self.rodata_section):
            return self.rodata_section[label]['size']   # type: ignore
        elif Segment_Mapper._exists_in_section(label, self.bss_section):
            return self.bss_section[label]['size']  # type: ignore
        else:
            raise ValueError(f"LABEL {label} NOT FOUND IN ANY SECTION DURING SIZE RETRIEVAL AT LINE {self.rip}!")       # should not happen
        
    def get_label_address(self, label: str) -> int:
        """
        Returns the address of a given label (variable)
        
        :param label: Label given to a value on its declaration
        :type label: str
        :return: Address of this label in memory
        :rtype: int
        """
        # Return types are ignored because the return type of each section is specific and mask for int values

        if Segment_Mapper._exists_in_section(label, self.rodata_section):
            return self.rodata_section[label]['addresses'][0]   #type: ignore 
        elif Segment_Mapper._exists_in_section(label, self.data_section):
            return self.data_section[label]['addresses'][0]     #type: ignore
        else:
            return self.bss_section[label]['addresses'][0]      #type: ignore


    def get_address_value(self, components: list[str], expression: str) -> int:
        """
        Docstring for get_address_value
        
        :param components: Elements of an operand declaration in an instruction
        :type components: list[str]
        :return: Description
        :rtype: int
        :raises ValueError:  ...
        """
        ret: int = 0
        list: list[str] = components
        try:
            ret_list: list[int] = self.verify_multiplication(components, expression)
            ret = ret_list[0]
            if ret_list[1] != -1:
                list = Control_Unit.get_new_list(list, ret_list[-1], 3)
        except ValueError as e:
            print(f"{e}")
            sys.exit(ExitCode.INVALID_INSTRUCTION_SYNTAX)   # To be determined
        try:
            ret += Control_Unit.calculate_list(list)
        except ValueError:
            print(f"INVALID EXPRESSION {expression} IN MEMORY ADDRESSING MODE AT LINE {self.rip}!")
            sys.exit(ExitCode.INVALID_INSTRUCTION_SYNTAX)   # To be determined
        return ret

    def get_encoded_value(self, value: str | int) -> int:
        """
        Processes a given value of type string or int to be returned as an integer.
        
        :param value: Value to be processed
        :type value: str | int
        :return: Integer value of the given value
        :rtype: int
        """
        if re.match(PM.NUMBER_REPRESENTATION_PATTERN, str(value)):
            return int(value, 0)   #type: ignore
        else:
            # The value is a String
            new_value: str = str(value).replace('"', '').replace("'", "")
            byte_value: bytes = str(new_value).encode()
            return int.from_bytes(byte_value, 'little')
            
    #-------------------------
    # Operand type validation
    #-------------------------

    def is_memory_addressing(self, expression: str) -> bool:
        """
        Verifies if a given expression is a memory addressing mode

        :param expression: Expression in verification
        :type expression: str
        :return: True if the expression is a memory addressing mode
        :rtype: bool
        :raises ValueError: If an invalid label is found in the expression
        """
        try:
            result: bool = self.verify_memory_addressing(expression, PM.DIRECT_AND_BASE_ADDRESSING_PATTERN) or self.verify_memory_addressing(expression,PM.DIRECT_AND_BASE_ADDRESSING_PATTERN, 2) or self.verify_memory_addressing(expression, PM.INDEXED_ADDRESSING_PATTERN, 2)
        except ValueError as e:
            raise ValueError(e)
        return result
    
    def verify_memory_addressing(self, expression: str, pattern: str, number_registers: int=0, number_labels: int=1) -> bool:
        """
        Verifies if a given expression is a direct, base or indexed memory addressing mode based on the number of registers and labels allowed to be used in it and the pattern to use for the verification.\n
        If the expression is none of those and does not take invalid registers or not existing labels  returns False.
        If any invalid or not existing components are found raises a ValueError.

        :param expression: Expression in verification
        :type expression: str
        :param pattern: Pattern to use for the match
        :type pattern: str
        :param number_registers: Number of registers allowed in the expression. Default to 0.
        :type number_registers: int
        :param number_labels: Number of labels allowed in the expression. Default to 1.
        :type number_labels: int
        :return: True if the expression follows the pattern given and has the correct number of each component or False otherwise.
        :rtype: bool
        :raises ValueError: If an invalid label is found in the expression
        """
        if re.match(pattern, expression):
            # If a match with the Direct/Base memory addressing pattern was found get the list of the labels used in the expression and the list of registers used in the expression
            labels: list[str] = self.get_labels(expression)
            registers_in_expression: list[str] = re.findall(PM.REGISTER_PATTERN, expression)
            # If the list returned 'invalid' then non existing label was found
            if 'Invalid' in labels:
                raise ValueError(f"INVALID LABEL IN MEMORY ADDRESSING MODE {expression} AT LINE {self.rip}!")
            # If there are more than label or registers involved in the expression than it is permitted by the arguments the expression is not syntactically correct
            elif len(labels) > number_labels or len(registers_in_expression) > number_registers:
                return False
            else:
                return True
        return False
    
    def is_address(self, expression: str) -> bool:
        """
        Verifies if a given expression is a direct address (immediate value or label)

        :param expression: Expression in verification
        :type expression: str
        :return: True if the expression is a direct address
        :rtype: bool
        :raises ValueError: If an invalid label is found in the expression
        """
        # If the expression has the memory address brackets it is not an address
        if expression.startswith('[') and expression.endswith(']'):
            return False
        # Assuming it is an address, tries to match the components valid in an address declaration declaration and verify if they are valid
        elif re.match(fr'^{PM.CONSTANTS_AND_LABELS_PATTERN}$', expression):
            if not (Segment_Mapper._exists_in_section(expression, self.data_section) or Segment_Mapper._exists_in_section(expression, self.rodata_section) or Segment_Mapper._exists_in_section(expression, self.bss_section)):
                raise ValueError(f"INVALID LABEL {expression} AT LINE {self.rip}!")
            else:
                return True
        elif re.match(fr'^{PM.NUMBER_REPRESENTATION_PATTERN}$', expression):
            return True
        return False
    
    def is_constant(self, expression: str) -> bool:
        """
        Verifies if a given expression is a constant

        :param expression: Expression in verification
        :type expression: str
        :return: True if the expression is a constant
        :rtype: bool
        """
        if expression in self.constants:
            return True
        return False
    
    def is_immediate_value(self, expression: str) -> bool:
        """
        Verifies if a given expression is an immediate value

        :param expression: Expression in verification
        :type expression: str
        :return: True if the expression is an immediate value
        :rtype: bool
        """
        if re.match(fr'^{PM.IMMEDIATE_VALUE_PATTERN}$', expression):
            return True
        return False
    
    def is_valid_line_for_constant(self, line: int) -> bool:
        """
        Verifies if a constant was declared before the current line being executed
        
        :param line: Line of the declaration of the constant
        :type line: int
        :return: True if the current line is bigger than line, False otherwise
        :rtype: bool
        """
        return self.rip > line
    
    #----------------------------------------------
    # Operand and expressions calculation methods
    #----------------------------------------------

    def parse_operand_info(self, op_info: list[str]) -> None:
        """
        Attributes the size and expression value of each operand to the respective instances of this class.\n
        If comes across a non declared size and there are no registers in the instruction raises SyntaxError. If any of the expressions for the operands are not set raises ValueError

        :param op_info: List with the size and expression of each operand as a pair in the format: [size;op2;size;op1]
        :type op_info: list[str]
        :raises SyntaxError: If comes across undeclared sizes with out registers in the instruction.
        :raises ValueError: If any of the operand expressions are not set.
        """
        has_op2 = op_info[1] != ""

        # Fail safe verification: op1 must always be set. op2's expression is only required if op2 exists.
        if op_info[3] == "":
            raise ValueError("Program parsing ran into a problem! Aborting execution ...")

        # Resolve op1's size if missing
        if op_info[2] == "":
            if self.is_register(op_info[3]):
                try:
                    op_info[2] = str(self.get_register_size(op_info[3]))
                except SyntaxError as e:
                    print(e)
                    sys.exit(ExitCode.INVALID_INSTRUCTION_SYNTAX)
            elif has_op2 and op_info[0] != "":
                # No size and not a register: infer from op2's size if available
                op_info[2] = op_info[0]
            else:
                raise SyntaxError(f"INVALID SYNTAX FORMAT AT LINE {self.rip}!")

        # Resolve op2's size if missing (only relevant if op2 exists)
        if has_op2 and op_info[0] == "":
            if self.is_register(op_info[1]):
                try:
                    op_info[0] = str(self.get_register_size(op_info[1]))
                except SyntaxError as e:
                    print(e)
                    sys.exit(ExitCode.INVALID_INSTRUCTION_SYNTAX)
            elif op_info[2] != "":
                # No size and not a register: infer from op1's size
                op_info[0] = op_info[2]
            else:
                raise SyntaxError(f"INVALID SYNTAX FORMAT AT LINE {self.rip}!")

        # Needs updating as setting logic has changed
        self.set_operand("op1", op_info[3], int(op_info[2]))
        if has_op2:
            self.set_operand("op2", op_info[1], int(op_info[0]))
    
    def calculate_memory_address(self, expression: str) -> int:
        """
        Calculates the address value of a memory addressing operand expression
        
        :param expression: Full operand expression to calculate
        :type expression: str
        :return: Address value of the expression
        :rtype: int
        """
        new_expression: str = expression.replace(" ", "").replace("[", "").replace("]", "")
        components: list[str] = re.split(r'([\+\-\*])', new_expression)
        try:
            parsed_address_expression: list[str] = self.parse_address_expression(components, expression)
        except ValueError as e:
            print(e)
            sys.exit(ExitCode.INVALID_INSTRUCTION_SYNTAX)
        return self.get_address_value(parsed_address_expression, expression)

    def parse_address_expression(self, components: list[str], expression: str) -> list[str]:
        """
        Returns a parsed list equivalent to the one given but with all labels and constants substituted by their address (labels) or values (constants)

        :param components: Operand declaration in an instruction to be parsed to integer values
        :type components: list[str]
        :param expression: Expression for the memory operand to calculate the address
        :type expression: str
        :return: Parsed list with integer representation of labels addresses and constants values
        :rtype: list[str]
        :raises ValueError: If an invalid label is found in the expression or if the memory addressing mode is invalid
        """

        ret: list[str] = []

        for element in components:
            if re.match(PM.GENERAL_PURPOSE_REGISTERS_PATTERN, element):
                register_value: str = str(self.registers.read_reg(element))
                ret.append(register_value)
            elif re.match(PM.FPU_REGISTERS_PATTERN, element):
                ### NOT CURRENTLY ACTIVE
                pass
            elif re.match(PM.CONSTANTS_AND_LABELS_PATTERN, element):
                if Segment_Mapper._exists_in_section(element, self.data_section) or Segment_Mapper._exists_in_section(element, self.rodata_section) or Segment_Mapper._exists_in_section(element, self.bss_section):
                    try:
                        label_address: str = str(self.get_label_address(element))
                        ret.append(label_address)
                    except ValueError as e:
                        raise ValueError(e)
                elif Segment_Mapper._exists_in_section(element, self.constants):
                    if not self.is_valid_line_for_constant(int(self.constants[element]['line'])):
                        raise ValueError(f"Constant {element} is not yet defined")
                    constant_value: str = str(self.get_encoded_value(self.constants[element]['value']))
                    ret.append(constant_value)
                else:
                    raise ValueError(f"INVALID LABEL {element} IN MEMORY ADDRESSING MODE {expression} AT LINE {self.rip}!")
            else:
                ret.append(element)
        return ret        

    def verify_multiplication(self, components: list[str], expression: str) -> list[int]:
        """
        Verifies if an operand instruction as a multiplication in its declaration.
        If so calculates it and verifies its correctness.\n
        Returns a list with 2 elements: 1º - Result of the calculation; 2º - Index of the first element used in the calculation (if -1 no calculation was made) 
        
        :param components: Elements of an operand declaration in an instruction
        :type components: list[str]
        :param expression: Expression of a memory addressing operand 
        :type expression: str
        :return: Partial calculation of the address and the index of the first element used in the calculation (will use always 3 followed indexes). Only multiplications calculated.
        :rtype: list[int]
        :raises ValueError: If a multiplication is detected but can't be calculated due to bad syntax
        """
        if Control_Unit.has_symbol(components, '*'):
            try:
                mult_index: int = Control_Unit.get_index_of(components, '*', 1)[0]
            except ValueError:
                print(f"INVALID EXPRESSION {expression} IN MEMORY ADDRESSING MODE AT LINE {self.rip}!")
                sys.exit(...)   # To be determined
            if mult_index != 0 and mult_index != len(components)-1:
                try:
                    return [int(components[mult_index-1]) * int(components[mult_index+1]), mult_index-1]
                except ValueError as e:
                    print(f"{e}")
                    sys.exit(...)   # To be determined
            else:
                raise ValueError(f"INVALID EXPRESSION {expression} IN MEMORY ADDRESSING MODE AT LINE {self.rip}!")
        else:
            return [0,-1]
    
    # -----------------------
    # STATIC HELPERS 
    # -----------------------

    @staticmethod
    def is_register(expression: str) -> bool:
        """
        Verifies if a given expression is a register

        :param expression: Expression in verification
        :type expression: str
        :return: True if the expression is a register
        :rtype: bool
        """
        if re.match(fr'^{PM.REGISTER_PATTERN}$', expression):
            return True
        return False

    @staticmethod
    def has_symbol(list: list[str], symbol: str) -> bool:
        """
        Verifies if a multiplication exists in a operand expression
        
        :param list: List of string elements
        :type list: list[str]
        :param symbol: character/element to search for
        :type symbol: str
        :return: True if a match was found, False if it wasn't
        :rtype: bool
        """
        for element in list:
            if element == symbol:
                return True
        return False
    
    @staticmethod
    def get_index_of(list: list[str], symbol: str, count: int) -> list[int]:
        """
        Returns the indexes of the occurrences of symbol in a given list of strings.\n
        If the return length does not match the count of indexes desired raises ValueError, else returns the list
        
        :param list: List of string elements 
        :type list: list[str]
        :param symbol: character/element to search for
        :type symbol: str
        :param count: Number of desired occurrences of the symbol on the list.
        :type count: int
        :return: List of the indexes of those occurrences
        :rtype: list[int]
        :raises ValueError: If the occurrence count and the length of the list do not match
        """
        ret: list[int] = []

        for i in range(len(list)):
            if list[i] == symbol:
                ret.append(i)
        
        if len(ret) != count:
            raise ValueError
        else:
            return ret

    @staticmethod
    def get_new_list(list: list[str], index: int, count: int) -> list[str]:
        """
        Returns a new list based on a given one without a given number of followed elements of that base list given by the first index of the sequence.
        
        :param list: List of string elements 
        :type list: list[str]
        :param index: Index of the first element to remove
        :type index: int
        :param count: Number of times to remove the element at index
        :type count: int
        :return: A new list without count elements starting at position index
        :rtype: list[str]
        """
        new_list: list[str] = list.copy()
        for _ in range(count):
            new_list.pop(index)
        return new_list
    
    @staticmethod
    def calculate_list(list: list[str]) -> int:
        """
        Calculates the value of a mathematic expression in list elements.\n
        Expects the elements to start on a digit and alternate between a addition or subtraction operator and a number.
        Raises ValueError if ths syntax is not followed
        
        :param list: List of string elements to calculate the value of 
        :type list: list[str]
        :return: Result of the mathematical expression on this list
        :rtype: int
        :raises ValueError: If no operation symbol is found on a given odd index of the list or if an even index of the list do not point to a digit
        """
        try:
            result: int = int(list[0])

            for i in range(1, len(list), 2):
                operator: str = list[i]
                value: int = int(list[i+1])

                if operator == "+":
                    result += value
                elif operator == "-":
                    result -= value
                else:
                    raise ValueError
                
            return result
        except ValueError, IndexError:
            raise ValueError