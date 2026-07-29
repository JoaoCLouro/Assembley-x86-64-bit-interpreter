#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <assert.h>
#include "../../interpreter/_src/execution/include/syscall.h"

// Helper macros for colored test output
#define PRINT_SUCCESS(msg) printf("\033[0;32m[PASS]\033[0m %s\n", msg)
#define PRINT_FAIL(msg)    printf("\033[0;31m[FAIL]\033[0m %s\n", msg)

void test_sys_write_stdout() {
    int p[2];
    assert(pipe(p) == 0); // Create a pipe

    // Save current stdout and redirect fd 1 to the write end of the pipe
    int old_stdout = dup(STDOUT_FILENO);
    dup2(p[1], STDOUT_FILENO);

    const char* msg = "Hello, simulated stdout!";
    size_t msg_len = strlen(msg);
    
    // Execute the function under test
    int64_t bytes_written = sys_write(1, (const uint8_t*)msg, msg_len);

    // Restore original stdout
    fflush(stdout);
    dup2(old_stdout, STDOUT_FILENO);
    close(old_stdout);

    // Read what was written to the pipe
    char buffer[256] = {0};
    read(p[0], buffer, sizeof(buffer));
    
    close(p[0]);
    close(p[1]);

    // Assertions
    assert(bytes_written == (int64_t)msg_len);
    assert(strcmp(buffer, msg) == 0);
    
    PRINT_SUCCESS("sys_write to stdout (fd=1)");
}

void test_sys_write_invalid_fd() {
    const uint8_t buffer[] = "Test data";
    
    // Test with an unsupported file descriptor (e.g., 3)
    int64_t res = sys_write(3, buffer, sizeof(buffer));
    assert(res == -1);

    // Test with a negative file descriptor
    res = sys_write(-1, buffer, sizeof(buffer));
    assert(res == -1);

    PRINT_SUCCESS("sys_write with invalid fd returns -1");
}

void test_sys_read_stdin() {
    int p[2];
    assert(pipe(p) == 0);

    // Save current stdin and redirect fd 0 to the read end of the pipe
    int old_stdin = dup(STDIN_FILENO);
    dup2(p[0], STDIN_FILENO);

    // Write mock data to the pipe so sys_read can consume it
    const char* input_data = "MockInput";
    size_t input_len = strlen(input_data);
    write(p[1], input_data, input_len);

    // Execute the function under test
    uint8_t buffer[256] = {0};
    int64_t bytes_read = sys_read(0, buffer, input_len);

    // Restore original stdin
    dup2(old_stdin, STDIN_FILENO);
    close(old_stdin);
    
    close(p[0]);
    close(p[1]);

    // Assertions
    assert(bytes_read == (int64_t)input_len);
    assert(memcmp(buffer, input_data, input_len) == 0);

    PRINT_SUCCESS("sys_read from stdin (fd=0)");
}

void test_sys_read_invalid_fd() {
    uint8_t buffer[10];
    
    // Try to read from stdout (fd=1), which should not be supported for sys_read
    // or at least test a completely invalid fd like 5
    int64_t res = sys_read(5, buffer, sizeof(buffer));
    
    assert(res == -1);
    PRINT_SUCCESS("sys_read with invalid fd returns -1");
}

int main() {
    printf("Starting syscall integration tests...\n");
    printf("--------------------------------------\n");

    test_sys_write_stdout();
    test_sys_write_invalid_fd();
    
    test_sys_read_stdin();
    test_sys_read_invalid_fd();

    printf("--------------------------------------\n");
    printf("\033[0;32mALL TESTS PASSED SUCCESSFULLY.\033[0m\n");

    return 0;
}