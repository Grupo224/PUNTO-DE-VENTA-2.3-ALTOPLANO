# BZPAY — solo como opción de pago (cuenta puente)

BZPAY **no** se integra por API en esta app. Se configura como un **modo de pago**
normal de ERPNext y su importe se registra en una **cuenta puente (cuenta de paso)**
hasta que se concilie con el banco.

## Configuración

1. Crea la cuenta puente (si no existe):

   - **Desk → Contabilidad → Plan de cuentas** (Chart of Accounts).
   - Nueva cuenta, por ejemplo `BZPAY por liquidar`, tipo `Banco` (o `Efectivo`
     según tu política contable). Es la cuenta de paso donde se acumulan los cobros
     de BZPAY hasta su liquidación.

2. Crea el modo de pago:

   - **Desk → Contabilidad → Modo de pago**, nuevo `BZPAY` (tipo `Banco`).
   - En la tabla **Cuentas**, agrega tu compañía y como **Cuenta por defecto**
     selecciona la cuenta puente `BZPAY por liquidar`.

3. Agrégalo al perfil de POS:

   - **Desk → Ventas → POS Profile** (tu perfil).
   - En **Pagos** agrega el modo de pago `BZPAY`.

## Comportamiento

- Cuando el cajero cobra con BZPAY, POSNext registra el pago contra la **cuenta puente**.
- Al recibir la liquidación real de BZPAY en tu banco, concilia la cuenta puente contra
  la cuenta de banco mediante un asiento (Journal Entry) o la herramienta de conciliación.

No se requiere código adicional: el flujo usa el modo de pago nativo de ERPNext/POSNext.
