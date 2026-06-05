# memory.py
# Virtual Memory Simulation for Small-C Interactive Interpreter

import struct

class SmallCMemoryError(Exception):
    """Exception raised for virtual memory access errors."""
    pass

class VirtualMemory:
    def __init__(self, size=1024 * 1024):
        self.size = size
        self.ram = bytearray(size)
        
        # Segment pointers
        # Address 0 is considered NULL. Static data starts at 1024.
        self.static_start = 1024
        self.static_ptr = self.static_start
        
        # Stack segment starts at the very end of RAM and grows downwards
        self.stack_start = size
        self.sp = self.stack_start
        
        # Record string literal offsets to deduplicate and cache
        self.string_cache = {}

    def reset_runtime(self):
        """Resets the stack pointer and dynamic allocations. 
        Keeps global allocations if doing incremental REPL definitions, 
        or completely resets if starting a new program RUN.
        """
        self.sp = self.stack_start

    def reset_all(self):
        """Completely clears the entire memory and resets all pointers."""
        self.ram = bytearray(self.size)
        self.static_ptr = self.static_start
        self.sp = self.stack_start
        self.string_cache.clear()

    def allocate_global(self, size_in_bytes):
        """Allocates contiguous space in the static/global segment."""
        addr = self.static_ptr
        if addr + size_in_bytes >= self.sp:
            raise SmallCMemoryError("Out of Memory: Global segment collided with Stack.")
        self.static_ptr += size_in_bytes
        return addr

    def allocate_stack(self, size_in_bytes):
        """Allocates space on the stack by moving stack pointer down."""
        if self.sp - size_in_bytes < self.static_ptr:
            raise SmallCMemoryError("Stack Overflow: Stack collided with Global segment.")
        self.sp -= size_in_bytes
        return self.sp

    def free_stack(self, size_in_bytes):
        """Frees space on the stack by moving stack pointer up."""
        self.sp += size_in_bytes
        if self.sp > self.stack_start:
            self.sp = self.stack_start

    def allocate_string(self, text):
        """Allocates a null-terminated string literal in global memory and returns its address.
        Deduplicates identical string constants.
        """
        if text in self.string_cache:
            return self.string_cache[text]
        
        # Convert string and handle escape sequences (which are resolved by parser/lexer)
        encoded = text.encode('ascii', errors='ignore') + b'\x00'
        size = len(encoded)
        addr = self.allocate_global(size)
        self.ram[addr:addr+size] = encoded
        self.string_cache[text] = addr
        return addr

    def _check_address(self, address, length):
        """Validates that the memory access is within bounds and safe."""
        if address is None:
            raise SmallCMemoryError("Null pointer dereference.")
        if address == 0:
            raise SmallCMemoryError("Null pointer dereference (accessing address 0).")
        if address < 0:
            raise SmallCMemoryError(f"Invalid memory access: negative address {address}.")
        if address < 1024:
            raise SmallCMemoryError(f"Access violation: Attempted to access reserved system memory at address {address}.")
        if address + length > self.size:
            raise SmallCMemoryError(f"Segmentation fault: Address {address} is out of simulated memory bounds (size: {self.size}).")

    def read_byte(self, address):
        self._check_address(address, 1)
        # Interpret as signed char (-128 to 127)
        val = self.ram[address]
        if val >= 128:
            val -= 256
        return val

    def write_byte(self, address, value):
        self._check_address(address, 1)
        # Force into a single byte range
        self.ram[address] = int(value) & 0xFF

    def read_int(self, address):
        self._check_address(address, 4)
        # Read 4 bytes little-endian signed integer
        data = self.ram[address:address+4]
        return struct.unpack("<i", data)[0]

    def write_int(self, address, value):
        self._check_address(address, 4)
        # Pack value into 4 bytes little-endian signed integer
        try:
            data = struct.pack("<i", int(value))
        except struct.error:
            # Handle integer overflow by masking to 32-bit signed
            masked_val = (int(value) & 0xFFFFFFFF)
            if masked_val >= 0x80000000:
                masked_val -= 0x100000000
            data = struct.pack("<i", masked_val)
        self.ram[address:address+4] = data

    def read_char(self, address):
        """Standard Small-C char read: 1 byte signed integer."""
        return self.read_byte(address)

    def write_char(self, address, value):
        """Standard Small-C char write: 1 byte."""
        self.write_byte(address, value)

    def read_string(self, address):
        """Helper to read a C-string from virtual memory up to null terminator."""
        chars = []
        curr = address
        while True:
            ch = self.read_byte(curr)
            if ch == 0:
                break
            chars.append(chr(ch))
            curr += 1
        return "".join(chars)

    def write_string(self, address, text):
        """Writes a string directly into virtual memory (e.g. for strcpy/strcat)."""
        encoded = text.encode('ascii', errors='ignore') + b'\x00'
        self._check_address(address, len(encoded))
        self.ram[address:address+len(encoded)] = encoded
