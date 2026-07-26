import { type FormEvent, useEffect, useState } from "react";
import { Loader2, Plus } from "lucide-react";

import { type Empresa, crearEmpresa, listarEmpresas } from "../api";

// Panel de empresas (solo superadmin): alta y listado de todas las empresas (tenants).
export default function Empresas() {
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [nombre, setNombre] = useState("");
  const [creando, setCreando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listarEmpresas()
      .then(setEmpresas)
      .catch((err) => setError(err instanceof Error ? err.message : "error al cargar"));
  }, []);

  async function onCrear(e: FormEvent) {
    e.preventDefault();
    if (!nombre.trim()) return;
    setCreando(true);
    setError(null);
    try {
      const empresa = await crearEmpresa(nombre.trim());
      setEmpresas((prev) =>
        [...prev, empresa].sort((a, b) => a.nombre.localeCompare(b.nombre)),
      );
      setNombre("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al crear la empresa");
    } finally {
      setCreando(false);
    }
  }

  return (
    <section className="panel">
      <header className="panel__header">
        <div>
          <h1 className="panel__title">Empresas</h1>
          <p className="panel__subtitle">Cada empresa es un espacio de datos aislado</p>
        </div>
      </header>

      <form className="buscador" onSubmit={onCrear}>
        <input
          className="buscador__input"
          type="text"
          placeholder="Nombre de la empresa nueva…"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
        />
        <button className="btn" type="submit" disabled={creando}>
          {creando ? (
            <Loader2 size={16} strokeWidth={2} className="spinner" />
          ) : (
            <Plus size={16} strokeWidth={1.75} />
          )}
          {creando ? "Creando…" : "Crear empresa"}
        </button>
      </form>

      {error && <p className="error-detail">{error}</p>}

      {empresas.length === 0 ? (
        <p className="empty">Aún no hay empresas. Crea la primera.</p>
      ) : (
        <table className="tabla">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>ID</th>
              <th>Creada</th>
            </tr>
          </thead>
          <tbody>
            {empresas.map((e) => (
              <tr key={e.id}>
                <td>{e.nombre}</td>
                <td className="mono">#{e.id}</td>
                <td className="muted">{new Date(e.creada).toLocaleString("es-ES")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
