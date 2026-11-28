# El núcleo se reescribe en Rust tras una suite de contrato

🇬🇧 [English](0001-rust-core-behind-contract-suite.md) | 🇪🇸 Español

El núcleo pasa de Python a Rust por partes (jugadores, convocatorias, partidos,
estadísticas, alojamiento de plugins), y cada parte se integra en `main` por separado. El
núcleo de Python sigue dando servicio a las peñas hasta que el de Rust pasa la misma suite
de caja negra, `contract/`, que prueba un núcleo solo a través de `/api/v1` y de sus
ficheros de `data/`. La suite está escrita en Rust y usa JSON en bruto en lugar de
`clients/pyball-client-rs`, así que no comparte código con ningún núcleo ni plugin. Activa
una feature de Cargo por área, de modo que a un núcleo parcial se le exigen solo las áreas
que tiene.

Al terminar la reescritura, la suite se queda: es el contrato del núcleo con los plugins,
la interfaz web y los ficheros de `data/`, sea cual sea el núcleo que lo implemente.

## Opciones consideradas

- **Portar los tests unitarios y de integración de Python.** Prueban las capas internas de
  Python, así que no podrían comprobar un núcleo en Rust, y portarlos junto con el código
  comprueba el código nuevo contra sí mismo.
- **Reescribir el núcleo de una vez.** Supondría una rama de larga duración sin nada que la
  comprobara contra el núcleo en producción hasta el cambio.
