# Guía de despliegue

Aplica para **Frappe / ERPNext v15** con **POSNext**.

## 1. Instalar POSNext

Instala el fork de POSNext (o el oficial) en tu bench:

```bash
bench get-app --branch version-15 https://github.com/<org>/pos_next
bench --site TU_SITIO install-app pos_next
```

## 2. Instalar la app de restaurante

```bash
bench get-app --branch main https://github.com/Grupo224/PUNTO-DE-VENTA-2.3-ALTOPLANO
bench --site TU_SITIO install-app pos_restaurant
bench --site TU_SITIO migrate
```

Al instalar, el parche `pos_restaurant.patches.create_restaurant_fields` crea los
siguientes Custom Fields de forma idempotente:

| DocType | Fieldname | Tipo |
|---|---|---|
| POS Profile | custom_restaurant_mode | Check |
| POS Profile | tip_account | Link → Account |
| Item | custom_kitchen_item | Check |
| Item | custom_preparation_options | Code (JSON) |
| Item | custom_restaurant_modifier_groups | Table → Restaurant Item Modifier Group |
| Sales Invoice | custom_tip_amount | Currency |
| Sales Invoice | custom_table | Link → Restaurant Table |
| Sales Invoice | custom_table_session | Link → Table Session |
| Sales Invoice Item | custom_restaurant_modifiers | Code (JSON) |

## 3. Aplicar el overlay de frontend

El overlay está en la carpeta `pos_next/` de este repositorio. Copia los archivos
sobre una instalación limpia de POSNext:

```bash
cd apps/pos_next

# Páginas (nuevas)
cp <repo>/pos_next/POS/src/pages/MesasView.vue     POS/src/pages/
cp <repo>/pos_next/POS/src/pages/KitchenView.vue   POS/src/pages/

# Páginas y componentes (modificados)
cp <repo>/pos_next/POS/src/pages/POSSale.vue               POS/src/pages/
cp <repo>/pos_next/POS/src/components/sale/InvoiceCart.vue POS/src/components/sale/
cp <repo>/pos_next/POS/src/components/sale/ModifierDialog.vue POS/src/components/sale/
cp <repo>/pos_next/POS/src/composables/useInvoice.js       POS/src/composables/
cp <repo>/pos_next/POS/src/router.js                        POS/src/

# Backend del POS (modificado)
cp <repo>/pos_next/pos_next/api/invoices.py            pos_next/api/
cp <repo>/pos_next/pos_next/overrides/sales_invoice.py pos_next/overrides/
cp <repo>/pos_next/pos_next/api/localization.py        pos_next/api/

npm install
npm run build
```

Después limpia la caché del navegador / service worker.

## 4. Rutas

- `/pos` — punto de venta.
- `/pos/cocina` — pantalla de cocina (KDS).
- `/pos/mesas` — plano de mesas / salones.

## 5. Roles

Los doctypes de restaurante otorgan permisos a `System Manager`,
`POSNext Cashier` y `Nexus POS Manager`. Ver [PERMISOS.md](PERMISOS.md).
