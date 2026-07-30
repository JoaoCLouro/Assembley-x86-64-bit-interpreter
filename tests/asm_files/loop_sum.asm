; Loop test: sums 1..5 using a conditional jump (jle) and cmp.
; Expected final state (before exit clobbers rax):
;   rcx = 6      (loop counter incremented past 5)
;   rbx = 15     (1+2+3+4+5, accumulator)

section .text
    global _start

_start:
    mov rbx, 0      ; accumulator
    mov rcx, 1      ; counter

loop_start:
    cmp rcx, 5
    jg loop_end

    add rbx, rcx
    inc rcx
    jmp loop_start

loop_end:
    mov rax, 60
    xor rdi, rdi
    syscall
