import PermissionCheckbox from '../atoms/PermissionCheckbox';
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
  onSaveUserRole: (user: ManagedUser) => void;
  onEditUserPermissions: (user: ManagedUser) => void;
  onClosePermissions: () => void;
  onUserPermissionChange: (permissionName: string, checked: boolean) => void;
  onSaveUserPermissions: (user: ManagedUser) => void;
};

export default function AccountsRolesPanel({
  users,
  filteredUsers,
  roles,
  permissions,
  userRoleFilter,
  assignedRoles,
  editingUserId,
  userPermissionDraft,
  currentUserId,
  saving,
  onUserRoleFilterChange,
  onAssignedRoleChange,
  onSaveUserRole,
  onEditUserPermissions,
  onClosePermissions,
  onUserPermissionChange,
  onSaveUserPermissions,
}: AccountsRolesPanelProps) {
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
                <div className="admin-user-role">
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
                    onClick={() => onSaveUserRole(user)}
                  >
                    Aplicar
                  </button>
                </div>
                <button
                  className="admin-button admin-button--secondary"
                  type="button"
                  disabled={saving}
                  onClick={() => editingUserId === user.id ? onClosePermissions() : onEditUserPermissions(user)}
                >
                  {editingUserId === user.id ? 'Cerrar permisos' : 'Editar permisos'}
                </button>
              </div>
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
                      <button className="admin-button admin-button--primary" type="button" disabled={saving} onClick={() => onSaveUserPermissions(user)}>
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
