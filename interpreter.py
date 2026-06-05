# interpreter.py
# AST Execution Engine for Small-C

import sys
from memory import SmallCMemoryError
from builtins_smallc import BuiltinsManager, SmallCExitException, SmallCBuiltinError
from symtable import SymbolTable, SmallCSemanticError

class SmallCRuntimeError(Exception):
    """Exception raised for runtime errors during Small-C execution."""
    def __init__(self, message, line_num=None):
        super().__init__(f"Runtime error at line {line_num}: {message}" if line_num else f"Runtime error: {message}")
        self.message = message
        self.line_num = line_num

# Flow control exceptions
class BreakException(Exception):
    pass

class ContinueException(Exception):
    pass

class ReturnException(Exception):
    def __init__(self, value, type_):
        self.value = value
        self.type = type_

class Interpreter:
    def __init__(self, memory, symtable):
        self.memory = memory
        self.symtable = symtable
        self.builtins = BuiltinsManager(memory)
        
        self.trace_enabled = False
        self.source_lines = []
        
        # User defined functions AST dictionary: name -> FuncDefNode
        self.user_functions = {}

    def reset_runtime(self):
        """Prepares the interpreter state and memory for a new RUN."""
        self.memory.reset_runtime()
        self.symtable.reset_runtime()
        self.builtins.reset()

    def reset_all(self):
        """Completely clears all functions, variables, memory, and states."""
        self.memory.reset_all()
        self.symtable.reset_all()
        self.builtins.reset()
        self.user_functions.clear()
        self.source_lines.clear()

    def set_source_lines(self, lines):
        self.source_lines = lines

    def _trace(self, node):
        """Helper to print statement execution traces if enabled."""
        if self.trace_enabled and hasattr(node, 'line_num') and node.line_num is not None:
            line_idx = node.line_num - 1
            if 0 <= line_idx < len(self.source_lines):
                source = self.source_lines[line_idx].strip()
                print(f"{{[line {node.line_num}] {source}}}")
                sys.stdout.flush()

    def execute_program(self, ast_root):
        """Registers all global functions and variables, then executes main()."""
        # Phase 1: Register all global declarations (without running them yet)
        for decl in ast_root.declarations:
            from parser import FuncDefNode, VarDeclNode
            if isinstance(decl, FuncDefNode):
                # Register function symbol prototype
                params_proto = [(p[0], p[1], p[2]) for p in decl.params]
                try:
                    self.symtable.declare_function(decl.name, decl.return_type, params_proto, decl.line_num)
                except SmallCSemanticError as e:
                    raise SmallCRuntimeError(e.message, decl.line_num)
                self.user_functions[decl.name] = decl
            elif isinstance(decl, VarDeclNode):
                self._execute_var_decl(decl)

        # Phase 2: Execute main() function
        main_func = self.symtable.lookup_function('main')
        if not main_func:
            raise SmallCRuntimeError("Function 'main' is not defined.")
        
        try:
            val, val_type = self._execute_call('main', [], 1)
            return val
        except SmallCExitException as e:
            return e.code

    def execute_interactive_node(self, node):
        """Executes a single top-level node entered in interactive REPL."""
        from parser import FuncDefNode, VarDeclNode
        if isinstance(node, FuncDefNode):
            # Register user-defined function
            params_proto = [(p[0], p[1], p[2]) for p in node.params]
            self.symtable.declare_function(node.name, node.return_type, params_proto, node.line_num)
            self.user_functions[node.name] = node
            return None
        elif isinstance(node, VarDeclNode):
            # Global variable declaration
            return self._execute_var_decl(node)
        else:
            # Statement or expression execution in global scope
            try:
                self._execute_statement(node)
            except (BreakException, ContinueException):
                raise SmallCRuntimeError("break or continue statement outside of loop", node.line_num)
            except ReturnException as r:
                return r.value
            return None

    # ----------------- Statement Execution -----------------

    def _execute_statement(self, node):
        if node is None:
            return

        from parser import (
            BlockNode, ExprStmtNode, IfNode, WhileNode, DoWhileNode,
            ForNode, BreakNode, ContinueNode, ReturnNode, SwitchNode
        )

        try:
            if isinstance(node, BlockNode):
                for stmt in node.statements:
                    self._execute_statement(stmt)

            elif isinstance(node, ExprStmtNode):
                self._trace(node)
                self._evaluate_expression(node.expr)

            elif isinstance(node, IfNode):
                self._trace(node)
                cond_val, _ = self._evaluate_expression(node.cond)
                if cond_val:
                    self._execute_statement(node.then_branch)
                elif node.else_branch:
                    self._execute_statement(node.else_branch)

            elif isinstance(node, WhileNode):
                while True:
                    self._trace(node)
                    cond_val, _ = self._evaluate_expression(node.cond)
                    if not cond_val:
                        break
                    try:
                        self._execute_statement(node.body)
                    except BreakException:
                        break
                    except ContinueException:
                        continue

            elif isinstance(node, DoWhileNode):
                while True:
                    try:
                        self._execute_statement(node.body)
                    except BreakException:
                        break
                    except ContinueException:
                        pass # Continue jumps straight to condition check
                    
                    self._trace(node)
                    cond_val, _ = self._evaluate_expression(node.cond)
                    if not cond_val:
                        break

            elif isinstance(node, ForNode):
                # Init
                if node.init:
                    if hasattr(node.init, 'type'): # VarDeclNode
                        self._execute_var_decl(node.init)
                    else:
                        self._evaluate_expression(node.init)
                
                while True:
                    self._trace(node)
                    if node.cond:
                        cond_val, _ = self._evaluate_expression(node.cond)
                        if not cond_val:
                            break
                    try:
                        self._execute_statement(node.body)
                    except BreakException:
                        break
                    except ContinueException:
                        pass # Jump straight to increment step
                    
                    if node.incr:
                        self._evaluate_expression(node.incr)

            elif isinstance(node, BreakNode):
                self._trace(node)
                raise BreakException()

            elif isinstance(node, ContinueNode):
                self._trace(node)
                raise ContinueException()

            elif isinstance(node, ReturnNode):
                self._trace(node)
                val = 0
                val_type = 'int'
                if node.expr:
                    val, val_type = self._evaluate_expression(node.expr)
                raise ReturnException(val, val_type)

            elif isinstance(node, SwitchNode):
                self._trace(node)
                switch_val, _ = self._evaluate_expression(node.expr)
                
                matched = False
                matched_cases = []
                default_case = None
                
                # Check for matching case
                for case in node.cases:
                    if matched or case.val == switch_val:
                        matched = True
                        matched_cases.append(case)
                
                if matched:
                    # Execute starting from matched case (fallthrough sequence)
                    try:
                        for case in matched_cases:
                            for stmt in case.statements:
                                self._execute_statement(stmt)
                    except BreakException:
                        pass # break exits the switch block
                else:
                    # Execute default if defined
                    if node.default_case:
                        try:
                            for stmt in node.default_case.statements:
                                self._execute_statement(stmt)
                        except BreakException:
                            pass
        
        except SmallCMemoryError as e:
            raise SmallCRuntimeError(f"Memory access violation: {e.args[0]}", node.line_num)
        except SmallCBuiltinError as e:
            raise SmallCRuntimeError(e.args[0], node.line_num)

    def _execute_var_decl(self, node):
        """Allocates variable in virtual memory and registers symbol table details."""
        # Calculate byte size of type
        sizeof_type = 4 if node.type == 'int' else 1
        is_array = node.array_size is not None
        
        # Byte size to allocate
        alloc_size = sizeof_type
        if is_array:
            alloc_size = node.array_size * sizeof_type
        elif node.is_pointer:
            # Pointer sizes are always 4 bytes
            alloc_size = 4

        # Memory allocation segment
        is_global = self.symtable.is_global_scope()
        if is_global:
            addr = self.memory.allocate_global(alloc_size)
        else:
            addr = self.memory.allocate_stack(alloc_size)

        # Suffix type representation
        sym_type = node.type
        if node.is_pointer:
            sym_type += '*'

        # Register symbol
        self.symtable.declare_var(
            name=node.name,
            type_=node.type,
            is_pointer=node.is_pointer,
            array_size=node.array_size,
            address=addr,
            line_num=node.line_num
        )

        # Initialize variable values if specified
        if node.initializer is not None:
            if is_array:
                if isinstance(node.initializer, str):
                    # Initialise character array with string literal
                    self.memory.write_string(addr, node.initializer)
                elif isinstance(node.initializer, list):
                    # Curly-brace initialization list
                    for idx, init_expr in enumerate(node.initializer):
                        if idx >= node.array_size:
                            raise SmallCRuntimeError(f"Array initializer list exceeds declared array size {node.array_size}", node.line_num)
                        val, _ = self._evaluate_expression(init_expr)
                        elem_addr = addr + idx * sizeof_type
                        if node.type == 'int':
                            self.memory.write_int(elem_addr, val)
                        else:
                            self.memory.write_char(elem_addr, val)
            else:
                # Scalar initializer
                val, _ = self._evaluate_expression(node.initializer)
                if node.is_pointer or node.type == 'int':
                    self.memory.write_int(addr, val)
                else:
                    self.memory.write_char(addr, val)

        return addr

    # ----------------- Expression Evaluation -----------------

    def _evaluate_expression(self, node):
        """Recursively evaluates an AST expression node and returns a tuple (value, type_str)."""
        from parser import (
            ConstNode, VarNode, SubscriptNode, UnaryOpNode, BinOpNode, AssignNode, CallNode
        )

        if isinstance(node, ConstNode):
            if node.type == 'string':
                # Allocate in static memory and return string pointer
                addr = self.memory.allocate_string(node.value)
                return addr, 'char*'
            elif node.type == 'char':
                return node.value, 'char'
            else:
                return node.value, 'int'

        elif isinstance(node, VarNode):
            sym = self.symtable.lookup_var(node.name)
            if not sym:
                raise SmallCRuntimeError(f"Undeclared variable '{node.name}'", node.line_num)
            
            sym_type = sym.type + ('*' if sym.is_pointer else '')
            if sym.array_size is not None:
                # Array decays to a pointer to its first element
                decayed_type = sym.type + '*'
                return sym.address, decayed_type
            
            # Read scalar or pointer value
            if sym.is_pointer or sym.type == 'int':
                return self.memory.read_int(sym.address), sym_type
            else:
                return self.memory.read_char(sym.address), sym_type

        elif isinstance(node, SubscriptNode):
            addr, base_type = self._evaluate_lvalue(node)
            pointed_type = base_type[:-1] # strip trailing '*'
            if pointed_type == 'int':
                return self.memory.read_int(addr), 'int'
            else:
                return self.memory.read_char(addr), 'char'

        elif isinstance(node, UnaryOpNode):
            if node.is_postfix:
                # Postfix ++/--
                addr, base_type = self._evaluate_lvalue(node.expr)
                is_int = (base_type == 'int' or '*' in base_type)
                
                # Fetch original value
                val = self.memory.read_int(addr) if is_int else self.memory.read_char(addr)
                
                # Scale step for pointer increment
                step = 1
                if '*' in base_type:
                    step = 4 if base_type.startswith('int') else 1

                new_val = val + step if node.op == '++' else val - step
                
                if is_int:
                    self.memory.write_int(addr, new_val)
                else:
                    self.memory.write_char(addr, new_val)
                
                return val, base_type
            
            else:
                # Prefix unary
                if node.op == '&':
                    # Address-of
                    addr, base_type = self._evaluate_lvalue(node.expr)
                    return addr, base_type + '*'
                
                elif node.op == '*':
                    # Dereference R-value
                    ptr_val, base_type = self._evaluate_expression(node.expr)
                    if not base_type.endswith('*'):
                        raise SmallCRuntimeError("Cannot dereference a non-pointer type", node.line_num)
                    
                    pointed_type = base_type[:-1]
                    if pointed_type == 'int':
                        return self.memory.read_int(ptr_val), pointed_type
                    else:
                        return self.memory.read_char(ptr_val), pointed_type

                elif node.op in {'++', '--'}:
                    # Prefix ++/--
                    addr, base_type = self._evaluate_lvalue(node.expr)
                    is_int = (base_type == 'int' or '*' in base_type)
                    
                    val = self.memory.read_int(addr) if is_int else self.memory.read_char(addr)
                    
                    step = 1
                    if '*' in base_type:
                        step = 4 if base_type.startswith('int') else 1

                    new_val = val + step if node.op == '++' else val - step
                    
                    if is_int:
                        self.memory.write_int(addr, new_val)
                    else:
                        self.memory.write_char(addr, new_val)
                    
                    return new_val, base_type
                
                else:
                    # Unary math/logic: -, ~, !
                    val, type_str = self._evaluate_expression(node.expr)
                    if node.op == '-':
                        return -val, 'int'
                    elif node.op == '~':
                        return ~val, 'int'
                    elif node.op == '!':
                        return int(not val), 'int'
                    else:
                        raise SmallCRuntimeError(f"Unsupported prefix operator '{node.op}'", node.line_num)

        elif isinstance(node, BinOpNode):
            # Short-circuit logical operators
            if node.op == '&&':
                l_val, _ = self._evaluate_expression(node.left)
                if not l_val:
                    return 0, 'int'
                r_val, _ = self._evaluate_expression(node.right)
                return int(bool(r_val)), 'int'
            
            elif node.op == '||':
                l_val, _ = self._evaluate_expression(node.left)
                if l_val:
                    return 1, 'int'
                r_val, _ = self._evaluate_expression(node.right)
                return int(bool(r_val)), 'int'

            # Standard math / bitwise / relational
            l_val, l_type = self._evaluate_expression(node.left)
            r_val, r_type = self._evaluate_expression(node.right)

            # Division / modulo by zero checks
            if node.op in {'/', '%'}:
                if r_val == 0:
                    raise SmallCRuntimeError("Division or modulo by zero.", node.line_num)

            # Pointer Arithmetic Scaling
            if node.op == '+':
                if '*' in l_type and r_type == 'int':
                    scale = 4 if l_type.startswith('int') else 1
                    return l_val + r_val * scale, l_type
                elif '*' in r_type and l_type == 'int':
                    scale = 4 if r_type.startswith('int') else 1
                    return r_val + l_val * scale, r_type
            
            elif node.op == '-':
                if '*' in l_type and r_type == 'int':
                    scale = 4 if l_type.startswith('int') else 1
                    return l_val - r_val * scale, l_type
                elif '*' in l_type and '*' in r_type:
                    # Subtracting two pointers of the same type: return offset index
                    if l_type != r_type:
                        raise SmallCRuntimeError("Pointer subtraction requires pointers of identical types", node.line_num)
                    scale = 4 if l_type.startswith('int') else 1
                    return (l_val - r_val) // scale, 'int'

            # Standard evaluations
            if node.op == '+': return l_val + r_val, 'int'
            elif node.op == '-': return l_val - r_val, 'int'
            elif node.op == '*': return l_val * r_val, 'int'
            elif node.op == '/': return int(l_val / r_val), 'int'
            elif node.op == '%': return l_val % r_val, 'int'
            elif node.op == '<<': return l_val << r_val, 'int'
            elif node.op == '>>': return l_val >> r_val, 'int'
            elif node.op == '<': return int(l_val < r_val), 'int'
            elif node.op == '<=': return int(l_val <= r_val), 'int'
            elif node.op == '>': return int(l_val > r_val), 'int'
            elif node.op == '>=': return int(l_val >= r_val), 'int'
            elif node.op == '==': return int(l_val == r_val), 'int'
            elif node.op == '!=': return int(l_val != r_val), 'int'
            elif node.op == '&': return l_val & r_val, 'int'
            elif node.op == '|': return l_val | r_val, 'int'
            elif node.op == '^': return l_val ^ r_val, 'int'
            
            raise SmallCRuntimeError(f"Unsupported binary operator '{node.op}'", node.line_num)

        elif isinstance(node, AssignNode):
            addr, left_type = self._evaluate_lvalue(node.left)
            r_val, r_type = self._evaluate_expression(node.right)

            # Resolve compounds: +=, -=, *=, /=, %=
            if node.op != '=':
                is_int = (left_type == 'int' or '*' in left_type)
                curr_val = self.memory.read_int(addr) if is_int else self.memory.read_char(addr)
                
                # Check division by zero in compounds
                if node.op in {'/=', '%='} and r_val == 0:
                    raise SmallCRuntimeError("Division or modulo by zero.", node.line_num)

                # Scale pointers in += and -=
                if '*' in left_type:
                    scale = 4 if left_type.startswith('int') else 1
                    scaled_r = r_val * scale
                else:
                    scaled_r = r_val

                if node.op == '+=': r_val = curr_val + scaled_r
                elif node.op == '-=': r_val = curr_val - scaled_r
                elif node.op == '*=': r_val = curr_val * scaled_r
                elif node.op == '/=': r_val = int(curr_val / scaled_r)
                elif node.op == '%=': r_val = curr_val % scaled_r

            # Write out value to L-value address
            if left_type == 'int' or '*' in left_type:
                self.memory.write_int(addr, r_val)
            else:
                self.memory.write_char(addr, r_val)

            return r_val, left_type

        elif isinstance(node, CallNode):
            arg_vals = [self._evaluate_expression(a)[0] for a in node.args]
            return self._execute_call(node.func_name, arg_vals, node.line_num)

    def _evaluate_lvalue(self, node):
        """Helper that evaluates an expression as a writeable address.
        Returns a tuple (memory_address, type_str).
        """
        from parser import VarNode, SubscriptNode, UnaryOpNode
        
        if isinstance(node, VarNode):
            sym = self.symtable.lookup_var(node.name)
            if not sym:
                raise SmallCRuntimeError(f"Undeclared variable '{node.name}'", node.line_num)
            
            sym_type = sym.type + ('*' if sym.is_pointer else '')
            if sym.array_size is not None:
                # Decay to base pointer address
                return sym.address, sym.type + '*'
            return sym.address, sym_type

        elif isinstance(node, SubscriptNode):
            # Form: expr1[expr2]
            # base pointer
            base_ptr, base_type = self._evaluate_expression(node.array)
            if not base_type.endswith('*'):
                raise SmallCRuntimeError("Subscript operator applied to non-pointer type", node.line_num)
            
            # Fetch index offset
            idx_val, _ = self._evaluate_expression(node.index)
            pointed_type = base_type[:-1]
            sizeof_elem = 4 if pointed_type == 'int' else 1
            
            # Runtime Array Bounds Check (if base array size was registered)
            # Find symbol to check bounds if indexing a registered array
            from parser import VarNode
            if isinstance(node.array, VarNode):
                sym = self.symtable.lookup_var(node.array.name)
                if sym and sym.array_size is not None:
                    if idx_val < 0 or idx_val >= sym.array_size:
                        raise SmallCRuntimeError(
                            f"Array index out of bounds (index {idx_val}, size {sym.array_size}).",
                            node.line_num
                        )
            
            target_addr = base_ptr + idx_val * sizeof_elem
            return target_addr, pointed_type + '*'

        elif isinstance(node, UnaryOpNode) and node.op == '*':
            # Form: *expr
            ptr_val, base_type = self._evaluate_expression(node.expr)
            if not base_type.endswith('*'):
                raise SmallCRuntimeError("Dereference operator applied to non-pointer type", node.line_num)
            return ptr_val, base_type[:-1]

        raise SmallCRuntimeError("Expression is not a writeable L-value location", node.line_num if hasattr(node, 'line_num') else None)

    # ----------------- Function Calling -----------------

    def _execute_call(self, name, arg_values, line_num):
        """Executes a function call by loading either a built-in or user-defined function AST."""
        # 1. Check if built-in function
        func_sym = self.symtable.lookup_function(name)
        if not func_sym:
            raise SmallCRuntimeError(f"Call to undeclared function '{name}'", line_num)

        if func_sym.start_line == "[built-in]":
            # Direct execute Python binding
            ret_val = self.builtins.call(name, arg_values)
            ret_type = func_sym.return_type
            if '*' in ret_type:
                ret_type = 'char*' # Standard built-in pointers
            return (ret_val or 0), ret_type

        # 2. Else user defined function
        func_ast = self.user_functions.get(name, None)
        if not func_ast:
            raise SmallCRuntimeError(f"Missing implementation for function '{name}'", line_num)

        # Parameter count check
        if len(arg_values) != len(func_ast.params):
            raise SmallCRuntimeError(f"Function '{name}' expects {len(func_ast.params)} arguments, got {len(arg_values)}", line_num)

        # Enter local frame scope
        self.symtable.enter_scope()

        # Capture the entry stack pointer to restore on exit
        entry_sp = self.memory.sp
        total_stack_bytes = 0

        try:
            # Bind arguments to parameters on virtual stack
            for (p_type, p_name, p_is_ptr), val in zip(func_ast.params, arg_values):
                sizeof_param = 4 if (p_type == 'int' or p_is_ptr) else 1
                addr = self.memory.allocate_stack(sizeof_param)
                total_stack_bytes += sizeof_param
                
                # Register param symbol
                self.symtable.declare_var(p_name, p_type, p_is_ptr, None, addr, func_ast.line_num)
                
                # Write initial argument value to stack address
                if p_is_ptr or p_type == 'int':
                    self.memory.write_int(addr, val)
                else:
                    self.memory.write_char(addr, val)

            # Declare local variables (declared at beginning of function body)
            for var_decl in func_ast.declarations:
                # _execute_var_decl returns address and allocates on stack automatically
                sizeof_var = 4 if (var_decl.type == 'int' or var_decl.is_pointer) else 1
                if var_decl.array_size is not None:
                    sizeof_var *= var_decl.array_size
                
                self._execute_var_decl(var_decl)
                total_stack_bytes += sizeof_var

            # Execute statements in the function body
            for stmt in func_ast.statements:
                self._execute_statement(stmt)

            # Normal fallthrough (e.g. void return)
            # Reclaim virtual stack space and return 0
            self.memory.free_stack(total_stack_bytes)
            self.symtable.exit_scope()
            return 0, func_ast.return_type

        except ReturnException as r:
            # Explicit return statement caught
            self.memory.free_stack(total_stack_bytes)
            self.symtable.exit_scope()
            return r.value, func_ast.return_type

        except Exception as e:
            # Reclaim stack memory and restore scope on error before bubbling up
            self.memory.sp = entry_sp
            self.symtable.exit_scope()
            raise e
