; Stack / call-ret test.
; add_five: adds 5 to rdi's value, returns result in rax via the stack
; (result also left in rax at the end for simple assertion).
;
; Expected final state (before exit clobbers rax):
;   rbx = 17     (result of add_five(12) = 12 + 5)
;   rax = 17     (same value, still in rax right after ret, until reused for exit)

section .text
    global _start

_start:
    mov rdi, 12
    call add_five
    mov rbx, rax    ; save result before rax gets reused for exit

    mov rax, 60
    xor rdi, rdi
    syscall

add_five:
    push rbp
    mov rbp, rsp

    mov rax, rdi
    add rax, 5

    mov rsp, rbp
    pop rbp
    ret
