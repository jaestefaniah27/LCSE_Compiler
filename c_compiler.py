import sys
import re

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
INPUT_FILE = 'main.c'
OUTPUT_FILE = 'PROGRAM.txt'

# Mapa de Memoria del Hardware
SYS_CONSTANTS = {
    # Registros del Sistema
    "RCBUF0": "X00", "RCBUF1": "X01", "RCBUF2": "X02", "NINST": "X03",
    "TXBUF0": "X04", "TXBUF1": "X05",
    "TSTAT": "X31", "GPMEM":  "X40", "TMP": "X41",
    "ADD_RPARITY": "X06", "ADDR_STOP": "X07", "ADDR_NBITS": "X08", 
    "ADDR_BAUD": "X09",

    # --- MAPA DE PINES GPIO ---
    # Entradas (0x18 - 0x1A)
    # Switches SW[0]..SW[7] -> 0x18
    "SW0": "0", "SW1": "1", "SW2": "2", "SW3": "3", 
    "SW4": "4", "SW5": "5", "SW6": "6", "SW7": "7",
    
    # Switches SW[8]..SW[14] -> 0x19
    "SW8": "8", "SW9": "9", "SW10": "10", "SW11": "11",
    "SW12": "12", "SW13": "13", "SW14": "14",
    
    # Botones
    "BTNC": "14", "BTNU": "15",
    "BTNL": "16", "BTNR": "17", "BTND": "18",

    # Salidas (0x1B - 0x1D)
    # LEDs Verdes LED[0]..LED[7] -> 0x1B
    "LED0": "0", "LED1": "1", "LED2": "2", "LED3": "3",
    "LED4": "4", "LED5": "5", "LED6": "6", "LED7": "7",

    # LED RGB 16
    "LED16_R": "8", "LED16_G": "9", "LED16_B": "10",

    # LED RGB 17
    "LED17_R": "11", "LED17_G": "12", "LED17_B": "13"
}

# Direcciones Base de los Puertos
GPIO_PORTS = {
    "IN_L": "X18", "IN_M": "X19", "IN_H": "X1A",
    "OUT_L": "X1B", "OUT_M": "X1C", "OUT_H": "X1D"
}

HARDWARE_ARRAYS = {
    "interruptor": "X10",
    "actuador":    "X20"
}

class SmartCCompiler:
    def __init__(self):
        self.code_setup = []
        self.code_loop = []
        self.code_isr = []
        self.current_buffer = None 
        self.vars = {}          
        self.defines = {}
        self.arrays = {} 
        self.mem_ptr = 0x42 
        self.label_count = 0
        self.block_stack = []   
        self.context = "GLOBAL" 

        for name, addr in HARDWARE_ARRAYS.items():
            self.arrays[name] = addr

    def emit(self, instr, comment=""):
        c = f"\t; {comment}" if comment else ""
        if self.current_buffer is not None:
            self.current_buffer.append(f"\t\t{instr}{c}")

    def emit_label(self, label):
        if self.current_buffer is not None:
            self.current_buffer.append(f"{label}")

    def new_label(self, tag):
        self.label_count += 1
        return f"#{tag}_{self.label_count}"

    def get_var_addr(self, name):
        name = name.strip()
        while name in self.defines: name = self.defines[name]

        if name in SYS_CONSTANTS: return SYS_CONSTANTS[name]
        if name.isdigit(): return f"X{int(name):02X}"
        if name.startswith("0x"): return f"X{int(name, 16):02X}"
        if name.startswith("'"): return f"X{ord(name[1]):02X}"
        if name in self.vars: return self.vars[name]
        
        addr = f"X{self.mem_ptr:02X}"
        self.vars[name] = addr
        self.mem_ptr += 1
        return addr

    def resolve_operand(self, op):
        addr = self.get_var_addr(op)
        if op.isdigit() or op.startswith("'") or op.startswith("0x"):
            return addr 
        return f"[{addr}]" 

    def compile_expr(self, dest, expr):
        dest = dest.strip()
        expr = expr.strip()

        match_array_write = re.match(r'(\w+)\[(.+)\]', dest)
        if match_array_write:
            arr_name, idx_expr = match_array_write.groups()
            if arr_name not in self.arrays: raise Exception(f"Array '{arr_name}' desconocido")
            base_addr = self.arrays[arr_name]

            if idx_expr.isdigit(): self.emit(f"LD\t.ACC, {self.get_var_addr(idx_expr)}")
            else: self.emit(f"LD\t.ACC, [{self.get_var_addr(idx_expr)}]")
            
            self.emit("LD\t.INDEX, .ACC")
            self.eval_rhs_to_acc(expr)
            self.emit(f"WRI\t{base_addr}")
            return

        self.eval_rhs_to_acc(expr)
        addr_dest = self.get_var_addr(dest)
        self.emit(f"WR\t{addr_dest}")

    def eval_rhs_to_acc(self, expr):
        expr = expr.strip()
        while expr in self.defines: expr = self.defines[expr]

        if "gpio_read" in expr:
            self.compile_gpio_read(expr)
            return

        match_array_read = re.match(r'(\w+)\[(.+)\]', expr)
        if match_array_read:
            arr_name, idx_expr = match_array_read.groups()
            base_addr = self.arrays[arr_name]
            if idx_expr.isdigit(): self.emit(f"LD\t.ACC, {self.get_var_addr(idx_expr)}")
            else: self.emit(f"LD\t.ACC, [{self.get_var_addr(idx_expr)}]")
            self.emit("LD\t.INDEX, .ACC")
            self.emit(f"LDI\t.ACC, [{base_addr}]")
            return

        match_bin = re.match(r'([a-zA-Z0-9_\']+) *([\+\-\&\|\^]) *([a-zA-Z0-9_\']+)', expr)
        if match_bin:
            op1, operator, op2 = match_bin.groups()
            self.emit(f"LD\t.A, {self.resolve_operand(op1)}")
            self.emit(f"LD\t.B, {self.resolve_operand(op2)}")
            if operator == '+': self.emit("ADD")
            elif operator == '-': self.emit("SUB")
            elif operator == '&': self.emit("AND")
            elif operator == '|': self.emit("OR")
            elif operator == '^': self.emit("XOR")
            return 

        match_shift = re.match(r'([a-zA-Z0-9_\']+) *(\>\>|\<\<) *([0-9]+)', expr)
        if match_shift:
            op1, operator, count = match_shift.groups()
            self.emit(f"LD\t.A, {self.resolve_operand(op1)}")
            self.emit("LD\t.B, X00"); self.emit("ADD") 
            for _ in range(int(count)):
                if operator == ">>": self.emit("SHIFTR")
                else: self.emit("SHIFTL")
            return

        src = expr
        addr_src = self.get_var_addr(src)
        if src.isdigit() or src.startswith("'") or src.startswith("0x"):
            self.emit(f"LD\t.ACC, {addr_src}")
        elif src in SYS_CONSTANTS:
            self.emit(f"LD\t.ACC, [{addr_src}]")
        else:
            self.emit(f"LD\t.ACC, [{addr_src}]")

    # ==========================================================================
    # GPIO WRITE (Híbrido) - CORREGIDO
    # ==========================================================================
    def compile_gpio_write(self, line):
        match = re.search(r'gpio_write\((.+),(.+)\)', line)
        if not match: return
        
        pin_name = match.group(1).strip()
        val_expr = match.group(2).strip()
        
        while pin_name in self.defines: pin_name = self.defines[pin_name]
        
        pin_num = None
        if pin_name in SYS_CONSTANTS: pin_num = int(SYS_CONSTANTS[pin_name])
        elif pin_name.isdigit(): pin_num = int(pin_name)

        if pin_num is not None:
            # --- MODO ESTÁTICO (Optimizado) ---
            port_addr = ""
            bit_rel = 0
            if pin_num < 8:   port_addr = GPIO_PORTS["OUT_L"]; bit_rel = pin_num
            elif pin_num < 16: port_addr = GPIO_PORTS["OUT_M"]; bit_rel = pin_num - 8
            else:             port_addr = GPIO_PORTS["OUT_H"]; bit_rel = pin_num - 16
            mask = 1 << bit_rel
            
            if val_expr == '1' or val_expr == 'true':
                 self.emit(f"LD\t.A, [{port_addr}]"); self.emit(f"LD\t.B, X{mask:02X}"); self.emit("OR"); self.emit(f"WR\t{port_addr}")
            elif val_expr == '0' or val_expr == 'false':
                 self.emit(f"LD\t.A, [{port_addr}]"); self.emit(f"LD\t.B, X{(~mask & 0xFF):02X}"); self.emit("AND"); self.emit(f"WR\t{port_addr}")
            else:
                 self.eval_rhs_to_acc(val_expr)
                 self.emit("LD\t.A, .ACC") 
                 lbl_zero = self.new_label("G_Z"); lbl_end = self.new_label("G_E")
                 self.emit("LD\t.B, X00"); self.emit("CMPE"); self.emit(f"JMPT\t{lbl_zero}")
                 self.emit(f"LD\t.A, [{port_addr}]"); self.emit(f"LD\t.B, X{mask:02X}"); self.emit("OR"); self.emit(f"WR\t{port_addr}"); self.emit(f"JMP\t{lbl_end}")
                 self.emit_label(lbl_zero)
                 self.emit(f"LD\t.A, [{port_addr}]"); self.emit(f"LD\t.B, X{(~mask & 0xFF):02X}"); self.emit("AND"); self.emit(f"WR\t{port_addr}")
                 self.emit_label(lbl_end)

        else:
            # --- MODO DINÁMICO (Variable Pin) ---
            self.emit("", comment=f"Dynamic GPIO Write: {pin_name}")
            addr_pin = self.get_var_addr("__d_pin")
            addr_off = self.get_var_addr("__d_off") 
            addr_bit = self.get_var_addr("__d_bit") 
            addr_msk = self.get_var_addr("__d_msk")
            
            self.eval_rhs_to_acc(pin_name)
            self.emit(f"WR\t{addr_pin}")
            
            lbl_try_m = self.new_label("TRY_M")
            lbl_try_h = self.new_label("TRY_H")
            lbl_calc_ok = self.new_label("CALC_OK")
            
            # --- FIX: Inicializar SIEMPRE por defecto a Puerto L ---
            self.emit("LD\t.ACC, X00"); self.emit(f"WR\t{addr_off}")
            self.emit(f"LD\t.ACC, [{addr_pin}]"); self.emit(f"WR\t{addr_bit}")
            
            # Comprobación de rango segura
            self.emit(f"LD\t.ACC, [{addr_pin}]"); self.emit("LD\t.A, .ACC") # FIX: Cargar A
            self.emit("LD\t.B, X08"); self.emit("CMPL"); self.emit(f"JMPT\t{lbl_calc_ok}")
            
            self.emit(f"LD\t.ACC, [{addr_pin}]"); self.emit("LD\t.A, .ACC") # FIX: Cargar A
            self.emit("LD\t.B, X10"); self.emit("CMPL"); self.emit(f"JMPT\t{lbl_try_m}")
            
            # Port H (>= 16)
            self.emit_label(lbl_try_h)
            self.emit("LD\t.ACC, X02"); self.emit(f"WR\t{addr_off}")
            self.emit(f"LD\t.ACC, [{addr_pin}]"); self.emit("LD\t.A, .ACC")
            self.emit("LD\t.B, X10"); self.emit("SUB"); self.emit(f"WR\t{addr_bit}")
            self.emit(f"JMP\t{lbl_calc_ok}")
            
            # Port M (>= 8)
            self.emit_label(lbl_try_m)
            self.emit("LD\t.ACC, X01"); self.emit(f"WR\t{addr_off}")
            self.emit(f"LD\t.ACC, [{addr_pin}]"); self.emit("LD\t.A, .ACC")
            self.emit("LD\t.B, X08"); self.emit("SUB"); self.emit(f"WR\t{addr_bit}")
            
            self.emit_label(lbl_calc_ok)
            
            # Calcular Mascara
            self.emit("LD\t.ACC, X01"); self.emit(f"WR\t{addr_msk}")
            lbl_s_loop = self.new_label("S_LOOP"); lbl_s_end = self.new_label("S_END")
            
            self.emit_label(lbl_s_loop)
            self.emit(f"LD\t.ACC, [{addr_bit}]"); self.emit("LD\t.A, .ACC"); self.emit("LD\t.B, X00"); self.emit("CMPE"); self.emit(f"JMPT\t{lbl_s_end}")
            self.emit(f"LD\t.ACC, [{addr_msk}]"); self.emit("LD\t.A, .ACC"); self.emit("LD\t.B, X00"); self.emit("ADD"); self.emit("SHIFTL"); self.emit(f"WR\t{addr_msk}")
            self.emit(f"LD\t.ACC, [{addr_bit}]"); self.emit("LD\t.A, .ACC"); self.emit("LD\t.B, X01"); self.emit("SUB"); self.emit(f"WR\t{addr_bit}")
            self.emit(f"JMP\t{lbl_s_loop}")
            self.emit_label(lbl_s_end)
            
            # Leer Puerto
            self.emit(f"LD\t.ACC, [{addr_off}]"); self.emit("LD\t.INDEX, .ACC")
            self.emit(f"LDI\t.ACC, [{GPIO_PORTS['OUT_L']}]") 
            self.emit(f"WR\t{SYS_CONSTANTS['TMP']}") 
            
            if val_expr == '0' or val_expr == 'false':
                self.emit(f"LD\t.ACC, [{addr_msk}]"); self.emit("LD\t.A, .ACC"); self.emit("LD\t.B, XFF"); self.emit("XOR") 
                self.emit("LD\t.B, .ACC")
                self.emit(f"LD\t.ACC, [{SYS_CONSTANTS['TMP']}]"); self.emit("LD\t.A, .ACC"); self.emit("AND")
            elif val_expr == '1' or val_expr == 'true':
                self.emit(f"LD\t.ACC, [{addr_msk}]"); self.emit("LD\t.B, .ACC")
                self.emit(f"LD\t.ACC, [{SYS_CONSTANTS['TMP']}]"); self.emit("LD\t.A, .ACC"); self.emit("OR")
            else:
                self.eval_rhs_to_acc(val_expr)
                self.emit("LD\t.A, .ACC") 
                lbl_d_zero = self.new_label("D_Z"); lbl_d_end = self.new_label("D_E")
                self.emit("LD\t.B, X00"); self.emit("CMPE"); self.emit(f"JMPT\t{lbl_d_zero}")
                self.emit(f"LD\t.ACC, [{addr_msk}]"); self.emit("LD\t.B, .ACC"); self.emit(f"LD\t.ACC, [{SYS_CONSTANTS['TMP']}]"); self.emit("LD\t.A, .ACC"); self.emit("OR"); self.emit(f"JMP\t{lbl_d_end}")
                self.emit_label(lbl_d_zero)
                self.emit(f"LD\t.ACC, [{addr_msk}]"); self.emit("LD\t.A, .ACC"); self.emit("LD\t.B, XFF"); self.emit("XOR")
                self.emit("LD\t.B, .ACC"); self.emit(f"LD\t.ACC, [{SYS_CONSTANTS['TMP']}]"); self.emit("LD\t.A, .ACC"); self.emit("AND")
                self.emit_label(lbl_d_end)

            self.emit(f"WR\t{SYS_CONSTANTS['TMP']}")
            self.emit(f"LD\t.ACC, [{addr_off}]"); self.emit("LD\t.INDEX, .ACC")
            self.emit(f"LD\t.ACC, [{SYS_CONSTANTS['TMP']}]")
            self.emit(f"WRI\t{GPIO_PORTS['OUT_L']}")

    # ==========================================================================
    # GPIO READ (Híbrido) - CORREGIDO
    # ==========================================================================
    def compile_gpio_read(self, line):
        match = re.search(r'gpio_read\((.+)\)', line)
        if not match: return
        
        pin_name = match.group(1).strip()
        while pin_name in self.defines: pin_name = self.defines[pin_name]
        
        pin_num = None
        if pin_name in SYS_CONSTANTS: pin_num = int(SYS_CONSTANTS[pin_name])
        elif pin_name.isdigit(): pin_num = int(pin_name)

        if pin_num is not None:
            # --- MODO ESTÁTICO ---
            port_addr = ""
            bit_rel = 0
            if pin_num < 8:   port_addr = GPIO_PORTS["IN_L"]; bit_rel = pin_num
            elif pin_num < 16: port_addr = GPIO_PORTS["IN_M"]; bit_rel = pin_num - 8
            else:             port_addr = GPIO_PORTS["IN_H"]; bit_rel = pin_num - 16

            self.emit(f"LD\t.A, [{port_addr}]")
            self.emit("LD\t.B, X00"); self.emit("ADD") 
            for _ in range(bit_rel): self.emit("SHIFTR")
            self.emit("LD\t.A, .ACC")
            self.emit("LD\t.B, X01"); self.emit("AND")
        else:
            # --- MODO DINÁMICO ---
            self.emit("", comment=f"Dynamic GPIO Read: {pin_name}")
            addr_pin = self.get_var_addr("__d_r_pin")
            addr_off = self.get_var_addr("__d_r_off")
            addr_bit = self.get_var_addr("__d_r_bit")
            
            self.eval_rhs_to_acc(pin_name)
            self.emit(f"WR\t{addr_pin}")
            
            lbl_try_m = self.new_label("R_TRY_M")
            lbl_try_h = self.new_label("R_TRY_H")
            lbl_calc_ok = self.new_label("R_CALC_OK")
            
            # --- FIX: Inicializar por defecto a Puerto L ---
            self.emit("LD\t.ACC, X00"); self.emit(f"WR\t{addr_off}")
            self.emit(f"LD\t.ACC, [{addr_pin}]"); self.emit(f"WR\t{addr_bit}")
            
            self.emit(f"LD\t.ACC, [{addr_pin}]"); self.emit("LD\t.A, .ACC") # FIX: Cargar A
            self.emit("LD\t.B, X08"); self.emit("CMPL"); self.emit(f"JMPT\t{lbl_calc_ok}")
            
            self.emit(f"LD\t.ACC, [{addr_pin}]"); self.emit("LD\t.A, .ACC")
            self.emit("LD\t.B, X10"); self.emit("CMPL"); self.emit(f"JMPT\t{lbl_try_m}")
            
            self.emit_label(lbl_try_h)
            self.emit("LD\t.ACC, X02"); self.emit(f"WR\t{addr_off}")
            self.emit(f"LD\t.ACC, [{addr_pin}]"); self.emit("LD\t.A, .ACC"); self.emit("LD\t.B, X10"); self.emit("SUB"); self.emit(f"WR\t{addr_bit}")
            self.emit(f"JMP\t{lbl_calc_ok}")
            
            self.emit_label(lbl_try_m)
            self.emit("LD\t.ACC, X01"); self.emit(f"WR\t{addr_off}")
            self.emit(f"LD\t.ACC, [{addr_pin}]"); self.emit("LD\t.A, .ACC"); self.emit("LD\t.B, X08"); self.emit("SUB"); self.emit(f"WR\t{addr_bit}")
            
            self.emit_label(lbl_calc_ok)
            
            self.emit(f"LD\t.ACC, [{addr_off}]"); self.emit("LD\t.INDEX, .ACC")
            self.emit(f"LDI\t.ACC, [{GPIO_PORTS['IN_L']}]")
            self.emit("LD\t.A, .ACC") 
            
            lbl_shift_loop = self.new_label("R_SH_LOOP")
            lbl_shift_end = self.new_label("R_SH_END")
            
            self.emit_label(lbl_shift_loop)
            self.emit(f"LD\t.ACC, [{addr_bit}]"); self.emit("LD\t.A, .ACC"); self.emit("LD\t.B, X00"); self.emit("CMPE"); self.emit(f"JMPT\t{lbl_shift_end}")
            
            self.emit("LD\t.B, X00"); self.emit("ADD") 
            self.emit("SHIFTR") 
            self.emit("LD\t.A, .ACC")
            
            self.emit(f"LD\t.ACC, [{addr_bit}]"); self.emit("LD\t.A, .ACC"); self.emit("LD\t.B, X01"); self.emit("SUB"); self.emit(f"WR\t{addr_bit}")
            self.emit(f"JMP\t{lbl_shift_loop}")
            
            self.emit_label(lbl_shift_end)
            self.emit("LD\t.B, X01")
            self.emit("AND")

    def smart_normalize(self, raw_source):
        raw_lines = raw_source.split('\n')
        clean_lines = []
        for line in raw_lines:
            line = line.split('//')[0].strip()
            if line: clean_lines.append(line)
        
        normalized_lines = []
        i = 0
        while i < len(clean_lines):
            line = clean_lines[i]
            if re.match(r'(if|while|switch|void)\s*.*\(.*\)', line) and not line.endswith('{'):
                if i + 1 < len(clean_lines) and clean_lines[i+1] == '{':
                    normalized_lines.append(line + " {"); i += 2; continue
            normalized_lines.append(line)
            i += 1
        return normalized_lines

    def compile(self, source):
        lines = self.smart_normalize(source)
        brace_level = 0

        for i, line in enumerate(lines):
            if line.startswith("#define"):
                parts = line.split()
                if len(parts) >= 3: self.defines[parts[1]] = parts[2]
                continue

            match_arr_decl = re.match(r'int\s+(\w+)\[(\d+)\];', line)
            if match_arr_decl:
                name, size = match_arr_decl.groups()
                base_addr = f"X{self.mem_ptr:02X}"
                self.arrays[name] = base_addr
                self.mem_ptr += int(size)
                continue

            if line.startswith("void setup()"):
                self.context = "SETUP"; self.current_buffer = self.code_setup
                self.emit_label("#SETUP")
                if line.endswith('{'): brace_level += 1
                continue
            if line.startswith("void loop()"):
                self.context = "LOOP"; self.current_buffer = self.code_loop
                self.emit_label("#LOOP_START")
                if line.endswith('{'): brace_level += 1
                continue
            if line.startswith("void ISR()"):
                self.context = "ISR"; self.current_buffer = self.code_isr
                if line.endswith('{'): brace_level += 1
                continue

            if "gpio_write" in line:
                self.compile_gpio_write(line)
                continue

            match_switch = re.match(r'switch\s*\((.+)\)\s*\{', line)
            if match_switch:
                var_switch = match_switch.group(1)
                l_end = self.new_label("SW_END")
                self.block_stack.append(['SWITCH', var_switch, l_end, None])
                brace_level += 1
                continue

            match_case = re.match(r'case\s*(.+)\s*:', line)
            if match_case:
                val_case = match_case.group(1)
                sw = None
                for block in reversed(self.block_stack):
                    if block[0] == 'SWITCH': sw = block; break
                if sw:
                    if sw[3]: self.emit_label(sw[3]) 
                    l_body, l_next = self.new_label("C_BODY"), self.new_label("C_NEXT")
                    self.emit(f"LD\t.A, {self.resolve_operand(sw[1])}")
                    self.emit(f"LD\t.B, {self.resolve_operand(val_case)}")
                    self.emit("CMPE"); self.emit(f"JMPT\t{l_body}"); self.emit(f"JMP\t{l_next}")
                    self.emit_label(l_body)
                    sw[3] = l_next
                continue

            if line == "break;":
                target_label = None
                for block in reversed(self.block_stack):
                    if block[0] in ['SWITCH', 'WHILE', 'WHILE_1']: target_label = block[2]; break
                if target_label: self.emit(f"JMP\t{target_label}")
                continue

            if line.endswith("{"):
                brace_level += 1
                if re.match(r'while\s*\(\s*(1|true)\s*\)\s*\{', line):
                    l_start = self.new_label("W1_S")
                    self.emit_label(l_start)
                    self.block_stack.append(('WHILE_1', l_start, None)) 
                    continue
                match_if = re.match(r'if\s*\((.+)\s*(==|>|<)\s*(.+)\)\s*\{', line)
                if match_if:
                    op1, cond, op2 = match_if.groups()
                    l_true, l_end = self.new_label("IF_T"), self.new_label("IF_E")
                    if "gpio_read" in op1:
                        self.compile_gpio_read(op1); self.emit("LD\t.A, .ACC")
                    else: self.emit(f"LD\t.A, {self.resolve_operand(op1)}")
                    self.emit(f"LD\t.B, {self.resolve_operand(op2)}")
                    if cond == "==": self.emit("CMPE")
                    elif cond == ">": self.emit("CMPG")
                    elif cond == "<": self.emit("CMPL")
                    self.emit(f"JMPT\t{l_true}"); self.emit(f"JMP\t{l_end}"); self.emit_label(l_true)
                    self.block_stack.append(('IF', l_end))
                    continue
                match_while = re.match(r'while\s*\((.+)\s*(==|>|<)\s*(.+)\)\s*\{', line)
                if match_while:
                    op1, cond, op2 = match_while.groups()
                    l_start, l_body, l_end = self.new_label("W_S"), self.new_label("W_B"), self.new_label("W_E")
                    self.emit_label(l_start)
                    self.emit(f"LD\t.A, {self.resolve_operand(op1)}")
                    self.emit(f"LD\t.B, {self.resolve_operand(op2)}")
                    if cond == "==": self.emit("CMPE")
                    elif cond == ">": self.emit("CMPG")
                    elif cond == "<": self.emit("CMPL")
                    self.emit(f"JMPT\t{l_body}"); self.emit(f"JMP\t{l_end}"); self.emit_label(l_body)
                    self.block_stack.append(('WHILE', l_start, l_end))
                    continue
                continue

            if line == "}":
                brace_level -= 1
                if self.block_stack:
                    blk = self.block_stack.pop()
                    if blk[0] == 'WHILE': 
                        self.emit(f"JMP\t{blk[1]}"); self.emit_label(blk[2])
                    elif blk[0] == 'WHILE_1': self.emit(f"JMP\t{blk[1]}")
                    elif blk[0] == 'IF': self.emit_label(blk[1])
                    elif blk[0] == 'SWITCH':
                        if blk[3]: self.emit_label(blk[3])
                        self.emit_label(blk[2])
                elif self.context == "LOOP" and brace_level == 0:
                    self.emit("JMP\t#LOOP_START"); self.context = "GLOBAL"; self.current_buffer = None
                elif self.context == "ISR" and brace_level == 0:
                    self.emit("RETI"); self.context = "GLOBAL"; self.current_buffer = None
                elif self.context == "SETUP" and brace_level == 0:
                    self.emit("JMP\t#LOOP_START"); self.context = "GLOBAL"; self.current_buffer = None
                continue

            if line.startswith("return;"): 
                if self.context == "LOOP": self.emit("JMP\t#LOOP_START")
                if self.context == "ISR": self.emit("RETI")
                continue

            if '=' in line and not line.startswith("if") and not line.startswith("while"):
                line = line.replace(';', '')
                dest, expr = line.split('=', 1)
                dest = dest.strip()
                if dest.startswith("int "): dest = dest[4:].strip()
                self.compile_expr(dest, expr)
                continue

            if "serial_print" in line:
                content_match = re.search(r'serial_print\((.*)\)', line)
                if content_match:
                    content = content_match.group(1)
                    parts = content.split(',', 1)
                    fmt_str_raw = parts[0].strip().strip('"')
                    args = []
                    if len(parts) > 1: args = [x.strip() for x in parts[1].split(',')]
                    print_queue = []
                    arg_idx = 0
                    k = 0
                    while k < len(fmt_str_raw):
                        if fmt_str_raw[k] == '%' and k+1 < len(fmt_str_raw) and fmt_str_raw[k+1] == 'd':
                            if arg_idx < len(args):
                                print_queue.append(('VAR', args[arg_idx])); arg_idx += 1
                            k += 2
                        elif fmt_str_raw[k] == '\\' and k+1 < len(fmt_str_raw):
                            next_char = fmt_str_raw[k+1]
                            if next_char == 'n':   print_queue.append(('LIT', '\n')); k += 2
                            elif next_char == 'r': print_queue.append(('LIT', '\r')); k += 2
                            else:                  print_queue.append(('LIT', fmt_str_raw[k])); k += 1
                        else:
                            print_queue.append(('LIT', fmt_str_raw[k])); k += 1
                    self.emit("", comment=f"Print: {fmt_str_raw}")
                    for chunk_i in range(0, len(print_queue), 2):
                        item1 = print_queue[chunk_i]
                        item2 = print_queue[chunk_i+1] if chunk_i+1 < len(print_queue) else ('LIT', ' ') 
                        if item1[0] == 'LIT': self.emit(f"LD\t.ACC, X{ord(item1[1]):02X}"); self.emit("WR\tTXBUF0")
                        else: self.eval_rhs_to_acc(item1[1]); self.emit("LD\t.A, .ACC"); self.emit("BIN2ASCII"); self.emit("WR\tTXBUF0")
                        if item2[0] == 'LIT': self.emit(f"LD\t.ACC, X{ord(item2[1]):02X}"); self.emit("WR\tTXBUF1")
                        else: self.eval_rhs_to_acc(item2[1]); self.emit("LD\t.A, .ACC"); self.emit("BIN2ASCII"); self.emit("WR\tTXBUF1")
                        self.emit("SEND")
                continue

        final_asm = []
        final_asm.append("; --- BOOT SECTOR ---")
        final_asm.append("JMP\t#SETUP")
        final_asm.append("; --- INTERRUPT VECTOR (0x002) ---")
        final_asm.append("#ISR")
        if self.code_isr: final_asm.extend(self.code_isr)
        else: final_asm.append("\t\tRETI ; ISR vacia por defecto")
        final_asm.append("; --- MAIN PROGRAM ---")
        final_asm.extend(self.code_setup)
        final_asm.extend(self.code_loop)
        return "\n".join(final_asm)

if __name__ == "__main__":
    try:
        with open(INPUT_FILE, 'r') as f: src = f.read()
    except: print(f"Error: Crea '{INPUT_FILE}'"); sys.exit(1)
    
    asm = SmartCCompiler().compile(src)
    print(asm)
    with open(OUTPUT_FILE, 'w') as f: f.write(asm)
    print(f"\n[OK] {OUTPUT_FILE} generado.")