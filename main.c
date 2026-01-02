// ==========================================
// CONTROLADOR PIC - FINAL
// ==========================================
// --- ENTRADAS (Para usar con gpio_read) ---

// Switches (SW0 es Reset, SW15 es Control Display)
#define SW1 0
#define SW2 1
#define SW3 2
#define SW4 3
#define SW5 4
#define SW6 5
#define SW7 6
#define SW8 7
#define SW9 8
#define SW10 9
#define SW11 10
#define SW12 11
#define SW13 12
#define SW14 13

// Botones
#define BTN_CENTER 14 // BTNC
#define BTN_UP 15     // BTNU
#define BTN_LEFT 16   // BTNL
#define BTN_RIGHT 17  // BTNR
#define BTN_DOWN 18   // BTND

// --- SALIDAS (Para usar con gpio_write) ---

// LEDs Verdes Inferiores
#define LED0 0
#define LED1 1
#define LED2 2
#define LED3 3
#define LED4 4
#define LED5 5
#define LED6 6
#define LED7 7

// LED RGB 16 (Derecho)
#define LED16_R 8  // Rojo
#define LED16_G 9  // Verde
#define LED16_B 10 // Azul

// LED RGB 17 (Izquierdo)
#define LED17_R 11 // Rojo
#define LED17_G 12 // Verde
#define LED17_B 13 // Azul

int temp_val = 0;
int cmd_id = 0;
int cmd_val = 0;
int decenas = 0;
int unidades = 0;

int boton_u_prev = 0;
int boton_d_prev = 0;
int boton_l_prev = 0;
int boton_r_prev = 0;
int boton_c_prev = 0;

int leds_state = 0;
int leds_state_tmp = 0;

int sw_temp = 0;

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
    gpio_write(leds_state, 1);
    serial_print("SYSTEM READY\n");
}

void ISR()
{
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
        if (RCBUF1 < '0')
        {
            serial_print("ER");
            break;
        }
        if (RCBUF1 > '2')
        {
            serial_print("ER");
            break;
        }
        if (RCBUF2 > '9')
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
        if (RCBUF1 == 'R') // Mostrar info de configuración Serial
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

void loop()
{
    if (gpio_read(BTN_UP) == 1)
    {
        if (boton_u_prev == 0)
        {
            boton_u_prev = 1;
            serial_print("Boton UP pulsado\n");
            if (TSTAT < 0x29)
            {
                TSTAT = TSTAT + 1;
                // decenas = TSTAT >> 4;
                unidades = TSTAT & 0x0F;
                if (unidades > 9)
                {
                    TSTAT = TSTAT + 0x06;
                }
            }
        }
    }
    if (gpio_read(BTN_UP) == 0)
    {
        boton_u_prev = 0;
    }
    if (gpio_read(BTN_DOWN) == 1)
    {
        if (boton_d_prev == 0)
        {
            boton_d_prev = 1;
            serial_print("Boton DOWN pulsado\n");
            if (TSTAT > 0x00)
            {
                TSTAT = TSTAT - 1;
                // decenas = TSTAT >> 4;
                unidades = TSTAT & 0x0F;
                if (unidades > 9)
                {
                    TSTAT = TSTAT - 0x06;
                }
            }
        }
    }
    if (gpio_read(BTN_DOWN) == 0)
    {
        boton_d_prev = 0;
    }
    if (gpio_read(BTN_LEFT) == 1)
    {
        if (boton_l_prev == 0)
        {
            boton_l_prev = 1;
            serial_print("Boton LEFT pulsado\n");
            if (leds_state < 7)
            {
                gpio_write(leds_state, 0);
                leds_state = leds_state + 1;
                gpio_write(leds_state, 1);
            }
        }
    }
    if (gpio_read(BTN_LEFT) == 0)
    {
        boton_l_prev = 0;
    }
    if (gpio_read(BTN_RIGHT) == 1)
    {
        if (boton_r_prev == 0)
        {
            boton_r_prev = 1;
            serial_print("Boton RIGHT pulsado\n");
            if (leds_state > 0)
            {
                gpio_write(leds_state, 0);
                leds_state = leds_state - 1;
                gpio_write(leds_state, 1);
            }
        }
    }
    if (gpio_read(BTN_RIGHT) == 0)
    {
        boton_r_prev = 0;
    }
    if (gpio_read(BTN_CENTER) == 1)
    {
        if (boton_c_prev == 0)
        {
            boton_c_prev = 1;
            serial_print("Boton CENTER pulsado\n");
            serial_print("led_state: %d\n", leds_state);
        }
    }
    if (gpio_read(BTN_CENTER) == 0)
    {
        boton_c_prev = 0;
    }
    gpio_write(LED16_R, gpio_read(SW1));
    gpio_write(LED16_G, gpio_read(SW2));
    gpio_write(LED16_B, gpio_read(SW3));
    gpio_write(LED17_R, gpio_read(SW4));
    gpio_write(LED17_G, gpio_read(SW5));
    gpio_write(LED17_B, gpio_read(SW6));
}