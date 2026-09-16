import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './components/templates/MainLayout';
import CatalogPage from './pages/CatalogPage';
import ProductDetailPage from './pages/ProductDetailPage';
import Dashboard from './pages/Dashboard';
import Carrito from './pages/Carrito';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route index element={<CatalogPage />} />
          <Route path="/" element={<CatalogPage />} />
          <Route path="/catalogo" element={<CatalogPage />} />
          <Route path="/producto/:id" element={<ProductDetailPage />} />
          <Route path="/carrito" element={<Carrito />} />
          <Route path="/admin/dashboard" element={<Dashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}