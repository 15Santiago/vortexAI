import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { AuthContext, type AuthUser } from './context';
import { API_BASE_URL } from '../data/api';

type AuthResponse = {
  user?: AuthUser;
  verification_required?: boolean;
};

async function parseAuthResponse(response: Response): Promise<AuthResponse> {
  const payload = (await response.json()) as AuthResponse & { detail?: string };
  if (!response.ok) {
    throw new Error(payload.detail || 'No se pudo completar la solicitud.');
  }
  return payload;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;

    fetch(`${API_BASE_URL}/api/auth/me`, { credentials: 'include' })
      .then(async (response) => {
        if (!response.ok) throw new Error('No se pudo verificar la sesión.');
        return (await response.json()) as { user: AuthUser | null };
      })
      .then((payload) => {
        if (active) setUser(payload.user);
      })
      .catch(() => {
        if (active) {
          setUser(null);
        }
      })
      .finally(() => {
        if (active) setReady(true);
      });

    return () => {
      active = false;
    };
  }, []);

  async function authenticate(path: string, payload: Record<string, string>) {
    const response = await fetch(`${API_BASE_URL}/api/auth/${path}`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await parseAuthResponse(response);
    if (result.user) setUser(result.user);
    setReady(true);
  }

  async function login(email: string, password: string) {
    await authenticate('login', { email, password });
  }

  async function register(fullName: string, email: string, password: string) {
    await authenticate('register', { full_name: fullName, email, password });
  }

  async function verifyRegistration(email: string, code: string) {
    await authenticate('verify-registration', { email, code });
  }

  async function refreshUser() {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, { credentials: 'include' });
    const payload = (await response.json()) as { user: AuthUser | null; detail?: string };
    if (!response.ok) throw new Error(payload.detail || 'No se pudo actualizar la sesión.');
    setUser(payload.user);
  }

  async function updateProfile(fullName: string, email: string, password?: string) {
    const bodyData: Record<string, string> = { full_name: fullName, email };
    if (password) {
      bodyData.password = password;
    }

    const response = await fetch(`${API_BASE_URL}/api/auth/profile`, {
      method: 'PUT',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bodyData),
    });

    const payload = (await response.json()) as { user?: AuthUser; detail?: string };
    if (!response.ok) {
      throw new Error(payload.detail || 'No se pudo actualizar el perfil.');
    }

    if (payload.user) {
      setUser(payload.user);
    } else {
      await refreshUser();
    }
  }

  const logout = useCallback(async () => {
    try {
      await fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      }).catch(() => undefined);
    } finally {
      setUser(null);
      setReady(true);
    }
  }, []);

  useEffect(() => {
    if (!user) return undefined;

    let timer: ReturnType<typeof setTimeout>;
    const resetIdleTimer = () => {
      clearTimeout(timer);
      timer = setTimeout(() => { void logout(); }, user.idle_timeout_minutes * 60_000);
    };
    const activityEvents: Array<keyof WindowEventMap> = [
      'keydown',
      'mousedown',
      'mousemove',
      'scroll',
      'touchstart',
    ];
    activityEvents.forEach((eventName) => {
      window.addEventListener(eventName, resetIdleTimer, { passive: true });
    });
    resetIdleTimer();

    return () => {
      clearTimeout(timer);
      activityEvents.forEach((eventName) => {
        window.removeEventListener(eventName, resetIdleTimer);
      });
    };
  }, [logout, user]);

  return (
    <AuthContext.Provider value={{ user, ready, login, register, verifyRegistration, logout, refreshUser, updateProfile }}>
      {children}
    </AuthContext.Provider>
  );
}
