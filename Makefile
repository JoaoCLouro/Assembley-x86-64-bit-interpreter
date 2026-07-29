CC = gcc
CFLAGS = -O3 -fPIC -I./interpreter/_src/execution/include
LDFLAGS = -shared

# == Directories ====

SRC_DIR = interpreter/_src/execution/src
INC_DIR = interpreter/_src/execution/include
LIB_DIR = interpreter/_src/lib
BUILD_DIR = build

TEST_DIR = tests/execution_tests
TEST_BIN_DIR = tests/bin

# == Targets & Libraries ========

# 1. Define the exact shared libraries you want to build
LIB_OPS  = $(LIB_DIR)/liboperations.so
LIB_MMU  = $(LIB_DIR)/libmmu.so
LIB_REG  = $(LIB_DIR)/libreg.so
LIB_SYS  = $(LIB_DIR)/librscl.so

SHARED_LIBS = $(LIB_OPS) $(LIB_MMU) $(LIB_REG)

# 2. Define the linker flags for the tests (matches the names above)
TEST_LIBS = -loperations -lmmu -lreg

# 3. Test files and binaries
TEST_SRCS = $(wildcard $(TEST_DIR)/*.c)
TEST_BINS = $(TEST_SRCS:$(TEST_DIR)/%.c=$(TEST_BIN_DIR)/%)

# == Rules ==========

.PHONY: all directories clean test

all: directories $(SHARED_LIBS) $(TEST_BINS)

directories:
	@mkdir -p $(LIB_DIR)
	@mkdir -p $(BUILD_DIR)
	@mkdir -p $(TEST_BIN_DIR)

# Rule to compile execution .c files to .o files automatically
$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c
	$(CC) $(CFLAGS) -c $< -o $@

# Explicit rules mapping specific .o files to your custom .so names
$(LIB_OPS): $(BUILD_DIR)/operations.o
	$(CC) $(LDFLAGS) -o $@ $<

$(LIB_MMU): $(BUILD_DIR)/memory_eng.o
	$(CC) $(LDFLAGS) -o $@ $<

$(LIB_REG): $(BUILD_DIR)/registers.o
	$(CC) $(LDFLAGS) -o $@ $<

$(LIB_SYS): $(BUILD_DIR)/syscall.o
	$(CC) $(LDFLAGS) -o $@ $<

# Rule to compile AND link test executables against the custom libraries
$(TEST_BIN_DIR)/%: $(TEST_DIR)/%.c $(SHARED_LIBS)
	$(CC) -O3 -I./interpreter/_src/execution/include $< -o $@ -L$(LIB_DIR) $(TEST_LIBS) -Wl,-rpath=$$(pwd)/$(LIB_DIR)

test: all
	@echo "Running tests..."
	@for test in $(TEST_BINS); do \
		echo "=> Executing $$test"; \
		./$$test || exit 1; \
	done

clean:
	rm -rf $(BUILD_DIR)/* $(LIB_DIR)/*
	@echo "Cleaned execution build and lib folders."
	rm -rf $(TEST_BIN_DIR)/*
	@echo "Cleaned test bin folders."