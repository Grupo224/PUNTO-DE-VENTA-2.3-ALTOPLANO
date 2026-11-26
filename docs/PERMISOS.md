# Permisos y roles

La app `pos_restaurant` no usa `ignore_permissions`; los permisos se declaran en cada
doctype para los siguientes roles:

| Doctype | Roles con acceso |
|---|---|
| Comanda | System Manager, POSNext Cashier, Nexus POS Manager |
| Comanda Item | (hijo de Comanda) |
| Restaurant Modifier Group | System Manager, POSNext Cashier, Nexus POS Manager |
| Restaurant Modifier Option | (hijo de Restaurant Modifier Group) |
| Restaurant Item Modifier Group | (hijo de Item) |
| Restaurant Room | System Manager, POSNext Cashier, Nexus POS Manager |
| Restaurant Table | System Manager, POSNext Cashier, Nexus POS Manager |
| Table Session | System Manager, POSNext Cashier, Nexus POS Manager |
| Table Session Item | (hijo de Table Session) |

Si usas roles propios distintos, otórgales lectura/escritura sobre estos doctypes.
