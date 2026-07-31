section .data
    msg: db "hi"
    exit: equ 60

section .text
    global _start

_start:
    mov rax, exit
    xor rdi, rdi
    syscall