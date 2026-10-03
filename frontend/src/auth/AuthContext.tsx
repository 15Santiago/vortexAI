import { useEffect, useState, type ReactNode } from 'react';
import { AuthContext, type AuthUser } from './context';
import { API_BASE_URL } from '../data/api';

type AuthResponse = {
  user: AuthUser;
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
        if (!response.ok) throw new Error('La sesión venció.');
        return (await response.json()) as { user: AuthUser };
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
    setUser(result.user);
    setReady(true);
  }

  async function login(email: string, password: string) {
    await authenticate('login', { email, password });
  }

  async function register(fullName: string, email: string, password: string) {
    await authenticate('register', { full_name: fullName, email, password });
  }

  async function logout() {
    try {
      await fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      }).catch(() => undefined);
    } finally {
      setUser(null);
      setReady(true);
    }
  }

  return (
    <AuthContext.Provider value={{ user, ready, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
