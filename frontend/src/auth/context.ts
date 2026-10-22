import { createContext } from 'react';

export type AuthUser = {
  id: number;
  full_name: string;
  email: string;
  is_admin: boolean;
  can_view_audit: boolean;
};

export type AuthContextValue = {
  user: AuthUser | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | null>(null);