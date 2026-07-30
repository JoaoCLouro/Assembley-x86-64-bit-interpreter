; Basic ALU test: arithmetic + bitwise ops, no memory.
; Expected final state (registers) BEFORE the exit syscall clobbers rax/rdi:
;   rax = 15   (5 + 10)
;   rbx = 4    (10 - 6)
;   rcx = 12   (0b1010 XOR 0b0110 = 0b1100)
;   rdx = 2    (0b1010 AND 0b0110 = 0b0010)
;   r8  = 14   (0b1010 OR  0b0110 = 0b1110)
;   r9  = 6    (5 + 1, via inc)
;   r10 = 4    (5 - 1, via dec)
;
; NOTE: rax and rdi are reused right before exit to stage the syscall
; (rax=60, rdi=0), so the interpreter's post-run state for rax/rdi will
; be 60/0, NOT 15/<unset>. Tests should assert on rbx/rcx/rdx/r8/r9/r10
; for the ALU results, and separately assert rax==60 to confirm the
; exit syscall executed.

section .text
    global _start

_start:
    mov rax, 5
    add rax, 10

    mov rbx, 10
    sub rbx, 6

    mov rcx, 10
    xor rcx, 6

    mov rdx, 10
    and rdx, 6

    mov r8, 10
    or r8, 6

    mov r9, 5
    inc r9

    mov r10, 5
    dec r10

    mov rax, 60
    xor rdi, rdi
    syscall
