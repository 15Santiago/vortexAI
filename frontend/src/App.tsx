import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './components/templates/MainLayout';
import RequireAdmin from './components/templates/RequireAdmin';
import CatalogPage from './pages/CatalogPage';
import ProductDetailPage from './pages/ProductDetailPage';
import Dashboard from './pages/Dashboard';
import HomePage from './pages/HomePage';
import AuthPage from './pages/AuthPage';
import { AuthProvider } from './auth/AuthContext';
import AdminPage from './pages/AdminPage';
import { LoginPage } from './pages/LoginPage';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Rutas públicas de autenticación */}
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/login" element={<LoginPage />} />

          {/* Rutas con el layout principal */}
          <Route element={<MainLayout />}>
            <Route index element={<HomePage />} />
            <Route path="/home" element={<HomePage />} />
            <Route path="/catalogo" element={<CatalogPage />} />
            <Route path="/producto/:id" element={<ProductDetailPage />} />
          </Route>

          {/* Rutas protegidas exclusivamente para administradores */}
          <Route path="/admin" element={<RequireAdmin><AdminPage /></RequireAdmin>} />
          <Route path="/admin/dashboard" element={<RequireAdmin><Dashboard /></RequireAdmin>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}