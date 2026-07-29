import pytest
import ctypes
from unittest.mock import MagicMock, patch

from interpreter._src.bridges.syscall import Syscall

@pytest.fixture
def mock_registers():
    """Provides a mocked Registers_Interface."""
    return MagicMock()

@pytest.fixture
def mock_memory():
    """Provides a mocked Data_Memory."""
    return MagicMock()

@pytest.fixture
def syscall_instance(mock_registers, mock_memory):
    """
    Initializes the Syscall class with mocked dependencies.
    We patch ctypes.CDLL to prevent it from attempting to load the actual 
    libscl.so file during unit testing, which keeps tests isolated.
    """
    with patch('ctypes.CDLL') as mock_cdll:
        instance = Syscall(mock_registers, mock_memory)
        yield instance

# --- Dispatch Tests ---

def test_syscall_dispatch_exit(syscall_instance, mock_registers):
    """Test that rax=1 dispatches to the exit handler."""
    mock_registers.read_reg.side_effect = lambda reg: {'rax': 1, 'rdi': 0, 'rsi': 0, 'rdx': 0}.get(reg, 0)
    
    # Patch the method on the Syscall class, not the instance
    with patch.object(Syscall, 'exit') as mock_exit:
        syscall_instance.syscall()
        mock_exit.assert_called_once()

def test_syscall_dispatch_read(syscall_instance, mock_registers):
    """Test that rax=3 dispatches to the read handler with correct arguments."""
    mock_registers.read_reg.side_effect = lambda reg: {'rax': 3, 'rdi': 0, 'rsi': 1024, 'rdx': 64}.get(reg, 0)
    
    # Patch the method on the Syscall class
    with patch.object(Syscall, 'read') as mock_read:
        syscall_instance.syscall()
        mock_read.assert_called_once_with(0, 1024, 64)

def test_syscall_dispatch_write(syscall_instance, mock_registers):
    """Test that rax=4 dispatches to the write handler with correct arguments."""
    mock_registers.read_reg.side_effect = lambda reg: {'rax': 4, 'rdi': 1, 'rsi': 2048, 'rdx': 128}.get(reg, 0)
    
    # Patch the method on the Syscall class
    with patch.object(Syscall, 'write') as mock_write:
        syscall_instance.syscall()
        mock_write.assert_called_once_with(1, 2048, 128)

def test_syscall_dispatch_unknown(syscall_instance, mock_registers):
    """Test that an unknown syscall code acts as a no-op."""
    mock_registers.read_reg.side_effect = lambda reg: {'rax': 999, 'rdi': 0, 'rsi': 0, 'rdx': 0}.get(reg, 0)
    
    # Patch the methods on the Syscall class
    with patch.object(Syscall, 'exit') as mock_exit, \
         patch.object(Syscall, 'read') as mock_read, \
         patch.object(Syscall, 'write') as mock_write:
        
        syscall_instance.syscall()
        
        mock_exit.assert_not_called()
        mock_read.assert_not_called()
        mock_write.assert_not_called()

# --- Handler Tests ---

def test_exit(syscall_instance):
    """Test that exit terminates the process using sys.exit(0)."""
    with pytest.raises(SystemExit) as exc_info:
        syscall_instance.exit()
    assert exc_info.value.code == 0

def test_read_success(syscall_instance, mock_memory):
    """
    Test successful read from C lib, padding logic, and memory write.
    """
    fd, addr, requested_size = 0, 1024, 10
    actual_read_size = 5
    
    # Configure the C lib mock on the instance.lib attribute
    syscall_instance.lib.sys_read.return_value = actual_read_size
    
    result = syscall_instance.read(fd, addr, requested_size)
    
    assert result == actual_read_size
    syscall_instance.lib.sys_read.assert_called_once()
    
    expected_data = b'\x00' * requested_size
    mock_memory.write_bytes.assert_called_once_with(addr, expected_data, requested_size)

def test_read_failure(syscall_instance, mock_memory):
    """Test that a failing sys_read (-1) aborts before writing to simulated memory."""
    fd, addr, size = 99, 1024, 10
    
    syscall_instance.lib.sys_read.return_value = -1
    
    result = syscall_instance.read(fd, addr, size)
    
    assert result == -1
    mock_memory.write_bytes.assert_not_called()

def test_write_success(syscall_instance, mock_memory):
    """Test successful read from simulated memory and write to C lib."""
    fd, addr, size = 1, 2048, 4
    
    mock_memory.read_bytes.return_value = b'Test'
    syscall_instance.lib.sys_write.return_value = size
    
    result = syscall_instance.write(fd, addr, size)
    
    assert result == size
    mock_memory.read_bytes.assert_called_once_with(addr, size)
    syscall_instance.lib.sys_write.assert_called_once()
    
    args, _ = syscall_instance.lib.sys_write.call_args
    assert args[0] == fd
    assert args[2] == size
    
    passed_buffer = args[1]
    assert bytes(passed_buffer[:size]) == b'Test'