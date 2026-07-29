#include "../include/syscall.h"

#include <stdint.h>
#include <stddef.h>
#include <stdio.h>

void read(void* stream, void* buffer, size_t size)
{
    // stdin
    if (stream == 1)
    {
        // To define
    }
    fread(buffer, size, sizeof(char), (FILE*) stream);
}


void write(void* stream, void* buffer, size_t size)
{
    if (stream == 1)
    {
        // To define
    }
    fwrite(buffer, size, sizeof(char), (FILE*) stream);
}