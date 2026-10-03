import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './components/templates/MainLayout';
import CatalogPage from './pages/CatalogPage';
import ProductDetailPage from './pages/ProductDetailPage';
import Dashboard from './pages/Dashboard';
import { LoginPage } from './pages/LoginPage'; // Importa tu LoginPage

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Ruta de Login independiente (sin la barra de navegación principal) */}
        <Route path="/login" element={<LoginPage />} />

        {/* Rutas principales envueltas en el Layout */}
        <Route element={<MainLayout />}>
          <Route index element={<CatalogPage />} />
          <Route path="/" element={<CatalogPage />} />
          <Route path="/catalogo" element={<CatalogPage />} />
          <Route path="/producto/:id" element={<ProductDetailPage />} />
          <Route path="/admin/dashboard" element={<Dashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}