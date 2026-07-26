import { type Area } from "../api";

// Chips seleccionables de áreas: selección múltiple con toggle. Lo comparten la subida y
// edición de documentos (Documentos) y la asignación del arnés (Áreas).
export default function ChipsAreas({
  areas,
  seleccion,
  onToggle,
}: {
  areas: Area[];
  seleccion: number[];
  onToggle: (id: number) => void;
}) {
  return (
    <div className="chips">
      {areas.map((a) => {
        const sel = seleccion.includes(a.id);
        return (
          <button
            key={a.id}
            type="button"
            className={`chip ${sel ? "chip--sel" : ""}`}
            aria-pressed={sel}
            onClick={() => onToggle(a.id)}
          >
            {a.nombre}
          </button>
        );
      })}
    </div>
  );
}
