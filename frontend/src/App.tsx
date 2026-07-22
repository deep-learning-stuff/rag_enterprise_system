import { type ChangeEvent, type FormEvent, useEffect, useRef, useState } from "react";
import { CircleAlert, FileText, Loader2, MessageCircleQuestion, Search } from "lucide-react";
import {
  type AnswerResult,
  type Chunk,
  type Documento,
  type Gap,
  type SearchResult,
  buscar,
  listarChunks,
  listarDocumentos,
  listarGaps,
  preguntar,
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

// Explica cada motivo de abstención en términos del usuario (no del sistema).
const MOTIVO_ABSTENCION: Record<string, string> = {
  sin_candidatos: "Ningún fragmento de los documentos supera el umbral de relevancia.",
  llm_abstuvo: "Los fragmentos recuperados no contienen la respuesta.",
  citas_invalidas:
    "El modelo citó fragmentos fuera del contexto; la respuesta se ha descartado.",
  salida_invalida: "El modelo no devolvió una salida válida; la respuesta se ha descartado.",
};

// Revela el texto en trozos, en una duración fija corta: se nota que "escribe"
// sin hacerse pesado en respuestas largas. Respeta prefers-reduced-motion.
function useEfectoEscritura(texto: string | null): string {
  const [longitud, setLongitud] = useState(0);

  useEffect(() => {
    if (!texto) {
      setLongitud(0);
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setLongitud(texto.length);
      return;
    }
    setLongitud(0);
    const duracionMs = 650;
    const pasos = 40;
    const porPaso = Math.max(1, Math.ceil(texto.length / pasos));
    const intervalo = setInterval(() => {
      setLongitud((actual) => {
        const siguiente = actual + porPaso;
        if (siguiente >= texto.length) {
          clearInterval(intervalo);
          return texto.length;
        }
        return siguiente;
      });
    }, duracionMs / pasos);
    return () => clearInterval(intervalo);
  }, [texto]);

  return texto ? texto.slice(0, longitud) : "";
}

function Preguntar() {
  const [consulta, setConsulta] = useState("");
  const [respuesta, setRespuesta] = useState<AnswerResult | null>(null);
  const [preguntando, setPreguntando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textoAnimado = useEfectoEscritura(
    !preguntando && respuesta?.answered ? respuesta.answer : null,
  );

  async function onPreguntar(e: FormEvent) {
    e.preventDefault();
    if (!consulta.trim()) return;
    setPreguntando(true);
    setError(null);
    setRespuesta(null);
    try {
      setRespuesta(await preguntar(consulta.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al preguntar");
    } finally {
      setPreguntando(false);
    }
  }

  return (
    <section className="panel">
      <header className="panel__header">
        <div>
          <h1 className="panel__title">Preguntar</h1>
          <p className="panel__subtitle">
            Respuesta generada solo con lo que hay en los documentos, con citas
          </p>
        </div>
      </header>

      <form className="buscador" onSubmit={onPreguntar}>
        <input
          className="buscador__input"
          type="text"
          placeholder="Haz una pregunta sobre los documentos…"
          value={consulta}
          onChange={(e) => setConsulta(e.target.value)}
        />
        <button className="btn" type="submit" disabled={preguntando}>
          {preguntando && <Loader2 size={16} strokeWidth={2} className="spinner" />}
          {preguntando ? "Generando…" : "Preguntar"}
        </button>
      </form>

      {error && <p className="error-detail">{error}</p>}

      {preguntando && (
        <div className="cargando">
          <Loader2 size={18} strokeWidth={1.75} className="spinner" />
          <p className="cargando__texto">
            Buscando en los documentos y generando la respuesta… el reranker en CPU
            puede tardar varios segundos.
          </p>
        </div>
      )}

      {!preguntando &&
        respuesta &&
        (respuesta.answered ? (
          <div className="respuesta respuesta--ok">
            <div className="respuesta__estado">
              <span className="pill pill--success">respondido</span>
            </div>
            <p className="respuesta__texto">{textoAnimado}</p>
            <details className="respuesta__fuentes">
              <summary className="respuesta__fuentes-titulo">
                Fuentes <span className="chunks__count">{respuesta.citations.length}</span>
              </summary>
              <ul className="resultados">
                {respuesta.citations.map((c) => (
                  <li key={c.chunk_id} className="resultado">
                    <div className="resultado__meta mono">
                      <span className="cita-chip">chunk {c.chunk_id}</span>
                      <span>doc #{c.doc_id}</span>
                      {rangoPaginas(c.page_start, c.page_end) && (
                        <span>{rangoPaginas(c.page_start, c.page_end)}</span>
                      )}
                      {c.rerank_score != null && (
                        <span className="via via--rerank">
                          relevancia {c.rerank_score.toFixed(3)}
                        </span>
                      )}
                    </div>
                    <p className="resultado__text">{c.texto}</p>
                  </li>
                ))}
              </ul>
            </details>
          </div>
        ) : (
          <div className="respuesta respuesta--gap">
            <div className="respuesta__estado">
              <span className="pill pill--warning">no está en los documentos</span>
            </div>
            <p className="respuesta__texto respuesta__texto--muted">
              {MOTIVO_ABSTENCION[respuesta.reason ?? ""] ??
                "No se ha podido responder con los documentos disponibles."}
            </p>
          </div>
        ))}
    </section>
  );
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
                  {r.cosine != null && (
                    <span className="via via--cos">coseno {r.cosine.toFixed(3)}</span>
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

function Gaps() {
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selId, setSelId] = useState<number | null>(null);

  useEffect(() => {
    listarGaps()
      .then(setGaps)
      .catch((err) => setError(err instanceof Error ? err.message : "error al cargar"));
  }, []);

  const gapSel = gaps.find((g) => g.id === selId) ?? null;

  return (
    <section className="panel">
      <header className="panel__header">
        <div>
          <h1 className="panel__title">Gaps</h1>
          <p className="panel__subtitle">
            Preguntas sin respuesta en los documentos, agrupadas por similitud
          </p>
        </div>
      </header>

      {error && <p className="error-detail">{error}</p>}

      {gaps.length === 0 ? (
        <p className="empty">
          Todavía no hay gaps: cuando una pregunta no encuentre respuesta en los
          documentos, aparecerá aquí.
        </p>
      ) : (
        <table className="tabla">
          <thead>
            <tr>
              <th>Pregunta</th>
              <th>Veces preguntada</th>
              <th>Última vez</th>
            </tr>
          </thead>
          <tbody>
            {gaps.map((g) => (
              <tr
                key={g.id}
                className={`fila ${g.id === selId ? "fila--sel" : ""}`}
                onClick={() => setSelId(selId === g.id ? null : g.id)}
              >
                <td>{g.pregunta_representativa}</td>
                <td>
                  <span className="pill pill--warning">{g.n_ocurrencias}×</span>
                </td>
                <td className="muted">{new Date(g.ultima_vez).toLocaleString("es-ES")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {gapSel && (
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
      )}
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

type Pantalla = "preguntar" | "buscar" | "gaps" | "documentos";

// Iconos de lucide, trazo fino y tamaño consistente (regla del design-system).
const NAV: { id: Pantalla; etiqueta: string; Icono: typeof Search }[] = [
  { id: "preguntar", etiqueta: "Preguntar", Icono: MessageCircleQuestion },
  { id: "buscar", etiqueta: "Buscar", Icono: Search },
  { id: "gaps", etiqueta: "Gaps", Icono: CircleAlert },
  { id: "documentos", etiqueta: "Documentos", Icono: FileText },
];

export default function App() {
  const [pantalla, setPantalla] = useState<Pantalla>("preguntar");

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <p className="sidebar__title">RAG interno</p>
          <p className="sidebar__subtitle">Base de conocimiento</p>
        </div>
        <nav className="nav">
          {NAV.map(({ id, etiqueta, Icono }) => (
            <button
              key={id}
              type="button"
              className={`nav__item ${pantalla === id ? "nav__item--activa" : ""}`}
              onClick={() => setPantalla(id)}
            >
              <Icono size={18} strokeWidth={1.75} />
              {etiqueta}
            </button>
          ))}
        </nav>
      </aside>

      {/* Las pantallas quedan montadas (hidden) para no perder su estado
          (resultados, respuesta, selección) al cambiar de pestaña. */}
      <main className="content">
        <div className="pantalla" hidden={pantalla !== "preguntar"}>
          <Preguntar />
        </div>
        <div className="pantalla" hidden={pantalla !== "buscar"}>
          <Buscador />
        </div>
        <div className="pantalla" hidden={pantalla !== "gaps"}>
          <Gaps />
        </div>
        <div className="pantalla" hidden={pantalla !== "documentos"}>
          <Documentos />
        </div>
      </main>
    </div>
  );
}
