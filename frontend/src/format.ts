// Helpers de presentación compartidos entre componentes.

export function rangoPaginas(a: number | null, b: number | null): string {
  if (a == null) return "";
  return a === b ? `pág. ${a}` : `págs. ${a}–${b}`;
}
