import { useState, type FormEvent } from 'react';
import { useAuth } from '../auth/useAuth';
import './ProfilePage.css';

export default function ProfilePage() {
  const { user, updateProfile } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      if (updateProfile) {
        await updateProfile(fullName, email, password ? password : undefined);
      }
      setMessage('¡Perfil actualizado con éxito!');
      setPassword('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo actualizar el perfil.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="profile-page">
      <div className="profile-card">
        <div className="profile-header">
          <span className="home-kicker">CONFIGURACIÓN</span>
          <h1>Mi Perfil</h1>
          <p>Actualiza tus datos personales y contraseña de acceso.</p>
        </div>

        {error && <p className="profile-alert-error" role="alert">{error}</p>}
        {message && <p className="profile-alert-success" role="status">{message}</p>}

        <form onSubmit={handleSubmit} className="profile-form">
          <div className="profile-field">
            <label htmlFor="fullName">Nombre completo</label>
            <input
              id="fullName"
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Tu nombre completo"
            />
          </div>

          <div className="profile-field">
            <label htmlFor="email">Correo electrónico</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="nombre@correo.com"
            />
          </div>

          <div className="profile-field">
            <label htmlFor="password">Nueva contraseña (opcional)</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Dejar en blanco para conservar la actual"
            />
          </div>

          <button type="submit" disabled={loading} className="profile-submit">
            {loading ? 'Guardando cambios...' : 'Guardar cambios'}
          </button>
        </form>
      </div>
    </main>
  );
}