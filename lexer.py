# lexer.py
# Lexical Analyzer with Preprocessor Support for Small-C

import re

class SmallCLexerError(Exception):
    """Exception raised for lexical analysis errors."""
    def __init__(self, message, line_num, col):
        super().__init__(f"Lexical error at line {line_num}, col {col}: {message}")
        self.message = message
        self.line_num = line_num
        self.col = col

class Token:
    def __init__(self, type_, value, line_num, col):
        self.type = type_        # Token type (e.g. 'KEYWORD', 'IDENTIFIER', 'NUMBER', 'OPERATOR')
        self.value = value      # Value of the token (string, int, etc.)
        self.line_num = line_num
        self.col = col

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)}, Line {self.line_num}:{self.col})"

class Lexer:
    # Small-C keywords
    KEYWORDS = {
        'int', 'char', 'void', 'if', 'else', 'while', 'for', 'do', 
        'break', 'continue', 'return', 'switch', 'case', 'default'
    }

    def __init__(self):
        self.macros = {}  # Store #define macro constants

    def clear_macros(self):
        self.macros.clear()

    def add_macro(self, name, value):
        self.macros[name] = value

    def parse_macro_line(self, line, line_num):
        """Helper to parse a #define directive.
        Format: #define NAME VALUE
        """
        match = re.match(r'^\s*#\s*define\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(.+)$', line)
        if match:
            name = match.group(1)
            val_str = match.group(2).strip()
            
            # Remove line comments from macro value if any
            if '//' in val_str:
                val_str = val_str.split('//')[0].strip()
            
            self.macros[name] = val_str
            return True
        return False

    def remove_comments(self, code_text):
        """Strips C-style block comments /*...*/ and C++ style line comments //...
        while preserving line numbers (replacing stripped lines with newlines).
        """
        # Remove block comments
        def block_replacer(match):
            s = match.group(0)
            return '\n' * s.count('\n')
        
        code_no_block = re.sub(r'/\*.*?\*/', block_replacer, code_text, flags=re.DOTALL)
        
        # Remove line comments
        def line_replacer(match):
            return ""
        
        code_clean = re.sub(r'//.*', line_replacer, code_no_block)
        return code_clean

    def decode_escapes(self, s, line_num, col):
        """Decodes C escape sequences in string/character literals."""
        res = []
        i = 0
        while i < len(s):
            if s[i] == '\\':
                if i + 1 >= len(s):
                    raise SmallCLexerError("Trailing backslash in escape sequence", line_num, col + i)
                esc = s[i+1]
                if esc == 'n':
                    res.append('\n')
                elif esc == 't':
                    res.append('\t')
                elif esc == '0':
                    res.append('\0')
                elif esc == '\\':
                    res.append('\\')
                elif esc == "'":
                    res.append("'")
                elif esc == '"':
                    res.append('"')
                else:
                    # Keep character as literal if unrecognized
                    res.append(esc)
                i += 2
            else:
                res.append(s[i])
                i += 1
        return "".join(res)

    def tokenize(self, code_text):
        """Tokenizes the entire source code text, handling preprocessor macros and comment removal."""
        # First process macros on a line-by-line basis
        lines = code_text.splitlines()
        clean_lines = []
        for idx, line in enumerate(lines):
            line_num = idx + 1
            if line.strip().startswith('#'):
                # Process macro definition
                if self.parse_macro_line(line, line_num):
                    # Keep line blank to preserve line numbers
                    clean_lines.append("")
                else:
                    raise SmallCLexerError(f"Invalid preprocessor directive: {line.strip()}", line_num, 1)
            else:
                clean_lines.append(line)
        
        code_without_macros = "\n".join(clean_lines)
        code_clean = self.remove_comments(code_without_macros)
        
        tokens = []
        
        # Regex patterns for matching
        # Hexadecimal constant: e.g. 0xFF or 0X1A
        hex_pattern = r'0[xX][0-9a-fA-F]+'
        # Decimal integer: e.g. 42
        dec_pattern = r'[0-9]+'
        # Identifier: e.g. val_1
        id_pattern = r'[a-zA-Z_][a-zA-Z0-9_]*'
        # Operator / delimiter: sorted by length descending to match longer ones first (e.g. '==' before '=')
        ops = [
            '==', '!=', '<=', '>=', '&&', '||', '<<', '>>', 
            '+=', '-=', '*=', '/=', '%=', '++', '--',
            '+', '-', '*', '/', '%', '<', '>', '&', '|', '^', '~', '!', '=', 
            '(', ')', '[', ']', '{', '}', ';', ',', ':', '?', '.'
        ]
        ops_pattern = "|".join(re.escape(op) for op in ops)
        
        # Combined regex pattern
        # Group 1: Hexadecimal number
        # Group 2: Decimal number
        # Group 3: Character literal (e.g. 'a' or '\n')
        # Group 4: String literal (e.g. "hello\n")
        # Group 5: Identifier / Keyword
        # Group 6: Operators and delimiters
        pattern = re.compile(
            rf'({hex_pattern})|'
            rf'({dec_pattern})|'
            rf'\'((?:[^\'\\]|\\.)*)\'|'
            rf'"((?:[^"\\]|\\.)*)"|'
            rf'({id_pattern})|'
            rf'({ops_pattern})'
        )
        
        lines_list = code_clean.splitlines()
        for idx, line in enumerate(lines_list):
            line_num = idx + 1
            col = 1
            length = len(line)
            
            while col <= length:
                # Skip whitespace
                whitespace_match = re.match(r'\s+', line[col-1:])
                if whitespace_match:
                    col += whitespace_match.end()
                    continue
                
                match = pattern.match(line, col-1)
                if not match:
                    # Check if it was an unrecognized symbol
                    raise SmallCLexerError(f"Unexpected character: {repr(line[col-1])}", line_num, col)
                
                hex_val, dec_val, char_val, str_val, ident_val, op_val = match.groups()
                start_col = col
                col += match.end() - match.start()
                
                if hex_val is not None:
                    val = int(hex_val, 16)
                    tokens.append(Token('NUMBER', val, line_num, start_col))
                
                elif dec_val is not None:
                    val = int(dec_val, 10)
                    tokens.append(Token('NUMBER', val, line_num, start_col))
                
                elif char_val is not None:
                    decoded = self.decode_escapes(char_val, line_num, start_col + 1)
                    if len(decoded) == 0:
                        val = 0  # Empty character constant e.g. '' (representing null byte)
                    elif len(decoded) == 1:
                        val = ord(decoded)
                    else:
                        raise SmallCLexerError(f"Multi-character char constant: '{char_val}'", line_num, start_col)
                    tokens.append(Token('NUMBER', val, line_num, start_col))
                
                elif str_val is not None:
                    decoded = self.decode_escapes(str_val, line_num, start_col + 1)
                    tokens.append(Token('STRING', decoded, line_num, start_col))
                
                elif ident_val is not None:
                    # Check if it's a keyword
                    if ident_val in self.KEYWORDS:
                        tokens.append(Token('KEYWORD', ident_val, line_num, start_col))
                    # Check if it's defined as a #define macro constant
                    elif ident_val in self.macros:
                        macro_val = self.macros[ident_val]
                        # Tokenize macro value dynamically
                        # If the macro is a number, we emit a NUMBER token
                        if re.match(rf'^\s*(?:{hex_pattern}|{dec_pattern})\s*$', macro_val):
                            if 'x' in macro_val.lower():
                                val = int(macro_val.strip(), 16)
                            else:
                                val = int(macro_val.strip(), 10)
                            tokens.append(Token('NUMBER', val, line_num, start_col))
                        else:
                            # If the macro is complex, we could recursively lex it, but for our assignment, 
                            # the spec says "僅需支援 #define 指令的簡單常數定義形式", so numeric constants are sufficient.
                            # Just in case, let's try lexing the macro value to support other literals
                            try:
                                sub_lexer = Lexer()
                                sub_lexer.macros = self.macros.copy()
                                sub_tokens = sub_lexer.tokenize(macro_val)
                                for sub_tok in sub_tokens:
                                    # Adjust position information
                                    sub_tok.line_num = line_num
                                    sub_tok.col = start_col
                                    tokens.append(sub_tok)
                            except Exception:
                                raise SmallCLexerError(f"Could not expand macro: {ident_val} -> {macro_val}", line_num, start_col)
                    else:
                        tokens.append(Token('IDENTIFIER', ident_val, line_num, start_col))
                
                elif op_val is not None:
                    tokens.append(Token('OPERATOR', op_val, line_num, start_col))
        
        return tokens
