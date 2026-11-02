import { useState, type FormEvent } from 'react';
import { PermissionCheckbox } from '../atoms/PermissionCheckbox';
import { PasswordInput } from '../atoms/PasswordInput';
import type { AppRole, ManagedUser, Permission } from '../../types/admin';

type AccountsRolesPanelProps = {
  users: ManagedUser[];
  filteredUsers: ManagedUser[];
  roles: AppRole[];
  permissions: Permission[];
  userRoleFilter: string;
  assignedRoles: Record<number, number>;
  editingUserId: number | null;
  userPermissionDraft: string[];
  currentUserId: number | undefined;
  saving: boolean;
  onUserRoleFilterChange: (roleName: string) => void;
  onAssignedRoleChange: (userId: number, roleId: number) => void;
  canAssignRoles: boolean;
  canManagePermissions: boolean;
  canEditUsers: boolean;
  canManageStatus: boolean;
  canDeleteUsers: boolean;
  onSaveUserRole: (user: ManagedUser, reason: string) => void;
  onEditUserPermissions: (user: ManagedUser) => void;
  onClosePermissions: () => void;
  onUserPermissionChange: (permissionName: string, checked: boolean) => void;
  onSaveUserPermissions: (user: ManagedUser, reason: string) => void;
  onUpdateUser: (user: ManagedUser, email: string, password: string, reason: string) => Promise<boolean>;
  onChangeUserStatus: (user: ManagedUser, isActive: boolean, reason: string) => void;
  onDeleteUser: (user: ManagedUser, reason: string) => void;
};

export function AccountsRolesPanel({
  users,
  filteredUsers,
  roles,
  permissions,
  userRoleFilter,
  assignedRoles,
  editingUserId,
  userPermissionDraft,
  currentUserId,
  canAssignRoles,
  canManagePermissions,
  canEditUsers,
  canManageStatus,
  canDeleteUsers,
  saving,
  onUserRoleFilterChange,
  onAssignedRoleChange,
  onSaveUserRole,
  onEditUserPermissions,
  onClosePermissions,
  onUserPermissionChange,
  onSaveUserPermissions,
  onUpdateUser,
  onChangeUserStatus,
  onDeleteUser,
}: AccountsRolesPanelProps) {
  const [editingAccountId, setEditingAccountId] = useState<number | null>(null);
  const [emailDraft, setEmailDraft] = useState('');
  const [passwordDraft, setPasswordDraft] = useState('');
  const [reasonDraft, setReasonDraft] = useState('');

  function askReason(action: string): string | null {
    const reason = window.prompt(`Indica el motivo para ${action}:`)?.trim();
    return reason && reason.length >= 3 ? reason : null;
  }

  async function submitAccountEdit(event: FormEvent<HTMLFormElement>, user: ManagedUser) {
    event.preventDefault();
    if (reasonDraft.trim().length < 3) return;
    if (await onUpdateUser(user, emailDraft.trim(), passwordDraft, reasonDraft.trim())) {
      setEditingAccountId(null);
      setPasswordDraft('');
      setReasonDraft('');
    }
  }

  return (
    <section className="admin-panel admin-panel--users">
      <div className="admin-panel__heading admin-panel__heading--inline">
        <div>
          <span className="admin-panel__eyebrow">CUENTAS</span>
          <h2>Usuarios y roles</h2>
          <p>Administra el rol y los permisos específicos de cada cuenta.</p>
        </div>
        <div className="admin-users-filter">
          <label htmlFor="admin-user-role-filter">Filtrar por rol</label>
          <select
            id="admin-user-role-filter"
            className="admin-users-filter__select"
            value={userRoleFilter}
            onChange={(event) => onUserRoleFilterChange(event.target.value)}
          >
            <option value="all">Todos los roles</option>
            {roles.map((role) => <option value={role.name} key={role.id}>{role.name}</option>)}
          </select>
          <span className="admin-panel__count">{filteredUsers.length} usuarios</span>
        </div>
      </div>
      {filteredUsers.length ? (
        <div className="admin-user-list">
          {filteredUsers.map((user) => (
            <div className="admin-user-entry" key={user.id}>
              <div className="admin-user-row">
                <div className="admin-user-row__identity">
                  <strong>{user.full_name}</strong>
                  <span>{user.email}</span>
                  {user.username ? <span>Usuario: {user.username}</span> : null}
                </div>
                {canAssignRoles ? <div className="admin-user-role">
                  <select
                    aria-label={`Rol de ${user.email}`}
                    value={assignedRoles[user.id] ?? user.role_id}
                    disabled={user.id === currentUserId}
                    onChange={(event) => onAssignedRoleChange(user.id, Number(event.target.value))}
                  >
                    {roles.map((role) => <option value={role.id} key={role.id}>{role.name}</option>)}
                  </select>
                  <button
                    className="admin-button admin-button--secondary"
                    type="button"
                    disabled={saving || (assignedRoles[user.id] ?? user.role_id) === user.role_id}
                    onClick={() => {
                      const reason = askReason('cambiar el rol');
                      if (reason) onSaveUserRole(user, reason);
                    }}
                  >
                    Aplicar
                  </button>
                </div> : null}
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {canEditUsers ? <button
                    className="admin-button admin-button--secondary"
                    type="button"
                    disabled={saving}
                    onClick={() => {
                      setEditingAccountId(editingAccountId === user.id ? null : user.id);
                      setEmailDraft(user.email);
                      setPasswordDraft('');
                      setReasonDraft('');
                    }}
                  >
                    {editingAccountId === user.id ? 'Cerrar edición' : 'Editar cuenta'}
                  </button> : null}
                  {canManagePermissions ? <button
                    className="admin-button admin-button--secondary"
                    type="button"
                    disabled={saving}
                    onClick={() => editingUserId === user.id ? onClosePermissions() : onEditUserPermissions(user)}
                  >
                    {editingUserId === user.id ? 'Cerrar permisos' : 'Editar permisos'}
                  </button> : null}
                  {canManageStatus ? <button
                    className="admin-button admin-button--secondary"
                    type="button"
                    disabled={saving || user.id === currentUserId}
                    onClick={() => {
                      const nextActive = !user.is_active;
                      const reason = askReason(nextActive ? 'reactivar la cuenta' : 'desactivar la cuenta');
                      if (reason && window.confirm(`¿${nextActive ? 'Reactivar' : 'Desactivar'} la cuenta de ${user.email}?`)) {
                        onChangeUserStatus(user, nextActive, reason);
                      }
                    }}
                  >
                    {user.is_active ? 'Desactivar' : 'Reactivar'}
                  </button> : null}
                  {canDeleteUsers ? <button
                    className="admin-button"
                    type="button"
                    disabled={saving || user.id === currentUserId}
                    onClick={() => {
                      if (!window.confirm(`¿Eliminar permanentemente la cuenta de ${user.email}?`)) return;
                      const reason = askReason('eliminar la cuenta');
                      if (reason) onDeleteUser(user, reason);
                    }}
                    style={{
                      background: 'rgba(239, 68, 68, 0.15)',
                      color: '#f87171',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      cursor: user.id === currentUserId ? 'not-allowed' : 'pointer',
                      opacity: user.id === currentUserId ? 0.5 : 1,
                    }}
                  >
                    Eliminar
                  </button> : null}
                </div>
              </div>
              <span className="admin-user-entry__status">{user.is_active ? 'Activa' : 'Desactivada'}</span>
              {editingAccountId === user.id ? (
                <form className="admin-user-permissions" onSubmit={(event) => void submitAccountEdit(event, user)}>
                  <label>
                    Correo electrónico
                    <input type="email" required maxLength={254} value={emailDraft} onChange={(event) => setEmailDraft(event.target.value)} />
                  </label>
                  <label>
                    Nueva contraseña (opcional)
                    <PasswordInput
                      minLength={12}
                      maxLength={72}
                      autoComplete="new-password"
                      value={passwordDraft}
                      onChange={(event) => setPasswordDraft(event.target.value)}
                      placeholder="Dejar en blanco para conservarla"
                    />
                  </label>
                  <label>
                    Motivo del cambio
                    <input required minLength={3} maxLength={500} value={reasonDraft} onChange={(event) => setReasonDraft(event.target.value)} />
                  </label>
                  <div className="admin-panel__actions">
                    <button className="admin-button admin-button--primary" type="submit" disabled={saving}>Guardar cuenta</button>
                  </div>
                </form>
              ) : null}
              {editingUserId === user.id ? (
                <div className="admin-user-permissions">
                  <div className="admin-panel__heading admin-panel__heading--inline">
                    <div>
                      <h3>Permisos de {user.full_name}</h3>
                      <p>Los permisos individuales pueden conceder o quitar los heredados del rol.</p>
                    </div>
                    <span className="admin-panel__count">{userPermissionDraft.length} asignados</span>
                  </div>
                  <div className="admin-permissions">
                    {permissions.map((permission) => (
                      <PermissionCheckbox
                        key={permission.id}
                        name={permission.name}
                        description={permission.description}
                        checked={userPermissionDraft.includes(permission.name)}
                        disabled={user.id === currentUserId && ['roles.manage', 'permissions.manage', 'users.manage'].includes(permission.name)}
                        onChange={(checked) => onUserPermissionChange(permission.name, checked)}
                      />
                    ))}
                  </div>
                  <div className="admin-panel__actions">
                    <span>El resto de permisos se hereda del rol.</span>
                    <div className="admin-user-permissions__actions">
                      <button className="admin-button admin-button--secondary" type="button" disabled={saving} onClick={onClosePermissions}>
                        Cancelar
                      </button>
                      <button
                        className="admin-button admin-button--primary"
                        type="button"
                        disabled={saving}
                        onClick={() => {
                          const reason = askReason('actualizar los permisos');
                          if (reason) onSaveUserPermissions(user, reason);
                        }}
                      >
                        Guardar permisos
                      </button>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <p className="admin-empty admin-empty--compact">
          {users.length ? 'No hay cuentas asignadas al rol seleccionado.' : 'Aún no hay cuentas registradas.'}
        </p>
      )}
    </section>
  );
}