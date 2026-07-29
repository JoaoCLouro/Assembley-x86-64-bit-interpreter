#ifndef SYSCALL
#define SYSCALL

#include <stdint.h>
#include <stddef.h>

// Compilation command: gcc -O3 -shared -o libscl.so -fPIC syscall.c 


/**
 * @brief Defines the read syscall.
 * * Takes a stream indicator, a buffer reference to read to and a number of bytes to read indicator
 * * All values are assumed to be correct and previously validated
 * @param stream Reference to the indicator of the source to read from
 * @param buffer Reference to the buffer to read to
 * @param size Number of bytes to read
 * @warning All parameters must be previously validated as they are assume to be valid 
 */
void read(void* stream, void* buffer, size_t size);

/**
 * @brief Defines the write syscall.
 * * Takes a stream indicator, a buffer reference to write from and a number of bytes to write indicator
 * * All values are assumed to be correct and previously validated
 * @param stream Reference to the indicator of the source to read from
 * @param buffer Reference to the buffer to write from
 * @param size Number of bytes to write
 * @warning All parameters must be previously validated as they are assume to be valid 
 */
void* write(void* stream, void* buffer, size_t size);

// To Complete with more syscalls

#endif // SYSCALL