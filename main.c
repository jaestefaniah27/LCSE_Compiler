// --- 1. PRUEBA DE GLOBALES E INICIALIZACIÓN ---
int contador_isr = 0; // Se debe inicializar en el bloque #GLOBAL_INIT
int test_array[5];    // Reserva de espacio sin valor inicial
int estado = 0;       // Máquina de estados para el test

// --- 2. PRUEBA DE INTERRUPCIÓN (ISR) ---
// El compilador debe colocar esto para ser llamado desde 0x002
void ISR()
{
    contador_isr = contador_isr + 1;
}

void setup()
{
    serial_print("--- INICIO DE TEST COMPLETO ---\n");

    // Inicializar array
    test_array[0] = 10;
    test_array[1] = 20;
    test_array[2] = 30;

    serial_print("Setup finalizado. Entrando al loop.\n");
}

void loop()
{
    // Usamos 'estado' para ejecutar las pruebas una sola vez secuencialmente

    // --- TEST 1: MATEMÁTICAS Y PRECEDENCIA ---
    if (estado == 0)
    {
        serial_print("TEST 1: Matematicas\n");

        int a = 5;
        int b = 3;
        int c = 2;

        // Debe respetar parentesis: (5 + 3) = 8, luego << 1 = 16.
        // Si fallara la precedencia y hiciera 3<<1 primero (6), daría 5+6=11.
        int res = (a + b) << 1;

        serial_print("  (5+3)<<1 Esperado 16: %d\n", res);

        // Prueba compleja combinada
        // (10 - 2) & (3 | 4) -> 8 & 7 -> 0
        int res2 = (10 - c) & (b | 4);
        serial_print("  (10-2)&(3|4) Esperado 0: %d\n", res2);

        estado = 1;
    }

    // --- TEST 2: ARRAYS Y ACCESO INDEXADO ---
    else if (estado == 1)
    {
        serial_print("TEST 2: Arrays\n");

        // Lectura con variable (Usa registro .INDEX)
        int i = 2;
        int val = test_array[i];
        serial_print("  Array[2] Esperado 30: %d\n", val);

        // Escritura con variable
        test_array[i] = 55;
        val = test_array[i];
        serial_print("  Nuevo Array[2] Esperado 55: %d\n", val);

        estado = 2;
    }

    // --- TEST 3: LÓGICA BOOLEANA AVANZADA ---
    else if (estado == 2)
    {
        serial_print("TEST 3: Logica && y !\n");

        int x = 10;
        int y = 0;

        // Prueba de AND Lógico (&&) y NOT (!)
        if (x == 10 && !y)
        {
            serial_print("  Condicion (x==10 && !0) -> CORRECTO\n");
        }
        else
        {
            serial_print("  Condicion FALLO\n");
        }

        if (x != 5)
        {
            serial_print("  Condicion (x!=5) -> CORRECTO\n");
        }

        estado = 3;
    }

    // --- TEST 4: BUCLES WHILE ---
    else if (estado == 3)
    {
        serial_print("TEST 4: While Loop\n");
        int k = 0;
        int suma = 0;

        // Sumatoria 1+2+3
        while (k < 4)
        {
            suma = suma + k;
            k = k + 1;
        }
        serial_print("  Suma 0+1+2+3 Esperado 6: %d\n", suma);

        estado = 4;
        serial_print("--- TEST FINALIZADO. PROBANDO GPIO ---\n");
    }

    // --- TEST 5: GPIO E INTERACTIVIDAD (Bucle infinito final) ---
    else
    {
        // Copiar botones a LEDs para probar lectura/escritura física
        // Si pulsas BTN_CENTER, enciende LED0
        if (gpio_read(BTN_CENTER) == 1)
        {
            gpio_write(LED0, 1);
        }
        else
        {
            gpio_write(LED0, 0);
        }

        // Si pulsas BTN_UP, enciende LED1
        if (gpio_read(BTN_UP))
        {
            gpio_write(LED1, 1);
        }
        else
        {
            gpio_write(LED1, 0);
        }
    }
}