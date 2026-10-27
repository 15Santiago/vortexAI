import { useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';
import { API_BASE_URL } from '../data/api';
import './AuthPage.css';

export default function AuthPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { login, register } = useAuth();
  
  const isRegister = location.pathname === '/registro';
  const [isForgotMode, setIsForgotMode] = useState(false); // Estado para alternar a recuperación

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const destination = (location.state as { from?: string } | null)?.from || '/admin/dashboard';


  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#._-]).{12,}$/;

  
  const isEmailValid = emailRegex.test(email);
  const isPasswordValid = passwordRegex.test(password);
  const isFormValid = isRegister ? (isEmailValid && isPasswordValid && fullName.trim().length > 0) : true;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setMessage('');

    if (isRegister) {
      if (!isEmailValid) {
        setError('El correo electrónico contiene caracteres no permitidos o formato incorrecto.');
        return;
      }
      if (!isPasswordValid) {
        setError('La contraseña no cumple con los requisitos mínimos de seguridad.');
        return;
      }
    }

    setSubmitting(true);
    try {
      if (isRegister) {
        await register(fullName, email, password);
        navigate(destination, { replace: true });
      } else {
        await login(email, password);
        navigate(destination, { replace: true });
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'No se pudo completar el acceso.');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleForgotSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setMessage('');
    setSubmitting(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'No se pudo procesar la solicitud.');

      setMessage('¡Instrucciones enviadas! Revisa la consola de tu servidor backend para ver el token simulado.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al solicitar la recuperación.');
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
        {!isForgotMode && (
          <div className="auth-mode" aria-label="Tipo de acceso">
            <Link className={!isRegister ? 'auth-mode__active' : ''} to="/acceso">Iniciar sesión</Link>
            <Link className={isRegister ? 'auth-mode__active' : ''} to="/registro">Crear cuenta</Link>
          </div>
        )}

        <div className="auth-form-panel__heading">
          <span className="home-kicker">{isForgotMode ? 'SEGURIDAD' : isRegister ? 'NUEVA CUENTA' : 'ACCESO PERSONAL'}</span>
          <h2>{isForgotMode ? 'Recuperar contraseña' : isRegister ? 'Crea tu cuenta' : 'Bienvenido de nuevo'}</h2>
          <p>{isForgotMode ? 'Introduce tu correo registrado para generar un token de recuperación.' : isRegister ? 'Regístrate para consultar el panel de métricas.' : 'Inicia sesión para continuar al panel de métricas.'}</p>
        </div>

        {error ? <p className="auth-form__error" role="alert">{error}</p> : null}
        {message ? <p style={{ color: '#22c55e', fontSize: '0.85rem', marginBottom: '1rem', background: 'rgba(34, 197, 94, 0.1)', padding: '10px', borderRadius: '6px' }}>{message}</p> : null}

        {/* FORMULARIO DE RECUPERACIÓN */}
        {isForgotMode ? (
          <form className="auth-form" onSubmit={handleForgotSubmit}>
            <label>
              Correo electrónico
              <input
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="nombre@correo.com"
              />
            </label>

            <button className="auth-submit" type="submit" disabled={submitting}>
              {submitting ? 'Procesando...' : 'Enviar token de recuperación'}
              <span aria-hidden="true">→</span>
            </button>

            <div style={{ marginTop: '1rem', textAlign: 'center' }}>
              <button
                type="button"
                onClick={() => { setIsForgotMode(false); setMessage(''); setError(''); }}
                style={{ background: 'none', border: 'none', color: '#38bdf8', cursor: 'pointer', fontSize: '0.85rem', textDecoration: 'underline' }}
              >
                ← Volver al inicio de sesión
              </button>
            </div>
          </form>
        ) : (
          /* FORMULARIO DE LOGIN / REGISTRO NORMAL */
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
              {isRegister ? 'Correo electrónico' : 'Correo electrónico o usuario'}
              <input
                autoComplete={isRegister ? 'email' : 'username'}
                maxLength={254}
                required
                type="text"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder={isRegister ? 'nombre@correo.com' : 'admin o nombre@correo.com'}
              />
            </label>

            {isRegister && email.length > 0 && !isEmailValid && (
              <p style={{ color: '#ef4444', fontSize: '0.8rem', margin: '-0.5rem 0 0.5rem 0' }}>
                No puedes usar caracteres raros o formato inválido (ej. usa @ y sin símbolos extraños).
              </p>
            )}

            <label>
              Contraseña
              <input
                autoComplete={isRegister ? 'new-password' : 'current-password'}
                maxLength={72}
                required
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder={isRegister ? 'Al menos 12 caracteres' : 'Tu contraseña'}
              />
            </label>

            {isRegister && (
              <ul className="password-requirements" style={{ fontSize: '0.8rem', listStyle: 'none', padding: 0, margin: '0.25rem 0 1rem 0' }}>
                <li style={{ color: password.length >= 12 ? '#22c55e' : '#94a3b8' }}>{password.length >= 12 ? '✓' : '•'} Mínimo 12 caracteres</li>
                <li style={{ color: /[A-Z]/.test(password) ? '#22c55e' : '#94a3b8' }}>{/[A-Z]/.test(password) ? '✓' : '•'} Al menos una letra mayúscula</li>
                <li style={{ color: /[a-z]/.test(password) ? '#22c55e' : '#94a3b8' }}>{/[a-z]/.test(password) ? '✓' : '•'} Al menos una letra minúscula</li>
                <li style={{ color: /\d/.test(password) ? '#22c55e' : '#94a3b8' }}>{/\d/.test(password) ? '✓' : '•'} Al menos un número</li>
                <li style={{ color: /[@$!%*?&#._-]/.test(password) ? '#22c55e' : '#94a3b8' }}>{/[@$!%*?&#._-]/.test(password) ? '✓' : '•'} Al menos un carácter especial (@$!%*?&#._-)</li>
              </ul>
            )}

            <button 
              className="auth-submit" 
              type="submit" 
              disabled={submitting || !isFormValid}
              style={{ opacity: (!isFormValid && isRegister) ? 0.6 : 1, cursor: (!isFormValid && isRegister) ? 'not-allowed' : 'pointer' }}
            >
              {submitting ? 'Procesando...' : isRegister ? 'Crear cuenta' : 'Iniciar sesión'}
              <span aria-hidden="true">→</span>
            </button>

            {!isRegister && (
              <div style={{ marginTop: '0.75rem', textAlign: 'center' }}>
                <button
                  type="button"
                  onClick={() => { setIsForgotMode(true); setError(''); setMessage(''); }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#38bdf8',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    textDecoration: 'underline',
                  }}
                >
                  ¿Olvidaste tu contraseña?
                </button>
              </div>
            )}
          </form>
        )}

        <p className="auth-form-panel__back"><Link to="/">← Volver al inicio</Link></p>
      </section>
    </main>
  );
}