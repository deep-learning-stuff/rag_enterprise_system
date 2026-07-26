import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, RefreshCw } from "lucide-react";

import {
  type Area,
  type EstadoGap,
  type Gap,
  confirmarResuelto,
  ignorarResuelto,
  listarAreas,
  listarGaps,
  recheckGaps,
} from "../api";
import EditorBorrador from "./EditorBorrador";

// Estado editorial del gap → clase de pill del design-system (descartado = neutro).
const ESTADO_PILL: Record<EstadoGap, string> = {
  pendiente: "pill--warning",
  borrador: "pill--accent",
  ingerido: "pill--success",
  resuelto: "pill--success",
  descartado: "",
};

// Filtro por estado del panel Gaps: "todos" + cada estado editorial.
type FiltroGap = "todos" | EstadoGap;

const FILTROS: { id: FiltroGap; etiqueta: string }[] = [
  { id: "todos", etiqueta: "Todos" },
  { id: "pendiente", etiqueta: "Pendiente" },
  { id: "borrador", etiqueta: "Borrador" },
  { id: "ingerido", etiqueta: "Ingerido" },
  { id: "resuelto", etiqueta: "Resuelto" },
  { id: "descartado", etiqueta: "Descartado" },
];

export default function Gaps() {
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selId, setSelId] = useState<number | null>(null);
  const [filtro, setFiltro] = useState<FiltroGap>("todos");
  const [rechecking, setRechecking] = useState(false);
  const [resolviendo, setResolviendo] = useState(false);

  useEffect(() => {
    listarGaps()
      .then(setGaps)
      .catch((err) => setError(err instanceof Error ? err.message : "error al cargar"));
    // Las áreas hacen falta para marcar el alcance del documento al subir un borrador.
    listarAreas().then(setAreas).catch(() => {});
  }, []);

  const gapSel = gaps.find((g) => g.id === selId) ?? null;
  const conteo = (f: FiltroGap) =>
    f === "todos" ? gaps.length : gaps.filter((g) => g.estado === f).length;
  const gapsVisibles =
    filtro === "todos" ? gaps : gaps.filter((g) => g.estado === filtro);

  function actualizarGap(g: Gap) {
    setGaps((prev) => prev.map((x) => (x.id === g.id ? g : x)));
  }

  async function onRecheck() {
    setRechecking(true);
    setError(null);
    try {
      setGaps(await recheckGaps());
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al re-comprobar");
    } finally {
      setRechecking(false);
    }
  }

  async function resolverGap(id: number, fn: (id: number) => Promise<Gap>) {
    setResolviendo(true);
    setError(null);
    try {
      actualizarGap(await fn(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "error");
    } finally {
      setResolviendo(false);
    }
  }

  return (
    <section className="panel">
      <header className="panel__header">
        <div>
          <h1 className="panel__title">Gaps</h1>
          <p className="panel__subtitle">
            Preguntas sin respuesta en los documentos, agrupadas por similitud
          </p>
        </div>
        {gaps.length > 0 && (
          <button
            className="btn btn--secundario"
            type="button"
            onClick={onRecheck}
            disabled={rechecking}
            title="Vuelve a buscar cada gap en la base actualizada y marca los que quizá ya estén cubiertos"
          >
            {rechecking ? (
              <Loader2 size={16} strokeWidth={2} className="spinner" />
            ) : (
              <RefreshCw size={16} strokeWidth={1.75} />
            )}
            {rechecking ? "Re-comprobando…" : "Re-comprobar gaps"}
          </button>
        )}
      </header>

      {error && <p className="error-detail">{error}</p>}

      {gaps.length > 0 && (
        <div className="segmento">
          {FILTROS.map((f) => (
            <button
              key={f.id}
              type="button"
              className={`segmento__btn ${filtro === f.id ? "segmento__btn--activo" : ""}`}
              onClick={() => setFiltro(f.id)}
            >
              {f.etiqueta}
              <span className="segmento__conteo">{conteo(f.id)}</span>
            </button>
          ))}
        </div>
      )}

      {gaps.length === 0 ? (
        <p className="empty">
          Todavía no hay gaps: cuando una pregunta no encuentre respuesta en los
          documentos, aparecerá aquí.
        </p>
      ) : gapsVisibles.length === 0 ? (
        <p className="empty">No hay gaps en este estado.</p>
      ) : (
        <table className="tabla">
          <thead>
            <tr>
              <th>Pregunta</th>
              <th>Veces preguntada</th>
              <th>Estado</th>
              <th>Última vez</th>
            </tr>
          </thead>
          <tbody>
            {gapsVisibles.map((g) => (
              <tr
                key={g.id}
                className={`fila ${g.id === selId ? "fila--sel" : ""}`}
                onClick={() => setSelId(selId === g.id ? null : g.id)}
              >
                <td>{g.pregunta_representativa}</td>
                <td>
                  <span className="pill pill--warning">{g.n_ocurrencias}×</span>
                </td>
                <td>
                  <span className="pills">
                    <span className={`pill ${ESTADO_PILL[g.estado]}`}>{g.estado}</span>
                    {g.posible_resuelto && (
                      <span className="pill pill--accent">quizá resuelto</span>
                    )}
                  </span>
                </td>
                <td className="muted">{new Date(g.ultima_vez).toLocaleString("es-ES")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {gapSel && (
        <>
          <div className="chunks">
            <h2 className="chunks__title">
              Preguntas agrupadas en este gap
              <span className="chunks__count">{gapSel.preguntas.length}</span>
            </h2>
            <ul className="resultados">
              {gapSel.preguntas.map((p) => (
                <li key={p.id} className="resultado">
                  <div className="resultado__meta muted">
                    {new Date(p.fecha).toLocaleString("es-ES")}
                  </div>
                  <p className="resultado__text">{p.pregunta}</p>
                </li>
              ))}
            </ul>
          </div>

          {gapSel.posible_resuelto && (
            <div className="aviso">
              <p className="aviso__texto">
                Con la base actualizada, esta pregunta ya parece cubierta por el documento{" "}
                <span className="mono">#{gapSel.resuelto_por_doc_id}</span>. Confírmalo
                para cerrarlo como resuelto, o ignóralo si no es la misma información.
              </p>
              <div className="acciones">
                <button
                  className="btn"
                  type="button"
                  disabled={resolviendo}
                  onClick={() => resolverGap(gapSel.id, confirmarResuelto)}
                >
                  {resolviendo ? (
                    <Loader2 size={16} strokeWidth={2} className="spinner" />
                  ) : (
                    <CheckCircle2 size={16} strokeWidth={1.75} />
                  )}
                  Confirmar resuelto
                </button>
                <button
                  className="btn btn--secundario"
                  type="button"
                  disabled={resolviendo}
                  onClick={() => resolverGap(gapSel.id, ignorarResuelto)}
                >
                  Ignorar
                </button>
              </div>
            </div>
          )}

          <EditorBorrador
            key={gapSel.id}
            gap={gapSel}
            areas={areas}
            onActualizar={actualizarGap}
          />
        </>
      )}
    </section>
  );
}
