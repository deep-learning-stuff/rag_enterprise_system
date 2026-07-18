import { type ChangeEvent, type FormEvent, useEffect, useRef, useState } from "react";
import {
  type Chunk,
  type Documento,
  type SearchResult,
  buscar,
  listarChunks,
  listarDocumentos,
  subirDocumento,
} from "./api";

// Mapea el estado del documento a la clase de pill del design-system.
function pillClase(estado: string): string {
  if (["indexado", "listo"].includes(estado)) return "pill--success";
  if (estado === "error") return "pill--danger";
  return "pill--warning"; // subido / parseado / chunkeado (en curso)
}

function rangoPaginas(a: number | null, b: number | null): string {
  if (a == null) return "";
  return a === b ? `pág. ${a}` : `págs. ${a}–${b}`;
}

function Buscador() {
  const [consulta, setConsulta] = useState("");
  const [resultados, setResultados] = useState<SearchResult[] | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onBuscar(e: FormEvent) {
    e.preventDefault();
    if (!consulta.trim()) return;
    setBuscando(true);
    setError(null);
    try {
      setResultados(await buscar(consulta.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al buscar");
      setResultados(null);
    } finally {
      setBuscando(false);
    }
  }

  return (
    <section className="panel">
      <header className="panel__header">
        <div>
          <h1 className="panel__title">Buscar</h1>
          <p className="panel__subtitle">
            Recuperación híbrida (vectorial + full-text) sobre los documentos
          </p>
        </div>
      </header>

      <form className="buscador" onSubmit={onBuscar}>
        <input
          className="buscador__input"
          type="text"
          placeholder="Escribe una pregunta o unas palabras clave…"
          value={consulta}
          onChange={(e) => setConsulta(e.target.value)}
        />
        <button className="btn" type="submit" disabled={buscando}>
          {buscando ? "Buscando…" : "Buscar"}
        </button>
      </form>

      {error && <p className="error-detail">{error}</p>}

      {resultados != null &&
        (resultados.length === 0 ? (
          <p className="empty">Sin resultados para esa consulta.</p>
        ) : (
          <ul className="resultados">
            {resultados.map((r) => (
              <li key={r.chunk_id} className="resultado">
                <div className="resultado__meta mono">
                  <span>doc #{r.doc_id}</span>
                  <span>#{r.chunk_index}</span>
                  {rangoPaginas(r.page_start, r.page_end) && (
                    <span>{rangoPaginas(r.page_start, r.page_end)}</span>
                  )}
                  {r.rerank_score != null && (
                    <span className="via via--rerank">
                      relevancia {r.rerank_score.toFixed(3)}
                    </span>
                  )}
                  {r.vector_rank != null && (
                    <span className="via via--vec">vec #{r.vector_rank}</span>
                  )}
                  {r.text_rank != null && (
                    <span className="via via--txt">txt #{r.text_rank}</span>
                  )}
                </div>
                <p className="resultado__text">{r.texto}</p>
              </li>
            ))}
          </ul>
        ))}
    </section>
  );
}

function Documentos() {
  const [docs, setDocs] = useState<Documento[]>([]);
  const [subiendo, setSubiendo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const [selId, setSelId] = useState<number | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [cargandoChunks, setCargandoChunks] = useState(false);

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

  async function onSubir(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setSubiendo(true);
    setError(null);
    try {
      await subirDocumento(file);
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

  const docSel = docs.find((d) => d.id === selId) ?? null;

  return (
    <section className="panel">
      <header className="panel__header">
        <div>
          <h1 className="panel__title">Documentos</h1>
          <p className="panel__subtitle">Base de conocimiento del RAG</p>
        </div>
        <label className="btn">
          {subiendo ? "Subiendo…" : "Subir documento"}
          <input
            ref={inputRef}
            type="file"
            hidden
            disabled={subiendo}
            onChange={onSubir}
          />
        </label>
      </header>

      {error && <p className="error-detail">{error}</p>}

      {docs.length === 0 ? (
        <p className="empty">Aún no hay documentos. Sube el primero.</p>
      ) : (
        <table className="tabla">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Tipo</th>
              <th>Estado</th>
              <th>Fecha</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr
                key={d.id}
                className={`fila ${d.id === selId ? "fila--sel" : ""}`}
                onClick={() => seleccionar(d.id)}
              >
                <td>{d.nombre}</td>
                <td className="mono">{d.tipo}</td>
                <td>
                  <span className={`pill ${pillClase(d.estado)}`}>{d.estado}</span>
                </td>
                <td className="muted">
                  {new Date(d.fecha_subida).toLocaleString("es-ES")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {docSel && (
        <div className="chunks">
          <h2 className="chunks__title">
            Chunks de <span className="mono">{docSel.nombre}</span>
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
      )}
    </section>
  );
}

export default function App() {
  return (
    <main className="page">
      <Buscador />
      <Documentos />
    </main>
  );
}
