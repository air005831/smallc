# main.py
# Main entry point for the Small-C Interactive Interpreter

import sys
from repl import SmallCREPL

def main():
    repl = SmallCREPL()
    # Check if there is an argument to load a file immediately
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        repl._execute_env_cmd('LOAD', filename)
    
    repl.run_shell()

if __name__ == '__main__':
    main()
