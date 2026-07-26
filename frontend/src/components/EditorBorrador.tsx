import { useState } from "react";
import { CheckCircle2, FileText, Loader2, PenLine, RefreshCw, Save, Trash2, Upload } from "lucide-react";

import {
  type Area,
  type Gap,
  descartarGap,
  generarBorrador,
  guardarBorrador,
  subirBorrador,
} from "../api";
import ChipsAreas from "./ChipsAreas";
import { RenderBorrador, fundirMarcadores } from "./RenderBorrador";

// Editor del borrador de un gap. Va montado con key={gap.id}, así su estado interno
// (texto en edición, huecos rellenados, acción en curso) se reinicia al cambiar de gap.
type AccionBorrador = "generando" | "manual" | "guardando" | "subiendo" | "descartando";
type ModoEditor = "rellenar" | "editar";

export default function EditorBorrador({
  gap,
  areas,
  onActualizar,
}: {
  gap: Gap;
  areas: Area[];
  onActualizar: (g: Gap) => void;
}) {
  const [texto, setTexto] = useState(gap.borrador ?? "");
  const [valores, setValores] = useState<Record<number, string>>({});
  const [modo, setModo] = useState<ModoEditor>("rellenar");
  const [accion, setAccion] = useState<AccionBorrador | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Áreas de acceso que el admin marca al subir el borrador como documento (≥1).
  const [areasSel, setAreasSel] = useState<number[]>([]);
  const ocupado = accion !== null;

  async function ejecutar(nombre: AccionBorrador, fn: () => Promise<Gap>) {
    setAccion(nombre);
    setError(null);
    try {
      const actualizado = await fn();
      onActualizar(actualizado);
      setTexto(actualizado.borrador ?? "");
      setValores({}); // el resultado del servidor ya trae los huecos rellenados fundidos
    } catch (err) {
      setError(err instanceof Error ? err.message : "error");
    } finally {
      setAccion(null);
    }
  }

  // "Escribir desde cero": abre un borrador EN BLANCO (sin LLM) y entra en modo Editar
  // para redactarlo a mano. Persiste el vacío (pendiente → borrador) reutilizando guardar.
  async function escribirDesdeCero() {
    setAccion("manual");
    setError(null);
    try {
      const g = await guardarBorrador(gap.id, "");
      onActualizar(g);
      setTexto("");
      setValores({});
      setModo("editar");
    } catch (err) {
      setError(err instanceof Error ? err.message : "error");
    } finally {
      setAccion(null);
    }
  }

  // Al pasar a "Editar" se funden los huecos rellenados en el texto (para poder tocar
  // todo). Al volver a "Rellenar" se re-parsea el texto: lo ya rellenado es contenido,
  // lo que quede como [COMPLETAR: …] vuelve a ser campo.
  function cambiarModo(nuevo: ModoEditor) {
    if (nuevo === modo) return;
    if (nuevo === "editar") setTexto(fundirMarcadores(texto, valores));
    setValores({});
    setModo(nuevo);
  }

  // Gap ya resuelto: se ingirió como documento. Solo lectura.
  if (gap.estado === "ingerido") {
    return (
      <div className="borrador">
        <h2 className="borrador__title">Borrador</h2>
        <p className="borrador__resuelto">
          <CheckCircle2 size={16} strokeWidth={1.75} />
          Resuelto: ingerido como documento
          <span className="mono">#{gap.documento_id}</span>
        </p>
        {gap.borrador && (
          <details className="respuesta__fuentes">
            <summary className="respuesta__fuentes-titulo">Ver texto ingerido</summary>
            <div className="borrador__vista">
              <RenderBorrador
                texto={gap.borrador}
                editable={false}
                valores={{}}
                onCampo={() => {}}
              />
            </div>
          </details>
        )}
      </div>
    );
  }

  // Gap cerrado por estar cubierto por OTRO documento existente. Solo lectura.
  if (gap.estado === "resuelto") {
    return (
      <div className="borrador">
        <h2 className="borrador__title">Estado</h2>
        <p className="borrador__resuelto">
          <CheckCircle2 size={16} strokeWidth={1.75} />
          Resuelto: ya cubierto por un documento existente
          {gap.resuelto_por_doc_id != null && (
            <span className="mono">#{gap.resuelto_por_doc_id}</span>
          )}
        </p>
      </div>
    );
  }

  // Sin borrador todavía (pendiente o descartado): solo se ofrece generarlo.
  if (gap.borrador == null || gap.estado === "descartado") {
    return (
      <div className="borrador">
        <h2 className="borrador__title">Borrador</h2>
        <p className="borrador__hint">
          {gap.estado === "descartado"
            ? "Este gap está descartado. Puedes retomarlo generando un esqueleto o escribiéndolo desde cero."
            : "Genera un esqueleto con el modelo (no inventa datos: deja marcadores para completar) o escribe el documento desde cero a mano."}
        </p>
        {error && <p className="error-detail">{error}</p>}
        <div className="acciones">
          <button
            className="btn"
            type="button"
            disabled={ocupado}
            onClick={() => ejecutar("generando", () => generarBorrador(gap.id))}
          >
            {accion === "generando" ? (
              <Loader2 size={16} strokeWidth={2} className="spinner" />
            ) : (
              <FileText size={16} strokeWidth={1.75} />
            )}
            {accion === "generando" ? "Generando…" : "Generar borrador"}
          </button>
          <button
            className="btn btn--secundario"
            type="button"
            disabled={ocupado}
            onClick={escribirDesdeCero}
          >
            {accion === "manual" ? (
              <Loader2 size={16} strokeWidth={2} className="spinner" />
            ) : (
              <PenLine size={16} strokeWidth={1.75} />
            )}
            Escribir desde cero
          </button>
        </div>
      </div>
    );
  }

  // Borrador activo. `fundido` = el Markdown con los huecos rellenados metidos dentro;
  // es lo que se guarda/sube. `hayCambios` compara contra lo último guardado en el gap.
  const fundido = fundirMarcadores(texto, valores);
  const hayCambios = fundido !== (gap.borrador ?? "");

  async function subir() {
    setAccion("subiendo");
    setError(null);
    try {
      // Se persiste lo editado antes de ingerir: el ingest usa el borrador del servidor.
      if (hayCambios) await guardarBorrador(gap.id, fundido);
      const actualizado = await subirBorrador(gap.id, areasSel);
      onActualizar(actualizado);
      setTexto(actualizado.borrador ?? "");
      setValores({});
    } catch (err) {
      setError(err instanceof Error ? err.message : "error");
    } finally {
      setAccion(null);
    }
  }

  return (
    <div className="borrador">
      <h2 className="borrador__title">Borrador</h2>
      <p className="borrador__hint">
        En <strong>Rellenar</strong> completas los huecos resaltados sin ver el formato;
        en <strong>Editar</strong> puedes cambiar la estructura (añadir o quitar
        secciones). Al subir, vuelve al pipeline de ingesta como documento nuevo.
      </p>

      <div className="segmento">
        <button
          type="button"
          className={`segmento__btn ${modo === "rellenar" ? "segmento__btn--activo" : ""}`}
          onClick={() => cambiarModo("rellenar")}
          disabled={ocupado}
        >
          Rellenar
        </button>
        <button
          type="button"
          className={`segmento__btn ${modo === "editar" ? "segmento__btn--activo" : ""}`}
          onClick={() => cambiarModo("editar")}
          disabled={ocupado}
        >
          Editar
        </button>
      </div>

      {modo === "editar" ? (
        <textarea
          className="borrador__area"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          disabled={ocupado}
          spellCheck={false}
        />
      ) : (
        <div className="borrador__vista">
          <RenderBorrador
            texto={texto}
            editable={!ocupado}
            valores={valores}
            onCampo={(i, v) => setValores((prev) => ({ ...prev, [i]: v }))}
          />
        </div>
      )}

      {error && <p className="error-detail">{error}</p>}

      <div className="editor-areas">
        <span className="subir__label">Áreas del documento al subir:</span>
        {areas.length === 0 ? (
          <p className="borrador__hint">
            No hay áreas todavía. Crea al menos una en «Áreas» para poder subir el borrador.
          </p>
        ) : (
          <ChipsAreas
            areas={areas}
            seleccion={areasSel}
            onToggle={(id) =>
              setAreasSel((prev) =>
                prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
              )
            }
          />
        )}
      </div>

      <div className="acciones">
        <button
          className="btn"
          type="button"
          disabled={ocupado || areasSel.length === 0}
          onClick={subir}
        >
          {accion === "subiendo" ? (
            <Loader2 size={16} strokeWidth={2} className="spinner" />
          ) : (
            <Upload size={16} strokeWidth={1.75} />
          )}
          {accion === "subiendo" ? "Subiendo…" : "Subir a la base de conocimiento"}
        </button>
        <button
          className="btn btn--secundario"
          type="button"
          disabled={ocupado || !hayCambios}
          onClick={() => ejecutar("guardando", () => guardarBorrador(gap.id, fundido))}
        >
          {accion === "guardando" ? (
            <Loader2 size={16} strokeWidth={2} className="spinner" />
          ) : (
            <Save size={16} strokeWidth={1.75} />
          )}
          Guardar cambios
        </button>
        <span className="acciones__sep" />
        <button
          className="btn btn--secundario"
          type="button"
          disabled={ocupado}
          onClick={() => ejecutar("generando", () => generarBorrador(gap.id))}
          title="Descarta el texto actual y genera un esqueleto nuevo"
        >
          {accion === "generando" ? (
            <Loader2 size={16} strokeWidth={2} className="spinner" />
          ) : (
            <RefreshCw size={16} strokeWidth={1.75} />
          )}
          Regenerar
        </button>
        <button
          className="btn btn--peligro"
          type="button"
          disabled={ocupado}
          onClick={() => ejecutar("descartando", () => descartarGap(gap.id))}
        >
          <Trash2 size={16} strokeWidth={1.75} />
          Descartar
        </button>
      </div>
    </div>
  );
}
