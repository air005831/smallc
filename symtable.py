# symtable.py
# Scoped Symbol Table and Semantic Analysis for Small-C

class SmallCSemanticError(Exception):
    """Exception raised for static semantic errors."""
    def __init__(self, message, line_num=None):
        super().__init__(f"Semantic error at line {line_num}: {message}" if line_num else f"Semantic error: {message}")
        self.message = message
        self.line_num = line_num

class Symbol:
    def __init__(self, name, type_, is_pointer=False, array_size=None, address=None):
        self.name = name                 # String name
        self.type = type_                 # 'int', 'char', 'void'
        self.is_pointer = is_pointer     # Bool
        self.array_size = array_size     # Int (if array, else None)
        self.address = address           # Integer virtual memory address

class FunctionSymbol:
    def __init__(self, name, return_type, params, start_line=None):
        self.name = name                 # String
        self.return_type = return_type   # 'int', 'char', 'void'
        self.params = params             # List of (type, name, is_pointer)
        self.start_line = start_line     # Line number in code

class SymbolTable:
    def __init__(self):
        # Nested scopes list. Index 0 is always global scope.
        self.scopes = [{}]
        self.functions = {}
        self._register_builtins()

    def reset_runtime(self):
        """Resets the scope to just global scope, but preserves global variables
        if incremental. If full reset, call reset_all."""
        self.scopes = [self.scopes[0]]

    def reset_all(self):
        """Completely clears all global variables, scopes, and user-defined functions."""
        self.scopes = [{}]
        self.functions = {}
        self._register_builtins()

    def _register_builtins(self):
        # Register all 22 built-in functions
        builtins = [
            # I/O
            ('putchar', 'int', [('int', 'ch', False)]),
            ('getchar', 'int', []),
            ('printf', 'void', [('char', 'fmt', True)]), # Variadic function, first arg is format string
            ('puts', 'void', [('char', 's', True)]),
            ('scanf', 'int', [('char', 'fmt', True)]),   # Variadic function
            # Strings
            ('strlen', 'int', [('char', 's', True)]),
            ('strcpy', 'void', [('char', 'dest', True), ('char', 'src', True)]),
            ('strcmp', 'int', [('char', 's1', True), ('char', 's2', True)]),
            ('strcat', 'void', [('char', 'dest', True), ('char', 'src', True)]),
            # Math
            ('abs', 'int', [('int', 'x', False)]),
            ('max', 'int', [('int', 'a', False), ('int', 'b', False)]),
            ('min', 'int', [('int', 'a', False), ('int', 'b', False)]),
            ('pow', 'int', [('int', 'base', False), ('int', 'exp', False)]),
            ('sqrt', 'int', [('int', 'x', False)]),
            ('mod', 'int', [('int', 'a', False), ('int', 'b', False)]),
            ('rand', 'int', []),
            ('srand', 'void', [('int', 'seed', False)]),
            # Memory & Utility
            ('memset', 'void', [('char', 'ptr', True), ('int', 'value', False), ('int', 'size', False)]),
            ('sizeof_int', 'int', []),
            ('sizeof_char', 'int', []),
            ('atoi', 'int', [('char', 's', True)]),
            ('itoa', 'void', [('int', 'value', False), ('char', 'str', True)]),
            ('exit', 'void', [('int', 'code', False)])
        ]
        
        for name, ret, params in builtins:
            self.functions[name] = FunctionSymbol(name, ret, params, start_line="[built-in]")

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()

    def declare_var(self, name, type_, is_pointer=False, array_size=None, address=None, line_num=None):
        """Declares a variable in the current active scope."""
        current_scope = self.scopes[-1]
        if name in current_scope:
            raise SmallCSemanticError(f"Redeclaration of variable '{name}' in the same scope", line_num)
        
        sym = Symbol(name, type_, is_pointer, array_size, address)
        current_scope[name] = sym
        return sym

    def declare_function(self, name, return_type, params, start_line, line_num=None):
        """Registers a function in the symbol table."""
        if name in self.functions:
            # Built-in or existing function
            if self.functions[name].start_line == "[built-in]":
                raise SmallCSemanticError(f"Cannot overwrite built-in function '{name}'", line_num)
            raise SmallCSemanticError(f"Redefinition of function '{name}'", line_num)
        
        func_sym = FunctionSymbol(name, return_type, params, start_line)
        self.functions[name] = func_sym
        return func_sym

    def lookup_var(self, name):
        """Looks up a variable scope by scope from innermost to global."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def lookup_function(self, name):
        """Looks up a function prototype by name."""
        return self.functions.get(name, None)

    def is_global_scope(self):
        return len(self.scopes) == 1
