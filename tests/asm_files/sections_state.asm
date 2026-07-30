; Sections test: .data, .rodata, .bss variables, verified both via
; register loads AND via get_state("data"/"rodata"/"bss") reading memory
; directly.
;
; Expected memory state:
;   .data:   counter = 42, flag = 1
;   .rodata: max_val = 100
;   .bss:    buffer reserved (5 dd slots), untouched -> 0
;            scratch reserved (1 dq slot), written with 7 during execution
;
; Expected final register state (before exit clobbers rax):
;   r8  = 42     (loaded from counter)
;   r9  = 1      (loaded from flag)
;   r10 = 100    (loaded from max_val)
;   r11 = 7      (loaded back from scratch after being written)

section .data
    counter: dd 42
    flag: dd 1

section .rodata
    max_val: dd 100

section .bss
    buffer: times 5 dd 0
    scratch: times 1 dq 0

section .text
    global _start

_start:
    mov r8d, [counter]
    mov r9d, [flag]
    mov r10d, [max_val]

    mov qword [scratch], 7
    mov r11, [scratch]

    mov rax, 60
    xor rdi, rdi
    syscall
