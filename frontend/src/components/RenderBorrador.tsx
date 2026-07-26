import { Fragment, type ReactNode } from "react";

// Sustituye cada [COMPLETAR: …] por lo que la persona escribió para ese hueco (en orden
// de aparición). Los huecos sin rellenar se quedan como están. Es la operación que
// "funde" el modo Rellenar en el Markdown real, al guardar o al pasar a Editar.
export function fundirMarcadores(texto: string, valores: Record<number, string>): string {
  let i = 0;
  return texto.replace(/\[COMPLETAR:\s*[^\]]*\]/gi, (original) => {
    const v = valores[i++];
    return v && v.trim() ? v : original;
  });
}

// Renderiza la negrita **así** dentro de una línea (el resto va tal cual).
function renderNegrita(texto: string, clave: string): ReactNode[] {
  return texto.split(/\*\*([^*]+)\*\*/g).map((parte, i) =>
    i % 2 === 1 ? (
      <strong key={`${clave}-b${i}`}>{parte}</strong>
    ) : (
      <Fragment key={`${clave}-n${i}`}>{parte}</Fragment>
    ),
  );
}

type CtxCampos = {
  editable: boolean; // modo Rellenar → los marcadores son inputs; si no, chips
  valores: Record<number, string>;
  onCampo: (i: number, v: string) => void;
  contador: { n: number }; // índice global del hueco, alineado con fundirMarcadores
};

// Renderiza una línea: negrita + los marcadores [COMPLETAR: …] como input o chip.
function renderLinea(texto: string, ctx: CtxCampos, clave: string): ReactNode[] {
  const re = /\[COMPLETAR:\s*([^\]]*)\]/gi;
  const nodos: ReactNode[] = [];
  let ultimo = 0;
  let k = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(texto)) !== null) {
    if (m.index > ultimo) {
      nodos.push(...renderNegrita(texto.slice(ultimo, m.index), `${clave}-t${k}`));
    }
    const i = ctx.contador.n++;
    const pista = m[1].trim();
    nodos.push(
      ctx.editable ? (
        <input
          key={`${clave}-c${k}`}
          className="campo"
          value={ctx.valores[i] ?? ""}
          placeholder={pista}
          onChange={(e) => ctx.onCampo(i, e.target.value)}
        />
      ) : (
        <span key={`${clave}-c${k}`} className="marcador">
          {pista}
        </span>
      ),
    );
    ultimo = m.index + m[0].length;
    k++;
  }
  if (ultimo < texto.length) {
    nodos.push(...renderNegrita(texto.slice(ultimo), `${clave}-t${k}`));
  }
  return nodos;
}

// Render del subconjunto de Markdown de los borradores (títulos, listas, negrita, hr).
export function RenderBorrador({
  texto,
  editable,
  valores,
  onCampo,
}: {
  texto: string;
  editable: boolean;
  valores: Record<number, string>;
  onCampo: (i: number, v: string) => void;
}) {
  const ctx: CtxCampos = { editable, valores, onCampo, contador: { n: 0 } };
  const bloques: ReactNode[] = [];
  let lista: ReactNode[] = [];
  const cerrarLista = (clave: string) => {
    if (lista.length) {
      bloques.push(<ul key={clave}>{lista}</ul>);
      lista = [];
    }
  };
  texto.split("\n").forEach((linea, li) => {
    const t = linea.trim();
    const clave = `l${li}`;
    if (t === "") {
      cerrarLista(`u${li}`);
      return;
    }
    const enc = t.match(/^(#{1,6})\s+(.*)$/);
    if (enc) {
      cerrarLista(`u${li}`);
      const nivel = Math.min(enc[1].length, 3);
      bloques.push(
        <div key={clave} className={`md-h${nivel}`}>
          {renderLinea(enc[2], ctx, clave)}
        </div>,
      );
      return;
    }
    if (/^---+$/.test(t)) {
      cerrarLista(`u${li}`);
      bloques.push(<hr key={clave} />);
      return;
    }
    const item = t.match(/^[-*]\s+(.*)$/);
    if (item) {
      lista.push(<li key={clave}>{renderLinea(item[1], ctx, clave)}</li>);
      return;
    }
    cerrarLista(`u${li}`);
    bloques.push(<p key={clave}>{renderLinea(t, ctx, clave)}</p>);
  });
  cerrarLista("u-fin");
  return <div className="md">{bloques}</div>;
}
