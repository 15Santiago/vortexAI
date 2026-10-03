import { useEffect, useState } from 'react';
import { API_BASE_URL } from '../data/api';
import './Dashboard.css';

interface MetricsData {
  totalSales: number;
  activeOrders: number;
  newCustomers: number;
  conversionRate: string;
}

const numberFormat = new Intl.NumberFormat('es-MX');
const currencyFormat = new Intl.NumberFormat('es-MX', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 2,
});

export default function Dashboard() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadMetrics() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/metrics`);
        const data = (await response.json()) as MetricsData;
        setMetrics(data);
      } catch (error) {
        console.error('Error al cargar métricas del dashboard:', error);
      } finally {
        setLoading(false);
      }
    }

    void loadMetrics();
  }, []);

  const totalSales = metrics?.totalSales ?? 0;
  const activeOrders = metrics?.activeOrders ?? 0;
  const newCustomers = metrics?.newCustomers ?? 0;
  const conversionRate = metrics?.conversionRate ?? '0%';

  return (
    <div style={{ display: 'flex', minHeight: '80vh', fontFamily: 'sans-serif', color: '#333' }}>
      {/* Sidebar gris */}
      <aside style={{ width: '200px', background: '#f5f5f5', borderRight: '1px solid #ddd', padding: '15px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <button style={{ padding: '10px', textAlign: 'left', border: '1px solid #000', borderRadius: '6px', background: '#fff' }}>Dashboard</button>
        <button style={{ padding: '10px', textAlign: 'left', border: '1px solid #ccc', borderRadius: '6px', background: 'transparent' }}>Productos</button>
        <button style={{ padding: '10px', textAlign: 'left', border: '1px solid #ccc', borderRadius: '6px', background: 'transparent' }}>Pedidos</button>
        <button style={{ padding: '10px', textAlign: 'left', border: '1px solid #ccc', borderRadius: '6px', background: 'transparent' }}>Usuarios</button>
        <button style={{ padding: '10px', textAlign: 'left', border: '1px solid #ccc', borderRadius: '6px', background: 'transparent' }}>Reportes</button>
      </aside>

      {/* Contenido Principal */}
      <main style={{ flex: 1, padding: '20px' }}>
        <h2>Dashboard analítico</h2>

        {loading ? (
          <div style={{ padding: '20px', color: '#666' }}>Cargando métricas...</div>
        ) : (
          <>
            {/* Tarjetas de Métricas */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px', marginBottom: '20px' }}>
              <div style={{ border: '1px solid #ccc', borderRadius: '8px', padding: '15px' }}>
                <span style={{ fontSize: '12px', color: '#666' }}>Ventas del mes</span>
                <h2 style={{ margin: '10px 0 0 0' }}>{currencyFormat.format(totalSales)}</h2>
              </div>
              <div style={{ border: '1px solid #ccc', borderRadius: '8px', padding: '15px' }}>
                <span style={{ fontSize: '12px', color: '#666' }}>Pedidos activos</span>
                <h2 style={{ margin: '10px 0 0 0' }}>{numberFormat.format(activeOrders)}</h2>
              </div>
              <div style={{ border: '1px solid #ccc', borderRadius: '8px', padding: '15px' }}>
                <span style={{ fontSize: '12px', color: '#666' }}>Nuevos clientes</span>
                <h2 style={{ margin: '10px 0 0 0' }}>{numberFormat.format(newCustomers)}</h2>
              </div>
              <div style={{ border: '1px solid #ccc', borderRadius: '8px', padding: '15px' }}>
                <span style={{ fontSize: '12px', color: '#666' }}>Tasa de conversión</span>
                <h2 style={{ margin: '10px 0 0 0' }}>{conversionRate}</h2>
              </div>
            </div>

            {/* Gráfica y Recomendaciones */}
            <div style={{ display: 'flex', gap: '20px' }}>
              <div style={{ flex: 2, border: '1px solid #ccc', borderRadius: '8px', padding: '20px', height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fafafa' }}>
                Ventas vs. tiempo (Gráfica)
              </div>
              <div style={{ flex: 1, border: '1px solid #ccc', borderRadius: '8px', padding: '20px' }}>
                <h4>Productos más recomendados (IA)</h4>
                <p style={{ color: '#888', fontSize: '13px' }}>1. Producto 1</p>
                <p style={{ color: '#888', fontSize: '13px' }}>2. Producto 2</p>
                <p style={{ color: '#888', fontSize: '13px' }}>3. Producto 3</p>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}