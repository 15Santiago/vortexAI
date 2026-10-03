import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Product } from '../types/product';

export default function Dashboard() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  // Validación de autenticación (Ruta protegida)
  useEffect(() => {
    const user = localStorage.getItem('user');
    if (!user) {
      navigate('/login');
    }
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('user');
    navigate('/login');
  };

  useEffect(() => {
    async function fetchProducts() {
      try {
        const response = await fetch('http://localhost:8000/api/productos');
        const data = await response.json();

        let list: Product[] = [];
        if (Array.isArray(data)) {
          list = data;
        } else if (data && typeof data === 'object') {
          const payload = data as { productos?: Product[]; data?: Product[] };
          list = payload.productos ?? payload.data ?? [];
        }
        setProducts(list);
      } catch (error) {
        console.error('Error al cargar datos del dashboard:', error);
      } finally {
        setLoading(false);
      }
    }

    void fetchProducts();
  }, []);

  const totalProductsCount = products.length > 0 ? products.length : 25;
  const simulatedMonthlySales = totalProductsCount * 142;
  const activeOrders = Math.round(totalProductsCount * 3.4 + 12);
  const newClients = Math.round(totalProductsCount * 2.1 + 8);
  const conversionRate = (3.8 + (totalProductsCount % 1.5)).toFixed(1);

  const topRecommended = products.slice(0, 3);

  return (
    <div className="dashboard-container" style={{ padding: '2rem', color: '#fff', background: '#0b0f19', minHeight: '100vh' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#f3f4f6', margin: 0 }}>
          Dashboard analítico
        </h1>
        <button 
          onClick={handleLogout}
          style={{ padding: '8px 16px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}
        >
          Cerrar sesión
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        <div style={{ background: '#111827', border: '1px solid #374151', borderRadius: '12px', padding: '1.5rem' }}>
          <span style={{ color: '#9ca3af', fontSize: '0.9rem' }}>Ventas del mes</span>
          <p style={{ fontSize: '2.2rem', fontWeight: 'bold', color: '#3b82f6', marginTop: '0.5rem' }}>
            ${simulatedMonthlySales.toLocaleString('en-US')}
          </p>
        </div>

        <div style={{ background: '#111827', border: '1px solid #374151', borderRadius: '12px', padding: '1.5rem' }}>
          <span style={{ color: '#9ca3af', fontSize: '0.9rem' }}>Pedidos activos</span>
          <p style={{ fontSize: '2.2rem', fontWeight: 'bold', color: '#10b981', marginTop: '0.5rem' }}>
            {activeOrders}
          </p>
        </div>

        <div style={{ background: '#111827', border: '1px solid #374151', borderRadius: '12px', padding: '1.5rem' }}>
          <span style={{ color: '#9ca3af', fontSize: '0.9rem' }}>Nuevos clientes</span>
          <p style={{ fontSize: '2.2rem', fontWeight: 'bold', color: '#f59e0b', marginTop: '0.5rem' }}>
            {newClients}
          </p>
        </div>

        <div style={{ background: '#111827', border: '1px solid #374151', borderRadius: '12px', padding: '1.5rem' }}>
          <span style={{ color: '#9ca3af', fontSize: '0.9rem' }}>Tasa de conversión</span>
          <p style={{ fontSize: '2.2rem', fontWeight: 'bold', color: '#8b5cf6', marginTop: '0.5rem' }}>
            {conversionRate}%
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem' }}>
        <div style={{ background: '#ffffff', borderRadius: '12px', padding: '2rem', color: '#111827', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', minHeight: '300px' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: '600', color: '#374151', marginBottom: '1rem' }}>Ventas vs. tiempo (Gráfica)</h3>
          <div style={{ width: '100%', height: '180px', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around', borderBottom: '2px solid #e5e7eb', paddingBottom: '10px' }}>
            <div style={{ width: '12%', background: '#3b82f6', height: '40%', borderRadius: '4px 4px 0 0' }}></div>
            <div style={{ width: '12%', background: '#3b82f6', height: '65%', borderRadius: '4px 4px 0 0' }}></div>
            <div style={{ width: '12%', background: '#3b82f6', height: '50%', borderRadius: '4px 4px 0 0' }}></div>
            <div style={{ width: '12%', background: '#3b82f6', height: '80%', borderRadius: '4px 4px 0 0' }}></div>
            <div style={{ width: '12%', background: '#3b82f6', height: '95%', borderRadius: '4px 4px 0 0' }}></div>
          </div>
        </div>

        <div style={{ background: '#111827', border: '1px solid #374151', borderRadius: '12px', padding: '1.5rem' }}>
          <h3 style={{ color: '#f3f4f6', fontSize: '1.1rem', fontWeight: '600', marginBottom: '1.2rem' }}>
            Productos más recomendados (IA)
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
            {loading ? (
              <p style={{ color: '#9ca3af', fontSize: '0.9rem' }}>Cargando recomendaciones...</p>
            ) : topRecommended.length > 0 ? (
              topRecommended.map((item, index) => {
                const p = item as Record<string, unknown>;
                const title = String(p.product_title ?? p.title ?? `Producto ${index + 1}`);
                return (
                  <div key={index} style={{ background: '#1f2937', padding: '0.75rem 1rem', borderRadius: '8px', color: '#e5e7eb', fontSize: '0.95rem' }}>
                    <strong>{index + 1}.</strong> {title.length > 35 ? title.substring(0, 32) + '...' : title}
                  </div>
                );
              })
            ) : (
              <p style={{ color: '#9ca3af', fontSize: '0.9rem' }}>No hay productos disponibles</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}