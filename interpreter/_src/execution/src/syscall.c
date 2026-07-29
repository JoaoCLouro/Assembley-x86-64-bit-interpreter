#include "../include/syscall.h"

#include <stdint.h>
#include <stddef.h>
#include <stdio.h>

// Maps a simulated fd (0/1/2) to the real host stream.
// Returns NULL if the fd is not supported.
static FILE* resolve_stream(int fd)
{
    switch (fd)
    {
        case 0: return stdin;
        case 1: return stdout;
        case 2: return stderr;
        default: return NULL;
    }
}

int64_t sys_read(int fd, uint8_t *buffer, size_t size)
{
    FILE* stream = resolve_stream(fd);
    if (!stream)
    {
        return -1;
    }

    size_t read_count = fread(buffer, sizeof(uint8_t), size, stream);
    if (read_count < size && ferror(stream))
    {
        return -1;
    }
    return (int64_t) read_count;
}

int64_t sys_write(int fd, const uint8_t *buffer, size_t size)
{
    FILE* stream = resolve_stream(fd);
    if (!stream)
    {
        return -1;
    }

    size_t written_count = fwrite(buffer, sizeof(uint8_t), size, stream);
    if (written_count < size && ferror(stream))
    {
        return -1;
    }
    fflush(stream);
    return (int64_t) written_count;
}