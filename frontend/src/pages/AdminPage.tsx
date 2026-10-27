import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../auth/useAuth';
import AccountsRolesPanel from '../components/organisms/AccountsRolesPanel';
import RoleAccountCreationPanel, { type RoleAccountFormData } from '../components/organisms/RoleAccountCreationPanel';
import { API_BASE_URL } from '../data/api';
import type { AppRole, ManagedUser, Permission } from '../types/admin';
import './AdminPage.css';

async function adminRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });
  const payload = (await response.json()) as T & { detail?: string };
  if (!response.ok) throw new Error(payload.detail || 'No se pudo completar la operación.');
  return payload;
}

export default function AdminPage() {
  const { user: currentAdmin, refreshUser } = useAuth();
  const [roles, setRoles] = useState<AppRole[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [userRoleFilter, setUserRoleFilter] = useState('all');
  const [assignedRoles, setAssignedRoles] = useState<Record<number, number>>({});
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [userPermissionDraft, setUserPermissionDraft] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    let active = true;
    async function loadAdministration() {
      setLoading(true);
      try {
        const [roleResult, permissionResult, userResult] = await Promise.all([
          adminRequest<{ roles: AppRole[] }>('/api/admin/roles'),
          adminRequest<{ permissions: Permission[] }>('/api/admin/permissions'),
          adminRequest<{ users: ManagedUser[] }>('/api/admin/users'),
        ]);
        if (!active) return;
        setRoles(roleResult.roles);
        setPermissions(permissionResult.permissions);
        setUsers(userResult.users);
        setAssignedRoles(Object.fromEntries(userResult.users.map((user) => [user.id, user.role_id])));
      } catch (loadError) {
        if (active) setError(loadError instanceof Error ? loadError.message : 'No se pudo cargar la administración.');
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadAdministration();
    return () => { active = false; };
  }, []);

  const filteredUsers = useMemo(
    () => userRoleFilter === 'all' ? users : users.filter((user) => user.role_name === userRoleFilter),
    [userRoleFilter, users],
  );

  async function createRole(formData: RoleAccountFormData): Promise<boolean> {
    setError('');
    setNotice('');
    setSaving(true);
    try {
      const result = await adminRequest<{ role: AppRole; user: ManagedUser }>('/api/admin/roles', {
        method: 'POST',
        body: JSON.stringify({
          ...formData,
          description: formData.description || null,
        }),
      });
      setRoles((current) => [...current, result.role].sort((left, right) => left.name.localeCompare(right.name)));
      setUsers((current) => [result.user, ...current]);
      setAssignedRoles((current) => ({ ...current, [result.user.id]: result.user.role_id }));
      setNotice('Rol, cuenta de acceso y permisos individuales creados.');
      return true;
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'No se pudo crear el rol.');
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function editUserPermissions(user: ManagedUser) {
    setError('');
    setNotice('');
    try {
      const result = await adminRequest<{ permission_names: string[] }>(`/api/admin/users/${user.id}/permissions`);
      setEditingUserId(user.id);
      setUserPermissionDraft(result.permission_names);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'No se pudieron cargar los permisos de la cuenta.');
    }
  }

  async function saveUserPermissions(user: ManagedUser) {
    setError('');
    setNotice('');
    setSaving(true);
    try {
      await adminRequest(`/api/admin/users/${user.id}/permissions`, {
        method: 'PUT',
        body: JSON.stringify({ permission_names: userPermissionDraft }),
      });
      setEditingUserId(null);
      setNotice(`Permisos de ${user.email} actualizados.`);
      if (user.id === currentAdmin?.id) {
        try {
          await refreshUser();
        } catch (refreshError) {
          const reason = refreshError instanceof Error ? refreshError.message : 'Error desconocido';
          setNotice(`Permisos guardados, pero no se pudo actualizar la sesión: ${reason}`);
        }
      }
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'No se pudieron guardar los permisos de la cuenta.');
    } finally {
      setSaving(false);
    }
  }

  async function saveUserRole(user: ManagedUser) {
    const roleId = assignedRoles[user.id];
    if (roleId === user.role_id) return;
    setError('');
    setNotice('');
    setSaving(true);
    try {
      await adminRequest(`/api/admin/users/${user.id}/role`, {
        method: 'PUT',
        body: JSON.stringify({ role_id: roleId }),
      });
      const role = roles.find((item) => item.id === roleId);
      if (!role) throw new Error('No se encontró el rol seleccionado.');
      setUsers((current) => current.map((item) => (
        item.id === user.id ? { ...item, role_id: role.id, role_name: role.name } : item
      )));
      setRoles((current) => current.map((item) => {
        if (item.id === user.role_id) return { ...item, user_count: Math.max(0, item.user_count - 1) };
        if (item.id === roleId) return { ...item, user_count: item.user_count + 1 };
        return item;
      }));
      setNotice(`Rol actualizado para ${user.email}.`);
    } catch (saveError) {
      setAssignedRoles((current) => ({ ...current, [user.id]: user.role_id }));
      setError(saveError instanceof Error ? saveError.message : 'No se pudo cambiar el rol del usuario.');
    } finally {
      setSaving(false);
    }
  }

  async function deleteUser(user: ManagedUser) {
    if (user.id === currentAdmin?.id) {
      setError('No puedes eliminar tu propia cuenta de administrador.');
      return;
    }
    if (!window.confirm(`¿Estás seguro de que deseas eliminar al usuario ${user.email}?`)) return;

    setError('');
    setNotice('');
    setSaving(true);
    try {
      await adminRequest(`/api/admin/users/${user.id}`, {
        method: 'DELETE',
      });
      
      setUsers((current) => current.filter((item) => item.id !== user.id));
      setRoles((current) => current.map((role) => {
        if (role.name === user.role_name) {
          return { ...role, user_count: Math.max(0, role.user_count - 1) };
        }
        return role;
      }));

      setNotice(`Usuario ${user.email} eliminado correctamente.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo eliminar el usuario.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="admin-page">
      <header className="admin-heading">
        <div>
          <span className="admin-heading__eyebrow">VORTEX / CONTROL DE ACCESO</span>
          <h1>Administración</h1>
          <p>Gestiona roles, permisos y acceso de usuarios.</p>
        </div>
        <span className="admin-heading__badge">ADMINISTRADOR</span>
      </header>

      {error ? <div className="admin-message admin-message--error" role="alert">{error}</div> : null}
      {notice ? <div className="admin-message admin-message--success" role="status">{notice}</div> : null}
      {loading ? <div className="admin-empty" role="status">Cargando configuración de acceso...</div> : (
        <>
          <RoleAccountCreationPanel
            permissions={permissions}
            saving={saving}
            onCreate={createRole}
          />

          <AccountsRolesPanel
            users={users}
            filteredUsers={filteredUsers}
            roles={roles}
            permissions={permissions}
            userRoleFilter={userRoleFilter}
            assignedRoles={assignedRoles}
            editingUserId={editingUserId}
            userPermissionDraft={userPermissionDraft}
            currentUserId={currentAdmin?.id}
            saving={saving}
            onUserRoleFilterChange={setUserRoleFilter}
            onAssignedRoleChange={(userId, roleId) => setAssignedRoles((current) => ({ ...current, [userId]: roleId }))}
            onSaveUserRole={(user) => void saveUserRole(user)}
            onEditUserPermissions={(user) => void editUserPermissions(user)}
            onClosePermissions={() => setEditingUserId(null)}
            onUserPermissionChange={(permissionName, checked) => setUserPermissionDraft((current) => (
              checked
                ? [...current, permissionName]
                : current.filter((name) => name !== permissionName)
            ))}
            onSaveUserPermissions={(user) => void saveUserPermissions(user)}
            onDeleteUser={(user) => void deleteUser(user)}
          />
        </>
      )}
    </main>
  );
}