# run_tests.py
# Automated Test Suite Runner for Small-C Interpreter

import os
import sys
import io
from lexer import Lexer, SmallCLexerError
from parser import Parser, SmallCParserError
from interpreter import Interpreter, SmallCRuntimeError
from symtable import SymbolTable, SmallCSemanticError
from memory import VirtualMemory

def run_test_file(sc_path):
    """Compiles and runs a single .sc file, capturing its stdout and any runtime errors."""
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    memory = VirtualMemory()
    symtable = SymbolTable()
    lexer = Lexer()
    interpreter = Interpreter(memory, symtable)

    error_occured = None
    try:
        with open(sc_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Split source into lines for tracing/error lookups if needed
        buffer_lines = source.splitlines()
        interpreter.set_source_lines(buffer_lines)
        
        # Lexical Analysis
        tokens = lexer.tokenize(source)
        
        # Parsing
        parser = Parser(tokens)
        ast_root = parser.parse()
        
        # Execution
        interpreter.execute_program(ast_root)
        
    except (SmallCLexerError, SmallCParserError, SmallCSemanticError, SmallCRuntimeError) as e:
        # Print caught compiler/runtime exception to output buffer to match expected errors
        sys.stdout.write(f"\n{str(e)}\n")
        error_occured = e
    except Exception as e:
        sys.stdout.write(f"\nUnexpected Interpreter Error: {str(e)}\n")
        error_occured = e
    finally:
        actual_output = sys.stdout.getvalue()
        sys.stdout = old_stdout

    return actual_output, error_occured

def main():
    tests_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests')
    if not os.path.exists(tests_dir):
        print(f"Creating tests directory at: {tests_dir}")
        os.makedirs(tests_dir)
        print("Please place .sc and .expected files inside the tests directory.")
        return

    # Find all .sc files
    test_files = sorted([f for f in os.listdir(tests_dir) if f.endswith('.sc')])
    if not test_files:
        print("No .sc test files found in tests/ directory.")
        return

    print("====================================================")
    print("           Small-C Automated Test Runner            ")
    print("====================================================")
    
    passed_count = 0
    failed_count = 0

    for tf in test_files:
        sc_path = os.path.join(tests_dir, tf)
        expected_path = os.path.join(tests_dir, tf.replace('.sc', '.expected'))
        
        test_name = tf
        if not os.path.exists(expected_path):
            print(f"[-] {test_name:<30} SKIPPED (Missing .expected file)")
            continue

        with open(expected_path, 'r', encoding='utf-8') as f:
            expected_output = f.read()

        actual_output, err = run_test_file(sc_path)

        # Standardise and strip trailing whitespaces/newlines for robust comparison
        expected_lines = [l.strip() for l in expected_output.strip().splitlines() if l.strip()]
        actual_lines = [l.strip() for l in actual_output.strip().splitlines() if l.strip()]

        is_match = (expected_lines == actual_lines)

        if is_match:
            print(f"[PASS] {test_name:<30}")
            passed_count += 1
        else:
            print(f"[FAIL] {test_name:<30}")
            failed_count += 1
            print("--- Expected Output ---")
            print("\n".join(expected_lines))
            print("--- Actual Output ---")
            print("\n".join(actual_lines))
            print("-----------------------")
            print()

    print("====================================================")
    print(f"Test Summary: {passed_count} Passed, {failed_count} Failed, Total {passed_count + failed_count}")
    print("====================================================")
    
    if failed_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
