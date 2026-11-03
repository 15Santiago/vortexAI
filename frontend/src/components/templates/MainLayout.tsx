import { Outlet } from 'react-router-dom';
import { Header } from '../organisms/Header';
import { ThemeToggle } from '../atoms/ThemeToggle';
import AssistantWidget from '../organisms/AssistantWidget';
import './MainLayout.css';

export function MainLayout() {
  return (
    <div className="main-layout">
      <Header />
      <main className="main-layout__content">
        <Outlet />
      </main>
      <ThemeToggle />
      <AssistantWidget />
    </div>
  );
}
