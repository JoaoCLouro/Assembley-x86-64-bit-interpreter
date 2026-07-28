# Assembly x86-64 Language Specification

This document defines the supported x86-64 Assembly subset, syntax constraints, preprocessing rules, memory alignment, and execution behavior for the interpreter.

---

## 1. Syntax & Preprocessing Rules

The interpreter parses `.asm` files adhering to **Intel Assembly Syntax**.

### 1.1 Operand Expression Formatting
* **No Whitespace in Complex Operands:** Address arithmetic or multi-component expressions must not contain spaces between operators and terms.
  * **Valid:** `[rbx+4*1]`, `CONSTANT+4`, `[rsp+8]`
  * **Invalid:** `[rbx + 4 * 1]`, `CONSTANT + 4`
* **Immediate Value Simplification:** All immediate numerical expressions must be pre-simplified to a single constant. Nested arithmetic expressions in instruction operands are strictly prohibited.
  * **Valid:** `58`
  * **Invalid:** `((4+3+1)*4 + 6 + (7 + 8)*2)`
* **Integer Constraints:** Immediates for general-purpose registers must be integer values (decimal, hexadecimal `0x...`, or binary `...b`). Floating-point literals are not permitted for standard ALU instructions.
  * **Valid:** `mov eax, 3`
  * **Invalid:** `mov eax, 3.14`

---

## 2. Program Sections

Assembly programs are parsed in two phases: **Phase 1 (Mapping)** validates section structures and symbol tables; **Phase 2 (Execution)** interprets instructions sequentially.

* **`.text`**: Executable instruction section. Must contain a valid entry label (e.g., `_start:`).
* **`.data`**: Initialized readable and writable memory variables.
* **`.rodata`**: Initialized read-only constants.
* **`.bss`**: Block Started by Symbol — reserved memory for uninitialized data.

---

## 3. Directives & Constants

### 3.1 Constant Declarations
Constants defined via `equ` or `#define` are resolved during Phase 1 parsing:

* **Standard Declarations:**
  ```asm
  MAX_SIZE equ: 100
  BUFFER_LEN equ: $-buffer
  ```
* **String & Character Constants:**
  ```asm
  CHAR_A equ: 'A'
  MSG equ: "Hello, World!"
  ```
* **C-Style Definitions:**
  ```asm
  #define BUFFER_SIZE 256
  ```

### 3.2 The `times` Directive

The `times directive is supported in .(ro)data and .bss sictions to declare repeated data buffers:

```asm
; Syntax: <label>: times <count> <size_specifier> <init_value>
buffer: times 10 db 0
array: times 5 dd 0x01
```

#### Supported Sixe Specifiers:
- `db` - Byte
- `dw` - Word
- `dd` - Double Word
- `dq` - Quad Word

---

## 4. Hardware State & Data Layout
Hardware state (registers and virtual memory) is managed in C shared libraries (`libreg.so` and `libmmu.so`) accessed via Python `ctypes` bindings (`interpreter/_src/bridges/`).

### 4.1 Register File

* 64-bit General Purpose Registers: rax, rbx, rcx, rdx, rsi, rdi, rbp, rsp, r8–r15.
* Sub-Register Mapping: Writes to sub-registers modify the corresponding sub-slice of the 64-bit parent register:
    - 32-bit: eax, ebx, ecx, edx, etc.
    - 16-bit: ax, bx, cx, dx, etc.
    - 8-bit Low/High: al/ah, bl/bh, cl/ch, dl/dh, dil, sil, bpl, spl.
* FPU Registers: Floating-point unit register set.
* EFLAGS Register: Maintained during operation execution in C (operations.c).
    - ZF (Zero Flag)
    - PF (Parity Flag)
    - CF (Carry Flag)
    - SF (Sign Flag)
    - OF (Overflow Flag)
    - TF (Trap Flag — reserved for step-by-step debugging)

### 4.2 Memory Representation & Endianness

* Virtual Memory: Implemented as a 4-level page table system in interpreter/_src/execution/src/memory_eng.c.
* Little-Endian Format: Byte sequences are written and read in Little-Endian order.
    - Example: Writing integer 0x1234 (4 bytes) places byte 0x34 at the base target address, followed by 0x12, 0x00, 0x00 at higher contiguous addresses.
* Stack: Grows downward from higher virtual addresses managed via rsp.

---

## 5. Functional Units (FUs) & Instruction Routing

The `control_unit.py` fetches and decodes instructions, dispatching operands to dedicated Functional Units in `interpreter/_src/FUs/`:

* ALU (`alu.py`): Arithmetic (`add`, `sub`, `inc`, `dec`), bitwise logic (`xor`, `and`, `or`), comparisons (`cmp`)
* FPU (`fpu.py`): Floating-point calculation and register operations.
* Data Path (`data_path.py`): Stack control (`push`, `pop`), data transfer (`mov`) and program counter manipulation (jumps, call, ret).

---

## 6. Exit Status Code Reference

The simulator halts and emits standardized status codes upon completion or error detection:

| Code | Enum Constant | Description |
| :--- | :--- | :--- |
| **0** | *Implicit* | Successful execution and exit. |
| **-1** | `DATA_FORMAT_ERROR` | Unsuccessful exit due to incorrect `.data`/`.rodata` format detected in the parsing phase. |
| **-2** | `BSS_FORMAT_ERROR` | Unsuccessful exit due to incorrect `.bss` format detected in the parsing phase. |
| **-3** | `CONSTANT_DECLARATION_ERROR` | Unsuccessful exit due to an incorrect constant declaration format. |
| **1** | `NO_START_LABEL` | Unsuccessful exit due to not finding an entry point to the program during `.text` parsing. |
| **2** | `DUPLICATE_LABEL` | Unsuccessful exit due to a duplicated label declaration found during `.text` parsing. |
| **4** | `UNOPENABLE_FILE` | Unsuccessful exit because the target file could not be opened or read. |
| **5** | `STACK_OVERFLOW` | Unsuccessful exit due to a detected stack overflow (stack exceeds its allowed size). |
| **10** | `INVALID_INSTRUCTION_SYNTAX` | Unsuccessful exit due to a syntax error in an instruction during parsing. |
| **11** | `RESERVED_KEYWORD_VIOLATION` | Unsuccessful exit due to conflict in label declaration with a reserved keyword |
| **109101** | `SOFTWARE_ERROR` | Unsuccessful exit due to an internal software bug (ASCII representation of "me"). |