# PUNTO DE VENTA 2.3 — Altoplano (POSNext + Restaurant)

Módulo de punto de venta y restaurante para **ERPNext v15 + POSNext**.

Incluye:

- **Comandas y cocina (KDS)**: envío incremental a cocina, estados Pendiente → En preparación → Lista → Entregada / Cancelada, recetario (ingredientes base + extras + retiros).
- **Salones y mesas**: plano de mesas (croquis), salones, sesiones de mesa, estados Disponible / Ocupada / Reservada / Limpieza, comensales y mesero.
- **Modificadores**: grupos y opciones de modificador con delta de precio e ingredientes (añadir / retirar).
- **Inventario por receta**: al facturar, descuenta insumos según BOM + modificadores mediante Stock Entry (Material Issue).
- **Propina**: campo de propina en factura POS con cuenta contable configurable por POS Profile.
- **BZPAY como opción de pago** (sin API): modo de pago con cuenta puente. Ver [docs/BZPAY.md](docs/BZPAY.md).

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `pos_restaurant/` | App Frappe de backend (comandas, cocina, salones, mesas, modificadores, inventario). Se instala con `bench get-app`. |
| `pos_next/` | Overlay del frontend de POSNext (páginas de cocina y mesas + integración en la venta). Se copia sobre una instalación limpia de POSNext. |
| `docs/` | Guía de despliegue, BZPAY (cuenta puente), permisos y roles. |

## Requisitos

- Frappe / ERPNext v15.
- POSNext (fork `pos_next`). La app `pos_restaurant` lo declara en `required_apps`.

## Instalación rápida

Ver la guía completa en [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md).

```bash
# 1) Instalar POSNext (tu fork o el oficial) en el bench
bench get-app --branch version-15 https://github.com/tu-org/pos_next

# 2) Instalar la app de restaurante
bench get-app --branch main https://github.com/Grupo224/PUNTO-DE-VENTA-2.3-ALTOPLANO
bench --site TU_SITIO install-app pos_restaurant
bench --site TU_SITIO migrate

# 3) Aplicar el overlay de frontend (cocina y mesas) sobre POSNext
#    (copiar los archivos de pos_next/ y reconstruir el build de Vite)
```

## Aplicación del overlay de frontend

Los archivos de `pos_next/` se copian sobre una instalación limpia de POSNext
y luego se reconstruye el frontend:

```bash
cd apps/pos_next
# copiar páginas y componentes (ver docs/DESPLIEGUE.md para la lista exacta)
npm install
npm run build
```

## Genericidad

- Sin datos de cliente ni de un sitio demo (sin empresa, almacén, usuarios ni credenciales).
- Sin secretos ni tokens.
- Nombres genéricos (`pos_restaurant`, doctypes `Restaurant *`).
- BZPAY solo como **opción de pago**; no incluye integración por API.

## Licencia

MIT
