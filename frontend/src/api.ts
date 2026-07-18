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
