# parser.py
# Recursive Descent Parser for Small-C

class SmallCParserError(Exception):
    """Exception raised for syntax analysis errors."""
    def __init__(self, message, line_num, col):
        super().__init__(f"Syntax error at line {line_num}, col {col}: {message}")
        self.message = message
        self.line_num = line_num
        self.col = col

# ----------------- AST Node Definitions -----------------

class ASTNode:
    pass

class ProgramNode(ASTNode):
    def __init__(self, declarations):
        self.declarations = declarations  # List of VarDeclNode or FuncDefNode

class VarDeclNode(ASTNode):
    def __init__(self, type_, name, is_pointer, array_size, initializer, line_num, col):
        self.type = type_                 # 'int', 'char', 'void'
        self.name = name                 # String
        self.is_pointer = is_pointer     # Bool
        self.array_size = array_size     # Int or None (if not array)
        self.initializer = initializer   # ExprNode, list of ExprNodes, or String literal
        self.line_num = line_num
        self.col = col

class FuncDefNode(ASTNode):
    def __init__(self, return_type, name, params, declarations, statements, line_num, col):
        self.return_type = return_type   # 'int', 'char', 'void'
        self.name = name                 # String
        self.params = params             # List of (type_, name, is_pointer)
        self.declarations = declarations  # List of local VarDeclNodes
        self.statements = statements     # List of statement nodes (BlockNode, IfNode, etc.)
        self.line_num = line_num
        self.col = col

class BlockNode(ASTNode):
    def __init__(self, statements, line_num, col):
        self.statements = statements
        self.line_num = line_num
        self.col = col

class ExprStmtNode(ASTNode):
    def __init__(self, expr, line_num, col):
        self.expr = expr
        self.line_num = line_num
        self.col = col

class IfNode(ASTNode):
    def __init__(self, cond, then_branch, else_branch, line_num, col):
        self.cond = cond                 # ExprNode
        self.then_branch = then_branch   # StmtNode
        self.else_branch = else_branch   # StmtNode or None
        self.line_num = line_num
        self.col = col

class WhileNode(ASTNode):
    def __init__(self, cond, body, line_num, col):
        self.cond = cond
        self.body = body                 # StmtNode
        self.line_num = line_num
        self.col = col

class DoWhileNode(ASTNode):
    def __init__(self, body, cond, line_num, col):
        self.body = body
        self.cond = cond
        self.line_num = line_num
        self.col = col

class ForNode(ASTNode):
    def __init__(self, init, cond, incr, body, line_num, col):
        self.init = init                 # ExprNode or VarDeclNode or None
        self.cond = cond                 # ExprNode or None
        self.incr = incr                 # ExprNode or None
        self.body = body                 # StmtNode
        self.line_num = line_num
        self.col = col

class BreakNode(ASTNode):
    def __init__(self, line_num, col):
        self.line_num = line_num
        self.col = col

class ContinueNode(ASTNode):
    def __init__(self, line_num, col):
        self.line_num = line_num
        self.col = col

class ReturnNode(ASTNode):
    def __init__(self, expr, line_num, col):
        self.expr = expr                 # ExprNode or None
        self.line_num = line_num
        self.col = col

class SwitchNode(ASTNode):
    def __init__(self, expr, cases, default_case, line_num, col):
        self.expr = expr                 # ExprNode
        self.cases = cases               # List of CaseNode
        self.default_case = default_case # DefaultNode or None
        self.line_num = line_num
        self.col = col

class CaseNode(ASTNode):
    def __init__(self, val, statements, line_num, col):
        self.val = val                   # Int constant
        self.statements = statements     # List of statements
        self.line_num = line_num
        self.col = col

class DefaultNode(ASTNode):
    def __init__(self, statements, line_num, col):
        self.statements = statements
        self.line_num = line_num
        self.col = col

# Expressions
class ExprNode(ASTNode):
    pass

class AssignNode(ExprNode):
    def __init__(self, left, op, right, line_num, col):
        self.left = left                 # L-value node (VarNode, SubscriptNode, DerefNode)
        self.op = op                     # '=', '+=', '-=', '*=', '/=', '%='
        self.right = right
        self.line_num = line_num
        self.col = col

class BinOpNode(ExprNode):
    def __init__(self, left, op, right, line_num, col):
        self.left = left
        self.op = op                     # '+', '-', '*', etc.
        self.right = right
        self.line_num = line_num
        self.col = col

class UnaryOpNode(ExprNode):
    def __init__(self, op, expr, is_postfix, line_num, col):
        self.op = op                     # '-', '!', '~', '*', '&', '++', '--'
        self.expr = expr
        self.is_postfix = is_postfix
        self.line_num = line_num
        self.col = col

class VarNode(ExprNode):
    def __init__(self, name, line_num, col):
        self.name = name                 # String
        self.line_num = line_num
        self.col = col

class ConstNode(ExprNode):
    def __init__(self, type_, value, line_num, col):
        self.type = type_                 # 'int', 'char', 'string'
        self.value = value               # Python value (int or string)
        self.line_num = line_num
        self.col = col

class SubscriptNode(ExprNode):
    def __init__(self, array, index, line_num, col):
        self.array = array               # ExprNode
        self.index = index               # ExprNode
        self.line_num = line_num
        self.col = col

class CallNode(ExprNode):
    def __init__(self, func_name, args, line_num, col):
        self.func_name = func_name       # String
        self.args = args                 # List of ExprNode
        self.line_num = line_num
        self.col = col


# ----------------- Parser Implementation -----------------

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self, offset=0):
        if self.pos + offset < len(self.tokens):
            return self.tokens[self.pos + offset]
        return None

    def match(self, type_, value=None):
        tok = self.peek()
        if not tok:
            return False
        if tok.type == type_ and (value is None or tok.value == value):
            self.pos += 1
            return tok
        return False

    def expect(self, type_, value=None, msg=None):
        tok = self.peek()
        if not tok:
            raise SmallCParserError(
                msg or f"Expected {type_} {f'({value})' if value else ''}, got End of File",
                self.tokens[-1].line_num if self.tokens else 1,
                self.tokens[-1].col if self.tokens else 1
            )
        match_tok = self.match(type_, value)
        if not match_tok:
            raise SmallCParserError(
                msg or f"Expected {type_} {f'({value})' if value else ''}, got {tok.type} ({tok.value})",
                tok.line_num,
                tok.col
            )
        return match_tok

    def parse(self):
        """Entry point: parses a full program (list of global declarations/functions)."""
        declarations = []
        while self.peek():
            declarations.append(self.parse_global_declaration())
        return ProgramNode(declarations)

    def parse_interactive_statement(self):
        """Parses a single line of input for interactive shell.
        Can be:
        1. Variable declaration e.g. `int x = 10;`
        2. Block or control flow or regular statement
        """
        tok = self.peek()
        if not tok:
            return None
        
        # Check if it starts with declaration keywords
        if tok.type == 'KEYWORD' and tok.value in {'int', 'char', 'void'}:
            # Check if it is a function definition or global var declaration
            # (In interactive mode, a variable declared in the root behaves as a global declaration).
            # Look ahead: e.g. `int x` vs `int add(...)`
            lookahead = self.peek(1)
            is_func = False
            i = 1
            # Skip pointers e.g. `int *p`
            while self.peek(i) and self.peek(i).type == 'OPERATOR' and self.peek(i).value == '*':
                i += 1
            if self.peek(i) and self.peek(i).type == 'IDENTIFIER':
                if self.peek(i+1) and self.peek(i+1).type == 'OPERATOR' and self.peek(i+1).value == '(':
                    is_func = True
            
            if is_func:
                return self.parse_global_declaration()
            else:
                return self.parse_var_declaration()
        else:
            return self.parse_statement()

    def parse_global_declaration(self):
        """Parses a global variable declaration or a function definition."""
        tok = self.peek()
        if not tok or tok.type != 'KEYWORD' or tok.value not in {'int', 'char', 'void'}:
            raise SmallCParserError("Expected type specifier (int, char, void)", tok.line_num if tok else 1, tok.col if tok else 1)
        
        type_tok = self.pos
        type_str = self.peek().value
        self.pos += 1
        
        is_pointer = False
        while self.match('OPERATOR', '*'):
            is_pointer = True
        
        id_tok = self.expect('IDENTIFIER', msg="Expected identifier in global declaration")
        name = id_tok.value
        
        # Determine if it's a function definition or variable declaration
        next_tok = self.peek()
        if next_tok and next_tok.type == 'OPERATOR' and next_tok.value == '(':
            # Function definition
            self.pos += 1  # consume '('
            
            params = []
            if not self.match('OPERATOR', ')'):
                while True:
                    # check if void parameter list e.g. add(void)
                    p_tok = self.peek()
                    if p_tok and p_tok.type == 'KEYWORD' and p_tok.value == 'void':
                        self.pos += 1
                        # If next is ')', then it was add(void)
                        if self.peek() and self.peek().type == 'OPERATOR' and self.peek().value == ')':
                            break
                        else:
                            # It's an error or void type param (invalid in Small-C, but let's be safe)
                            raise SmallCParserError("Invalid parameter type 'void'", p_tok.line_num, p_tok.col)
                    
                    p_type_tok = self.expect('KEYWORD', msg="Expected type specifier in parameter list")
                    p_type = p_type_tok.value
                    if p_type not in {'int', 'char'}:
                        raise SmallCParserError(f"Invalid parameter type '{p_type}'", p_type_tok.line_num, p_type_tok.col)
                    
                    p_is_ptr = False
                    while self.match('OPERATOR', '*'):
                        p_is_ptr = True
                    
                    p_id = self.expect('IDENTIFIER', msg="Expected identifier in parameter list")
                    params.append((p_type, p_id.value, p_is_ptr))
                    
                    if self.match('OPERATOR', ')'):
                        break
                    self.expect('OPERATOR', ',', msg="Expected ',' or ')' in parameter list")
            
            self.expect('OPERATOR', '{', msg="Expected '{' to start function body")
            
            # Local declarations must be at the very start of the function body
            local_declarations = []
            while True:
                p_tok = self.peek()
                if p_tok and p_tok.type == 'KEYWORD' and p_tok.value in {'int', 'char'}:
                    local_declarations.append(self.parse_var_declaration())
                else:
                    break
            
            # Followed by statements
            statements = []
            while not self.match('OPERATOR', '}'):
                if not self.peek():
                    raise SmallCParserError(f"Unclosed function body for function '{name}'", id_tok.line_num, id_tok.col)
                statements.append(self.parse_statement())
            
            return FuncDefNode(type_str, name, params, local_declarations, statements, type_tok, id_tok.col)
        
        else:
            # Global variable declaration (rewind type specifier and let parse_var_declaration do it)
            self.pos = type_tok
            return self.parse_var_declaration()

    def parse_var_declaration(self):
        """Parses variable declarations e.g.:
        int x;
        int y = 10;
        char s[20];
        char str[80] = "hello";
        int arr[10] = {1, 2, 3};
        """
        type_tok = self.expect('KEYWORD', msg="Expected type specifier")
        type_str = type_tok.value
        if type_str not in {'int', 'char'}:
            raise SmallCParserError(f"Type '{type_str}' cannot be used to declare a variable", type_tok.line_num, type_tok.col)
        
        is_pointer = False
        while self.match('OPERATOR', '*'):
            is_pointer = True
        
        id_tok = self.expect('IDENTIFIER', msg="Expected identifier in variable declaration")
        name = id_tok.value
        
        array_size = None
        if self.match('OPERATOR', '['):
            size_tok = self.expect('NUMBER', msg="Array size must be an integer constant")
            array_size = size_tok.value
            self.expect('OPERATOR', ']', msg="Expected ']' in array declaration")
        
        initializer = None
        if self.match('OPERATOR', '='):
            if array_size is not None:
                # Array initializer
                # Can be a string literal (for char arrays)
                if self.peek() and self.peek().type == 'STRING':
                    if type_str != 'char':
                        raise SmallCParserError("Cannot initialize non-char array with string literal", self.peek().line_num, self.peek().col)
                    str_tok = self.pos
                    initializer = self.peek().value
                    self.pos += 1
                elif self.match('OPERATOR', '{'):
                    # Array curly-brace initializer, e.g. = {10, 20, 30}
                    elements = []
                    if not self.match('OPERATOR', '}'):
                        while True:
                            elements.append(self.parse_expression())
                            if self.match('OPERATOR', '}'):
                                break
                            self.expect('OPERATOR', ',', msg="Expected ',' or '}' in array initializer list")
                    initializer = elements
                else:
                    raise SmallCParserError("Invalid array initializer. Must be string literal or curly brace initializer", self.peek().line_num, self.peek().col)
            else:
                # Scalar initializer
                initializer = self.parse_expression()
        
        self.expect('OPERATOR', ';', msg="Expected ';' after variable declaration")
        return VarDeclNode(type_str, name, is_pointer, array_size, initializer, type_tok.line_num, type_tok.col)

    def parse_statement(self):
        """Parses a statement."""
        tok = self.peek()
        if not tok:
            raise SmallCParserError("Unexpected End of File inside statement", 1, 1)
        
        if tok.type == 'OPERATOR' and tok.value == '{':
            self.pos += 1
            statements = []
            while not self.match('OPERATOR', '}'):
                if not self.peek():
                    raise SmallCParserError("Unclosed statement block '{'", tok.line_num, tok.col)
                statements.append(self.parse_statement())
            return BlockNode(statements, tok.line_num, tok.col)
        
        if tok.type == 'KEYWORD':
            if tok.value == 'if':
                self.pos += 1
                self.expect('OPERATOR', '(', msg="Expected '(' after 'if'")
                cond = self.parse_expression()
                self.expect('OPERATOR', ')', msg="Expected ')' after 'if' condition")
                then_branch = self.parse_statement()
                
                else_branch = None
                if self.match('KEYWORD', 'else'):
                    else_branch = self.parse_statement()
                return IfNode(cond, then_branch, else_branch, tok.line_num, tok.col)
            
            elif tok.value == 'while':
                self.pos += 1
                self.expect('OPERATOR', '(', msg="Expected '(' after 'while'")
                cond = self.parse_expression()
                self.expect('OPERATOR', ')', msg="Expected ')' after 'while' condition")
                body = self.parse_statement()
                return WhileNode(cond, body, tok.line_num, tok.col)
            
            elif tok.value == 'do':
                self.pos += 1
                body = self.parse_statement()
                self.expect('KEYWORD', 'while', msg="Expected 'while' in do-while statement")
                self.expect('OPERATOR', '(', msg="Expected '(' in do-while statement")
                cond = self.parse_expression()
                self.expect('OPERATOR', ')', msg="Expected ')' in do-while statement")
                self.expect('OPERATOR', ';', msg="Expected ';' at end of do-while statement")
                return DoWhileNode(body, cond, tok.line_num, tok.col)
            
            elif tok.value == 'for':
                self.pos += 1
                self.expect('OPERATOR', '(', msg="Expected '(' after 'for'")
                
                # init
                init = None
                if not self.match('OPERATOR', ';'):
                    # Check if it starts with declaration
                    p_tok = self.peek()
                    if p_tok and p_tok.type == 'KEYWORD' and p_tok.value in {'int', 'char'}:
                        init = self.parse_var_declaration() # Already parses the semicolon
                    else:
                        init = self.parse_expression()
                        self.expect('OPERATOR', ';', msg="Expected ';' in for-loop initialization")
                
                # cond
                cond = None
                if not self.match('OPERATOR', ';'):
                    cond = self.parse_expression()
                    self.expect('OPERATOR', ';', msg="Expected ';' in for-loop condition")
                
                # incr
                incr = None
                if not self.match('OPERATOR', ')'):
                    incr = self.parse_expression()
                    self.expect('OPERATOR', ')', msg="Expected ')' in for-loop iteration")
                
                body = self.parse_statement()
                return ForNode(init, cond, incr, body, tok.line_num, tok.col)
            
            elif tok.value == 'break':
                self.pos += 1
                self.expect('OPERATOR', ';', msg="Expected ';' after break")
                return BreakNode(tok.line_num, tok.col)
            
            elif tok.value == 'continue':
                self.pos += 1
                self.expect('OPERATOR', ';', msg="Expected ';' after continue")
                return ContinueNode(tok.line_num, tok.col)
            
            elif tok.value == 'return':
                self.pos += 1
                expr = None
                if not self.match('OPERATOR', ';'):
                    expr = self.parse_expression()
                    self.expect('OPERATOR', ';', msg="Expected ';' after return value")
                return ReturnNode(expr, tok.line_num, tok.col)
            
            elif tok.value == 'switch':
                # Parse switch/case/default
                self.pos += 1
                self.expect('OPERATOR', '(', msg="Expected '(' after switch")
                expr = self.parse_expression()
                self.expect('OPERATOR', ')', msg="Expected ')' after switch expression")
                self.expect('OPERATOR', '{', msg="Expected '{' for switch body")
                
                cases = []
                default_case = None
                
                while not self.match('OPERATOR', '}'):
                    if not self.peek():
                        raise SmallCParserError("Unclosed switch body '{'", tok.line_num, tok.col)
                    
                    sub_tok = self.peek()
                    if sub_tok.type == 'KEYWORD' and sub_tok.value == 'case':
                        self.pos += 1
                        # Parse constant integer or character literal (which evaluates to integer in parser)
                        val_tok = self.peek()
                        if val_tok.type == 'NUMBER':
                            val = val_tok.value
                            self.pos += 1
                        else:
                            # Let's see if we have unary minus e.g. case -5:
                            if self.match('OPERATOR', '-'):
                                val_num = self.expect('NUMBER', msg="Expected number constant in case label")
                                val = -val_num.value
                            else:
                                raise SmallCParserError("Expected integer constant after 'case'", val_tok.line_num if val_tok else 1, val_tok.col if val_tok else 1)
                        
                        self.expect('OPERATOR', ':', msg="Expected ':' after case value")
                        
                        # Collect statements until next case, default, or '}'
                        statements = []
                        while self.peek():
                            peek_t = self.peek()
                            if peek_t.type == 'KEYWORD' and peek_t.value in {'case', 'default'}:
                                break
                            if peek_t.type == 'OPERATOR' and peek_t.value == '}':
                                break
                            statements.append(self.parse_statement())
                        
                        cases.append(CaseNode(val, statements, sub_tok.line_num, sub_tok.col))
                    
                    elif sub_tok.type == 'KEYWORD' and sub_tok.value == 'default':
                        self.pos += 1
                        self.expect('OPERATOR', ':', msg="Expected ':' after default")
                        
                        statements = []
                        while self.peek():
                            peek_t = self.peek()
                            if peek_t.type == 'KEYWORD' and peek_t.value in {'case', 'default'}:
                                break
                            if peek_t.type == 'OPERATOR' and peek_t.value == '}':
                                break
                            statements.append(self.parse_statement())
                        
                        if default_case is not None:
                            raise SmallCParserError("Multiple 'default' cases defined in switch", sub_tok.line_num, sub_tok.col)
                        default_case = DefaultNode(statements, sub_tok.line_num, sub_tok.col)
                    
                    else:
                        raise SmallCParserError("Statements in switch body must appear inside 'case' or 'default'", sub_tok.line_num, sub_tok.col)
                
                return SwitchNode(expr, cases, default_case, tok.line_num, tok.col)
            
            # Check if block declaration by accident
            elif tok.value in {'int', 'char'}:
                raise SmallCParserError("Variable declarations must appear at the beginning of the function body", tok.line_num, tok.col)
        
        # Else, expression statement
        expr = self.parse_expression()
        self.expect('OPERATOR', ';', msg="Expected ';' after expression statement")
        return ExprStmtNode(expr, tok.line_num, tok.col)


    # ----------------- Expression Parsing (Pratt Parsing) -----------------

    def parse_expression(self):
        """Parses an expression, which handles assignments and basic operators."""
        return self.parse_assignment()

    def parse_assignment(self):
        """Parses assignment expressions (lowest precedence, right associative).
        e.g., x = y = 5;
        """
        expr = self.parse_logical_or()
        
        tok = self.peek()
        if tok and tok.type == 'OPERATOR' and tok.value in {'=', '+=', '-=', '*=', '/=', '%='}:
            op = tok.value
            self.pos += 1
            right = self.parse_assignment()  # Right-associative recursion
            
            # L-value validation: Must be VarNode, SubscriptNode, or UnaryOpNode (for *dereference)
            # We can perform the l-value check here in the parser or during execution.
            # To be robust, let's allow it in parser, but check it in interpreter.
            return AssignNode(expr, op, right, tok.line_num, tok.col)
        
        return expr

    def parse_logical_or(self):
        expr = self.parse_logical_and()
        while True:
            tok = self.peek()
            if tok and tok.type == 'OPERATOR' and tok.value == '||':
                self.pos += 1
                right = self.parse_logical_and()
                expr = BinOpNode(expr, '||', right, tok.line_num, tok.col)
            else:
                break
        return expr

    def parse_logical_and(self):
        expr = self.parse_bitwise_or()
        while True:
            tok = self.peek()
            if tok and tok.type == 'OPERATOR' and tok.value == '&&':
                self.pos += 1
                right = self.parse_bitwise_or()
                expr = BinOpNode(expr, '&&', right, tok.line_num, tok.col)
            else:
                break
        return expr

    def parse_bitwise_or(self):
        expr = self.parse_bitwise_xor()
        while True:
            tok = self.peek()
            if tok and tok.type == 'OPERATOR' and tok.value == '|':
                self.pos += 1
                right = self.parse_bitwise_xor()
                expr = BinOpNode(expr, '|', right, tok.line_num, tok.col)
            else:
                break
        return expr

    def parse_bitwise_xor(self):
        expr = self.parse_bitwise_and()
        while True:
            tok = self.peek()
            if tok and tok.type == 'OPERATOR' and tok.value == '^':
                self.pos += 1
                right = self.parse_bitwise_and()
                expr = BinOpNode(expr, '^', right, tok.line_num, tok.col)
            else:
                break
        return expr

    def parse_bitwise_and(self):
        expr = self.parse_equality()
        while True:
            tok = self.peek()
            if tok and tok.type == 'OPERATOR' and tok.value == '&':
                self.pos += 1
                right = self.parse_equality()
                expr = BinOpNode(expr, '&', right, tok.line_num, tok.col)
            else:
                break
        return expr

    def parse_equality(self):
        expr = self.parse_relational()
        while True:
            tok = self.peek()
            if tok and tok.type == 'OPERATOR' and tok.value in {'==', '!='}:
                self.pos += 1
                right = self.parse_relational()
                expr = BinOpNode(expr, tok.value, right, tok.line_num, tok.col)
            else:
                break
        return expr

    def parse_relational(self):
        expr = self.parse_shift()
        while True:
            tok = self.peek()
            if tok and tok.type == 'OPERATOR' and tok.value in {'<', '<=', '>', '>='}:
                self.pos += 1
                right = self.parse_shift()
                expr = BinOpNode(expr, tok.value, right, tok.line_num, tok.col)
            else:
                break
        return expr

    def parse_shift(self):
        expr = self.parse_additive()
        while True:
            tok = self.peek()
            if tok and tok.type == 'OPERATOR' and tok.value in {'<<', '>>'}:
                self.pos += 1
                right = self.parse_additive()
                expr = BinOpNode(expr, tok.value, right, tok.line_num, tok.col)
            else:
                break
        return expr

    def parse_additive(self):
        expr = self.parse_multiplicative()
        while True:
            tok = self.peek()
            if tok and tok.type == 'OPERATOR' and tok.value in {'+', '-'}:
                self.pos += 1
                right = self.parse_multiplicative()
                expr = BinOpNode(expr, tok.value, right, tok.line_num, tok.col)
            else:
                break
        return expr

    def parse_multiplicative(self):
        expr = self.parse_unary()
        while True:
            tok = self.peek()
            if tok and tok.type == 'OPERATOR' and tok.value in {'*', '/', '%'}:
                self.pos += 1
                right = self.parse_unary()
                expr = BinOpNode(expr, tok.value, right, tok.line_num, tok.col)
            else:
                break
        return expr

    def parse_unary(self):
        """Parses prefix unary operators (right associative).
        -expr, !expr, ~expr, *expr (dereference), &expr (address-of), ++expr, --expr.
        """
        tok = self.peek()
        if tok and tok.type == 'OPERATOR' and tok.value in {'-', '!', '~', '*', '&', '++', '--'}:
            op = tok.value
            self.pos += 1
            expr = self.parse_unary()  # Right associative recursion
            return UnaryOpNode(op, expr, is_postfix=False, line_num=tok.line_num, col=tok.col)
        
        return self.parse_postfix()

    def parse_postfix(self):
        """Parses postfix operator suffixes: array subscript [], function calls (), postfix ++/--."""
        expr = self.parse_primary()
        
        while True:
            tok = self.peek()
            if not tok:
                break
            
            if tok.type == 'OPERATOR' and tok.value == '[':
                self.pos += 1
                index = self.parse_expression()
                self.expect('OPERATOR', ']', msg="Expected ']' in array indexing")
                expr = SubscriptNode(expr, index, tok.line_num, tok.col)
            
            elif tok.type == 'OPERATOR' and tok.value == '(':
                self.pos += 1
                args = []
                if not self.match('OPERATOR', ')'):
                    while True:
                        args.append(self.parse_expression())
                        if self.match('OPERATOR', ')'):
                            break
                        self.expect('OPERATOR', ',', msg="Expected ',' or ')' in argument list")
                
                # Call validation: left expression must be a simple variable name in Small-C
                if not isinstance(expr, VarNode):
                    raise SmallCParserError("Function calls must be called directly on an identifier in Small-C", tok.line_num, tok.col)
                
                expr = CallNode(expr.name, args, tok.line_num, tok.col)
            
            elif tok.type == 'OPERATOR' and tok.value in {'++', '--'}:
                # Postfix ++/-- (Extra Credit / optional)
                op = tok.value
                self.pos += 1
                expr = UnaryOpNode(op, expr, is_postfix=True, line_num=tok.line_num, col=tok.col)
            
            else:
                break
        
        return expr

    def parse_primary(self):
        """Parses primary leaf nodes: numbers, strings, variables, parenthesized expressions."""
        tok = self.peek()
        if not tok:
            raise SmallCParserError("Unexpected End of File: Expected primary expression", 1, 1)
        
        if tok.type == 'NUMBER':
            self.pos += 1
            return ConstNode('int', tok.value, tok.line_num, tok.col)
        
        elif tok.type == 'STRING':
            self.pos += 1
            return ConstNode('string', tok.value, tok.line_num, tok.col)
        
        elif tok.type == 'IDENTIFIER':
            self.pos += 1
            return VarNode(tok.value, tok.line_num, tok.col)
        
        elif tok.type == 'OPERATOR' and tok.value == '(':
            self.pos += 1
            expr = self.parse_expression()
            self.expect('OPERATOR', ')', msg="Expected ')' to close parenthesized expression")
            return expr
        
        raise SmallCParserError(f"Unexpected token in expression: {tok.type} ({tok.value})", tok.line_num, tok.col)
