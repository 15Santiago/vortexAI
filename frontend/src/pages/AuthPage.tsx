import { useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';
import './AuthPage.css';

export default function AuthPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const isRegister = location.pathname === '/registro';
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const destination = (location.state as { from?: string } | null)?.from || '/admin/dashboard';

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      if (isRegister) await register(fullName, email, password);
      else await login(email, password);
      navigate(destination, { replace: true });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'No se pudo completar el acceso.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-intro">
        <Link to="/" className="auth-intro__brand">Vortex<span>AI</span></Link>
        <span className="home-kicker">ESPACIO DE ANÁLISIS</span>
        <h1>Un catálogo.<br />Más contexto.</h1>
        <p>Accede a métricas de productos, precios, puntuaciones y reseñas desde un solo panel.</p>
        <div className="auth-intro__signals" aria-hidden="true">
          <span>PRECIO <i /></span><span>VALORACIÓN <i /></span><span>RESEÑAS <i /></span>
        </div>
      </section>

      <section className="auth-form-panel">
        <div className="auth-mode" aria-label="Tipo de acceso">
          <Link className={!isRegister ? 'auth-mode__active' : ''} to="/acceso">Iniciar sesión</Link>
          <Link className={isRegister ? 'auth-mode__active' : ''} to="/registro">Crear cuenta</Link>
        </div>
        <div className="auth-form-panel__heading">
          <span className="home-kicker">{isRegister ? 'NUEVA CUENTA' : 'ACCESO PERSONAL'}</span>
          <h2>{isRegister ? 'Crea tu cuenta' : 'Bienvenido de nuevo'}</h2>
          <p>{isRegister ? 'Regístrate para consultar el panel de métricas.' : 'Inicia sesión para continuar al panel de métricas.'}</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {isRegister ? (
            <label>
              Nombre completo
              <input
                autoComplete="name"
                maxLength={150}
                required
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Tu nombre"
              />
            </label>
          ) : null}
          <label>
            Correo electrónico
            <input
              autoComplete="email"
              maxLength={254}
              required
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="nombre@correo.com"
            />
          </label>
          <label>
            Contraseña
            <input
              autoComplete={isRegister ? 'new-password' : 'current-password'}
              minLength={12}
              maxLength={72}
              required
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={isRegister ? 'Al menos 12 caracteres' : 'Tu contraseña'}
            />
          </label>
          {error ? <p className="auth-form__error" role="alert">{error}</p> : null}
          <button className="auth-submit" type="submit" disabled={submitting}>
            {submitting ? 'Procesando...' : isRegister ? 'Crear cuenta' : 'Iniciar sesión'}
            <span aria-hidden="true">→</span>
          </button>
        </form>

        <p className="auth-form-panel__back"><Link to="/">← Volver al inicio</Link></p>
      </section>
    </main>
  );
}