#include "../include/operations.h"


// --------------------------------------------------------------------------------
// Structures implementations
// --------------------------------------------------------------------------------

// Structure for each alu operand's necessary info
typedef struct Operand{
    long long address;  // virtual address for memory or index for registers
    OpType op_type;
    uint8_t size;       // 1,2,4,8
    uint8_t is_high;
    uint8_t is_signed;  // only for registers
} Operand;

// To be implemented a fpu operand struct

// Structure for all necessary instruction info
struct Info {
    CPURegs* registers;
    Table* table;
    unsigned long long res_value;
    unsigned long long op1_value;
    unsigned long long op2_value;
    Operand op1;
    Operand op2;
    Operand result;
    Opcode opcode;
};

// --------------------------------------------------------------------------------
// Prototypes
// --------------------------------------------------------------------------------
static void set_operands_values(Info* s);
static unsigned long long get_operand_value(Info* s, Operand* op);
static void exec_cmp(Info *s); 
static void exec_add(Info *s); 
static void exec_adc(Info *s);
static void exec_sub(Info *s); 
static void exec_sbb(Info *s); 
static void exec_inc(Info *s);
static void exec_dec(Info *s); 
static void exec_and(Info *s); static void exec_or(Info *s);
static void exec_xor(Info *s); 
static void exec_not(Info *s); 
static void exec_neg(Info *s);
static void exec_xchg(Info *s);
static void set_result_info(Info *current_state);
static void commit_operand (Info* current_instruction_state, Operand* op, long long value);

// --------------------------------------------------------------------------------
// Lookup Table
// --------------------------------------------------------------------------------

// Instructions link struct
// Typedef for instruction handler function pointers
typedef void (*InstructionHandler)(Info*);

// Direct O(1) indexed lookup table
const InstructionHandler dispatch_table[OP_COUNT] = {
    // Data Path
    [OP_CMP]  = exec_cmp,
    // ALU
    [OP_ADD]  = exec_add,
    [OP_ADC]  = exec_adc,
    [OP_SUB]  = exec_sub,
    [OP_SBB]  = exec_sbb,
    [OP_INC]  = exec_inc,
    [OP_DEC]  = exec_dec,
    [OP_AND]  = exec_and,
    [OP_OR]   = exec_or,
    [OP_XOR]  = exec_xor,
    [OP_NOT]  = exec_not,
    [OP_NEG]  = exec_neg,
    [OP_XCHG] = exec_xchg,
    [OP_MUL]  = exec_mult,
    [OP_IMUL] = exec_imult,
    [OP_DIV]  = exec_div,
    [OP_IDIV] = exec_idiv,
    [OP_SHL]  = exec_shl,
    [OP_SAL]  = exec_sal,
    [OP_SHR]  = exec_shr,
    [OP_SAR]  = exec_sar,
    [OP_ROL]  = exec_rol,
    [OP_RCL]  = exec_rcl,
    [OP_ROR]  = exec_ror,
    [OP_RCR]  = exec_rcr

    // FPU
};


// --------------------------------------------------------------------------------
// Operand fetching, setting and cleaning functions
// --------------------------------------------------------------------------------

// -------------------
// Operand state init
// -------------------

Info* create_operand_state ()
{
    Info *op_state = (Info*)calloc(1, sizeof(Info));

    if (op_state == NULL)
    {
        printf("Operand table creation error. NULL pointer was achieved!\n");
        return NULL;
    }
    return op_state;
}

void free_operand_state (Info* s)
{
    if (s) free(s);
}

// ----------------------------
// Info setters
// ----------------------------

void set_operand_info (Info *current_instruction_state, char *operand, long long address, uint8_t size, uint8_t op_type, uint8_t is_high, uint8_t is_signed)
{
    if (operand != NULL && strcmp(operand, "op1") == 0 )
    {
        current_instruction_state->op1.address = address;
        current_instruction_state->op1.size = size;
        current_instruction_state->op1.op_type = op_type;
        current_instruction_state->op1.is_high = is_high;
        current_instruction_state->op1.is_signed = is_signed;
    } else
    {
        current_instruction_state->op2.address = address;
        current_instruction_state->op2.size = size;
        current_instruction_state->op2.op_type = op_type;
        current_instruction_state->op2.is_high = is_high;
        current_instruction_state->op2.is_signed = is_signed;
    }
}

void set_instruction (Info *current_instruction_state, uint8_t instruction)
{
    current_instruction_state->opcode = instruction;
}

void set_registers_ref (Info *current_state, CPURegs *r)
{
    current_state->registers = r;
}

void set_table_ref (Info *current_state, Table *t)
{
    current_state->table = t;
}

/**
 * @brief Commits the result of an operation to the appropriate destination (memory or register) based on the operand type.
 * * This function is called after an operation has been executed and the result is ready to be stored.
 * @param current_instruction_state Pointer to the Info structure holding all operand, instruction, registers and results info
 * @param op Pointer to the Operand structure that holds the destination information (address, type, size, etc.)
 * @param value The result value to be committed to the destination
 * @warning This function assumes that the operand type is either "memory" or "register". If the operand type is unknown, an error message will be printed.
 */
static void commit_operand (Info *current_instruction_state, Operand *op, long long value)
{
    if (op->op_type == OP_MEMORY) {
        write_mem(current_instruction_state->table, op->address, (uint8_t*)&value, op->size, 1);
    } else if (op->op_type == OP_REGISTER) {
        write_reg(current_instruction_state->registers, op->address, value, op->size, op->is_high);
    }
    else
    {
        printf("Error: Unknown operand type %d\n", (uint8_t)op->op_type);
    }
}

// -------------------
// Cleaners
// -------------------


void clean(Info *s) {
    memset(&s->op1, 0, sizeof(Operand));
    memset(&s->op2, 0, sizeof(Operand));
    memset(&s->result, 0, sizeof(Operand));
    s->opcode = OP_NULL;
    s->res_value = 0;
    s->op1_value = 0;
    s->op2_value = 0;
}

//--------------------------------
// Instruction execution functions
//--------------------------------

void dispatch(Info *s)
{
    Opcode op = s->opcode; 

    // Failsafe verification. Python calls should always make sure this is not triggered
    if (op < 0 || op >= OP_COUNT || dispatch_table[op] == NULL)
    {
        printf("Error: invalid or unimplemented opcode (%d)\n", (int)op);
        clean(s);
        return;
    }
    
    set_result_info(s);
    set_operands_values(s);

    uint8_t no_overwrite = op == OP_XCHG || op == OP_CMP;
    dispatch_table[op](s);
    if (!no_overwrite)
    {
        commit_operand(s, &s->result, s->res_value);
    }
    clean(s);
    return;
}

// --------------
// Result setter
// --------------

/**
 * @brief Sets the information about the result based on the operators info.
 * * Leaves the result value non altered to be set by the operation called.
 * 
 * @param current_state Pointer to the Info structure holding all operand, instruction result and registers info
 */
static void set_result_info (Info *current_state)
{
    current_state->result.op_type = current_state->op1.op_type;
    current_state->result.size = current_state->op1.size;
    current_state->result.address = current_state->op1.address;
    current_state->result.is_high = current_state->op1.is_high;
    current_state->result.is_signed = current_state->op1.is_signed;
}


//----------------------
// Data Path Functions
//----------------------

/**
 * @brief Universal function to update the flags after an operation based on the result of the operation and the operands info.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @param result The result of the operation of the two operands, used to set the flags
 */
static void flags_update(Info *s, unsigned long long result)
{
    int bit_count = 8 * s->op1.size;
    int msb_mask = bit_count - 1;
    
    unsigned long long bits_mask = (bit_count >= 64) ? 0xFFFFFFFFFFFFFFFFULL : (1ULL << bit_count) - 1;
    unsigned long long res_msb = result & bits_mask;

    // Arithmetic flags
    uint8_t zero = (uint8_t) (res_msb == 0);
    uint8_t sign = (uint8_t) ((res_msb >> (bit_count - 1)) & 1);

    // Logical flags
    uint8_t carry;
    if (bit_count >= 64) {
    
        switch (s->opcode) {
            case OP_ADD:
            case OP_ADC:
                carry = (uint8_t) (result < s->op1_value);
                break;
            case OP_SUB:
            case OP_SBB:
            case OP_CMP:
                carry = (uint8_t) (s->op1_value < s->op2_value);
                break;
            default:
                carry = 0;
        }
    } else {
        carry = (uint8_t) ((result >> bit_count) & 1);
    }

    uint8_t overflow;
    switch (s->opcode) {
        case OP_ADD:
        case OP_ADC:
            // Addition overflow: operands have the SAME sign, but the
            // result's sign differs from theirs.
            overflow = (uint8_t) (((s->op1_value ^ result) & (s->op2_value ^ result)) >> msb_mask & 1);
            break;
        case OP_SUB:
        case OP_SBB:
        case OP_CMP:
            // Subtraction overflow: operands have DIFFERENT signs, and
            // the result's sign differs from op1's sign.
            overflow = (uint8_t) (((s->op1_value ^ s->op2_value) & (s->op1_value ^ result)) >> msb_mask & 1);
            break;
        default:
            overflow = 0;
    }

    // More flags can be later implemented as needed

    // Preserving the state of the trap flag as it is not affected by the operations
    uint8_t trap = (uint8_t) read_trap_flag(s->registers);

    uint32_t rflags_value = (carry << 0) | (zero << 6) | (sign << 7) | (overflow << 11) | (trap << 8);
    write_rflags(s->registers, rflags_value);
}

// -----------------
// Value fetching
// -----------------

/**
 * @brief Automatically fetches and stores the resolved values for both instruction operands.
 * 
 * Evaluates s->op1 and s->op2, saving the extracted values directly into
 * s->op1_value and s->op2_value respectively.
 * 
 * @param s   Pointer to the current instruction Info execution context.
 */
static void set_operands_values(Info *s)
{
    if (!s) return;

    // Automatically resolve and set both operand values inside the Info struct
    s->op1_value = get_operand_value(s, &s->op1);
    s->op2_value = get_operand_value(s, &s->op2);
}

/**
 * @brief Reads and returns the masked unsigned 64-bit value for a single operand.
 * 
 * Determines whether to read from memory or registers based on op->op_type,
 * and masks off unused upper bits according to op->size.
 * 
 * @param s   Pointer to the current instruction Info execution context.
 * @param op  Pointer to the Operand struct to evaluate.
 * @return    The resolved 64-bit unsigned integer value.
 */
static unsigned long long get_operand_value(Info *s, Operand *op)
{
    if (!s || !op) return 0ULL;

    unsigned long long value = 0ULL;

    switch (op->op_type) 
    {
        case OP_MEMORY:
            // Fetch value from memory table
            read_mem(s->table, op->address, (uint8_t*)&value, op->size);
            break;

        case OP_REGISTER:
            // Fetch value from CPU registers 
            switch (op->size)
            {
                case 1:
                    value = (unsigned long long) read_1b_reg(s->registers, op->address, op->is_high);
                    break;
                case 2:
                    value = (unsigned long long)  read_2b_reg(s->registers, op->address);
                    break;
                case 4:
                    value = (unsigned long long)  read_4b_reg(s->registers, op->address);
                    break;
                case 8:
                    value = (unsigned long long)  read_8b_reg(s->registers, op->address);
                    break;
                default:
                    value = 0;
            }
            break;

        default:
            // Immediate
            value = op->address;
    }

    // Zero-extend/mask value to guarantee upper bits above op->size are clean
    if (op->size < 8 && op->size > 0) {
        unsigned long long mask = (1ULL << (op->size * 8)) - 1ULL;
        value &= mask;
    }

    return value;
}


// ----------------------------
// Main Flux Control function
// ----------------------------

/**
 * @brief Executes the compare instruction, which is a subtraction that only updates the flags and does not store the result.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the subtraction is not stored, only the flags are updated based on the result of the operation
 */
static void exec_cmp(Info *s)
{
    // Need cmp syntax rules check
    unsigned long long result = (unsigned long long) s->op1_value - s->op2_value;
    // Sets flags based on the result
    flags_update(s, result);
}

//----------------------
// ALU Functions
//----------------------

/**
 * @brief Executes non carried addition
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the addition is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_add(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1_value + s->op2_value;
    flags_update(s, result);
    s->res_value = (long long) result;
}

/**
 * @brief Executes carried addition 
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the addition is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_adc(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1_value + s->op2_value + read_carry_flag(s->registers);
    flags_update(s, result);
    s->res_value = (long long) result;
}

/**
 * @brief Executes non carried subtraction
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the subtraction is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_sub(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1_value - s->op2_value;
    flags_update(s, result);
    s->res_value = (long long) result;
}

/**
 * @brief Executes carried subtraction
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the subtraction is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_sbb(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1_value - s->op2_value - read_carry_flag(s->registers);
    flags_update(s, result);
    s->res_value = (long long) result;
}

/**
 * @brief Executes the increment instruction, which adds 1 to the operand and updates the flags based on the result.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the increment is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_inc(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1_value + 1;
    flags_update(s, result);
    s->res_value = (long long) result;
}

/**
 * @brief Executes the decrement instruction, which subtracts 1 from the operand and updates the flags based on the result.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the decrement is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_dec(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1_value - 1;
    flags_update(s, result);
    s->res_value = (long long) result;
}

/**
 * @brief Executes the bitwise AND instruction, which performs a bitwise AND operation between the two operands and updates the flags based on the result.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the AND operation is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_and(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1_value & s->op2_value;
    flags_update(s, result);
    s->res_value = (long long) result;
}

/**
 * @brief Executes the bitwise OR instruction, which performs a bitwise OR operation between the two operands and updates the flags based on the result.
 *  
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the OR operation is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_or(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1_value | s->op2_value;
    flags_update(s, result);
    s->res_value = (long long) result;
}

/**
 * @brief Executes the bitwise XOR instruction, which performs a bitwise XOR operation between the two operands and updates the flags based on the result.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the XOR operation is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_xor(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1_value ^ s->op2_value;
    flags_update(s, result);
    s->res_value = (long long) result;
}

/**
 * @brief Executes the bitwise NOT instruction, which performs a bitwise NOT operation on the operand and updates the flags based on the result.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the NOT operation is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_not(Info *s)
{
    unsigned long long result = (unsigned long long) ~s->op1_value;
    flags_update(s, result);
    s->res_value = (long long) result;
}

/**
 * @brief Executes the NEG instruction, which negates the operand and updates the flags based on the result.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the NEG operation is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_neg(Info *s)
{
    unsigned long long result = (unsigned long long) -s->op1_value;
    flags_update(s, result);
    s->res_value = (long long) result;
}

/**
 * @brief Executes the XCHG instruction, which exchanges the values of the two operands without updating the flags.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the XCHG operation is stored in the op1 and op2 fields of the Info structure and the flags are not updated based on the result of the operation
 */
static void exec_xchg(Info *s)
{
    // Fetches each value
    long long val1 = s->op1_value;
    long long val2 = s->op2_value;
    // commits each value
    commit_operand(s, &s->op1, val2);
    commit_operand(s, &s->op2, val1);
}

static void exec_mult(Info *s){}

static void exec_imult(Info *s) {}

static void exec_div(Info *s) {}

static void exec_idiv(Info *s) {}

static void exec_shl(Info *s) {}

static void exec_sal(Info * s) {}

static void exec_shr(Info *s) {}

static void exec_sar(Info * s) {}

static void exec_rol(Info *s) {}

static void exec_rcl(Info * s) {}

static void exec_ror(Info *s) {}

static void exec_rcr(Info * s) {}