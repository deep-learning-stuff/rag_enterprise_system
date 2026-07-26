import {
  type ChangeEvent,
  Fragment,
  type MouseEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import { Trash2 } from "lucide-react";

import {
  type Area,
  type Chunk,
  type Documento,
  editarAreasDocumento,
  eliminarDocumento,
  listarAreas,
  listarChunks,
  listarDocumentos,
  subirDocumento,
} from "../api";
import { rangoPaginas } from "../format";
import ChipsAreas from "./ChipsAreas";

// Mapea el estado del documento a la clase de pill del design-system.
function pillClase(estado: string): string {
  if (["indexado", "listo"].includes(estado)) return "pill--success";
  if (estado === "error") return "pill--danger";
  return "pill--warning"; // subido / parseado / chunkeado (en curso)
}

export default function Documentos({
  puedeSubir,
  activo,
}: {
  puedeSubir: boolean;
  activo: boolean;
}) {
  const [docs, setDocs] = useState<Documento[]>([]);
  const [subiendo, setSubiendo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Áreas de la empresa: solo el admin las gestiona (para un usuario normal, GET /areas
  // daría 403). Con `puedeSubir` (= admin) activamos toda la UI de áreas.
  const [areas, setAreas] = useState<Area[]>([]);
  const [subirAreas, setSubirAreas] = useState<number[]>([]);

  const [selId, setSelId] = useState<number | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [cargandoChunks, setCargandoChunks] = useState(false);
  const [filtroNombre, setFiltroNombre] = useState("");

  const [editAreas, setEditAreas] = useState<number[]>([]);
  const [guardandoAreas, setGuardandoAreas] = useState(false);

  async function refrescar() {
    try {
      setDocs(await listarDocumentos());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al cargar");
    }
  }

  useEffect(() => {
    refrescar();
  }, []);

  // Las áreas se gestionan en otro panel, así que se recargan cada vez que se entra en
  // Documentos: si el admin acaba de crear un área, aquí ya aparece sin recargar la app.
  useEffect(() => {
    if (activo && puedeSubir) {
      listarAreas().then(setAreas).catch(() => {});
    }
  }, [activo, puedeSubir]);

  function toggle(lista: number[], id: number): number[] {
    return lista.includes(id) ? lista.filter((x) => x !== id) : [...lista, id];
  }

  async function onSubir(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setSubiendo(true);
    setError(null);
    try {
      await subirDocumento(file, subirAreas);
      setSubirAreas([]);
      await refrescar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al subir");
    } finally {
      setSubiendo(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function seleccionar(id: number) {
    if (selId === id) {
      setSelId(null);
      return;
    }
    setSelId(id);
    setEditAreas(docs.find((d) => d.id === id)?.area_ids ?? []);
    setCargandoChunks(true);
    try {
      setChunks(await listarChunks(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al cargar chunks");
      setChunks([]);
    } finally {
      setCargandoChunks(false);
    }
  }

  async function onEliminar(e: MouseEvent, doc: Documento) {
    e.stopPropagation(); // no seleccionar la fila (que abriría sus chunks)
    if (
      !window.confirm(
        `¿Eliminar «${doc.nombre}»? Se borrará junto con sus fragmentos. No se puede deshacer.`,
      )
    ) {
      return;
    }
    setError(null);
    try {
      await eliminarDocumento(doc.id);
      setDocs((prev) => prev.filter((d) => d.id !== doc.id));
      if (selId === doc.id) setSelId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al eliminar");
    }
  }

  async function onGuardarAreas() {
    if (selId === null) return;
    setGuardandoAreas(true);
    setError(null);
    try {
      const upd = await editarAreasDocumento(selId, editAreas);
      setDocs((prev) => prev.map((d) => (d.id === upd.id ? upd : d)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al guardar áreas");
    } finally {
      setGuardandoAreas(false);
    }
  }

  const docSel = docs.find((d) => d.id === selId) ?? null;
  const nombreArea = (id: number) => areas.find((a) => a.id === id)?.nombre ?? `#${id}`;
  const consulta = filtroNombre.trim().toLowerCase();
  const docsVisibles = consulta
    ? docs.filter((d) => d.nombre.toLowerCase().includes(consulta))
    : docs;

  // Cambió el conjunto de áreas del doc seleccionado (para habilitar "Guardar").
  const areasCambiadas =
    docSel !== null &&
    (editAreas.length !== docSel.area_ids.length ||
      editAreas.some((id) => !docSel.area_ids.includes(id)));

  // Columnas de la tabla (para el colSpan de la fila-detalle desplegable):
  // Nombre, Tipo, Estado, Fecha + (Áreas, acciones) solo para el admin.
  const nCols = 4 + (puedeSubir ? 2 : 0);

  // Detalle desplegable de un documento: editor de áreas (admin) + sus chunks. Se
  // renderiza inline, justo debajo de su fila, para no tener que bajar hasta el final.
  function detalleDoc(d: Documento) {
    return (
      <div className="detalle-doc">
        {puedeSubir && areas.length > 0 && (
          <div className="editor-areas">
            <h2 className="chunks__title">
              Áreas de <span className="mono">{d.nombre}</span>
            </h2>
            <ChipsAreas
              areas={areas}
              seleccion={editAreas}
              onToggle={(id) => setEditAreas((prev) => toggle(prev, id))}
            />
            <div className="acciones">
              <button
                className="btn btn--sm"
                type="button"
                disabled={guardandoAreas || !areasCambiadas || editAreas.length === 0}
                onClick={onGuardarAreas}
              >
                {guardandoAreas ? "Guardando…" : "Guardar áreas"}
              </button>
              {editAreas.length === 0 && (
                <span className="muted">Un documento debe tener al menos un área.</span>
              )}
            </div>
          </div>
        )}

        <h2 className="chunks__title">
          Chunks de <span className="mono">{d.nombre}</span>
          {!cargandoChunks && <span className="chunks__count">{chunks.length}</span>}
        </h2>
        {cargandoChunks ? (
          <p className="empty">Cargando…</p>
        ) : chunks.length === 0 ? (
          <p className="empty">
            Este documento no tiene chunks (¿estado distinto de «indexado»?).
          </p>
        ) : (
          <ul className="chunk-list">
            {chunks.map((c) => (
              <li key={c.id} className="chunk">
                <div className="chunk__meta mono">
                  #{c.chunk_index}
                  {rangoPaginas(c.page_start, c.page_end) &&
                    ` · ${rangoPaginas(c.page_start, c.page_end)}`}
                </div>
                <p className="chunk__text">{c.texto}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  return (
    <section className="panel">
      <header className="panel__header">
        <div>
          <h1 className="panel__title">Documentos</h1>
          <p className="panel__subtitle">Base de conocimiento del RAG</p>
        </div>
      </header>

      {puedeSubir && (
        <div className="subir">
          {areas.length === 0 ? (
            <p className="subir__hint">
              Crea al menos un área en «Áreas» antes de subir documentos.
            </p>
          ) : (
            <>
              <span className="subir__label">Áreas del nuevo documento:</span>
              <ChipsAreas
                areas={areas}
                seleccion={subirAreas}
                onToggle={(id) => setSubirAreas((prev) => toggle(prev, id))}
              />
              <label className={`btn ${subirAreas.length === 0 ? "btn--desactivado" : ""}`}>
                {subiendo ? "Subiendo…" : "Subir documento"}
                <input
                  ref={inputRef}
                  type="file"
                  hidden
                  disabled={subiendo || subirAreas.length === 0}
                  onChange={onSubir}
                />
              </label>
            </>
          )}
        </div>
      )}

      {error && <p className="error-detail">{error}</p>}

      {docs.length > 0 && (
        <div className="buscador">
          <input
            className="buscador__input"
            type="text"
            placeholder="Filtrar por nombre…"
            value={filtroNombre}
            onChange={(e) => setFiltroNombre(e.target.value)}
          />
        </div>
      )}

      {docs.length === 0 ? (
        <p className="empty">Aún no hay documentos.</p>
      ) : docsVisibles.length === 0 ? (
        <p className="empty">Ningún documento coincide con «{filtroNombre.trim()}».</p>
      ) : (
        <table className="tabla">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Tipo</th>
              <th>Estado</th>
              {puedeSubir && <th>Áreas</th>}
              <th>Fecha</th>
              {puedeSubir && <th />}
            </tr>
          </thead>
          <tbody>
            {docsVisibles.map((d) => (
              <Fragment key={d.id}>
                <tr
                  className={`fila ${d.id === selId ? "fila--sel" : ""}`}
                  onClick={() => seleccionar(d.id)}
                >
                  <td>{d.nombre}</td>
                  <td className="mono">{d.tipo}</td>
                  <td>
                    <span className={`pill ${pillClase(d.estado)}`}>{d.estado}</span>
                  </td>
                  {puedeSubir && (
                    <td>
                      <div className="pills">
                        {d.area_ids.map((id) => (
                          <span key={id} className="pill">
                            {nombreArea(id)}
                          </span>
                        ))}
                      </div>
                    </td>
                  )}
                  <td className="muted">
                    {new Date(d.fecha_subida).toLocaleString("es-ES")}
                  </td>
                  {puedeSubir && (
                    <td>
                      <button
                        className="btn btn--peligro btn--sm"
                        type="button"
                        title="Eliminar documento"
                        onClick={(e) => onEliminar(e, d)}
                      >
                        <Trash2 size={15} strokeWidth={1.75} />
                      </button>
                    </td>
                  )}
                </tr>
                {d.id === selId && (
                  <tr className="fila-detalle">
                    <td className="detalle-celda" colSpan={nCols}>
                      {detalleDoc(d)}
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
