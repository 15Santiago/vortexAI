import { Outlet } from 'react-router-dom';
import { Header } from '../organisms/Header';
import { ThemeToggle } from '../atoms/ThemeToggle';
import './MainLayout.css';

export function MainLayout() {
  return (
    <div className="main-layout">
      <Header />
      <main className="main-layout__content">
        <Outlet />
      </main>
      <ThemeToggle />
    </div>
  );
}
