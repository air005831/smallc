# repl.py
# Interactive REPL Environment for Small-C

import os
import sys
from lexer import Lexer, SmallCLexerError
from parser import Parser, SmallCParserError
from interpreter import Interpreter, SmallCRuntimeError
from symtable import SymbolTable, SmallCSemanticError
from memory import VirtualMemory, SmallCMemoryError

class SmallCREPL:
    VERSION = "1.0"
    COURSE = "System Software Final Project, Spring 2026"
    
    def __init__(self):
        self.memory = VirtualMemory()
        self.symtable = SymbolTable()
        self.lexer = Lexer()
        self.interpreter = Interpreter(self.memory, self.symtable)
        
        self.buffer = []           # Program buffer (1-indexed lines, stored as list of strings)
        self.current_file = None   # Current filename loaded
        self.is_dirty = False      # Unsaved changes flag

    def welcome(self):
        print("============================================")
        print(f"Small-C Interactive Interpreter v{self.VERSION}")
        print(f"{self.COURSE}")
        print("============================================")
        print("Type 'HELP' for a list of commands.")
        print()

    def run_shell(self):
        """Starts the main REPL execution loop."""
        self.welcome()
        
        while True:
            try:
                prompt = "sc> "
                sys.stdout.write(prompt)
                sys.stdout.flush()
                
                line = sys.stdin.readline()
                if not line:
                    break # EOF
                
                line_str = line.strip()
                if not line_str:
                    continue
                
                # Check for environment command (case insensitive)
                tokens = line_str.split(maxsplit=1)
                cmd = tokens[0].upper()
                arg = tokens[1] if len(tokens) > 1 else ""
                
                if cmd in {
                    'LOAD', 'SAVE', 'LIST', 'EDIT', 'DELETE', 'INSERT', 'APPEND', 
                    'NEW', 'RUN', 'CHECK', 'TRACE', 'VARS', 'FUNCS', 'HELP', 
                    'ABOUT', 'CLEAR', 'QUIT', 'EXIT'
                }:
                    if cmd == 'QUIT' or cmd == 'EXIT':
                        if self._confirm_dirty("exit the interpreter"):
                            print("Goodbye.")
                            break
                    else:
                        self._execute_env_cmd(cmd, arg)
                else:
                    # Else treat as direct interactive Small-C statement
                    self._execute_interactive_code(line_str)
                    
            except KeyboardInterrupt:
                print("\nOperation cancelled. Type 'QUIT' to exit.")
            except Exception as e:
                print(f"Error: {e}")

    def _confirm_dirty(self, action_desc):
        """Helper to prompt user if they have unsaved buffer changes."""
        if self.is_dirty:
            sys.stdout.write(f"Warning: You have unsaved changes. Are you sure you want to {action_desc}? (y/n): ")
            sys.stdout.flush()
            ans = sys.stdin.readline().strip().lower()
            return ans.startswith('y')
        return True

    def _execute_env_cmd(self, cmd, arg):
        # 1. LOAD <filename>
        if cmd == 'LOAD':
            if not arg:
                print("Usage: LOAD <filename>")
                return
            if not self._confirm_dirty(f"overwrite buffer and load '{arg}'"):
                return
            filename = arg.strip('"').strip("'")
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.buffer = [line.rstrip('\r\n') for line in f.readlines()]
                self.current_file = filename
                self.is_dirty = False
                print(f"Loaded {len(self.buffer)} lines from '{filename}'.")
            except FileNotFoundError:
                print(f"Error: File '{filename}' not found.")
            except Exception as e:
                print(f"Error reading file: {e}")

        # 2. SAVE <filename>
        elif cmd == 'SAVE':
            save_file = arg.strip('"').strip("'") if arg else self.current_file
            if not save_file:
                print("Usage: SAVE <filename>")
                return
            try:
                with open(save_file, 'w', encoding='utf-8') as f:
                    for line in self.buffer:
                        f.write(line + '\n')
                self.current_file = save_file
                self.is_dirty = False
                print(f"Saved {len(self.buffer)} lines to '{save_file}'.")
            except Exception as e:
                print(f"Error writing to file: {e}")

        # 3. LIST
        elif cmd == 'LIST':
            if not self.buffer:
                print("Buffer is empty.")
                return
            
            # Check for range: e.g. LIST 5 or LIST 4-8
            if not arg:
                # List entire buffer
                for idx, line in enumerate(self.buffer):
                    print(f"{idx+1:4}: {line}")
            else:
                arg_clean = arg.strip()
                if '-' in arg_clean:
                    # Range list
                    try:
                        n1_str, n2_str = arg_clean.split('-')
                        n1, n2 = int(n1_str), int(n2_str)
                        if n1 < 1 or n2 > len(self.buffer) or n1 > n2:
                            raise ValueError()
                        for idx in range(n1 - 1, n2):
                            print(f"{idx+1:4}: {self.buffer[idx]}")
                    except ValueError:
                        print(f"Error: Invalid range. Buffer has {len(self.buffer)} lines.")
                else:
                    # Single line list
                    try:
                        n = int(arg_clean)
                        if n < 1 or n > len(self.buffer):
                            raise ValueError()
                        print(f"{n:4}: {self.buffer[n-1]}")
                    except ValueError:
                        print(f"Error: Invalid line number. Buffer has {len(self.buffer)} lines.")

        # 4. EDIT <n>
        elif cmd == 'EDIT':
            if not arg:
                print("Usage: EDIT <n>")
                return
            try:
                n = int(arg.strip())
                if n < 1 or n > len(self.buffer):
                    raise ValueError()
                # Print original line
                print(f"{n}: {self.buffer[n-1]}")
                sys.stdout.write("New content: ")
                sys.stdout.flush()
                new_line = sys.stdin.readline().rstrip('\r\n')
                if new_line: # If empty Enter, keep unchanged
                    self.buffer[n-1] = new_line
                    self.is_dirty = True
            except ValueError:
                print(f"Error: Invalid line number. Buffer has {len(self.buffer)} lines.")

        # 5. DELETE <n> or DELETE <n1>-<n2>
        elif cmd == 'DELETE':
            if not arg:
                print("Usage: DELETE <n> or DELETE <n1>-<n2>")
                return
            arg_clean = arg.strip()
            if '-' in arg_clean:
                try:
                    n1_str, n2_str = arg_clean.split('-')
                    n1, n2 = int(n1_str), int(n2_str)
                    if n1 < 1 or n2 > len(self.buffer) or n1 > n2:
                        raise ValueError()
                    # Delete lines in reverse order to keep indices correct
                    for idx in range(n2 - 1, n1 - 2, -1):
                        self.buffer.pop(idx)
                    self.is_dirty = True
                except ValueError:
                    print(f"Error: Invalid range. Buffer has {len(self.buffer)} lines.")
            else:
                try:
                    n = int(arg_clean)
                    if n < 1 or n > len(self.buffer):
                        raise ValueError()
                    self.buffer.pop(n-1)
                    self.is_dirty = True
                except ValueError:
                    print(f"Error: Invalid line number.")

        # 6. INSERT <n>
        elif cmd == 'INSERT':
            if not arg:
                print("Usage: INSERT <n>")
                return
            try:
                n = int(arg.strip())
                if n < 1 or n > len(self.buffer) + 1:
                    print(f"Error: Insert position out of bounds (1 to {len(self.buffer)+1}).")
                    return
                
                print("Entering insert mode. Enter '.' on a line by itself to finish.")
                idx = n - 1
                while True:
                    sys.stdout.write(f"{idx+1:4}> ")
                    sys.stdout.flush()
                    in_line = sys.stdin.readline().rstrip('\r\n')
                    if in_line == '.':
                        break
                    self.buffer.insert(idx, in_line)
                    idx += 1
                self.is_dirty = True
            except ValueError:
                print("Error: Invalid line number.")

        # 7. APPEND
        elif cmd == 'APPEND':
            print("Entering append mode. Enter '.' on a line by itself to finish.")
            while True:
                sys.stdout.write(f"{len(self.buffer)+1:4}> ")
                sys.stdout.flush()
                in_line = sys.stdin.readline().rstrip('\r\n')
                if in_line == '.':
                    break
                self.buffer.append(in_line)
            self.is_dirty = True

        # 8. NEW
        elif cmd == 'NEW':
            if not self._confirm_dirty("clear the program buffer"):
                return
            self.buffer.clear()
            self.current_file = None
            self.is_dirty = False
            self.interpreter.reset_all()
            print("All cleared.")

        # 9. RUN
        elif cmd == 'RUN':
            if not self.buffer:
                print("Error: Program buffer is empty.")
                return
            
            source_code = "\n".join(self.buffer)
            self._compile_and_execute(source_code)

        # 10. CHECK
        elif cmd == 'CHECK':
            if not self.buffer:
                print("Error: Program buffer is empty.")
                return
            source_code = "\n".join(self.buffer)
            self._check_program(source_code)

        # 11. TRACE ON/OFF
        elif cmd == 'TRACE':
            arg_upper = arg.upper().strip()
            if arg_upper == 'ON':
                self.interpreter.trace_enabled = True
                print("Trace mode enabled.")
            elif arg_upper == 'OFF':
                self.interpreter.trace_enabled = False
                print("Trace mode disabled.")
            else:
                print("Usage: TRACE ON or TRACE OFF")

        # 12. VARS
        elif cmd == 'VARS':
            self._print_vars()

        # 13. FUNCS
        elif cmd == 'FUNCS':
            self._print_funcs()

        # 14. HELP
        elif cmd == 'HELP':
            self._print_help(arg)

        # 15. ABOUT
        elif cmd == 'ABOUT':
            print("--------------------------------------------")
            print(f"Small-C Interactive Interpreter v{self.VERSION}")
            print(f"Developed for course: {self.COURSE}")
            print("Author: Final Project Team (Antigravity)")
            print("Features: SCOPED MEMORY, POINTER SCALING,")
            print("          TRACE DEBUG, SW/CASE, MACROS.")
            print("--------------------------------------------")

        # 16. CLEAR
        elif cmd == 'CLEAR':
            # Cross-platform screen clear
            os.system('cls' if os.name == 'nt' else 'clear')

    def _execute_interactive_code(self, source_line):
        """Compiles and executes a single statement entered directly into the REPL."""
        try:
            # 1. Lexical Analysis
            tokens = self.lexer.tokenize(source_line)
            if not tokens:
                return
            
            # 2. Syntax Parsing
            parser = Parser(tokens)
            node = parser.parse_interactive_statement()
            
            # 3. Execution
            self.interpreter.set_source_lines([source_line])
            ret = self.interpreter.execute_interactive_node(node)
            if ret is not None:
                # If expression statement returned something, print it (in C this is usually ignored, 
                # but let's print if it evaluates to an integer/char to be convenient in REPL)
                pass
        
        except SmallCLexerError as e:
            print(e)
        except SmallCParserError as e:
            print(e)
        except SmallCSemanticError as e:
            print(e)
        except SmallCRuntimeError as e:
            print(e)
        except Exception as e:
            print(f"Internal Error: {e}")

    def _compile_and_execute(self, source_code):
        try:
            # Reset state for run
            self.interpreter.reset_runtime()
            self.lexer.clear_macros()
            
            # Tokenize
            tokens = self.lexer.tokenize(source_code)
            
            # Parse
            parser = Parser(tokens)
            ast_root = parser.parse()
            
            # Set source mapping for TRACE ON
            self.interpreter.set_source_lines(self.buffer)
            
            # Run
            val = self.interpreter.execute_program(ast_root)
            print(f"Program exited with return value {val}.")
            
        except SmallCLexerError as e:
            print(e)
        except SmallCParserError as e:
            print(e)
        except SmallCSemanticError as e:
            print(e)
        except SmallCRuntimeError as e:
            print(e)
        except Exception as e:
            print(f"Execution failed due to: {e}")

    def _check_program(self, source_code):
        """Tokenize and parse to check for lexical/syntactic/semantic errors without running."""
        try:
            # Reset symbol table statically
            self.symtable.reset_all()
            self.lexer.clear_macros()
            
            # Tokenize
            tokens = self.lexer.tokenize(source_code)
            
            # Parse
            parser = Parser(tokens)
            ast_root = parser.parse()
            
            # Run semantic phase (register symbols globally to detect duplicate declarations)
            for decl in ast_root.declarations:
                from parser import FuncDefNode, VarDeclNode
                if isinstance(decl, FuncDefNode):
                    params_proto = [(p[0], p[1], p[2]) for p in decl.params]
                    self.symtable.declare_function(decl.name, decl.return_type, params_proto, decl.line_num)
                elif isinstance(decl, VarDeclNode):
                    # Validate static declarations
                    sizeof_type = 4 if decl.type == 'int' else 1
                    is_array = decl.array_size is not None
                    self.symtable.declare_var(decl.name, decl.type, decl.is_pointer, decl.array_size, 0, decl.line_num)
            
            # Check if main exists
            if not self.symtable.lookup_function('main'):
                print("Error: Function 'main' is not defined.")
            else:
                print("No errors found.")
                
        except SmallCLexerError as e:
            print(e)
        except SmallCParserError as e:
            print(e)
        except SmallCSemanticError as e:
            print(e)
        except Exception as e:
            print(f"Validation failed: {e}")

    def _print_vars(self):
        """Prints all variables in the active global scope in the exact requested format."""
        global_scope = self.symtable.scopes[0]
        if not global_scope:
            print("No global variables defined.")
            return

        for name, sym in sorted(global_scope.items()):
            # Determine suffix declaration
            ptr_str = "*" if sym.is_pointer else ""
            
            if sym.array_size is not None:
                # Read array elements
                sizeof_elem = 4 if sym.type == 'int' else 1
                elements = []
                # Print up to 10 elements
                display_len = min(sym.array_size, 10)
                for idx in range(display_len):
                    elem_addr = sym.address + idx * sizeof_elem
                    try:
                        val = self.memory.read_int(elem_addr) if sym.type == 'int' else self.memory.read_char(elem_addr)
                        elements.append(str(val))
                    except SmallCMemoryError:
                        elements.append("?")
                
                # Check for ellipses
                if sym.array_size > 10:
                    elements.append("...")
                
                elems_str = ", ".join(elements)
                print(f"{sym.type} {sym.name}[{sym.array_size}] = {{{elems_str}}}")
            
            else:
                # Read scalar/pointer
                try:
                    val = self.memory.read_int(sym.address) if (sym.is_pointer or sym.type == 'int') else self.memory.read_char(sym.address)
                except SmallCMemoryError:
                    val = "?"
                
                if sym.is_pointer:
                    print(f"{sym.type} *{sym.name} = {val}")
                elif sym.type == 'char':
                    # Format as: char ch = 65 ('A')
                    ch_char = chr(val & 0xFF) if 32 <= (val & 0xFF) <= 126 else '\\0'
                    print(f"char {sym.name} = {val} ('{ch_char}')")
                else:
                    print(f"int {sym.name} = {val}")

    def _print_funcs(self):
        """Lists defined and built-in functions."""
        user_funcs = []
        builtin_funcs = []
        
        for name, sym in sorted(self.symtable.functions.items()):
            # Param listing e.g. void bubble_sort(int *arr, int n)
            param_strs = []
            for p_type, p_name, p_is_ptr in sym.params:
                p_ptr = "*" if p_is_ptr else ""
                param_strs.append(f"{p_type} {p_ptr}{p_name}")
            
            param_list = ", ".join(param_strs)
            func_sig = f"{sym.return_type} {name}({param_list})"
            
            if sym.start_line == "[built-in]":
                builtin_funcs.append((func_sig, "[built-in]"))
            else:
                user_funcs.append((func_sig, f"line {sym.start_line}"))

        # Print user defined
        for sig, line in user_funcs:
            print(f"{sig:<35} {line}")
            
        print("--- built-in functions ---")
        for sig, line in builtin_funcs:
            print(f"{sig:<35} {line}")

    def _print_help(self, cmd_arg):
        help_dict = {
            'LOAD': "LOAD <filename> : Loads Small-C source lines into program buffer.",
            'SAVE': "SAVE <filename> : Saves program buffer contents into file.",
            'LIST': "LIST [<range>]  : Displays lines of buffer with numbers. Range can be '<n>' or '<n1>-<n2>'.",
            'EDIT': "EDIT <n>        : Overwrites line <n> content in buffer.",
            'DELETE': "DELETE <range>  : Deletes lines in buffer. Range can be '<n>' or '<n1>-<n2>'.",
            'INSERT': "INSERT <n>      : Inserts lines before index <n>. Stop by typing '.' on its own line.",
            'APPEND': "APPEND          : Appends lines to end of buffer. Stop by typing '.' on its own line.",
            'NEW': "NEW             : Clears the program buffer and resets interpreter environment.",
            'RUN': "RUN             : Parses and executes the program in buffer starting from main().",
            'CHECK': "CHECK           : Parses and performs syntax/semantic checks on the buffer.",
            'TRACE': "TRACE ON/OFF    : Enables or disables line-by-line source tracing before execution.",
            'VARS': "VARS            : Lists all active global variables, pointers, arrays and values.",
            'FUNCS': "FUNCS           : Lists all user defined and C standard library built-in functions.",
            'ABOUT': "ABOUT           : Shows interpreter version, course, semester, and developer info.",
            'CLEAR': "CLEAR           : Clears the terminal screen.",
            'QUIT': "QUIT or EXIT    : Safely terminates the Small-C interpreter shell."
        }
        
        arg_upper = cmd_arg.upper().strip()
        if arg_upper in help_dict:
            print(help_dict[arg_upper])
        else:
            print("Available environment commands (case-insensitive):")
            for c, desc in sorted(help_dict.items()):
                print(f"  {c:<10} - {desc.split(':', 1)[1].strip() if ':' in desc else desc}")
            print("\nYou can also type Small-C declarations (e.g. 'int x = 5;') or statements directly to run them.")
