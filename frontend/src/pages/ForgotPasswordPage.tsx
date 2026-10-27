import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { API_BASE_URL } from '../data/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [token, setToken] = useState('');
  const [step, setStep] = useState(1); // Paso 1: Pedir correo, Paso 2: Cambiar contraseña
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleRequestToken(e: FormEvent) {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'No se pudo procesar la solicitud.');
      
      setMessage('¡Petición procesada! Revisa la consola de tu servidor backend para ver el token simulado.');
      setStep(2); // Pasamos al siguiente paso
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido.');
    } finally {
      setLoading(false);
    }
  }

  async function handleResetPassword(e: FormEvent) {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      // Endpoint simulado o directo para actualizar usando el token
      const response = await fetch(`${API_BASE_URL}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, token, new_password: newPassword }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'No se pudo restablecer la contraseña.');

      setMessage('¡Contraseña actualizada con éxito! Ya puedes iniciar sesión.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-intro">
        <Link to="/" className="auth-intro__brand">Vortex<span>AI</span></Link>
        <span className="home-kicker">RECUPERACIÓN DE ACCESO</span>
        <h1>Restablece tu contraseña</h1>
        <p>Introduce tu correo para generar un token de seguridad y asignar una nueva clave.</p>
      </section>

      <section className="auth-form-panel">
        <div className="auth-form-panel__heading">
          <span className="home-kicker">SEGURIDAD</span>
          <h2>{step === 1 ? '¿Olvidaste tu contraseña?' : 'Nueva contraseña'}</h2>
          <p>{step === 1 ? 'Escribe tu correo registrado.' : 'Introduce el token de la consola y tu nueva clave.'}</p>
        </div>

        {error && <p className="auth-form__error" role="alert">{error}</p>}
        {message && <p style={{ color: '#22c55e', fontSize: '0.9rem', marginBottom: '1rem' }}>{message}</p>}

        {step === 1 ? (
          <form className="auth-form" onSubmit={handleRequestToken}>
            <label>
              Correo electrónico
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="nombre@correo.com"
              />
            </label>
            <button className="auth-submit" type="submit" disabled={loading}>
              {loading ? 'Generando...' : 'Solicitar token'}
              <span aria-hidden="true">→</span>
            </button>
          </form>
        ) : (
          <form className="auth-form" onSubmit={handleResetPassword}>
            <label>
              Token de recuperación (ver consola del backend)
              <input
                type="text"
                required
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Pega el token aquí"
              />
            </label>
            <label>
              Nueva contraseña (mínimo 12 caracteres)
              <input
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="••••••••••••"
              />
            </label>
            <button className="auth-submit" type="submit" disabled={loading}>
              {loading ? 'Actualizando...' : 'Cambiar contraseña'}
              <span aria-hidden="true">→</span>
            </button>
          </form>
        )}

        <p className="auth-form-panel__back" style={{ marginTop: '1.5rem' }}>
          <Link to="/acceso">← Volver al inicio de sesión</Link>
        </p>
      </section>
    </main>
  );
}