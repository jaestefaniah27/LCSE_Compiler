// ==========================================
// CONTROLADOR PIC - FINAL
// ==========================================

int temp_val = 0;
int cmd_id = 0;
int cmd_val = 0;
int decenas = 0;
int unidades = 0;

void setup()
{
    ADDR_ORDER = 0;
    ADDR_PARITY = 4; // None
    ADDR_STOP = 2;   // 1bit
    ADDR_NBITS = 8;  // 8bits
    ADDR_BAUD = 8;   // 115200bps (Ajustar segun tu NCO)

    TSTAT = 16;
    actuador[0] = 0;
    interruptor[0] = 0;

    NINST = 0;
    serial_print("SYSTEM READY");
}

void loop()
{
    while (NINST < 255)
    {
        // Wait
    }
    NINST = 0;

    switch (RCBUF0)
    {

    case 'I': // Interruptores
        cmd_id = RCBUF1 - 48;
        cmd_val = RCBUF2 - 48;

        if (cmd_id > 7)
        {
            serial_print("ER");
            break;
        }
        if (cmd_val > 1)
        {
            serial_print("ER");
            break;
        }

        interruptor[cmd_id] = cmd_val;
        serial_print("OK");
        break;

    case 'A': // Actuadores
        cmd_id = RCBUF1 - 48;
        cmd_val = RCBUF2 - 48;

        if (cmd_id > 9)
        {
            serial_print("ER");
            break;
        }
        if (cmd_val > 9)
        {
            serial_print("ER");
            break;
        }

        actuador[cmd_id] = cmd_val;
        serial_print("OK");
        break;

    case 'T': // Termostato
        if (RCBUF1 < '1')
        {
            serial_print("ER");
            break;
        }
        if (RCBUF1 > '2')
        {
            serial_print("ER");
            break;
        }

        decenas = RCBUF1 - 48;
        decenas = decenas << 4;
        unidades = RCBUF2 - 48;

        TSTAT = decenas + unidades;
        serial_print("OK");
        break;

    case 'S': // Info
        if (RCBUF1 == 'T')
        {
            decenas = TSTAT >> 4;
            unidades = TSTAT & 0x0F;
            serial_print("%d%d", decenas, unidades);
            break;
        }
        if (RCBUF1 == 'A')
        {
            cmd_id = RCBUF2 - 48;
            if (cmd_id > 9)
            {
                serial_print("ER");
                break;
            }

            // Leer Actuador del array
            cmd_val = actuador[cmd_id];

            // Enviar respuesta "A" + Valor
            serial_print("A%d", cmd_val); // Trigger manual
            break;
        }
        if (RCBUF1 == 'I')
        {
            cmd_id = RCBUF2 - 48;
            if (cmd_id > 7)
            {
                serial_print("ER");
                break;
            }

            cmd_val = interruptor[cmd_id];
            serial_print("I%d", cmd_val);
            break;
        }
        if (RCBUF1 == 'R')
        {
            serial_print("BAUD: ");
            if (ADDR_BAUD == 0)
            {
                serial_print("300 ");
            }
            if (ADDR_BAUD == 1)
            {
                serial_print("1200 ");
            }
            if (ADDR_BAUD == 2)
            {
                serial_print("2400 ");
            }
            if (ADDR_BAUD == 3)
            {
                serial_print("4800 ");
            }
            if (ADDR_BAUD == 4)
            {
                serial_print("9600 ");
            }
            if (ADDR_BAUD == 5)
            {
                serial_print("19200 ");
            }
            if (ADDR_BAUD == 6)
            {
                serial_print("38400 ");
            }
            if (ADDR_BAUD == 7)
            {
                serial_print("57600 ");
            }
            if (ADDR_BAUD == 8)
            {
                serial_print("115200 ");
            }
            if (ADDR_BAUD == 9)
            {
                serial_print("230400 ");
            }
            serial_print("N_BITS: ");
            serial_print("%d", ADDR_NBITS);
            serial_print("STOP: ");
            if (ADDR_STOP == 2)
            {
                serial_print("1 ");
            }
            if (ADDR_STOP == 3)
            {
                serial_print("1.5 ");
            }
            if (ADDR_STOP == 4)
            {
                serial_print("2 ");
            }
            serial_print("PARITY: ");
            if (ADDR_PARITY == 0)
            {
                serial_print("EVEN ");
            }
            if (ADDR_PARITY == 1)
            {
                serial_print("ODD ");
            }
            if (ADDR_PARITY == 2)
            {
                serial_print("MARK ");
            }
            if (ADDR_PARITY == 3)
            {
                serial_print("SPACE ");
            }
            if (ADDR_PARITY == 4)
            {
                serial_print("NONE ");
            }
            break;
        }

        serial_print("ER");
        break;

    case 'R': // CONFIGURACIÓN SERIAL
        cmd_val = RCBUF2 - 48;

        // R9: Baudios
        if (RCBUF1 == '9')
        {
            if (cmd_val > 9)
            {
                serial_print("ER");
                break;
            }

            serial_print("BAUD: ");
            if (RCBUF2 == '0')
            {
                serial_print("300 ");
            }
            if (RCBUF2 == '1')
            {
                serial_print("1200 ");
            }
            if (RCBUF2 == '2')
            {
                serial_print("2400 ");
            }
            if (RCBUF2 == '3')
            {
                serial_print("4800 ");
            }
            if (RCBUF2 == '4')
            {
                serial_print("9600 ");
            }
            if (RCBUF2 == '5')
            {
                serial_print("19200 ");
            }
            if (RCBUF2 == '6')
            {
                serial_print("38400 ");
            }
            if (RCBUF2 == '7')
            {
                serial_print("57600 ");
            }
            if (RCBUF2 == '8')
            {
                serial_print("115200 ");
            }
            if (RCBUF2 == '9')
            {
                serial_print("230400 ");
            }

            serial_print("OK");
            ADDR_BAUD = cmd_val;
            break;
        }

        // R8: Data Bits
        if (RCBUF1 == '8')
        {
            if (cmd_val < 5)
            {
                serial_print("ER");
                break;
            }
            if (cmd_val > 8)
            {
                serial_print("ER");
                break;
            }

            serial_print("N_BITS: ");
            serial_print("%d", RCBUF2 - 48);

            serial_print("OK");
            ADDR_NBITS = cmd_val;
            break;
        }

        // R7: Stop Bits
        if (RCBUF1 == '7')
        {
            if (cmd_val < 2)
            {
                serial_print("ER");
                break;
            }
            if (cmd_val > 4)
            {
                serial_print("ER");
                break;
            }

            serial_print("STOP: ");
            if (RCBUF2 == '2')
            {
                serial_print("1 ");
            }
            if (RCBUF2 == '3')
            {
                serial_print("1.5 ");
            }
            if (RCBUF2 == '4')
            {
                serial_print("2 ");
            }

            serial_print("OK");
            ADDR_STOP = cmd_val;
            break;
        }

        // R6: Parity
        if (RCBUF1 == '6')
        {
            if (cmd_val > 4)
            {
                serial_print("ER");
                break;
            }

            serial_print("PARITY: ");
            if (RCBUF2 == '0')
            {
                serial_print("EVEN ");
            }
            if (RCBUF2 == '1')
            {
                serial_print("ODD ");
            }
            if (RCBUF2 == '2')
            {
                serial_print("MARK ");
            }
            if (RCBUF2 == '3')
            {
                serial_print("SPACE ");
            }
            if (RCBUF2 == '4')
            {
                serial_print("NONE ");
            }

            serial_print("OK");
            ADDR_PARITY = cmd_val;
            break;
        }
    default:
        serial_print("ER");
        break;
    }
}