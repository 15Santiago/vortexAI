import { Navigate } from 'react-router-dom';
import { useAuth } from '../../auth/useAuth';

export default function RequireAuditAccess({ children }: { children: React.ReactNode }) {
  const { user, ready } = useAuth();

  if (!ready) return <div className="auth-route-state" role="status">Verificando sesión...</div>;
  if (!user) return <Navigate to="/acceso" replace state={{ from: '/admin/logs' }} />;
  if (!user.can_view_audit) return <Navigate to="/" replace />;

  return children;
}
