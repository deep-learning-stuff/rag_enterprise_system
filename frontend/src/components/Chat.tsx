import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { Loader2, Plus, SendHorizontal, Trash2 } from "lucide-react";

import {
  type Conversacion,
  type Mensaje,
  borrarConversacion,
  crearConversacion,
  enviarMensaje,
  getConversacion,
  listarConversaciones,
} from "../api";
import { rangoPaginas } from "../format";

// Explica cada motivo de abstención en términos del usuario (no del sistema).
const MOTIVO_ABSTENCION: Record<string, string> = {
  sin_candidatos: "No hay nada en los documentos que responda a esto.",
  fuera_de_alcance:
    "Esta información existe en tu empresa, pero está en un área a la que no tienes acceso. Pídele acceso a tu administrador.",
  llm_abstuvo: "Los fragmentos recuperados no contienen la respuesta.",
  citas_invalidas: "La respuesta se descartó (citó fragmentos fuera del contexto).",
  salida_invalida: "La respuesta se descartó (el modelo no devolvió una salida válida).",
};

// Revela el texto del asistente carácter a carácter, como si se escribiera.
// Solo se activa en respuestas recién generadas (`activo`); al abrir un hilo
// antiguo el texto aparece entero. Respeta prefers-reduced-motion.
function TextoAnimado({
  texto,
  activo,
  onTick,
}: {
  texto: string;
  activo: boolean;
  onTick?: () => void;
}) {
  const [n, setN] = useState(activo ? 0 : texto.length);

  useEffect(() => {
    if (!activo) {
      setN(texto.length);
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setN(texto.length);
      return;
    }
    setN(0);
    let i = 0;
    // Cadencia constante (~2 s como máximo): más caracteres por tick si es largo.
    const paso = Math.max(1, Math.round(texto.length / 120));
    const id = window.setInterval(() => {
      i = Math.min(texto.length, i + paso);
      setN(i);
      onTick?.();
      if (i >= texto.length) window.clearInterval(id);
    }, 18);
    return () => window.clearInterval(id);
    // onTick se omite a propósito: es una función estable de scroll.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [texto, activo]);

  const escribiendo = activo && n < texto.length;
  return (
    <>
      {texto.slice(0, n)}
      {escribiendo && <span className="msg__cursor" aria-hidden="true" />}
    </>
  );
}

function Fuentes({ mensaje }: { mensaje: Mensaje }) {
  if (mensaje.citas.length === 0) return null;
  return (
    <details className="respuesta__fuentes">
      <summary className="respuesta__fuentes-titulo">
        Fuentes <span className="chunks__count">{mensaje.citas.length}</span>
      </summary>
      <ul className="resultados">
        {mensaje.citas.map((c) => (
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
  );
}

function MensajeBurbuja({
  mensaje,
  animar,
  onTick,
}: {
  mensaje: Mensaje;
  animar: boolean;
  onTick?: () => void;
}) {
  if (mensaje.rol === "usuario") {
    return (
      <div className="msg msg--usuario">
        <div className="msg__burbuja">{mensaje.texto}</div>
        {mensaje.consulta_resuelta && (
          <p className="msg__nota">Interpretado como: {mensaje.consulta_resuelta}</p>
        )}
      </div>
    );
  }
  // Asistente: respuesta grounded o abstención.
  if (mensaje.answered) {
    return (
      <div className="msg msg--asistente">
        <div className="msg__burbuja">
          <TextoAnimado texto={mensaje.texto ?? ""} activo={animar} onTick={onTick} />
        </div>
        <Fuentes mensaje={mensaje} />
      </div>
    );
  }
  return (
    <div className="msg msg--asistente">
      <div className="msg__burbuja msg__burbuja--gap">
        <span className="pill pill--warning">
          {mensaje.reason === "fuera_de_alcance" ? "sin acceso" : "no está en los documentos"}
        </span>
        <p className="msg__abstencion">
          {MOTIVO_ABSTENCION[mensaje.reason ?? ""] ??
            "No se ha podido responder con los documentos disponibles."}
        </p>
      </div>
    </div>
  );
}

export default function Chat() {
  const [conversaciones, setConversaciones] = useState<Conversacion[]>([]);
  const [activaId, setActivaId] = useState<number | null>(null);
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [cargandoHilo, setCargandoHilo] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [pendiente, setPendiente] = useState<string | null>(null);
  const [borrador, setBorrador] = useState("");
  const [error, setError] = useState<string | null>(null);
  // Id del mensaje del asistente que debe "escribirse" (solo el recién generado).
  const [animarId, setAnimarId] = useState<number | null>(null);

  const finRef = useRef<HTMLDivElement>(null);
  const scrollFin = () => finRef.current?.scrollIntoView({ block: "end" });

  useEffect(() => {
    listarConversaciones()
      .then(setConversaciones)
      .catch((err) => setError(err instanceof Error ? err.message : "error al cargar"));
  }, []);

  // Baja al último mensaje cuando llegan nuevos o mientras se genera.
  useEffect(() => {
    finRef.current?.scrollIntoView({ block: "end" });
  }, [mensajes, pendiente, cargandoHilo]);

  async function seleccionar(id: number) {
    if (id === activaId) return;
    setActivaId(id);
    setError(null);
    setAnimarId(null); // al abrir un hilo existente no se re-anima nada
    setCargandoHilo(true);
    try {
      setMensajes((await getConversacion(id)).mensajes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al abrir la conversación");
      setMensajes([]);
    } finally {
      setCargandoHilo(false);
    }
  }

  function nueva() {
    setActivaId(null);
    setMensajes([]);
    setError(null);
    setAnimarId(null);
  }

  async function enviar() {
    const texto = borrador.trim();
    if (!texto || enviando) return;
    setEnviando(true);
    setError(null);
    setPendiente(texto);
    setBorrador("");
    try {
      if (activaId === null) {
        const det = await crearConversacion(texto);
        setConversaciones((prev) => [
          { id: det.id, titulo: det.titulo, creada: det.creada, actualizada: det.actualizada },
          ...prev,
        ]);
        setActivaId(det.id);
        setMensajes(det.mensajes);
        const asis = det.mensajes.find((m) => m.rol === "asistente");
        if (asis) setAnimarId(asis.id);
      } else {
        const nuevos = await enviarMensaje(activaId, texto);
        setMensajes((prev) => [...prev, ...nuevos]);
        const asis = nuevos.find((m) => m.rol === "asistente");
        if (asis) setAnimarId(asis.id);
        // Sube la conversación al tope de la lista (fue la última activa).
        setConversaciones((prev) => {
          const actual = prev.find((c) => c.id === activaId);
          if (!actual) return prev;
          return [
            { ...actual, actualizada: new Date().toISOString() },
            ...prev.filter((c) => c.id !== activaId),
          ];
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al enviar");
      setBorrador(texto); // devuelve el texto para reintentar
    } finally {
      setEnviando(false);
      setPendiente(null);
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      enviar();
    }
  }

  async function borrar(e: React.MouseEvent, id: number) {
    e.stopPropagation();
    if (!window.confirm("¿Eliminar esta conversación? No se puede deshacer.")) return;
    try {
      await borrarConversacion(id);
      setConversaciones((prev) => prev.filter((c) => c.id !== id));
      if (id === activaId) nueva();
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al eliminar");
    }
  }

  const hiloVacio = mensajes.length === 0 && !cargandoHilo && !enviando;

  return (
    <section className="panel panel--chat">
      <header className="panel__header">
        <div>
          <h1 className="panel__title">Chat</h1>
          <p className="panel__subtitle">
            Conversación sobre tus documentos, con memoria y citas
          </p>
        </div>
        <button className="btn" type="button" onClick={nueva} disabled={activaId === null}>
          <Plus size={16} strokeWidth={1.75} />
          Nueva conversación
        </button>
      </header>

      {error && <p className="error-detail">{error}</p>}

      <div className="chat">
        <aside className="chat__lista">
          {conversaciones.length === 0 ? (
            <p className="chat__lista-vacia">Aún no hay conversaciones.</p>
          ) : (
            conversaciones.map((c) => (
              <button
                key={c.id}
                type="button"
                className={`chat__item ${c.id === activaId ? "chat__item--activa" : ""}`}
                onClick={() => seleccionar(c.id)}
              >
                <span className="chat__item-titulo">{c.titulo}</span>
                <span
                  className="chat__item-borrar"
                  role="button"
                  tabIndex={-1}
                  title="Eliminar conversación"
                  onClick={(e) => borrar(e, c.id)}
                >
                  <Trash2 size={14} strokeWidth={1.75} />
                </span>
              </button>
            ))
          )}
        </aside>

        <div className="chat__hilo">
          <div className="chat__mensajes">
            {cargandoHilo ? (
              <div className="chat__cargando">
                <Loader2 size={18} strokeWidth={1.75} className="spinner" />
              </div>
            ) : hiloVacio ? (
              <p className="empty">
                Escribe abajo para empezar. Cada conversación recuerda el hilo y responde
                solo con lo que hay en tus documentos.
              </p>
            ) : (
              mensajes.map((m) => (
                <MensajeBurbuja
                  key={m.id}
                  mensaje={m}
                  animar={m.id === animarId}
                  onTick={scrollFin}
                />
              ))
            )}

            {enviando && pendiente && (
              <>
                <div className="msg msg--usuario">
                  <div className="msg__burbuja">{pendiente}</div>
                </div>
                <div className="msg msg--asistente">
                  <div className="msg__burbuja msg__burbuja--pensando">
                    <Loader2 size={16} strokeWidth={1.75} className="spinner" />
                    Buscando en los documentos…
                  </div>
                </div>
              </>
            )}
            <div ref={finRef} />
          </div>

          <form
            className="chat__input"
            onSubmit={(e) => {
              e.preventDefault();
              enviar();
            }}
          >
            <textarea
              className="chat__textarea"
              placeholder="Escribe tu pregunta… (Enter para enviar, Mayús+Enter para salto de línea)"
              value={borrador}
              onChange={(e) => setBorrador(e.target.value)}
              onKeyDown={onKeyDown}
              rows={2}
              disabled={enviando}
            />
            <button
              className="btn chat__enviar"
              type="submit"
              disabled={enviando || !borrador.trim()}
            >
              {enviando ? (
                <Loader2 size={16} strokeWidth={2} className="spinner" />
              ) : (
                <SendHorizontal size={16} strokeWidth={1.75} />
              )}
            </button>
          </form>
        </div>
      </div>
    </section>
  );
}
