import { Outlet } from 'react-router-dom';
import Header from '../organisms/Header';
import './MainLayout.css';

export default function MainLayout() {
  return (
    <div className="main-layout">
      <Header />
      <main className="main-layout__content">
        <Outlet />
      </main>
    </div>
  );
}
