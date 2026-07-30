; Syscall test: write(1, msg, len) to stdout, then exit(0).
; This test is verified by capturing stdout (e.g. via monkeypatch on
; sys.stdout / os.write, or by redirecting fd 1) rather than by
; register/memory state alone, since the point is exercising the real
; write() syscall path.
;
; Expected behavior:
;   - stdout receives exactly "hi\n" (3 bytes)
;   - rax = 3 immediately after the write syscall (bytes written)
;   - process exits cleanly afterward (exit syscall, rax=60)

section .data
    msg: db "hi", 0x0a
    msg_len equ: 3

section .text
    global _start

_start:
    mov rax, 1          ; sys_write
    mov rdi, 1          ; fd = stdout
    mov rsi, msg
    mov rdx, msg_len
    syscall             ; rax now holds bytes written (expect 3)

    mov r8, rax         ; preserve write() return value before exit clobbers rax

    mov rax, 60
    xor rdi, rdi
    syscall
