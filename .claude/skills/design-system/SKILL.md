---
name: design-system
description: Lenguaje visual del proyecto (paleta, tipografía, formas, componentes). Úsala SIEMPRE que crees o modifiques cualquier UI, componente React, pantalla, estilo o CSS. Ignora tus patrones visuales por defecto y aplica ESTOS tokens y reglas. Si algo no está cubierto aquí, pregunta antes de inventar estética.
---

# Design system

Base neutra + un acento cálido. Denso pero legible, con carácter, sin parecer plantilla. Referencias: dashboards tipo tracking/logística (datos densos sobre el lienzo, un acento fuerte).

## Reglas duras (NO las rompas)

- Un solo acento (naranja). Prohibido morados/violetas y el azul genérico de SaaS.
- **Integrado, no "todo son cards".** Ver la sección _Layout_: una pantalla es un espacio de trabajo a sangre sobre el lienzo, con la información separada por hairlines de 1px; NO una tarjeta flotante llena de cajas anidadas. Las cajas rellenas se reservan para lo que de verdad flota.
- Superficies **planas con borde de 1px** cuando haya que delimitar (campos, celdas de detalle). Sombra suave SOLO en elementos flotantes (menús, dropdowns, modales). Nunca sombras exageradas.
- Radios medios (6-14px). Nada de pills en todo ni esquinas de 24px+.
- Gradiente permitido SOLO como acento deliberado y puntual (barra de progreso, un énfasis). Fuera de eso, color plano. (Esto matiza el "prohibido gradientes" del CLAUDE.md: prohibido el gradiente _decorativo_, permitido este.)
- Sin emojis en la UI. Iconos de una sola librería (p.ej. lucide), trazo fino y tamaño consistente.
- IDs, chunk-ids y citas en fuente monoespaciada.

## Layout: pantallas integradas, no tarjetas sueltas

El patrón por defecto de CUALQUIER pantalla es **integrado**: la información fluye sobre el lienzo separada por líneas finas, no encerrada en tarjetas independientes. Esto es lo que da carácter y evita el look de plantilla.

- **La pantalla NO es una tarjeta.** Es una columna de trabajo (`max-width` ~1040px, centrada) directamente sobre el `--bg`, sin fondo, sin borde y sin padding de caja. La cabecera es una fila plana (título + acciones) separada del cuerpo por una **hairline** (`border-bottom: 1px solid var(--border)`), no por un margen suelto ni un borde envolvente.
- **Listas = filas separadas por hairline**, no una pila de mini-tarjetas. Cada ítem: `padding` vertical + `border-top: 1px solid var(--border)`, fondo transparente. Nada de `--surface-2` + borde + radius por ítem. (Resultados de búsqueda, chunks, preguntas agrupadas, fuentes de una respuesta, lista de áreas… todos siguen este patrón.)
- **Secciones dentro de una pantalla**: se separan con un `border-top`/`border-bottom` de 1px y aire, no metiéndolas en su propia tarjeta.
- **Tablas**: ya son el ideal (filas con hairline sobre el lienzo). No las envuelvas en una tarjeta.
- **Callout puntual** (aviso, enlace destacado): solo filo de acento a la izquierda (`border-left: 3px solid var(--accent)`) + padding a la izquierda. Sin caja rellena.
- **Texto de respuesta / lectura**: corrido sobre el fondo, sin burbuja ni caja. Nada de estilo "chat de mensajería".

### Cuándo SÍ una caja rellena (`--surface`/`--surface-2` + borde)

Es la excepción, no la regla. Solo cuando el elemento **de verdad flota o es una zona hundida diferenciada**:
- Campos de entrada (input, textarea, select, el composer del chat): borde 1px, y en foco `border-color: var(--accent)`.
- Overlays flotantes (menús, dropdowns, modales, tooltips): `--surface` + `--shadow-float`.
- Zona hundida puntual que agrupa un detalle (p. ej. la fila-detalle desplegable de una tabla): `--surface-2`, opcionalmente con filo de acento inset.
- La tarjeta centrada de una pantalla de autenticación (login): patrón legítimo, no es "la app".

## Colores semánticos

Usa siempre las variables, nunca hex sueltos en los componentes.

### Tema claro

```css
--bg: #f7f7f5; /* lienzo */
--surface: #ffffff; /* tarjetas */
--surface-2: #f1f0ed; /* zonas hundidas */
--border: #e4e3df; /* hairline 1px */
--text: #1a1a19; /* casi negro, cálido */
--text-muted: #6b6a66;
--accent: #e8590c; /* naranja quemado */
--accent-hover: #c74a08;
--accent-soft: #fce7d6; /* fondo de pills/acento */
--success: #16794c; /* respondido / en la base */
--warning: #ca8a04; /* gap / pendiente */
--danger: #c0362c;
```

### Tema oscuro

```css
--bg: #141210;
--surface: #1f1c18;
--surface-2: #26221d;
--border: #322d27;
--text: #f2f0ec;
--text-muted: #9a958c;
--accent: #f0691f;
--accent-hover: #ff7a2e;
--accent-soft: #3a2416;
--success: #3fb076;
--warning: #e0a93b;
--danger: #e06055;
```

## Formas y elevación

```css
--radius-sm: 6px;
--radius-md: 10px;
--radius-lg: 14px;
--shadow-float: 0 4px 12px rgba(0, 0, 0, 0.08); /* solo overlays */
```

Radios y sombra solo aplican a lo que lleva caja (campos, overlays, zonas hundidas): ver _Layout_ para cuándo hay caja. La sombra `--shadow-float` es exclusiva de menús/modales/tooltips; el resto de la UI es plano.

## Espaciado

Escala de 4: `4, 8, 12, 16, 24, 32, 48`. Nada intermedio a ojo.

## Tipografía

- Texto e interfaz: sans neutra (Inter o system-ui).
- IDs, citas, datos técnicos: mono (ui-monospace).
- Pesos: 400 texto, 500 labels, 600 títulos. No uses 700+ salvo un número destacado.

## Estados semánticos (mapeo del RAG)

- **Respondido / contenido en la base** → `--success`.
- **Gap / pregunta sin respuesta / borrador pendiente** → `--warning`.
- **Error del sistema** → `--danger`.
- **Acción primaria / activo / selección** → `--accent`.

## Componentes (pautas rápidas)

- **Botón primario**: fondo `--accent`, texto sobre él claro, radius-md, sin sombra. Hover → `--accent-hover`.
- **Botón secundario**: `--surface` + borde, texto `--text`.
- **Pill/estado**: fondo soft del color semántico + texto del color pleno, radius-sm.
- **Fila de lista** (el patrón, no la excepción): `padding` vertical + `border-top` de 1px, fondo transparente. Sobre el lienzo, integrada. Ver _Layout_.
- **Campo** (input/textarea/select/composer): `--surface` + borde 1px, radius-md; en foco `border-color: var(--accent)`.
- **Cita en respuesta**: chip mono pequeño con el chunk-id, color `--text-muted`, clicable al documento origen.
