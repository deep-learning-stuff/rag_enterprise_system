// La identidad (y con ella la empresa) viaja en la cookie de sesión httpOnly, que el
// navegador envía sola al ser mismo origen. Este wrapper es el único punto de llamada al
// backend, por si más adelante hace falta lógica común (p.ej. manejar 401 globalmente).
function apiFetch(url: string, init: RequestInit = {}): Promise<Response> {
  return fetch(url, init);
}

// --- Auth ---

export type Rol = "superadmin" | "admin" | "usuario";

export type Usuario = {
  id: number;
  email: string;
  nombre: string;
  rol: Rol;
  empresa_id: number | null;
  empresa_nombre: string | null;
  activo: boolean;
  invitacion_pendiente: boolean;
};

// Usuario de la sesión actual, o null si no hay sesión (401): así el arranque distingue
// "no logueado" de un error real sin lanzar excepción.
export async function me(): Promise<Usuario | null> {
  const res = await apiFetch("/auth/me");
  if (res.status === 401) return null;
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function jsonOrError<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res
      .json()
      .then((d) => d.detail)
      .catch(() => null);
    throw new Error(detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export function login(email: string, password: string): Promise<Usuario> {
  return apiFetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  }).then((r) => jsonOrError<Usuario>(r));
}

export async function logout(): Promise<void> {
  await apiFetch("/auth/logout", { method: "POST" });
}

export function aceptarInvitacion(token: string, password: string): Promise<Usuario> {
  return apiFetch("/auth/aceptar-invitacion", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, password }),
  }).then((r) => jsonOrError<Usuario>(r));
}

// --- Gestión (panel de admin) ---

export type Empresa = {
  id: number;
  nombre: string;
  creada: string;
};

export type UsuarioCreado = {
  usuario: Usuario;
  enlace_invitacion: string;
};

export function listarEmpresas(): Promise<Empresa[]> {
  return apiFetch("/empresas").then((r) => jsonOrError<Empresa[]>(r));
}

export function crearEmpresa(nombre: string): Promise<Empresa> {
  return apiFetch("/empresas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre }),
  }).then((r) => jsonOrError<Empresa>(r));
}

export function listarUsuarios(): Promise<Usuario[]> {
  return apiFetch("/usuarios").then((r) => jsonOrError<Usuario[]>(r));
}

export function crearUsuario(datos: {
  email: string;
  nombre: string;
  rol: "admin" | "usuario";
  empresa_id?: number;
}): Promise<UsuarioCreado> {
  return apiFetch("/usuarios", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(datos),
  }).then((r) => jsonOrError<UsuarioCreado>(r));
}

export function reinvitarUsuario(id: number): Promise<{ enlace_invitacion: string }> {
  return apiFetch(`/usuarios/${id}/reinvitar`, { method: "POST" }).then((r) =>
    jsonOrError<{ enlace_invitacion: string }>(r),
  );
}

export function activarUsuario(id: number): Promise<Usuario> {
  return apiFetch(`/usuarios/${id}/activar`, { method: "POST" }).then((r) =>
    jsonOrError<Usuario>(r),
  );
}

export function desactivarUsuario(id: number): Promise<Usuario> {
  return apiFetch(`/usuarios/${id}/desactivar`, { method: "POST" }).then((r) =>
    jsonOrError<Usuario>(r),
  );
}

// --- Áreas (acceso por departamento dentro de la empresa) ---

export type Area = {
  id: number;
  nombre: string;
};

export function listarAreas(): Promise<Area[]> {
  return apiFetch("/areas").then((r) => jsonOrError<Area[]>(r));
}

export function crearArea(nombre: string): Promise<Area> {
  return apiFetch("/areas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre }),
  }).then((r) => jsonOrError<Area>(r));
}

export function renombrarArea(id: number, nombre: string): Promise<Area> {
  return apiFetch(`/areas/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre }),
  }).then((r) => jsonOrError<Area>(r));
}

export function areasDeUsuario(id: number): Promise<Area[]> {
  return apiFetch(`/usuarios/${id}/areas`).then((r) => jsonOrError<Area[]>(r));
}

export function asignarAreasUsuario(id: number, areaIds: number[]): Promise<Area[]> {
  return apiFetch(`/usuarios/${id}/areas`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ area_ids: areaIds }),
  }).then((r) => jsonOrError<Area[]>(r));
}

export type Documento = {
  id: number;
  nombre: string;
  tipo: string;
  estado: string;
  fecha_subida: string;
  area_ids: number[];
};

export async function listarDocumentos(): Promise<Documento[]> {
  const res = await apiFetch("/documents");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// Un documento exige al menos un área: `area_ids` viaja como campos de formulario
// REPETIDOS (multipart), no como JSON, porque la subida lleva el fichero.
export function subirDocumento(file: File, areaIds: number[]): Promise<Documento> {
  const form = new FormData();
  form.append("file", file);
  for (const id of areaIds) form.append("area_ids", String(id));
  return apiFetch("/documents", { method: "POST", body: form }).then((r) =>
    jsonOrError<Documento>(r),
  );
}

export function editarAreasDocumento(id: number, areaIds: number[]): Promise<Documento> {
  return apiFetch(`/documents/${id}/areas`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ area_ids: areaIds }),
  }).then((r) => jsonOrError<Documento>(r));
}

export async function eliminarDocumento(id: number): Promise<void> {
  const res = await apiFetch(`/documents/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    const detail = await res.json().then((d) => d.detail).catch(() => null);
    throw new Error(detail ?? `HTTP ${res.status}`);
  }
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
  const res = await apiFetch(`/documents/${docId}/chunks`);
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
  const res = await apiFetch("/search", {
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
  const res = await apiFetch("/answer", {
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

export type EstadoGap = "pendiente" | "borrador" | "ingerido" | "descartado" | "resuelto";

export type Gap = {
  id: number;
  pregunta_representativa: string;
  n_ocurrencias: number;
  estado: EstadoGap;
  borrador: string | null;
  documento_id: number | null;
  posible_resuelto: boolean;
  resuelto_por_doc_id: number | null;
  primera_vez: string;
  ultima_vez: string;
  preguntas: PreguntaGap[];
};

export async function listarGaps(): Promise<Gap[]> {
  const res = await apiFetch("/gaps");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// Las acciones sobre un gap devuelven el gap actualizado. El backend manda el motivo
// del fallo en `detail` (409 estado inválido, 502/503 proveedor LLM), igual que /answer.
async function accionGap(url: string, init?: RequestInit): Promise<Gap> {
  const res = await apiFetch(url, init);
  if (!res.ok) {
    const detail = await res
      .json()
      .then((d) => d.detail)
      .catch(() => null);
    throw new Error(detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export function generarBorrador(gapId: number): Promise<Gap> {
  return accionGap(`/gaps/${gapId}/draft`, { method: "POST" });
}

export function guardarBorrador(gapId: number, borrador: string): Promise<Gap> {
  return accionGap(`/gaps/${gapId}/draft`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ borrador }),
  });
}

export function subirBorrador(gapId: number, areaIds: number[]): Promise<Gap> {
  return accionGap(`/gaps/${gapId}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ area_ids: areaIds }),
  });
}

export function descartarGap(gapId: number): Promise<Gap> {
  return accionGap(`/gaps/${gapId}/discard`, { method: "POST" });
}

export function confirmarResuelto(gapId: number): Promise<Gap> {
  return accionGap(`/gaps/${gapId}/resolve`, { method: "POST" });
}

export function ignorarResuelto(gapId: number): Promise<Gap> {
  return accionGap(`/gaps/${gapId}/ignore-resolved`, { method: "POST" });
}

// Re-comprueba todos los gaps abiertos y devuelve la lista completa ya actualizada.
export async function recheckGaps(): Promise<Gap[]> {
  const res = await apiFetch("/gaps/recheck", { method: "POST" });
  if (!res.ok) {
    const detail = await res
      .json()
      .then((d) => d.detail)
      .catch(() => null);
    throw new Error(detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// --- Chat persistente (Fase C) ---

export type RolMensaje = "usuario" | "asistente";

export type Mensaje = {
  id: number;
  rol: RolMensaje;
  texto: string | null;
  // Versión autónoma con la que se recuperó (si se reescribió un seguimiento).
  consulta_resuelta: string | null;
  answered: boolean | null;
  reason: string | null;
  citas: SearchResult[];
  creado: string;
};

export type Conversacion = {
  id: number;
  titulo: string;
  creada: string;
  actualizada: string;
};

export type ConversacionDetalle = Conversacion & { mensajes: Mensaje[] };

export function listarConversaciones(): Promise<Conversacion[]> {
  return apiFetch("/conversaciones").then((r) => jsonOrError<Conversacion[]>(r));
}

export function crearConversacion(mensaje: string): Promise<ConversacionDetalle> {
  return apiFetch("/conversaciones", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mensaje }),
  }).then((r) => jsonOrError<ConversacionDetalle>(r));
}

export function getConversacion(id: number): Promise<ConversacionDetalle> {
  return apiFetch(`/conversaciones/${id}`).then((r) =>
    jsonOrError<ConversacionDetalle>(r),
  );
}

// Devuelve los dos mensajes nuevos: [del usuario, del asistente].
export function enviarMensaje(id: number, mensaje: string): Promise<Mensaje[]> {
  return apiFetch(`/conversaciones/${id}/mensajes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mensaje }),
  }).then((r) => jsonOrError<Mensaje[]>(r));
}

export async function borrarConversacion(id: number): Promise<void> {
  const res = await apiFetch(`/conversaciones/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    const detail = await res.json().then((d) => d.detail).catch(() => null);
    throw new Error(detail ?? `HTTP ${res.status}`);
  }
}
