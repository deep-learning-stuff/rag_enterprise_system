import { type FormEvent, useEffect, useState } from "react";
import { Loader2, Plus } from "lucide-react";

import {
  type Empresa,
  type Usuario,
  activarUsuario,
  crearUsuario,
  desactivarUsuario,
  listarEmpresas,
  listarUsuarios,
  reinvitarUsuario,
} from "../api";

function estadoUsuario(u: Usuario): { clase: string; txt: string } {
  if (u.invitacion_pendiente) return { clase: "pill--warning", txt: "invitación pendiente" };
  if (!u.activo) return { clase: "pill--danger", txt: "desactivado" };
  return { clase: "pill--success", txt: "activo" };
}

// Panel de usuarios. Superadmin: ve/crea en cualquier empresa (agrupado por empresa).
// Admin: solo su empresa. El backend hace el scoping; aquí adaptamos el formulario.
export default function Usuarios({ actor }: { actor: Usuario }) {
  const esSuper = actor.rol === "superadmin";

  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [nombre, setNombre] = useState("");
  const [rol, setRol] = useState<"admin" | "usuario">("usuario");
  const [empresaId, setEmpresaId] = useState<number | "">("");
  const [creando, setCreando] = useState(false);

  const [invitacion, setInvitacion] = useState<{ enlace: string; para: string } | null>(null);
  const [copiado, setCopiado] = useState(false);
  const [accionId, setAccionId] = useState<number | null>(null);

  useEffect(() => {
    listarUsuarios()
      .then(setUsuarios)
      .catch((err) => setError(err instanceof Error ? err.message : "error al cargar"));
    if (esSuper) {
      listarEmpresas().then(setEmpresas).catch(() => {});
    }
  }, [esSuper]);

  function copiar(texto: string) {
    navigator.clipboard?.writeText(texto);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 1500);
  }

  async function onCrear(e: FormEvent) {
    e.preventDefault();
    if (!email.trim() || !nombre.trim()) return;
    if (esSuper && !empresaId) {
      setError("Elige una empresa para el usuario.");
      return;
    }
    setCreando(true);
    setError(null);
    try {
      const creado = await crearUsuario({
        email: email.trim(),
        nombre: nombre.trim(),
        rol,
        empresa_id: esSuper ? Number(empresaId) : undefined,
      });
      setUsuarios((prev) => [...prev, creado.usuario]);
      setInvitacion({
        enlace: window.location.origin + creado.enlace_invitacion,
        para: creado.usuario.email,
      });
      setEmail("");
      setNombre("");
      setRol("usuario");
      setEmpresaId("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al crear el usuario");
    } finally {
      setCreando(false);
    }
  }

  async function onReinvitar(u: Usuario) {
    setAccionId(u.id);
    setError(null);
    try {
      const r = await reinvitarUsuario(u.id);
      setInvitacion({ enlace: window.location.origin + r.enlace_invitacion, para: u.email });
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al reinvitar");
    } finally {
      setAccionId(null);
    }
  }

  async function onToggle(u: Usuario) {
    setAccionId(u.id);
    setError(null);
    try {
      const upd = u.activo ? await desactivarUsuario(u.id) : await activarUsuario(u.id);
      setUsuarios((prev) => prev.map((x) => (x.id === upd.id ? upd : x)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al cambiar el estado");
    } finally {
      setAccionId(null);
    }
  }

  function renderTabla(lista: Usuario[]) {
    return (
      <table className="tabla">
        <thead>
          <tr>
            <th>Nombre</th>
            <th>Email</th>
            <th>Rol</th>
            <th>Estado</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {lista.map((u) => {
            const est = estadoUsuario(u);
            const ocupado = accionId === u.id;
            return (
              <tr key={u.id}>
                <td>{u.nombre}</td>
                <td className="mono">{u.email}</td>
                <td>
                  <span className="pill pill--accent">{u.rol}</span>
                </td>
                <td>
                  <span className={`pill ${est.clase}`}>{est.txt}</span>
                </td>
                <td>
                  <div className="acciones-fila">
                    {u.invitacion_pendiente && (
                      <button
                        className="btn btn--secundario btn--sm"
                        type="button"
                        disabled={ocupado}
                        onClick={() => onReinvitar(u)}
                      >
                        Reinvitar
                      </button>
                    )}
                    {u.id !== actor.id && (
                      <button
                        className="btn btn--secundario btn--sm"
                        type="button"
                        disabled={ocupado}
                        onClick={() => onToggle(u)}
                      >
                        {u.activo ? "Desactivar" : "Activar"}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  }

  // Superadmin: agrupa por empresa + un grupo "Plataforma" para los superadmins.
  const grupos = esSuper
    ? [
        ...empresas.map((e) => ({
          clave: `e${e.id}`,
          titulo: e.nombre,
          lista: usuarios.filter((u) => u.empresa_id === e.id),
        })),
        {
          clave: "plataforma",
          titulo: "Plataforma (superadmins)",
          lista: usuarios.filter((u) => u.empresa_id === null),
        },
      ].filter((g) => g.lista.length > 0)
    : [];

  return (
    <section className="panel">
      <header className="panel__header">
        <div>
          <h1 className="panel__title">Usuarios</h1>
          <p className="panel__subtitle">
            {esSuper
              ? "Usuarios de todas las empresas, agrupados por empresa"
              : "Usuarios de tu empresa"}
          </p>
        </div>
      </header>

      <form className="form" onSubmit={onCrear}>
        <div className="form__fila">
          <input
            className="buscador__input"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            className="buscador__input"
            type="text"
            placeholder="Nombre"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
          />
        </div>
        <div className="form__fila">
          <select
            className="select"
            value={rol}
            onChange={(e) => setRol(e.target.value as "admin" | "usuario")}
          >
            <option value="usuario">Usuario</option>
            <option value="admin">Admin</option>
          </select>
          {esSuper && (
            <select
              className="select"
              value={empresaId}
              onChange={(e) => setEmpresaId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">Empresa…</option>
              {empresas.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.nombre}
                </option>
              ))}
            </select>
          )}
          <button className="btn" type="submit" disabled={creando}>
            {creando ? (
              <Loader2 size={16} strokeWidth={2} className="spinner" />
            ) : (
              <Plus size={16} strokeWidth={1.75} />
            )}
            {creando ? "Creando…" : "Crear e invitar"}
          </button>
        </div>
      </form>

      {invitacion && (
        <div className="enlace">
          <div className="enlace__info">
            <span className="enlace__label">
              Enlace de invitación para <span className="mono">{invitacion.para}</span> — cópialo
              y envíaselo:
            </span>
            <span className="enlace__url">{invitacion.enlace}</span>
          </div>
          <button
            className="btn btn--secundario btn--sm"
            type="button"
            onClick={() => copiar(invitacion.enlace)}
          >
            {copiado ? "Copiado" : "Copiar"}
          </button>
        </div>
      )}

      {error && <p className="error-detail">{error}</p>}

      {esSuper ? (
        grupos.length === 0 ? (
          <p className="empty">Aún no hay usuarios. Crea el primero.</p>
        ) : (
          grupos.map((g) => (
            <div key={g.clave} className="panel__grupo">
              <h2 className="panel__grupo-titulo">{g.titulo}</h2>
              {renderTabla(g.lista)}
            </div>
          ))
        )
      ) : usuarios.length === 0 ? (
        <p className="empty">Aún no hay usuarios en tu empresa. Crea el primero.</p>
      ) : (
        renderTabla(usuarios)
      )}
    </section>
  );
}
