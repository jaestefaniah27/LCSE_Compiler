import sys
import ply.lex as lex
import ply.yacc as yacc

# ==============================================================================
# 1. HARDWARE & MEMORY MAP
# ==============================================================================
SYS_CONSTANTS = {
    "RCBUF0": "X00", "RCBUF1": "X01", "RCBUF2": "X02", "NINST": "X03",
    "TXBUF0": "X04", "TXBUF1": "X05", "TSTAT": "X31", "GPMEM":  "X40", 
    "TMP": "X41", "SP": "X42", 
    
    # GPIOs
    "SW0": "0", "SW1": "1", "LED0": "0", "LED1": "1",
    "BTN_UP": "15", "BTN_DOWN": "18", "BTN_CENTER": "14",
    "BTNC": "14", "BTNU": "15", "BTNL": "16", "BTNR": "17", "BTND": "18"
}

GPIO_PORTS = {
    "IN_L": "X18", "IN_M": "X19", "IN_H": "X1A",
    "OUT_L": "X1B", "OUT_M": "X1C", "OUT_H": "X1D"
}

HEAP_START = 0x50

# ==============================================================================
# 2. FRONTEND: LEXER
# ==============================================================================
tokens = (
    'ID', 'NUMBER', 'STRING',
    'PLUS', 'MINUS', 'AND_BIT', 'OR_BIT', 'XOR_BIT', 'LSHIFT', 'RSHIFT',
    'EQ', 'NEQ', 'GT', 'LT', 'AND_LOG', 'NOT', 'ASSIGN',
    'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE', 'SEMI', 'COMMA', 'LBRACKET', 'RBRACKET',
    'INT', 'VOID', 'IF', 'ELSE', 'WHILE', 'RETURN'
)

t_PLUS    = r'\+'
t_MINUS   = r'-'
t_AND_BIT = r'&'
t_OR_BIT  = r'\|'
t_XOR_BIT = r'\^'
t_LSHIFT  = r'<<'
t_RSHIFT  = r'>>'
t_EQ      = r'=='
t_NEQ     = r'!='
t_GT      = r'>'
t_LT      = r'<'
t_AND_LOG = r'&&'
t_NOT     = r'!'
t_ASSIGN  = r'='
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_LBRACE  = r'\{'
t_RBRACE  = r'\}'
t_SEMI    = r';'
t_COMMA   = r','
t_LBRACKET = r'\['
t_RBRACKET = r'\]'

reserved = {
    'int': 'INT', 'void': 'VOID', 'if': 'IF', 'else': 'ELSE', 
    'while': 'WHILE', 'return': 'RETURN'
}

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = reserved.get(t.value, 'ID')
    return t

def t_NUMBER(t):
    r'\d+|0x[0-9A-Fa-f]+'
    if t.value.startswith('0x'): t.value = int(t.value, 16)
    else: t.value = int(t.value)
    return t

def t_STRING(t):
    r'\"([^\\\n]|(\\.))*?\"'
    t.value = t.value[1:-1]
    return t

def t_COMMENT(t):
    r'//.*'
    pass

t_ignore = ' \t'

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    print(f"Carácter ilegal '{t.value[0]}' en línea {t.lineno}")
    t.lexer.skip(1)

lexer = lex.lex()

# ==============================================================================
# 3. MIDDLE-END: AST NODES
# ==============================================================================
class Node: pass
class Program(Node):
    def __init__(self, items): self.items = items
class Function(Node):
    def __init__(self, name, body): self.name = name; self.body = body
class VarDecl(Node):
    def __init__(self, name, size=1, init=None): 
        self.name = name; self.size = size; self.init = init
class Block(Node):
    def __init__(self, statements): self.statements = statements
class If(Node):
    def __init__(self, cond, then_body, else_body=None):
        self.cond = cond; self.then_body = then_body; self.else_body = else_body
class While(Node):
    def __init__(self, cond, body): self.cond = cond; self.body = body
class Assign(Node):
    def __init__(self, target, expr): self.target = target; self.expr = expr
class BinOp(Node):
    def __init__(self, left, op, right): self.left = left; self.op = op; self.right = right
class UnOp(Node):
    def __init__(self, op, expr): self.op = op; self.expr = expr
class Literal(Node):
    def __init__(self, value): self.value = value
class VarAccess(Node):
    def __init__(self, name, index=None): self.name = name; self.index = index
class Call(Node):
    def __init__(self, name, args): self.name = name; self.args = args
class Return(Node): pass

# ==============================================================================
# 4. PARSER
# ==============================================================================
precedence = (
    ('left', 'AND_LOG'),
    ('left', 'EQ', 'NEQ'),
    ('left', 'LT', 'GT'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'LSHIFT', 'RSHIFT', 'AND_BIT', 'OR_BIT', 'XOR_BIT'),
    ('right', 'NOT'),
)

def p_program(p):
    '''program : program function
               | program declaration
               | function
               | declaration'''
    if len(p) == 3: p[0] = p[1]; p[0].items.append(p[2])
    else: p[0] = Program([p[1]])

def p_declaration(p):
    '''declaration : INT ID SEMI
                   | INT ID ASSIGN expression SEMI
                   | INT ID LBRACKET NUMBER RBRACKET SEMI'''
    if len(p) == 4:
        p[0] = VarDecl(p[2], size=1, init=None)
    elif len(p) == 6 and p[3] == '=': 
        p[0] = VarDecl(p[2], size=1, init=p[4])
    else: 
        p[0] = VarDecl(p[2], size=p[4], init=None)

def p_function(p):
    '''function : VOID ID LPAREN RPAREN block'''
    p[0] = Function(p[2], p[5])

def p_block(p):
    '''block : LBRACE statements RBRACE'''
    p[0] = Block(p[2])

def p_statements(p):
    '''statements : statements statement
                  | statement'''
    if len(p) == 3: p[0] = p[1] + [p[2]]
    else: p[0] = [p[1]]

def p_statement(p):
    '''statement : declaration
                 | assignment
                 | if_stmt
                 | while_stmt
                 | call_stmt
                 | return_stmt'''
    p[0] = p[1]

def p_assignment(p):
    '''assignment : var_access ASSIGN expression SEMI'''
    p[0] = Assign(p[1], p[3])

def p_var_access(p):
    '''var_access : ID
                  | ID LBRACKET expression RBRACKET'''
    if len(p) == 2: p[0] = VarAccess(p[1])
    else: p[0] = VarAccess(p[1], p[3])

def p_if_stmt(p):
    '''if_stmt : IF LPAREN expression RPAREN block
               | IF LPAREN expression RPAREN block ELSE block'''
    if len(p) == 6: p[0] = If(p[3], p[5])
    else: p[0] = If(p[3], p[5], p[7])

def p_while_stmt(p):
    '''while_stmt : WHILE LPAREN expression RPAREN block'''
    p[0] = While(p[3], p[5])

def p_call_stmt(p):
    '''call_stmt : ID LPAREN args RPAREN SEMI'''
    p[0] = Call(p[1], p[3])

def p_call_expr(p):
    '''expression : ID LPAREN args RPAREN'''
    p[0] = Call(p[1], p[3])

def p_args(p):
    '''args : args COMMA expression
            | expression
            | empty'''
    if len(p) == 2: 
        if p[1] is None: p[0] = []
        else: p[0] = [p[1]]
    else: p[0] = p[1] + [p[3]]

def p_return_stmt(p):
    '''return_stmt : RETURN SEMI'''
    p[0] = Return()

def p_expression_binop(p):
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression AND_BIT expression
                  | expression OR_BIT expression
                  | expression XOR_BIT expression
                  | expression LSHIFT expression
                  | expression RSHIFT expression
                  | expression EQ expression
                  | expression NEQ expression
                  | expression LT expression
                  | expression GT expression
                  | expression AND_LOG expression'''
    p[0] = BinOp(p[1], p[2], p[3])

def p_expression_unop(p):
    '''expression : NOT expression'''
    p[0] = UnOp(p[1], p[2])

def p_expression_group(p):
    '''expression : LPAREN expression RPAREN'''
    p[0] = p[2]

def p_expression_atom(p):
    '''expression : NUMBER
                  | STRING
                  | var_access'''
    if isinstance(p[1], int) or isinstance(p[1], str): p[0] = Literal(p[1])
    else: p[0] = p[1]

def p_empty(p):
    'empty :'
    pass

def p_error(p):
    if p: print(f"Error de sintaxis en '{p.value}' línea {p.lineno}")
    else: print("Error de sintaxis en EOF")

parser = yacc.yacc()

# ==============================================================================
# 5. BACKEND: CODE GENERATOR (BUFFERIZADO)
# ==============================================================================
class CodeGenerator:
    def __init__(self):
        # Buffers separados para emular el comportamiento del compilador original
        self.code_main = []  # Setup, Loop y Funciones de usuario
        self.code_isr  = []  # Código específico de la ISR
        self.code_init = []  # Inicialización de variables globales
        
        # Puntero al buffer actual
        self.current_buffer = self.code_main
        
        self.label_count = 0
        self.mem_ptr = HEAP_START
        self.global_vars = {}
        self.temp_vars = []
        
        for name, addr in SYS_CONSTANTS.items():
            self.global_vars[name] = addr
            
    def emit(self, instr, comment=""):
        # Escribe en el buffer activo en ese momento
        self.current_buffer.append(f"\t\t{instr}" + (f"\t; {comment}" if comment else ""))

    def emit_label(self, label):
        self.current_buffer.append(f"{label}")

    def new_label(self, tag="L"):
        self.label_count += 1
        return f"#{tag}_{self.label_count}"

    def alloc_global(self, name, size=1):
        addr = f"X{self.mem_ptr:02X}"
        self.global_vars[name] = addr
        self.mem_ptr += size
        return addr

    def get_temp(self):
        name = f"__T{len(self.temp_vars)}"
        addr = f"X{self.mem_ptr:02X}"
        self.mem_ptr += 1
        self.temp_vars.append(addr)
        return addr

    def get_var_addr(self, name):
        if name in self.global_vars: return self.global_vars[name]
        return self.alloc_global(name)

    # --- VISITORS ---

    def visit(self, node):
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise Exception(f"No visit_{type(node).__name__} method")

    def visit_Program(self, node):
        # 1. Variables Globales (llenan code_init)
        self.current_buffer = self.code_init
        for item in node.items:
            if isinstance(item, VarDecl):
                self.visit(item)

        # 2. Funciones (llenan code_main O code_isr)
        for item in node.items:
            if isinstance(item, Function):
                self.visit(item)

    def visit_VarDecl(self, node):
        addr = self.alloc_global(node.name, node.size)
        if node.init:
            if isinstance(node.init, Literal) and isinstance(node.init.value, int):
                # Escribimos explícitamente en el buffer de init
                self.code_init.append(f"\t\tLD\t.ACC, X{node.init.value:02X}")
                self.code_init.append(f"\t\tWR\t{addr}")
            else:
                print(f"Advertencia: Init complejo en global '{node.name}' no soportado.")

    def visit_Function(self, node):
        # Selección de Buffer según nombre de función
        if node.name == "ISR":
            self.current_buffer = self.code_isr
            # No ponemos etiqueta #ISR aquí, la pone el generador final
        else:
            self.current_buffer = self.code_main
            if node.name == "setup": self.emit_label("#SETUP")
            elif node.name == "loop": self.emit_label("#LOOP_START")
            else: self.emit_label(f"#{node.name}")
        
        self.visit(node.body)
        
        # Retorno / Loop
        if node.name == "loop": self.emit("JMP\t#LOOP_START")
        elif node.name == "ISR": self.emit("RETI") # ISR termina siempre con RETI

        # Restaurar buffer por seguridad
        self.current_buffer = self.code_main

    def visit_Block(self, node):
        for stmt in node.statements:
            self.visit(stmt)

    # ... (Resto de visitors idénticos, usan self.emit que ahora es inteligente) ...
    def visit_Assign(self, node):
        self.visit(node.expr)
        if isinstance(node.target, VarAccess):
            if node.target.index:
                val_temp = self.get_temp()
                self.emit(f"WR\t{val_temp}")
                self.visit(node.target.index)
                self.emit("LD\t.INDEX, .ACC")
                self.emit(f"LD\t.ACC, [{val_temp}]")
                base = self.get_var_addr(node.target.name)
                self.emit(f"WRI\t{base}")
            else:
                addr = self.get_var_addr(node.target.name)
                self.emit(f"WR\t{addr}")

    def visit_VarAccess(self, node):
        if node.index:
            self.visit(node.index)
            self.emit("LD\t.INDEX, .ACC")
            base = self.get_var_addr(node.name)
            self.emit(f"LDI\t.ACC, [{base}]")
        else:
            addr = self.get_var_addr(node.name)
            self.emit(f"LD\t.ACC, [{addr}]")

    def visit_Literal(self, node):
        if isinstance(node.value, int):
            self.emit(f"LD\t.ACC, X{node.value:02X}")

    def visit_BinOp(self, node):
        self.visit(node.left)
        temp = self.get_temp()
        self.emit(f"WR\t{temp}")
        self.visit(node.right)
        
        self.emit(f"WR\t{self.get_temp()}") 
        self.emit(f"LD\t.A, [{temp}]")      
        self.emit(f"LD\t.B, [{self.temp_vars[-1]}]") 
        
        op = node.op
        if op == '+': self.emit("ADD")
        elif op == '-': self.emit("SUB")
        elif op == '&': self.emit("AND")
        elif op == '|': self.emit("OR")
        elif op == '^': self.emit("XOR")
        elif op in ['==', '!=', '>', '<']:
            if op == '==': self.emit("CMPE")
            elif op == '>': self.emit("CMPG")
            elif op == '<': self.emit("CMPL")
            elif op == '!=': self.emit("CMPE")
            
            lbl_true = self.new_label("TRUE")
            lbl_end = self.new_label("END")
            
            if op == '!=':
                self.emit(f"JMPT\t{lbl_end}") 
                self.emit("LD\t.ACC, X01")    
                self.emit(f"JMP\t{lbl_true}") 
                self.emit_label(lbl_end)      
                self.emit("LD\t.ACC, X00")    
                self.emit_label(lbl_true)
            else:
                self.emit(f"JMPT\t{lbl_true}")
                self.emit("LD\t.ACC, X00")
                self.emit(f"JMP\t{lbl_end}")
                self.emit_label(lbl_true)
                self.emit("LD\t.ACC, X01")
                self.emit_label(lbl_end)

    def visit_UnOp(self, node):
        if node.op == '!':
            self.visit(node.expr)
            self.emit("LD\t.A, .ACC")
            self.emit("LD\t.B, X00")
            self.emit("CMPE")
            lbl_z = self.new_label("IS_Z")
            lbl_e = self.new_label("NO_Z")
            self.emit(f"JMPT\t{lbl_z}")
            self.emit("LD\t.ACC, X00")
            self.emit(f"JMP\t{lbl_e}")
            self.emit_label(lbl_z)
            self.emit("LD\t.ACC, X01")
            self.emit_label(lbl_e)

    def visit_If(self, node):
        lbl_else = self.new_label("ELSE")
        lbl_end = self.new_label("IF_END")
        
        self.visit(node.cond)
        self.emit("LD\t.A, .ACC")
        self.emit("LD\t.B, X00")
        self.emit("CMPE")
        self.emit(f"JMPT\t{lbl_else}")
        
        self.visit(node.then_body)
        self.emit(f"JMP\t{lbl_end}")
        
        self.emit_label(lbl_else)
        if node.else_body:
            self.visit(node.else_body)
        self.emit_label(lbl_end)

    def visit_While(self, node):
        lbl_start = self.new_label("WHILE_S")
        lbl_end = self.new_label("WHILE_E")
        self.emit_label(lbl_start)
        
        if isinstance(node.cond, Literal) and node.cond.value == 1:
            pass
        else:
            self.visit(node.cond)
            self.emit("LD\t.A, .ACC")
            self.emit("LD\t.B, X00")
            self.emit("CMPE")
            self.emit(f"JMPT\t{lbl_end}")
            
        self.visit(node.body)
        self.emit(f"JMP\t{lbl_start}")
        self.emit_label(lbl_end)

    def visit_Call(self, node):
        if node.name == "gpio_write":
            pin_node, val_node = node.args
            if isinstance(pin_node, VarAccess) and pin_node.name in SYS_CONSTANTS:
                pnum = int(SYS_CONSTANTS[pin_node.name])
                if pnum < 8: port = GPIO_PORTS["OUT_L"]; bit = pnum
                elif pnum < 16: port = GPIO_PORTS["OUT_M"]; bit = pnum-8
                else: port = GPIO_PORTS["OUT_H"]; bit = pnum-16
                mask = 1 << bit
                self.visit(val_node) 
                self.emit(f"WR\t{SYS_CONSTANTS['TMP']}") 
                self.emit(f"LD\t.A, [{port}]") 
                self.emit(f"LD\t.B, [{SYS_CONSTANTS['TMP']}]") 
                if isinstance(val_node, Literal):
                     if val_node.value:
                         self.emit(f"LD\t.B, X{mask:02X}"); self.emit("OR")
                     else:
                         self.emit(f"LD\t.B, X{(~mask & 0xFF):02X}"); self.emit("AND")
                     self.emit(f"WR\t{port}")
                else:
                    self.emit("; Warn: gpio_write dinámico no soportado")

        elif node.name == "gpio_read":
            pin_node = node.args[0]
            if isinstance(pin_node, VarAccess) and pin_node.name in SYS_CONSTANTS:
                pnum = int(SYS_CONSTANTS[pin_node.name])
                if pnum < 8: port = GPIO_PORTS["IN_L"]; bit = pnum
                elif pnum < 16: port = GPIO_PORTS["IN_M"]; bit = pnum-8
                else: port = GPIO_PORTS["IN_H"]; bit = pnum-16
                self.emit(f"LD\t.A, [{port}]"); self.emit("LD\t.B, X00"); self.emit("ADD")
                for _ in range(bit): self.emit("SHIFTR")
                self.emit("LD\t.A, .ACC"); self.emit("LD\t.B, X01"); self.emit("AND")

        elif node.name == "serial_print":
            fmt = node.args[0].value
            arg_idx = 1
            i = 0
            while i < len(fmt):
                if fmt[i] == '%' and i+1 < len(fmt) and fmt[i+1] == 'd':
                    if arg_idx < len(node.args):
                        self.visit(node.args[arg_idx])
                        self.emit("LD\t.A, .ACC")
                        self.emit("BIN2ASCII")
                        self.emit("WR\tTXBUF0")
                        self.emit("SEND")
                        arg_idx += 1
                    i += 2
                else:
                    char = fmt[i]
                    if char == '\\' and i+1 < len(fmt):
                        nxt = fmt[i+1]
                        if nxt == 'n': val = 10
                        elif nxt == 'r': val = 13
                        else: val = ord(nxt)
                        i += 2
                    else:
                        val = ord(char)
                        i += 1
                    self.emit(f"LD\t.ACC, X{val:02X}")
                    self.emit("WR\tTXBUF0")
                    self.emit("SEND")

    def visit_Return(self, node):
        self.emit("RETI")

    def generate(self):
        # ENSAMBLADO FINAL (Linker)
        final_asm = []
        
        # 1. BOOT (0x000)
        final_asm.append("; --- BOOT (0x000) ---")
        final_asm.append("JMP\t#GLOBAL_INIT")
        # El salto ocupa 2 palabras (0x000 y 0x001). 
        # La siguiente instrucción cae exactamente en 0x002.
        
        # 2. VECTOR ISR (0x002)
        final_asm.append("; --- INTERRUPT VECTOR (0x002) ---")
        final_asm.append("#ISR")
        if self.code_isr:
            # Si el usuario escribió void ISR(), ponemos SU código
            final_asm.extend(self.code_isr)
        else:
            # Si no, ponemos un RETI vacío
            final_asm.append("\t\tRETI")

        # 3. GLOBAL INIT
        final_asm.append("; --- GLOBAL INIT ---")
        final_asm.append("#GLOBAL_INIT")
        final_asm.extend(self.code_init)
        final_asm.append("JMP\t#SETUP")

        # 4. MAIN PROGRAM
        final_asm.append("; --- MAIN PROGRAM ---")
        final_asm.extend(self.code_main)
        
        return "\n".join(final_asm)

# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    try:
        with open('main.c', 'r', encoding='utf-8') as f: source = f.read()
        
        print("[1/3] Tokenizing...")
        print("[2/3] Parsing to AST...")
        ast = parser.parse(source, lexer=lexer)
        if not ast:
            print("Error: No se pudo generar el AST.")
            sys.exit(1)
            
        print("[3/3] Generating Assembly...")
        cg = CodeGenerator()
        cg.visit(ast)
        
        with open('PROGRAM.txt', 'w') as f:
            f.write(cg.generate())
            
        print("\n[ÉXITO] PROGRAM.txt generado usando arquitectura AST.")
        print(" -> Vector ISR en 0x002 (Sin padding)")
        print(f" -> ISR detectada: {'SÍ' if cg.code_isr else 'NO'}")
        
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")