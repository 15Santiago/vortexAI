import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/useAuth';
import Logo from '../atoms/Logo';
import './Header.css';

export default function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/');
  }

  return (
    <header className="header">
      <Link to="/" className="header__brand">
        <Logo />
        <span className="header__subtitle">Analítica de comercio electrónico</span>
      </Link>

      <nav className="header__nav" aria-label="Navegación principal">
        <NavLink to="/" end className={({ isActive }) => (isActive ? 'header__link header__link--active' : 'header__link')}>
          Inicio
        </NavLink>
        <NavLink to="/catalogo" className={({ isActive }) => (isActive ? 'header__link header__link--active' : 'header__link')}>
          Catálogo
        </NavLink>
        <NavLink to="/admin/dashboard" className={({ isActive }) => (isActive ? 'header__link header__link--active' : 'header__link')}>
          Métricas
        </NavLink>
        {user ? (
          <>
            <span className="header__user">{user.full_name}</span>
            <button className="header__account-action" type="button" onClick={() => void handleLogout()}>Salir</button>
          </>
        ) : (
          <>
            <Link to="/acceso" className="header__account-action">Iniciar sesión</Link>
            <Link to="/registro" className="header__account-action header__account-action--primary">Crear cuenta</Link>
          </>
        )}
      </nav>
    </header>
  );
}
