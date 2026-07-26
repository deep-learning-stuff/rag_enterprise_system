import { type FormEvent, useState } from "react";

import { type SearchResult, buscar } from "../api";
import { rangoPaginas } from "../format";

export default function Buscador() {
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
