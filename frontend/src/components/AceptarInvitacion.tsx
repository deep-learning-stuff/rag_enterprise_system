import { type FormEvent, useState } from "react";
import { Loader2 } from "lucide-react";

import { aceptarInvitacion } from "../api";

// Página pública a la que lleva el enlace de invitación (/aceptar-invitacion?token=…).
// El invitado aún no tiene sesión: solo fija su contraseña con el token.
export default function AceptarInvitacion({ token }: { token: string }) {
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [listo, setListo] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (password !== password2) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      await aceptarInvitacion(token, password);
      setListo(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al activar la cuenta");
    } finally {
      setEnviando(false);
    }
  }

  if (!token) {
    return (
      <div className="auth">
        <div className="auth__card">
          <p className="auth__title">Invitación no válida</p>
          <p className="auth__subtitle">
            El enlace no incluye un token. Pide a un administrador que te reinvite.
          </p>
        </div>
      </div>
    );
  }

  if (listo) {
    return (
      <div className="auth">
        <div className="auth__card">
          <p className="auth__title">Cuenta activada</p>
          <p className="auth__subtitle">Ya puedes iniciar sesión con tu contraseña.</p>
          <a className="btn auth__btn" href="/">
            Ir a iniciar sesión
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="auth">
      <form className="auth__card" onSubmit={onSubmit}>
        <div className="auth__brand">
          <p className="auth__title">Activa tu cuenta</p>
          <p className="auth__subtitle">Elige una contraseña (mínimo 8 caracteres)</p>
        </div>

        <label className="auth__campo">
          <span className="auth__label">Contraseña</span>
          <input
            className="buscador__input"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />
        </label>

        <label className="auth__campo">
          <span className="auth__label">Repite la contraseña</span>
          <input
            className="buscador__input"
            type="password"
            autoComplete="new-password"
            value={password2}
            onChange={(e) => setPassword2(e.target.value)}
            required
            minLength={8}
          />
        </label>

        {error && <p className="error-detail">{error}</p>}

        <button className="btn auth__btn" type="submit" disabled={enviando}>
          {enviando && <Loader2 size={16} strokeWidth={2} className="spinner" />}
          {enviando ? "Activando…" : "Activar cuenta"}
        </button>
      </form>
    </div>
  );
}
