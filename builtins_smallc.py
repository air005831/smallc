# builtins_smallc.py
# Runtime Implementation of Small-C Built-in Functions

import sys
import re
import math
import random
from memory import SmallCMemoryError

class SmallCExitException(Exception):
    """Exception raised when exit() is called in Small-C code."""
    def __init__(self, code):
        super().__init__(f"Program exited with code {code}.")
        self.code = code

class SmallCBuiltinError(Exception):
    """Exception raised for errors in built-in functions."""
    pass

class BuiltinsManager:
    def __init__(self, memory):
        self.memory = memory
        # Rand LCG state
        self.rand_seed = 1
        # Input buffer for scanf
        self.scanf_buffer = []

    def reset(self):
        self.rand_seed = 1
        self.scanf_buffer.clear()

    def call(self, name, args):
        """Dispatches built-in function calls to their Python implementations.
        `args` are already evaluated integer values/addresses.
        """
        handler = getattr(self, f"_builtin_{name}", None)
        if handler:
            try:
                return handler(*args)
            except TypeError as e:
                raise SmallCBuiltinError(f"Built-in '{name}': incorrect argument count. Details: {e}")
        else:
            raise SmallCBuiltinError(f"Built-in function '{name}' is not implemented.")

    # ----------------- Input / Output -----------------

    def _builtin_putchar(self, ch):
        # Print single character
        sys.stdout.write(chr(int(ch) & 0xFF))
        sys.stdout.flush()
        return ch

    def _builtin_getchar(self):
        # Read single character
        char = sys.stdin.read(1)
        if not char:
            return -1
        return ord(char)

    def _builtin_printf(self, fmt_addr, *args):
        try:
            fmt_str = self.memory.read_string(fmt_addr)
        except SmallCMemoryError as e:
            raise SmallCBuiltinError(f"printf: invalid format string pointer. {e}")

        output = []
        arg_idx = 0
        i = 0
        n = len(fmt_str)

        while i < n:
            if fmt_str[i] == '%' and i + 1 < n:
                spec = fmt_str[i+1]
                i += 2
                
                if spec == '%':
                    output.append('%')
                    continue
                
                # Fetch argument
                if arg_idx >= len(args):
                    raise SmallCBuiltinError("printf: not enough arguments for format string")
                arg = args[arg_idx]
                arg_idx += 1

                if spec == 'd':
                    output.append(str(int(arg)))
                elif spec == 'c':
                    output.append(chr(int(arg) & 0xFF))
                elif spec == 's':
                    try:
                        str_val = self.memory.read_string(arg)
                        output.append(str_val)
                    except SmallCMemoryError as e:
                        raise SmallCBuiltinError(f"printf: invalid string pointer %s. {e}")
                elif spec == 'x':
                    # Hexadecimal lowercase, without prefix 0x
                    val = int(arg) & 0xFFFFFFFF
                    output.append(f"{val:x}")
                else:
                    # Unrecognized specifier, output as literal
                    output.append('%' + spec)
            else:
                output.append(fmt_str[i])
                i += 1

        sys.stdout.write("".join(output))
        sys.stdout.flush()

    def _builtin_puts(self, s_addr):
        try:
            s = self.memory.read_string(s_addr)
        except SmallCMemoryError as e:
            raise SmallCBuiltinError(f"puts: invalid string pointer. {e}")
        print(s)

    def _builtin_scanf(self, fmt_addr, *args):
        try:
            fmt_str = self.memory.read_string(fmt_addr)
        except SmallCMemoryError as e:
            raise SmallCBuiltinError(f"scanf: invalid format string pointer. {e}")

        # Collect specifiers
        specifiers = []
        i = 0
        n = len(fmt_str)
        while i < n:
            if fmt_str[i] == '%' and i + 1 < n:
                spec = fmt_str[i+1]
                i += 2
                if spec == '%':
                    continue
                if spec in {'d', 'c'}:
                    specifiers.append(spec)
                else:
                    raise SmallCBuiltinError(f"scanf: unsupported format specifier '%{spec}'")
            else:
                i += 1

        if len(specifiers) != len(args):
            raise SmallCBuiltinError(f"scanf: expected {len(specifiers)} arguments, got {len(args)}")

        # Read tokens from stdin if buffer is empty
        items_read = 0
        for spec, dest_addr in zip(specifiers, args):
            # Check destination address validity
            if dest_addr == 0 or dest_addr is None:
                raise SmallCBuiltinError("scanf: null pointer argument passed as target")
            
            # Fetch next token from buffer
            while not self.scanf_buffer:
                line = sys.stdin.readline()
                if not line:
                    break
                self.scanf_buffer = line.split()
            
            if not self.scanf_buffer:
                break # EOF reached
            
            token = self.scanf_buffer.pop(0)
            
            try:
                if spec == 'd':
                    val = int(token)
                    self.memory.write_int(dest_addr, val)
                elif spec == 'c':
                    val = ord(token[0])
                    self.memory.write_char(dest_addr, val)
                    items_read += 1
            except ValueError:
                # Failed to parse, stop scanning
                break
            except SmallCMemoryError as e:
                raise SmallCBuiltinError(f"scanf: memory write failed at address {dest_addr}. {e}")

        return items_read

    # ----------------- String Manipulation -----------------

    def _builtin_strlen(self, s_addr):
        try:
            s = self.memory.read_string(s_addr)
            return len(s)
        except SmallCMemoryError as e:
            raise SmallCBuiltinError(f"strlen: invalid pointer. {e}")

    def _builtin_strcpy(self, dest_addr, src_addr):
        try:
            src = self.memory.read_string(src_addr)
            self.memory.write_string(dest_addr, src)
        except SmallCMemoryError as e:
            raise SmallCBuiltinError(f"strcpy: invalid memory access. {e}")

    def _builtin_strcmp(self, s1_addr, s2_addr):
        try:
            s1 = self.memory.read_string(s1_addr)
            s2 = self.memory.read_string(s2_addr)
            if s1 < s2:
                return -1
            elif s1 > s2:
                return 1
            return 0
        except SmallCMemoryError as e:
            raise SmallCBuiltinError(f"strcmp: invalid pointer. {e}")

    def _builtin_strcat(self, dest_addr, src_addr):
        try:
            dest = self.memory.read_string(dest_addr)
            src = self.memory.read_string(src_addr)
            self.memory.write_string(dest_addr, dest + src)
        except SmallCMemoryError as e:
            raise SmallCBuiltinError(f"strcat: invalid memory access. {e}")

    # ----------------- Math Functions -----------------

    def _builtin_abs(self, x):
        return abs(int(x))

    def _builtin_max(self, a, b):
        return max(int(a), int(b))

    def _builtin_min(self, a, b):
        return min(int(a), int(b))

    def _builtin_pow(self, base, exp):
        b = int(base)
        e = int(exp)
        if e < 0:
            return 0
        if e == 0:
            return 1
        return int(b ** e)

    def _builtin_sqrt(self, x):
        val = int(x)
        if val < 0:
            raise SmallCBuiltinError("sqrt: argument must be non-negative.")
        return int(math.isqrt(val))

    def _builtin_mod(self, a, b):
        divisor = int(b)
        if divisor == 0:
            raise SmallCBuiltinError("mod: division or modulo by zero.")
        return int(a) % divisor

    def _builtin_rand(self):
        self.rand_seed = (self.rand_seed * 1103515245 + 12345) & 0x7FFFFFFF
        return (self.rand_seed // 65536) % 32768

    def _builtin_srand(self, seed):
        self.rand_seed = int(seed)

    # ----------------- Memory & Utility -----------------

    def _builtin_memset(self, ptr_addr, value, size):
        val = int(value) & 0xFF
        sz = int(size)
        try:
            for offset in range(sz):
                self.memory.write_byte(ptr_addr + offset, val)
        except SmallCMemoryError as e:
            raise SmallCBuiltinError(f"memset: memory access out of bounds. {e}")

    def _builtin_sizeof_int(self):
        return 4

    def _builtin_sizeof_char(self):
        return 1

    def _builtin_atoi(self, s_addr):
        try:
            s = self.memory.read_string(s_addr).strip()
            match = re.match(r'^[+-]?\d+', s)
            if match:
                return int(match.group(0))
            return 0
        except SmallCMemoryError as e:
            raise SmallCBuiltinError(f"atoi: invalid pointer. {e}")
        except Exception:
            return 0

    def _builtin_itoa(self, value, str_addr):
        s = str(int(value))
        try:
            self.memory.write_string(str_addr, s)
        except SmallCMemoryError as e:
            raise SmallCBuiltinError(f"itoa: invalid memory access at {str_addr}. {e}")

    def _builtin_exit(self, code):
        raise SmallCExitException(int(code))
