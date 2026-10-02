import { useEffect, useState, type FormEvent } from 'react';
import { useAuth } from '../auth/useAuth';
import PermissionCheckbox from '../components/atoms/PermissionCheckbox';
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
  const { user: currentAdmin } = useAuth();
  const [roles, setRoles] = useState<AppRole[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [permissionDrafts, setPermissionDrafts] = useState<Record<number, string[]>>({});
  const [assignedRoles, setAssignedRoles] = useState<Record<number, number>>({});
  const [roleName, setRoleName] = useState('');
  const [roleDescription, setRoleDescription] = useState('');
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
        setSelectedRoleId((current) => current ?? roleResult.roles.find((role) => role.name === 'usuario')?.id ?? roleResult.roles[0]?.id ?? null);
      } catch (loadError) {
        if (active) setError(loadError instanceof Error ? loadError.message : 'No se pudo cargar la administración.');
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadAdministration();
    return () => { active = false; };
  }, []);

  const selectedRole = roles.find((role) => role.id === selectedRoleId) ?? null;
  const selectedPermissions = selectedRole
    ? permissionDrafts[selectedRole.id] ?? selectedRole.permission_names
    : [];

  async function createRole(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setNotice('');
    setSaving(true);
    try {
      const result = await adminRequest<{ role: AppRole }>('/api/admin/roles', {
        method: 'POST',
        body: JSON.stringify({ name: roleName, description: roleDescription || null }),
      });
      setRoles((current) => [...current, result.role].sort((left, right) => left.name.localeCompare(right.name)));
      setSelectedRoleId(result.role.id);
      setRoleName('');
      setRoleDescription('');
      setNotice('Rol creado. Asigna sus permisos para habilitar funciones.');
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'No se pudo crear el rol.');
    } finally {
      setSaving(false);
    }
  }

  async function savePermissions() {
    if (!selectedRole) return;
    setError('');
    setNotice('');
    setSaving(true);
    try {
      await adminRequest(`/api/admin/roles/${selectedRole.id}/permissions`, {
        method: 'PUT',
        body: JSON.stringify({ permission_names: selectedPermissions }),
      });
      setRoles((current) => current.map((role) => (
        role.id === selectedRole.id ? { ...role, permission_names: selectedPermissions } : role
      )));
      setPermissionDrafts((current) => {
        const next = { ...current };
        delete next[selectedRole.id];
        return next;
      });
      setNotice(`Permisos de ${selectedRole.name} actualizados.`);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'No se pudieron guardar los permisos.');
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
      setUsers((current) => current.map((item) => (
        item.id === user.id && role ? { ...item, role_id: role.id, role_name: role.name } : item
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
          <section className="admin-grid">
            <article className="admin-panel admin-panel--create">
              <div className="admin-panel__heading">
                <span className="admin-panel__eyebrow">ESTRUCTURA</span>
                <h2>Crear un rol</h2>
                <p>Los roles nuevos empiezan sin permisos.</p>
              </div>
              <form className="admin-role-form" onSubmit={(event) => void createRole(event)}>
                <label>
                  Nombre del rol
                  <input
                    required
                    minLength={1}
                    maxLength={80}
                    placeholder="Analista de ventas"
                    value={roleName}
                    onChange={(event) => setRoleName(event.target.value)}
                  />
                </label>
                <label>
                  Descripción
                  <input
                    maxLength={255}
                    placeholder="Acceso para análisis de ventas"
                    value={roleDescription}
                    onChange={(event) => setRoleDescription(event.target.value)}
                  />
                </label>
                <button className="admin-button admin-button--primary" type="submit" disabled={saving}>
                  Crear rol <span aria-hidden="true">+</span>
                </button>
              </form>
              <div className="admin-role-list" aria-label="Roles existentes">
                {roles.map((role) => (
                  <button
                    className={`admin-role-row${selectedRoleId === role.id ? ' admin-role-row--selected' : ''}`}
                    type="button"
                    key={role.id}
                    onClick={() => setSelectedRoleId(role.id)}
                  >
                    <span className="admin-role-row__name">{role.name}</span>
                    <span className="admin-role-row__meta">{role.user_count} usuarios</span>
                  </button>
                ))}
              </div>
            </article>

            <article className="admin-panel admin-panel--permissions">
              <div className="admin-panel__heading admin-panel__heading--inline">
                <div>
                  <span className="admin-panel__eyebrow">AUTORIZACIÓN</span>
                  <h2>Permisos del rol</h2>
                  <p>{selectedRole ? `${selectedRole.name}: ${selectedRole.description || 'sin descripción'}` : 'Selecciona un rol.'}</p>
                </div>
                <span className="admin-panel__count">{selectedPermissions.length} asignados</span>
              </div>
              <div className="admin-permissions">
                {permissions.map((permission) => (
                  <PermissionCheckbox
                    key={permission.id}
                    name={permission.name}
                    description={permission.description}
                    checked={selectedPermissions.includes(permission.name)}
                    disabled={selectedRole?.name === 'administrador' && ['roles.manage', 'permissions.manage', 'users.manage'].includes(permission.name)}
                    onChange={(checked) => setPermissionDrafts((drafts) => {
                      if (!selectedRole) return drafts;
                      const current = drafts[selectedRole.id] ?? selectedRole.permission_names;
                      return checked
                        ? { ...drafts, [selectedRole.id]: [...current, permission.name] }
                        : { ...drafts, [selectedRole.id]: current.filter((name) => name !== permission.name) };
                    })}
                  />
                ))}
              </div>
              <div className="admin-panel__actions">
                <span>Los cambios se aplican al guardar.</span>
                <button className="admin-button admin-button--primary" type="button" disabled={!selectedRole || saving} onClick={() => void savePermissions()}>
                  Guardar permisos
                </button>
              </div>
            </article>
          </section>

          <section className="admin-panel admin-panel--users">
            <div className="admin-panel__heading admin-panel__heading--inline">
              <div>
                <span className="admin-panel__eyebrow">CUENTAS</span>
                <h2>Usuarios y roles</h2>
                <p>Asigna a cada cuenta el nivel de acceso adecuado.</p>
              </div>
              <span className="admin-panel__count">{users.length} usuarios</span>
            </div>
            {users.length ? (
              <div className="admin-user-list">
                {users.map((user) => (
                  <div className="admin-user-row" key={user.id}>
                    <div className="admin-user-row__identity">
                      <strong>{user.full_name}</strong>
                      <span>{user.email}</span>
                    </div>
                    <select
                      aria-label={`Rol de ${user.email}`}
                      value={assignedRoles[user.id] ?? user.role_id}
                      disabled={user.id === currentAdmin?.id}
                      onChange={(event) => setAssignedRoles((current) => ({ ...current, [user.id]: Number(event.target.value) }))}
                    >
                      {roles.map((role) => <option value={role.id} key={role.id}>{role.name}</option>)}
                    </select>
                    <button className="admin-button admin-button--secondary" type="button" disabled={saving || (assignedRoles[user.id] ?? user.role_id) === user.role_id} onClick={() => void saveUserRole(user)}>
                      Aplicar
                    </button>
                  </div>
                ))}
              </div>
            ) : <p className="admin-empty admin-empty--compact">Aún no hay cuentas registradas.</p>}
          </section>
        </>
      )}
    </main>
  );
}