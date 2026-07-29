#ifndef SYSCALL_H
#define SYSCALL_H

#include <stdint.h>
#include <stddef.h>

// Compilation command: gcc -O3 -shared -o libscl.so -fPIC syscall.c

/**
 * @brief Performs a real host read from a simulated file descriptor (0/1/2).
 * * Reads up to `size` bytes from the real stream mapped to `fd` (stdin/stdout/stderr)
 * * into `buffer`. `buffer` is a plain host-allocated byte array, NOT a simulated
 * * memory address — the Python side is responsible for copying the result into
 * * simulated memory afterwards.
 * @param fd Simulated file descriptor (0 = stdin, 1 = stdout, 2 = stderr)
 * @param buffer Host buffer to read into, must be at least `size` bytes
 * @param size Number of bytes to read
 * @return Number of bytes actually read, or -1 on error / unsupported fd
 * @warning fd must be validated by the caller; only 0/1/2 are currently supported
 */
int64_t sys_read(int fd, uint8_t *buffer, size_t size);

/**
 * @brief Performs a real host write to a simulated file descriptor (0/1/2).
 * * Writes `size` bytes from `buffer` to the real stream mapped to `fd`
 * * (stdin/stdout/stderr). `buffer` is a plain host-allocated byte array that
 * * the Python side has already populated from simulated memory.
 * @param fd Simulated file descriptor (0 = stdin, 1 = stdout, 2 = stderr)
 * @param buffer Host buffer to write from, must contain at least `size` bytes
 * @param size Number of bytes to write
 * @return Number of bytes actually written, or -1 on error / unsupported fd
 * @warning fd must be validated by the caller; only 0/1/2 are currently supported
 */
int64_t sys_write(int fd, const uint8_t *buffer, size_t size);

// To complete with more syscalls

#endif // SYSCALL_H