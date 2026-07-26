import { type FormEvent, useState } from "react";
import { Loader2 } from "lucide-react";

import { type Usuario, login } from "../api";
import Logo from "./Logo";

export default function Login({ onLogin }: { onLogin: (u: Usuario) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      onLogin(await login(email.trim(), password));
    } catch (err) {
      setError(err instanceof Error ? err.message : "error al iniciar sesión");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="auth">
      <form className="auth__card" onSubmit={onSubmit}>
        <div className="auth__brand">
          <span className="auth__logo">
            <Logo size={26} />
          </span>
          <p className="auth__title">Cortex</p>
          <p className="auth__subtitle">Inicia sesión para continuar</p>
        </div>

        <label className="auth__campo">
          <span className="auth__label">Email</span>
          <input
            className="buscador__input"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>

        <label className="auth__campo">
          <span className="auth__label">Contraseña</span>
          <input
            className="buscador__input"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>

        {error && <p className="error-detail">{error}</p>}

        <button className="btn auth__btn" type="submit" disabled={enviando}>
          {enviando && <Loader2 size={16} strokeWidth={2} className="spinner" />}
          {enviando ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </div>
  );
}
