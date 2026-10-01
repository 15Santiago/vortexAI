import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../auth/useAuth';

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, ready } = useAuth();
  const location = useLocation();

  if (!ready) {
    return <div className="auth-route-state" role="status">Verificando sesión...</div>;
  }

  if (!user) {
    return <Navigate to="/acceso" replace state={{ from: location.pathname }} />;
  }

  return children;
}