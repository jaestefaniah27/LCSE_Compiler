int t1 = 0;
int t2 = 1;
int next_term = 0;

// Variable para recordar el estado del botón en el ciclo anterior
int btn_prev = 0;

void setup()
{
    serial_print("SISTEMA LISTO: FIBONACCI (Flancos). PULSAR CENTRAL\n");
}

void loop()
{
    // 1. Leemos el estado ACTUAL del botón
    int btn_now = gpio_read(BTN_CENTER);

    // 2. Comprobamos FLANCO DE SUBIDA (Rising Edge)
    //    (Si ahora está pulsado Y antes no lo estaba)
    if (btn_now == 1 && btn_prev == 0)
    {

        // --- INICIO DE LA LÓGICA FIBONACCI ---
        t1 = 0;
        t2 = 1;
        int seguir = 1;

        serial_print("Secuencia: %d, %d", t1, t2);

        while (seguir == 1)
        {
            next_term = t1 + t2;

            if (next_term < t1)
            { // Detección de Overflow (8 bits)
                seguir = 0;
            }
            else
            {
                serial_print(", %d", next_term);
                t1 = t2;
                t2 = next_term;

                if (t1 > 144)
                { // Límite de seguridad
                    seguir = 0;
                }
            }
        }
        serial_print("\n");
        // --- FIN DE LA LÓGICA ---
    }

    // 3. Guardar el estado actual para la siguiente vuelta
    //    Esto es lo que permite detectar el cambio la próxima vez
    btn_prev = btn_now;
}