# Excluir materiales de una fotografía

Esta herramienta permite corregir manualmente la ROI; no reconoce objetos automáticamente ni aporta validación de campo.

1. Seleccione imagen, área de cálculo y referencia iluminada de la misma superficie. Confirme y genere una primera curva: se necesita un elemento completo del carrusel para vincular las correcciones a sus entradas guardadas.
2. Pulse **Excluir materiales de la foto**. En la rejilla analizada, arrastre rectángulos sobre copas, agua u otras superficies que no correspondan a la superficie comparada. El rojo indica exclusión; la referencia iluminada no cambia. No excluya zonas solo por estar en sombra: la decisión debe responder al tipo de superficie que desea comparar.
3. Use **Deshacer** o **Limpiar** para revisar la selección. **Cancelar** no aplica el borrador. **Aplicar** rechaza una máscara que elimine toda el área válida.
4. Al aplicar, se actualizan cobertura y atenuación, se retiran los resultados térmicos anteriores y se indica que debe generar la curva de nuevo. Los valores excluidos quedan ausentes (NaN), también para los modelos térmicos estándar y avanzado, en lugar de contarse como sol.
5. Genere la curva y guarde el proyecto. Las exclusiones completas quedan en el bundle NPZ y su procedencia en SQLite. Si guarda antes de recalcular, el JSON conserva la corrección pendiente en formato compacto. Al reabrir se selecciona el mismo elemento del carrusel, incluso si no era el último.
6. Para cambiar de elemento con una corrección pendiente, genere la curva o vuelva al editor y use **Restaurar guardado** para descartar lo aplicado. No se modifica la fotografía original.

Las exclusiones están ligadas a las matrices, referencia y máscaras de su selección, además del elemento activo. Una máscara de otro tamaño o con datos no finitos se rechaza. Si falta una máscara guardada que el registro declara, no se elimina silenciosamente para recalcular otro resultado.

## Cálculo y compatibilidad

Se quitan los píxeles excluidos tanto del numerador como del denominador. En este modo, el control de contraste combina MAD y amplitud entre percentiles 5–95 de los píxeles retenidos: evita tratar dos poblaciones sustanciales como una región uniforme cuando la mediana/MAD es cero. Se registra el método `manual-exclusions-v1` y la política `retained_percentile_span_v1`. Esta es una regla operativa, sin precisión de campo acreditada.

Sin exclusiones, o con una máscara vacía, se mantienen el algoritmo y los resultados anteriores. El detector opcional, cuando hay exclusiones, informa su cobertura sobre la misma rejilla retenida y lo identifica en sus metadatos. Sus candidatos siguen siendo fotométricos.

Los proyectos que usan correcciones requieren **esquema de estado 3 y Sombra 4.2 o posterior**. Las versiones anteriores los rechazan para evitar ignorar las máscaras. Los proyectos sin esta función siguen usando esquema 2; Sombra 4.2 abre los proyectos anteriores. El esquema científico y la física radiativa v2 no cambian.
