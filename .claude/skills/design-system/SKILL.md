---
name: design-system
description: Lenguaje visual del proyecto (paleta, tipografía, formas, componentes). Úsala SIEMPRE que crees o modifiques cualquier UI, componente React, pantalla, estilo o CSS. Ignora tus patrones visuales por defecto y aplica ESTOS tokens y reglas. Si algo no está cubierto aquí, pregunta antes de inventar estética.
---

# Design system

Base neutra + un acento cálido. Denso pero legible, con carácter, sin parecer plantilla. Referencias: dashboards tipo tracking/logística (tarjetas sobre lienzo, datos densos, un acento fuerte).

## Reglas duras (NO las rompas)

- Un solo acento (naranja). Prohibido morados/violetas y el azul genérico de SaaS.
- Superficies **planas con borde de 1px** por defecto. Sombra suave SOLO en elementos flotantes (menús, dropdowns, modales). Nunca sombras exageradas.
- Radios medios (6-14px). Nada de pills en todo ni esquinas de 24px+.
- Gradiente permitido SOLO como acento deliberado y puntual (barra de progreso, un énfasis). Fuera de eso, color plano. (Esto matiza el "prohibido gradientes" del CLAUDE.md: prohibido el gradiente _decorativo_, permitido este.)
- Sin emojis en la UI. Iconos de una sola librería (p.ej. lucide), trazo fino y tamaño consistente.
- IDs, chunk-ids y citas en fuente monoespaciada.

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

Tarjetas y paneles: `--surface` + `border: 1px solid var(--border)`, sin sombra. La sombra `--shadow-float` es exclusiva de menús/modales/tooltips.

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
- **Tarjeta**: `--surface` + borde 1px, padding 16-24, radius-md.
- **Cita en respuesta**: chip mono pequeño con el chunk-id, color `--text-muted`, clicable al documento origen.
