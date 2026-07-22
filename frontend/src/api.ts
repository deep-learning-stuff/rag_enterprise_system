export type Documento = {
  id: number;
  nombre: string;
  tipo: string;
  estado: string;
  fecha_subida: string;
};

export async function listarDocumentos(): Promise<Documento[]> {
  const res = await fetch("/documents");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function subirDocumento(file: File): Promise<Documento> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/documents", { method: "POST", body: form });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export type Chunk = {
  id: number;
  page_start: number | null;
  page_end: number | null;
  section: string | null;
  chunk_index: number;
  texto: string;
};

export async function listarChunks(docId: number): Promise<Chunk[]> {
  const res = await fetch(`/documents/${docId}/chunks`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export type SearchResult = {
  chunk_id: number;
  doc_id: number;
  chunk_index: number;
  page_start: number | null;
  page_end: number | null;
  texto: string;
  rerank_score: number | null;
  cosine: number | null;
  rrf_score: number;
  vector_rank: number | null;
  text_rank: number | null;
};

export async function buscar(query: string): Promise<SearchResult[]> {
  const res = await fetch("/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export type AnswerResult = {
  answered: boolean;
  answer: string | null;
  reason: string | null;
  citations: SearchResult[];
};

export async function preguntar(query: string): Promise<AnswerResult> {
  const res = await fetch("/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) {
    // El backend manda el motivo en `detail` (503 falta API key, 502 proveedor caído).
    const detail = await res.json().then((d) => d.detail).catch(() => null);
    throw new Error(detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export type PreguntaGap = {
  id: number;
  pregunta: string;
  fecha: string;
};

export type Gap = {
  id: number;
  pregunta_representativa: string;
  n_ocurrencias: number;
  primera_vez: string;
  ultima_vez: string;
  preguntas: PreguntaGap[];
};

export async function listarGaps(): Promise<Gap[]> {
  const res = await fetch("/gaps");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
