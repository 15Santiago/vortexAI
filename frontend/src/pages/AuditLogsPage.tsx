import { useCallback, useEffect, useState } from 'react';
import { API_BASE_URL } from '../data/api';
import './AuditLogsPage.css';

type AuditLog = {
  id: number;
  actor_user_id: number | null;
  actor_name: string;
  actor_email: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  old_values: Record<string, unknown> | string | null;
  new_values: Record<string, unknown> | string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
};

const PAGE_SIZE = 50;

function formatAuditValues(value: AuditLog['old_values']): string {
  if (value === null) return '—';
  if (typeof value === 'string') {
    try {
      return JSON.stringify(JSON.parse(value), null, 2);
    } catch {
      return value;
    }
  }
  return JSON.stringify(value, null, 2);
}

function formatAction(action: string) {
  const labels: Record<string, string> = {
    'role.create': 'Creación de rol y cuenta',
    'role.permissions.update': 'Actualización de permisos',
    'user.role.update': 'Cambio de rol de usuario',
    'user.permissions.update': 'Actualización de permisos de usuario',
  };
  return labels[action] ?? action;
}

function formatTimestamp(value: string) {
  const timestamp = value.includes('Z') || /[+-]\d{2}:\d{2}$/.test(value)
    ? value
    : `${value.replace(' ', 'T')}Z`;
  const parsed = new Date(timestamp);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');

  const loadLogs = useCallback(async (offset: number) => {
    const response = await fetch(`${API_BASE_URL}/api/admin/audit-logs?limit=${PAGE_SIZE}&offset=${offset}`, {
      credentials: 'include',
    });
    const payload = (await response.json()) as { logs?: AuditLog[]; has_more?: boolean; detail?: string };
    if (!response.ok) throw new Error(payload.detail || 'No se pudieron cargar los registros de auditoría.');
    return { logs: payload.logs ?? [], hasMore: payload.has_more ?? false };
  }, []);

  useEffect(() => {
    let active = true;
    loadLogs(0)
      .then((result) => {
        if (!active) return;
        setLogs(result.logs);
        setHasMore(result.hasMore);
      })
      .catch((loadError: unknown) => {
        if (active) setError(loadError instanceof Error ? loadError.message : 'No se pudieron cargar los registros.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [loadLogs]);

  async function loadMore() {
    setLoadingMore(true);
    setError('');
    try {
      const result = await loadLogs(logs.length);
      setLogs((current) => [...current, ...result.logs]);
      setHasMore(result.hasMore);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'No se pudieron cargar más registros.');
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <main className="audit-page">
      <header className="audit-heading">
        <div>
          <span className="audit-heading__eyebrow">VORTEX / SEGURIDAD</span>
          <h1>Registros de auditoría</h1>
          <p>Historial de cambios realizados en roles, permisos y cuentas.</p>
        </div>
        <span className="audit-heading__count">{logs.length} registros</span>
      </header>

      {error ? <div className="admin-message admin-message--error" role="alert">{error}</div> : null}
      {loading ? <div className="admin-empty" role="status">Cargando registros...</div> : logs.length ? (
        <section className="audit-list" aria-label="Historial de auditoría">
          {logs.map((log) => (
            <article className="audit-entry" key={log.id}>
              <div className="audit-entry__header">
                <div>
                  <h2>{formatAction(log.action)}</h2>
                  <p>{log.actor_name} · {log.actor_email}</p>
                </div>
                <time dateTime={`${log.created_at.replace(' ', 'T')}Z`}>{formatTimestamp(log.created_at)}</time>
              </div>
              <dl className="audit-entry__meta">
                <div><dt>Elemento</dt><dd>{log.entity_type}{log.entity_id ? ` #${log.entity_id}` : ''}</dd></div>
                {log.ip_address ? <div><dt>Dirección IP</dt><dd>{log.ip_address}</dd></div> : null}
                {log.user_agent ? <div><dt>Dispositivo</dt><dd>{log.user_agent}</dd></div> : null}
              </dl>
              {log.old_values || log.new_values ? (
                <details className="audit-entry__changes">
                  <summary>Ver cambios</summary>
                  <div className="audit-entry__values">
                    {log.old_values ? <div><h3>Antes</h3><pre>{formatAuditValues(log.old_values)}</pre></div> : null}
                    {log.new_values ? <div><h3>Después</h3><pre>{formatAuditValues(log.new_values)}</pre></div> : null}
                  </div>
                </details>
              ) : null}
            </article>
          ))}
        </section>
      ) : (
        <p className="admin-empty audit-empty">Todavía no hay cambios registrados.</p>
      )}

      {!loading && hasMore ? (
        <button className="admin-button admin-button--secondary audit-load-more" type="button" disabled={loadingMore} onClick={() => void loadMore()}>
          {loadingMore ? 'Cargando...' : 'Cargar más'}
        </button>
      ) : null}
    </main>
  );
}
