// Marca de Cortex: glifo geométrico que insinúa un córtex / red neuronal (un pliegue
// abierto + tres nodos sinápticos enlazados). Es un SVG en línea, sin dependencias ni
// assets externos, así que funciona offline dentro de Docker. Hereda el color con
// `currentColor` (lo pintamos con el acento teal desde el CSS).
export default function Logo({ size = 22 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {/* Pliegue del córtex: un arco abierto, nunca una caja cerrada. */}
      <path d="M18 5.2A9 9 0 1 0 20.5 13" />
      {/* Enlaces entre nodos (las sinapsis). */}
      <path d="M9 9.2 14.6 13.4 8.2 15.4 9 9.2" />
      {/* Nodos. */}
      <circle cx="9" cy="9.2" r="1.7" fill="currentColor" stroke="none" />
      <circle cx="14.6" cy="13.4" r="1.7" fill="currentColor" stroke="none" />
      <circle cx="8.2" cy="15.4" r="1.7" fill="currentColor" stroke="none" />
    </svg>
  );
}
