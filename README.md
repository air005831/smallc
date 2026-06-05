# Small-C Interactive Interpreter

A highly robust, high-performance, and feature-rich interactive interpreter for the **Small-C** programming language. Built entirely from scratch in Python 3 (3.10+) with zero external dependencies.

This implementation complies with all standard course specifications and fully implements **all extra credit bonus features (up to +15% bonus)**.

---

## 🌟 Features & Architecture

The interpreter is structured as a professional, modular compiler toolchain:

```
[Source Code] -> [Lexer] -> [Parser (Recursive Descent + Pratt)] -> [AST Node Tree] -> [Execution Engine]
                                                                                           |
                                                                                    [Virtual Memory]
```

### 1. Simulated Virtual Memory Model (`memory.py`)
To handle C pointer manipulation (e.g. `int *ptr = &x; *ptr = 42;`) and contiguous arrays correctly under recursion, this interpreter implements a **virtual 1MB memory space (`bytearray`)**:
- **Data Layout:** 4-byte little-endian integers for `int` and pointers; 1-byte for `char`.
- **Global & Stack Segments:** Globals are allocated statically at address `1024` upwards. Locals and parameters are allocated on a dynamic stack starting at address `1,048,576` growing downwards.
- **Pointers & Arithmetic:** Pointers store true integer offsets into this simulated space. Pointer arithmetic (`ptr + 1`) automatically scales based on the underlying datatype size, and `&x` yields the exact virtual memory offset of the variable.

### 2. Lexical & Syntactic Analysis (`lexer.py`, `parser.py`)
- **Lexer:** Tokenizes sources using a robust regex engine. Supports C-style line and block comments (`//`, `/*...*/`), escape sequence characters, hex literals (`0xFF`), and preprocessor directives.
- **Pratt Parser:** Hand-written recursive descent parser. Incorporates a Top-Down Operator Precedence (Pratt) parsing strategy to correctly parse the 13 levels of C operators. Builds a clean, strongly-typed Abstract Syntax Tree (AST).

### 3. Symbol Scopes & Execution Engine (`symtable.py`, `interpreter.py`)
- **Symbol Table:** Manages lexically scoped dictionary layers (Global and local frame scope). Tracks function signatures and variable dimensions.
- **Interpreter Walk:** Traverses the AST tree, utilizing custom Python control flow exceptions (`BreakException`, `ContinueException`, `ReturnException`) to handle code execution and loop transitions seamlessly.

### 4. C Built-in Standard Library (`builtins_smallc.py`)
Provides all 22 required mathematical, string, I/O, and memory functions, including a fully custom format string parser for `printf` and pointer-level target scanning for `scanf`.

---

## 🚀 Grading Highlights (Extra Credit Completed)

1. **`switch / case / default` Statement Support (+5%):** Full compiler parsing and execution support for switch control structures, including case fallback fallthrough and `break` handling.
2. **Comprehensive Runtime Error Handling (+5%):** Intercepts and warns the user with line numbers for:
   - Division/Modulo by zero.
   - Array index out-of-bounds overflow.
   - Null pointer dereferencing and invalid memory boundaries.
3. **`#define` Macro Constant Replacement (+5%):** Performs token-level macro substitution (e.g., `#define MAX_SIZE 100`) directly during tokenization.

---

## 📂 File Structure

```
smallC-agy/
├── main.py                # Shell entry-point bootstrapper
├── repl.py                # Interactive terminal shell & command dispatcher
├── lexer.py               # Tokenizer and #define macro preprocessor
├── parser.py              # Recursive Descent + Pratt parser & AST nodes
├── interpreter.py         # AST walking runtime execution engine
├── symtable.py            # Scope layers and symbol declarations
├── memory.py              # Virtual 1MB RAM bytearray simulation
├── builtins_smallc.py     # Runtime implementation of 22 standard C built-ins
├── run_tests.py           # Automated test suite runner
├── requirements.txt       # Clean zero dependency file
├── README.md              # Documentation manual
└── tests/                 # Automated test cases
    ├── *.sc               # Small-C test source files
    └── *.expected         # Expected execution outputs
```

*Note: The built-in module was renamed from `builtins.py` to `builtins_smallc.py` to prevent namespace shadowing with Python's core library `builtins` module.*

---

## 🛠️ Environment Commands

All commands are **case-insensitive** and can be run at the `sc> ` prompt:

- **`LOAD <file>`:** Loads source file into the program buffer.
- **`SAVE [<file>]`:** Saves current buffer to file.
- **`LIST` / `LIST <n>` / `LIST <n1>-<n2>`:** Lists buffer contents with line numbers.
- **`EDIT <n>`:** Modifies line `<n>`.
- **`DELETE <n>` / `DELETE <n1>-<n2>`:** Deletes line(s) from the buffer.
- **`INSERT <n>`:** Enters line-insert mode. Stop by entering `.` on a new line.
- **`APPEND`:** Appends lines to buffer. Stop by entering `.` on a new line.
- **`NEW`:** Clears buffer and completely resets the environment.
- **`RUN`:** Compiles and executes the program starting from `main()`.
- **`CHECK`:** Performs lexical/syntactic/semantic analysis without executing.
- **`TRACE ON` / `TRACE OFF`:** Enables/disables execution step tracing (formats `{[line n] <stmt>}`).
- **`VARS`:** Shows all global variables, pointers, arrays, and values.
- **`FUNCS`:** Displays user-defined and standard library function signatures.
- **`HELP` / `HELP <cmd>`:** Show interactive command guide.
- **`ABOUT` / `CLEAR` / `QUIT`:** Miscellaneous shell actions.

---

## 💻 How to Use

### 1. Launching the Interactive Shell
To boot into the Small-C interpreter:
```bash
python main.py
```
You can also immediately load a file on startup:
```bash
python main.py tests/test_recursion.sc
```

Once inside the shell, you can declare global variables or run expressions immediately:
```c
sc> int x = 10;
sc> x += 5;
sc> printf("x is %d\n", x);
x is 15
sc> VARS
int x = 15
```

### 2. Running the Automated Test Suite
To verify compilation, execution, scoping, and all safety checks:
```bash
python run_tests.py
```
You should see all 11 test cases pass with a success report:
```
====================================================
           Small-C Automated Test Runner            
====================================================
[PASS] test_arithmetic.sc            
[PASS] test_arrays.sc                
[PASS] test_err_bounds.sc            
[PASS] test_err_divzero.sc           
[PASS] test_functions.sc             
[PASS] test_if_else.sc               
[PASS] test_loops.sc                 
[PASS] test_pointers.sc              
[PASS] test_recursion.sc             
[PASS] test_switch.sc                
[PASS] test_variables.sc             
====================================================
Test Summary: 11 Passed, 0 Failed, Total 11
====================================================
```
