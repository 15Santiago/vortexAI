import { useEffect, useState } from 'react';
import { API_BASE_URL } from '../data/api';
import MetricCard from '../components/molecules/MetricCard';
import MetricsOverview from '../components/organisms/MetricsOverview';
import type { Metrics } from '../types/metrics';
import './Dashboard.css';

const numberFormat = new Intl.NumberFormat('es-MX');
const currencyFormat = new Intl.NumberFormat('es-MX', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 2,
});

export default function Dashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;

    async function loadMetrics() {
      setLoading(true);
      setError('');
      try {
        const response = await fetch(`${API_BASE_URL}/api/metricas`, { credentials: 'include' });
        const payload = (await response.json()) as Metrics & { error?: string };
        if (!response.ok || payload.error) {
          throw new Error(payload.error || 'No se pudieron cargar las métricas.');
        }
        if (active) setMetrics(payload);
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : 'Error al conectar con la API.');
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadMetrics();
    return () => {
      active = false;
    };
  }, [refreshKey]);

  return (
    <div className="dashboard-page">
      <header className="dashboard-heading">
        <div>
          <span className="dashboard-heading__eyebrow">VORTEX / ANALÍTICA</span>
          <h1>Métricas del catálogo</h1>
          <p>Una lectura del catálogo y su actividad de reseñas.</p>
        </div>
        <button
          className="dashboard-refresh"
          type="button"
          onClick={() => setRefreshKey((current) => current + 1)}
          disabled={loading}
          aria-label="Actualizar métricas"
          title="Actualizar métricas"
        >
          <span aria-hidden="true">↻</span>
        </button>
      </header>

      {error ? (
        <section className="dashboard-state dashboard-state--error" role="alert">
          <strong>No se pudieron cargar las métricas</strong>
          <p>{error}</p>
          <button type="button" onClick={() => setRefreshKey((current) => current + 1)}>Reintentar</button>
        </section>
      ) : loading && !metrics ? (
        <section className="dashboard-state" aria-live="polite">Cargando métricas del catálogo...</section>
      ) : metrics ? (
        <>
          <section className="metric-grid" aria-label="Indicadores principales">
            <MetricCard
              label="Productos"
              value={numberFormat.format(metrics.total_products)}
              detail={`${metrics.total_categories} categorías activas`}
              symbol="#"
              tone="cyan"
            />
            <MetricCard
              label="Valoración media"
              value={metrics.average_rating === null ? 'N/D' : `${metrics.average_rating.toFixed(2)} / 5`}
              detail="Promedio de la última observación"
              symbol="★"
              tone="gold"
            />
            <MetricCard
              label="Reseñas registradas"
              value={numberFormat.format(metrics.total_reviews)}
              detail="Suma de reseñas por producto"
              symbol="↗"
              tone="mint"
            />
            <MetricCard
              label="Precio medio"
              value={metrics.average_price === null ? 'N/D' : currencyFormat.format(metrics.average_price)}
              detail="Precio vigente por producto"
              symbol="$"
              tone="coral"
            />
          </section>
          <MetricsOverview metrics={metrics} />
        </>
      ) : null}
    </div>
  );
}