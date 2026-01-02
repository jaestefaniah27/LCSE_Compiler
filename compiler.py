import sys
import re

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
INPUT_FILE = 'PROGRAM.txt'
OUTPUT_FILE = 'ROM_Generated.vhd'
MAX_ROM_SIZE = 4096 

# ==============================================================================
# CONSTANTES Y MAPEO
# ==============================================================================
DEFAULT_SYMBOLS = {
    "RCBUF0": "X00", "RCBUF1": "X01", "RCBUF2": "X02", "NINST": "X03",
    "TXBUF0": "X04", "TXBUF1": "X05",
    "SWBASE": "X10", "LEVBASE": "X20", "TSTAT": "X31", "GPMEM": "X40", "TMP": "X41",
    "ADDR_PARITY": "X06", "ADDR_STOP": "X07", "ADDR_NBITS": "X08", "ADDR_BAUD": "X09"
}

# Instrucciones ALU (TYPE 1)
ALU_OPS = {
    'ADD': 'ALU_ADD', 'SUB': 'ALU_SUB', 
    'SHIFTL': 'ALU_SHIFTL', 'SHIFTR': 'ALU_SHIFTR',
    'AND': 'ALU_AND', 'OR': 'ALU_OR', 'XOR': 'ALU_XOR',
    'CMPE': 'ALU_CMPE', 'CMPG': 'ALU_CMPG', 'CMPL': 'ALU_CMPL',
    'ASCII2BIN': 'ALU_ASCII2BIN', 'BIN2ASCII': 'ALU_BIN2ASCII',
    'OEACC':    'ALU_OEACC',
    'MVACC2A':  'ALU_MVACC2A', 
    'MVACC2B':  'ALU_MVACC2B',
    'MVACC2ID': 'ALU_MVACC2ID'
}

# Instrucciones Especiales (TYPE 4)
SPECIAL_OPS = {
    'SEND': 'I_SEND', 
    'RETI': 'I_RETI'
}

REGISTERS = {'.A': 'DST_A', '.B': 'DST_B', '.ACC': 'DST_ACC', '.INDEX': 'DST_INDX'}

# ==============================================================================
# UTILIDADES
# ==============================================================================
def to_hex_12bit(value_str):
    value_str = value_str.strip()
    try:
        val = int(value_str[1:], 16) if value_str.startswith('X') else int(value_str)
        val = val & 0xFFF 
    except ValueError: return None
    return f'X"{val:03X}"'

def parse_line(line): return line.split(';')[0].strip()

label_table = {}
symbol_table = DEFAULT_SYMBOLS.copy()
rom_content = []

# ==============================================================================
# PASADA 1: ETIQUETAS
# ==============================================================================
try:
    with open(INPUT_FILE, 'r') as f: lines = f.readlines()
except: print(f"Error: Falta {INPUT_FILE}"); sys.exit(1)

pc = 0
for line in lines:
    clean = parse_line(line)
    if not clean: continue
    if ':' in clean:
        parts = clean.split(':')
        symbol_table[parts[0].strip()] = parts[1].strip()
        continue
    if clean.startswith('#'):
        label_table[clean.split()[0][1:]] = pc
        if len(clean.split()) > 1: clean = " ".join(clean.split()[1:])
        else: continue
    
    parts = clean.replace(',', ' ').split()
    mnemonic = parts[0].upper()
    
    if mnemonic in ALU_OPS or mnemonic in SPECIAL_OPS: pc += 1
    elif mnemonic in ['JMP', 'JMPT']: pc += 2
    elif mnemonic in ['LD', 'LDI', 'WR', 'WRI']:
        if mnemonic == 'LD' and len(parts) > 2 and parts[2].upper() == '.ACC': pc += 1
        else: pc += 2

# ==============================================================================
# PASADA 2: GENERACIÓN DE CÓDIGO
# ==============================================================================
pc = 0
def resolve(token):
    res = to_hex_12bit(token)
    if res: return res
    if token in symbol_table: return to_hex_12bit(symbol_table[token])
    if token in label_table: return f'X"{label_table[token]:03X}"'
    if token.startswith('[') and token.endswith(']'): return resolve(token[1:-1])
    return f'ERROR({token})'

for line in lines:
    clean = parse_line(line)
    if not clean: continue
    if ':' in clean: continue
    if clean.startswith('#'):
        if len(clean.split()) > 1: clean = " ".join(clean.split()[1:])
        else: continue

    parts = clean.replace(',', ' ').split()
    mnemonic = parts[0].upper()

    if pc >= MAX_ROM_SIZE:
        print(f"ERROR FATAL: El programa excede el tamaño de la ROM ({MAX_ROM_SIZE}).")
        sys.exit(1)

    # --- TYPE 1: ALU ---
    if mnemonic in ALU_OPS:
        rom_content.append((pc, f'X"0" & TYPE_1 & {ALU_OPS[mnemonic]}'))
        pc += 1
        
    # --- TYPE 2: SALTOS ---
    elif mnemonic in ['JMP', 'JMPT']:
        type_jmp = 'JMP_UNCOND' if mnemonic == 'JMP' else 'JMP_COND'
        rom_content.append((pc, f'X"0" & TYPE_2 & {type_jmp}'))
        pc += 1
        rom_content.append((pc, resolve(parts[1].replace('#', ''))))
        pc += 1
        
    # --- TYPE 3: CARGA/ALMACENAMIENTO ---
    elif mnemonic in ['LD', 'LDI', 'WR', 'WRI']:
        op1 = parts[1]
        
        if mnemonic == 'LD':
            # CORRECCIÓN: El destino está en op1 (parts[1]), no en op2
            dst = REGISTERS.get(op1.upper(), 'DST_UNK')
            op2 = parts[2]
            
            if op2.upper() == '.ACC': # LD DST, .ACC
                rom_content.append((pc, f'X"0" & TYPE_3 & LD & SRC_ACC & {dst}'))
                pc += 1
            else:
                # Determinar si es Memoria directa [Xnn] o Constante Xnn
                src_type = 'SRC_MEM' if op2.startswith('[') else 'SRC_CONSTANT'
                rom_content.append((pc, f'X"0" & TYPE_3 & LD & {src_type} & {dst}'))
                pc += 1
                rom_content.append((pc, resolve(op2)))
                pc += 1
                
        elif mnemonic == 'LDI':
            dst = REGISTERS.get(op1.upper(), 'DST_UNK')
            op2 = parts[2] # Origen Indexado
            rom_content.append((pc, f'X"0" & TYPE_3 & LD & SRC_INDXD_MEM & {dst}'))
            pc += 1
            rom_content.append((pc, resolve(op2)))
            pc += 1
            
        elif mnemonic == 'WR':
            rom_content.append((pc, f'X"0" & TYPE_3 & WR & SRC_ACC & DST_MEM'))
            pc += 1
            rom_content.append((pc, resolve(op1)))
            pc += 1
            
        elif mnemonic == 'WRI':
            rom_content.append((pc, f'X"0" & TYPE_3 & WR & SRC_ACC & DST_INDXD_MEM'))
            pc += 1
            rom_content.append((pc, resolve(op1)))
            pc += 1

    # --- TYPE 4: SPECIAL (SEND, RETI) ---
    elif mnemonic in SPECIAL_OPS:
        vhdl_constant = SPECIAL_OPS[mnemonic]
        rom_content.append((pc, f'X"0" & TYPE_4 & {vhdl_constant}'))
        pc += 1

# ==============================================================================
# ESCRITURA DEL ARCHIVO VHDL
# ==============================================================================
with open(OUTPUT_FILE, 'w') as f:
    f.write("""LIBRARY IEEE;
USE IEEE.std_logic_1164.all;
USE IEEE.numeric_std.all;
USE work.PIC_pkg.all;

entity ROM_Generated is
  port (
    Instruction     : out std_logic_vector(11 downto 0);
    Program_counter : in  std_logic_vector(11 downto 0));
end ROM_Generated;

architecture AUTOMATIC of ROM_Generated is
begin
    with Program_counter select
        Instruction <=
""")
    for addr, code in rom_content:
        f.write(f'            {code} when X"{addr:03X}",\n')
    f.write('            X"0" & TYPE_1 & ALU_ADD when others;\nend AUTOMATIC;')

print(f"[OK] ROM Generada. Tamaño: {pc}/{MAX_ROM_SIZE} palabras.")