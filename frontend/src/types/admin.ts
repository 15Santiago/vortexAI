export type Permission = {
  id: number;
  name: string;
  description: string;
};

export type AppRole = {
  id: number;
  name: string;
  description: string | null;
  user_count: number;
  permission_names: string[];
};

export type ManagedUser = {
  id: number;
  full_name: string;
  email: string;
  is_active: boolean;
  created_at: string;
  role_id: number;
  role_name: string;
};