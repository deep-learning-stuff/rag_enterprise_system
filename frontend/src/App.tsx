import { useEffect, useState } from "react";
import {
  Building2,
  CircleAlert,
  FileText,
  Layers,
  Loader2,
  LogOut,
  MessageCircleQuestion,
  Search,
  Users,
} from "lucide-react";

import { type Rol, type Usuario, logout, me } from "./api";
import AceptarInvitacion from "./components/AceptarInvitacion";
import Areas from "./components/Areas";
import Buscador from "./components/Buscador";
import Chat from "./components/Chat";
import Documentos from "./components/Documentos";
import Empresas from "./components/Empresas";
import Gaps from "./components/Gaps";
import Logo from "./components/Logo";
import Login from "./components/Login";
import Usuarios from "./components/Usuarios";

type Pantalla =
  | "chat"
  | "buscar"
  | "gaps"
  | "documentos"
  | "areas"
  | "empresas"
  | "usuarios";

// Iconos de lucide, trazo fino y tamaño consistente (regla del design-system).
// `roles` decide qué ve cada quién: el RAG es por empresa (admin/usuario); el superadmin
// gestiona la plataforma (empresas + usuarios) y no pregunta al RAG.
const NAV: { id: Pantalla; etiqueta: string; Icono: typeof Search; roles: Rol[] }[] = [
  { id: "chat", etiqueta: "Chat", Icono: MessageCircleQuestion, roles: ["admin", "usuario"] },
  { id: "buscar", etiqueta: "Buscar", Icono: Search, roles: ["admin", "usuario"] },
  { id: "gaps", etiqueta: "Gaps", Icono: CircleAlert, roles: ["admin"] },
  { id: "documentos", etiqueta: "Documentos", Icono: FileText, roles: ["admin", "usuario"] },
  { id: "areas", etiqueta: "Áreas", Icono: Layers, roles: ["admin"] },
  { id: "empresas", etiqueta: "Empresas", Icono: Building2, roles: ["superadmin"] },
  { id: "usuarios", etiqueta: "Usuarios", Icono: Users, roles: ["admin", "superadmin"] },
];

export default function App() {
  // Ruta pública de aceptación de invitación: no requiere sesión, se detecta por la URL
  // (la app no usa router; basta mirar el path).
  const esInvitacion = window.location.pathname === "/aceptar-invitacion";

  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargandoSesion, setCargandoSesion] = useState(!esInvitacion);
  const [pantalla, setPantalla] = useState<Pantalla>("chat");

  useEffect(() => {
    if (esInvitacion) return;
    me()
      .then(setUsuario)
      .catch(() => setUsuario(null))
      .finally(() => setCargandoSesion(false));
  }, [esInvitacion]);

  async function onLogout() {
    await logout();
    setUsuario(null);
  }

  if (esInvitacion) {
    const token = new URLSearchParams(window.location.search).get("token") ?? "";
    return <AceptarInvitacion token={token} />;
  }

  if (cargandoSesion) {
    return (
      <div className="auth">
        <div className="auth__cargando">
          <Loader2 size={18} strokeWidth={1.75} className="spinner" />
          Cargando…
        </div>
      </div>
    );
  }

  if (!usuario) {
    return <Login onLogin={setUsuario} />;
  }

  // La nav depende del rol. La pantalla activa es la elegida si su rol la permite, o la
  // primera permitida (evita que un superadmin caiga en una pantalla de RAG que no puede).
  const navVisible = NAV.filter((n) => n.roles.includes(usuario.rol));
  const permitidas = navVisible.map((n) => n.id);
  const pantallaActiva = permitidas.includes(pantalla) ? pantalla : permitidas[0];
  const puede = (id: Pantalla) => permitidas.includes(id);

  return (
    <div className="app">
      <aside className="sidebar">
        {/* Marca: "Cortex" + el contexto debajo. Para admin/usuario, el contexto es el
            nombre de su empresa; el superadmin no está atado a ninguna, así que ve el
            rol de plataforma. */}
        <div className="sidebar__brand">
          <span className="sidebar__logo">
            <Logo size={22} />
          </span>
          <div className="sidebar__brand-text">
            <span className="sidebar__title">Cortex</span>
            <span className="sidebar__subtitle">
              {usuario.rol === "superadmin"
                ? "Administración de plataforma"
                : (usuario.empresa_nombre ?? "Base de conocimiento")}
            </span>
          </div>
        </div>
        <nav className="nav">
          {navVisible.map(({ id, etiqueta, Icono }) => (
            <button
              key={id}
              type="button"
              className={`nav__item ${pantallaActiva === id ? "nav__item--activa" : ""}`}
              onClick={() => setPantalla(id)}
            >
              <Icono size={18} strokeWidth={1.75} />
              {etiqueta}
            </button>
          ))}
        </nav>
        <div className="sidebar__foot">
          <div className="sidebar__user">
            <strong>{usuario.nombre}</strong>
            {usuario.email}
            <span className="pill pill--accent sidebar__rol">{usuario.rol}</span>
          </div>
          <button type="button" className="sidebar__salir" onClick={onLogout}>
            <LogOut size={16} strokeWidth={1.75} />
            Salir
          </button>
        </div>
      </aside>

      {/* Solo se montan las pantallas permitidas por el rol (así un superadmin no dispara
          peticiones del RAG).
          Preguntar, Documentos y el panel se quedan montadas (ocultas con `hidden`) para
          CONSERVAR su estado al cambiar de pestaña. Buscar y Gaps se montan solo cuando
          están activas: así se REINICIAN cada vez que se sale de ellas. */}
      <main className="content">
        {puede("chat") && (
          <div className="pantalla" hidden={pantallaActiva !== "chat"}>
            <Chat />
          </div>
        )}
        {puede("buscar") && pantallaActiva === "buscar" && (
          <div className="pantalla">
            <Buscador />
          </div>
        )}
        {puede("gaps") && pantallaActiva === "gaps" && (
          <div className="pantalla">
            <Gaps />
          </div>
        )}
        {puede("documentos") && (
          <div className="pantalla" hidden={pantallaActiva !== "documentos"}>
            <Documentos
              puedeSubir={usuario.rol === "admin"}
              activo={pantallaActiva === "documentos"}
            />
          </div>
        )}
        {puede("areas") && pantallaActiva === "areas" && (
          <div className="pantalla">
            <Areas />
          </div>
        )}
        {puede("empresas") && (
          <div className="pantalla" hidden={pantallaActiva !== "empresas"}>
            <Empresas />
          </div>
        )}
        {puede("usuarios") && (
          <div className="pantalla" hidden={pantallaActiva !== "usuarios"}>
            <Usuarios actor={usuario} />
          </div>
        )}
      </main>
    </div>
  );
}
