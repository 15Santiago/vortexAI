import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import Catalogo from './pages/Catalogo';
import DetalleProducto from './pages/DetalleProducto';
import Carrito from './pages/Carrito';
import Dashboard from './pages/Dashboard';

export default function App() {
  return (
    <BrowserRouter>
      {/* Header en tono oscuro suave */}
      <header style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        padding: '14px 40px', 
        background: '#1e293b',
        borderBottom: '1px solid #334155',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}>
        {/* Logo y Nombre */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <span style={{ 
            background: '#3b82f6', 
            color: '#ffffff', 
            padding: '6px 14px', 
            borderRadius: '8px', 
            fontWeight: 'bold', 
            letterSpacing: '1px' 
          }}>
            LOGO
          </span>
          <span style={{ color: '#94a3b8', fontSize: '14px', fontWeight: '500' }}>
            Comercio Electrónico Inteligente
          </span>
        </div>
        
        {/* Menú de Navegación */}
        <nav style={{ display: 'flex', gap: '25px', alignItems: 'center' }}>
          <Link to="/catalogo" style={{ textDecoration: 'none', color: '#cbd5e1', fontWeight: '500', fontSize: '14px' }}>Inicio</Link>
          <Link to="/catalogo" style={{ textDecoration: 'none', color: '#cbd5e1', fontWeight: '500', fontSize: '14px' }}>Categorías</Link>
          <Link to="/catalogo" style={{ textDecoration: 'none', color: '#cbd5e1', fontWeight: '500', fontSize: '14px' }}>Ofertas</Link>
          
          <Link to="/carrito" style={{ 
            padding: '8px 16px', 
            background: '#334155',
            border: '1px solid #475569', 
            borderRadius: '20px', 
            textDecoration: 'none', 
            color: '#f8fafc', 
            fontSize: '13px',
            fontWeight: '600'
          }}>
            🛒 Carrito (3)
          </Link>
          
          <Link to="/admin/dashboard" style={{ 
            width: '38px', 
            height: '38px', 
            background: '#3b82f6', 
            color: '#fff',
            borderRadius: '50%', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            textDecoration: 'none', 
            fontWeight: 'bold'
          }}>
            U
          </Link>
        </nav>
      </header>

      {/* Contenedor principal */}
      <main style={{ maxWidth: '1200px', margin: '30px auto', padding: '0 20px' }}>
        <Routes>
          <Route path="/" element={<Catalogo />} />
          <Route path="/catalogo" element={<Catalogo />} />
          <Route path="/producto/:id" element={<DetalleProducto />} />
          <Route path="/carrito" element={<Carrito />} />
          <Route path="/admin/dashboard" element={<Dashboard />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}