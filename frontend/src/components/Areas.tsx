import { type FormEvent, useEffect, useState } from "react";
import { Loader2, Plus } from "lucide-react";

import {
  type Area,
  type Usuario,
  areasDeUsuario,
  asignarAreasUsuario,
  crearArea,
  listarAreas,
  listarUsuarios,
  renombrarArea,
} from "../api";
import ChipsAreas from "./ChipsAreas";

const porNombre = (a: Area, b: Area) => a.nombre.localeCompare(b.nombre);

// Panel de áreas (solo admin de empresa). Dos cosas: dar de alta/renombrar áreas y
// asignar a cada persona su "arnés" (las áreas cuyos documentos podrá ver).
export default function Areas() {
  const [areas, setAreas] = useState<Area[]>([]);
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  // Áreas actuales de cada usuario (solo rol "usuario"); se precargan para mostrarlas.
  const [areasPorUsuario, setAreasPorUsuario] = useState<Record<number, number[]>>({});
  const [error, setError] = useState<string | null>(null);

  const [nuevoNombre, setNuevoNombre] = useState("");
  const [creando, setCreando] = useState(false);

  const [editandoAreaId, setEditandoAreaId] = useState<number | null>(null);
  const [nombreEdit, setNombreEdit] = useState("");

  const [editUsuarioId, setEditUsuarioId] = useState<number | null>(null);
  const [seleccion, setSeleccion] = useState<number[]>([]);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    listarAreas()
      .then((as) => setAreas([...as].sort(porNombre)))
      .catch((err) => setError(err instanceof Error ? err.message : "error al cargar áreas"));
    listarUsuarios()
      .then(async (us) => {
        setUsuarios(us);
        const normales = us.filter((u) => u.rol === "usuario");
        const entradas = await Promise.all(
          normales.map(
            async (u) => [u.id, (await areasDeUsuario(u.id)).map((a) => a.id)] as const,
          ),
        );
        setAreasPorUsuario(Object.fromEntries(entradas));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "error al cargar usuarios"));
  }, []);

  function toggle(lista: number[], id: number): number[] {
    return lista.includes(id) ? lista.filter((x) => x !== id) : [...lista, id];
  }

  async function onCrear(e: FormEvent) {
    e.preventDefault();
    if (!nuevoNombre.trim()) return;
    setCreando(true);
    setError(null);
    try {
      const a = await crearArea(nuevoNombre.trim());
      setAreas((prev) => [...prev, a].sort(porNombre));
      setNuevoNombre("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al crear el área");
    } finally {
      setCreando(false);
    }
  }

  async function onRenombrar(id: number) {
    if (!nombreEdit.trim()) return;
    setError(null);
    try {
      const a = await renombrarArea(id, nombreEdit.trim());
      setAreas((prev) => prev.map((x) => (x.id === a.id ? a : x)).sort(porNombre));
      setEditandoAreaId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al renombrar el área");
    }
  }

  async function onGuardarAsignacion(usuarioId: number) {
    setGuardando(true);
    setError(null);
    try {
      const res = await asignarAreasUsuario(usuarioId, seleccion);
      setAreasPorUsuario((prev) => ({ ...prev, [usuarioId]: res.map((a) => a.id) }));
      setEditUsuarioId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al asignar áreas");
    } finally {
      setGuardando(false);
    }
  }

  const nombreArea = (id: number) => areas.find((a) => a.id === id)?.nombre ?? `#${id}`;
  const normales = usuarios.filter((u) => u.rol === "usuario");

  return (
    <section className="panel">
      <header className="panel__header">
        <div>
          <h1 className="panel__title">Áreas</h1>
          <p className="panel__subtitle">
            Departamentos de tu empresa y quién accede a cada uno
          </p>
        </div>
      </header>

      {error && <p className="error-detail">{error}</p>}

      <form className="form" onSubmit={onCrear}>
        <div className="form__fila">
          <input
            className="buscador__input"
            type="text"
            placeholder="Nombre del área (p. ej. Contabilidad)"
            value={nuevoNombre}
            onChange={(e) => setNuevoNombre(e.target.value)}
          />
          <button className="btn" type="submit" disabled={creando}>
            {creando ? (
              <Loader2 size={16} strokeWidth={2} className="spinner" />
            ) : (
              <Plus size={16} strokeWidth={1.75} />
            )}
            {creando ? "Creando…" : "Crear área"}
          </button>
        </div>
      </form>

      {areas.length === 0 ? (
        <p className="empty">Aún no hay áreas. Crea la primera.</p>
      ) : (
        <ul className="lista-areas">
          {areas.map((a) => (
            <li key={a.id} className="lista-areas__item">
              {editandoAreaId === a.id ? (
                <>
                  <input
                    className="buscador__input"
                    type="text"
                    value={nombreEdit}
                    autoFocus
                    onChange={(e) => setNombreEdit(e.target.value)}
                  />
                  <button
                    className="btn btn--sm"
                    type="button"
                    onClick={() => onRenombrar(a.id)}
                  >
                    Guardar
                  </button>
                  <button
                    className="btn btn--secundario btn--sm"
                    type="button"
                    onClick={() => setEditandoAreaId(null)}
                  >
                    Cancelar
                  </button>
                </>
              ) : (
                <>
                  <span className="lista-areas__nombre">{a.nombre}</span>
                  <button
                    className="btn btn--secundario btn--sm"
                    type="button"
                    onClick={() => {
                      setEditandoAreaId(a.id);
                      setNombreEdit(a.nombre);
                    }}
                  >
                    Renombrar
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="panel__grupo">
        <h2 className="panel__grupo-titulo">Acceso de las personas</h2>
        {normales.length === 0 ? (
          <p className="empty">
            No hay usuarios normales en tu empresa. Los admin ven todas las áreas.
          </p>
        ) : (
          <table className="tabla">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Email</th>
                <th>Áreas</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {normales.map((u) => {
                const editando = editUsuarioId === u.id;
                const suyas = areasPorUsuario[u.id] ?? [];
                return (
                  <tr key={u.id}>
                    <td>{u.nombre}</td>
                    <td className="mono">{u.email}</td>
                    <td>
                      {editando ? (
                        <ChipsAreas
                          areas={areas}
                          seleccion={seleccion}
                          onToggle={(id) => setSeleccion((prev) => toggle(prev, id))}
                        />
                      ) : suyas.length === 0 ? (
                        <span className="muted">Sin áreas (no ve documentos)</span>
                      ) : (
                        <div className="pills">
                          {suyas.map((id) => (
                            <span key={id} className="pill">
                              {nombreArea(id)}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td>
                      <div className="acciones-fila">
                        {editando ? (
                          <>
                            <button
                              className="btn btn--sm"
                              type="button"
                              disabled={guardando}
                              onClick={() => onGuardarAsignacion(u.id)}
                            >
                              {guardando ? "Guardando…" : "Guardar"}
                            </button>
                            <button
                              className="btn btn--secundario btn--sm"
                              type="button"
                              disabled={guardando}
                              onClick={() => setEditUsuarioId(null)}
                            >
                              Cancelar
                            </button>
                          </>
                        ) : (
                          <button
                            className="btn btn--secundario btn--sm"
                            type="button"
                            disabled={areas.length === 0}
                            onClick={() => {
                              setEditUsuarioId(u.id);
                              setSeleccion(suyas);
                            }}
                          >
                            Editar
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
