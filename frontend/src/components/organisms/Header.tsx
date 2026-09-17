import { NavLink, Link } from 'react-router-dom';
import Logo from '../atoms/Logo';
import './Header.css';

export default function Header() {
  return (
    <header className="header">
      <div className="header__brand">
        <Logo />
        <span className="header__subtitle">Analítica de comercio electrónico</span>
      </div>

      <nav className="header__nav" aria-label="Navegación principal">
        <NavLink to="/catalogo" className={({ isActive }) => (isActive ? 'header__link header__link--active' : 'header__link')}>
          Inicio
        </NavLink>
        <NavLink to="/catalogo" className={({ isActive }) => (isActive ? 'header__link header__link--active' : 'header__link')}>
          Categorías
        </NavLink>
        <NavLink to="/admin/dashboard" className={({ isActive }) => (isActive ? 'header__link header__link--active' : 'header__link')}>
          Métricas
        </NavLink>

        <Link to="/admin/dashboard" className="header__avatar" aria-label="Panel administrador">
          U
        </Link>
      </nav>
    </header>
  );
}
