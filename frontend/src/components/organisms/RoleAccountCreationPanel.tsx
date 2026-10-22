import { useState, type FormEvent } from 'react';
import PermissionCheckbox from '../atoms/PermissionCheckbox';
import type { Permission } from '../../types/admin';

export type RoleAccountFormData = {
  name: string;
  description: string;
  staff_full_name: string;
  staff_email: string;
  staff_username: string;
  staff_password: string;
  permission_names: string[];
};

type RoleAccountCreationPanelProps = {
  permissions: Permission[];
  saving: boolean;
  onCreate: (formData: RoleAccountFormData) => Promise<boolean>;
};

const emptyForm: RoleAccountFormData = {
  name: '',
  description: '',
  staff_full_name: '',
  staff_email: '',
  staff_username: '',
  staff_password: '',
  permission_names: [],
};

export default function RoleAccountCreationPanel({
  permissions,
  saving,
  onCreate,
}: RoleAccountCreationPanelProps) {
  const [formData, setFormData] = useState(emptyForm);

  function updateField(field: keyof Omit<RoleAccountFormData, 'permission_names'>, value: string) {
    setFormData((current) => ({ ...current, [field]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (await onCreate(formData)) setFormData(emptyForm);
  }

  function togglePermission(name: string, checked: boolean) {
    setFormData((current) => ({
      ...current,
      permission_names: checked
        ? [...current.permission_names, name]
        : current.permission_names.filter((permission) => permission !== name),
    }));
  }

  return (
    <form className="admin-grid admin-grid--create" onSubmit={(event) => void submit(event)}>
      <article className="admin-panel admin-panel--create">
        <div className="admin-panel__heading">
          <span className="admin-panel__eyebrow">ESTRUCTURA</span>
          <h2>Crear un rol</h2>
          <p>La cuenta de acceso se crea junto con el rol.</p>
        </div>
        <div className="admin-role-form">
          <label>
            Nombre del rol
            <input
              required
              minLength={1}
              maxLength={80}
              placeholder="Analista de ventas"
              value={formData.name}
              onChange={(event) => updateField('name', event.target.value)}
            />
          </label>
          <label>
            Descripción
            <input
              maxLength={255}
              placeholder="Acceso para análisis de ventas"
              value={formData.description}
              onChange={(event) => updateField('description', event.target.value)}
            />
          </label>
          <label>
            Nombre completo del personal
            <input
              required
              maxLength={150}
              autoComplete="name"
              value={formData.staff_full_name}
              onChange={(event) => updateField('staff_full_name', event.target.value)}
            />
          </label>
          <label>
            Correo electrónico
            <input
              required
              type="email"
              maxLength={254}
              autoComplete="email"
              value={formData.staff_email}
              onChange={(event) => updateField('staff_email', event.target.value)}
            />
          </label>
          <label>
            Usuario de acceso
            <input
              required
              minLength={3}
              maxLength={50}
              autoComplete="username"
              value={formData.staff_username}
              onChange={(event) => updateField('staff_username', event.target.value)}
            />
          </label>
          <label>
            Contraseña inicial
            <input
              required
              type="password"
              minLength={12}
              maxLength={72}
              autoComplete="new-password"
              value={formData.staff_password}
              onChange={(event) => updateField('staff_password', event.target.value)}
            />
          </label>
          <button className="admin-button admin-button--primary" type="submit" disabled={saving}>
            Crear rol y cuenta <span aria-hidden="true">+</span>
          </button>
        </div>
      </article>

      <article className="admin-panel admin-panel--permissions">
        <div className="admin-panel__heading admin-panel__heading--inline">
          <div>
            <span className="admin-panel__eyebrow">AUTORIZACIÓN</span>
            <h2>Permisos de la cuenta</h2>
            <p>Se asignarán únicamente al usuario que se crea, no a todo el rol.</p>
          </div>
          <span className="admin-panel__count">{formData.permission_names.length} asignados</span>
        </div>
        <div className="admin-permissions">
          {permissions.map((permission) => (
            <PermissionCheckbox
              key={permission.id}
              name={permission.name}
              description={permission.description}
              checked={formData.permission_names.includes(permission.name)}
              onChange={(checked) => togglePermission(permission.name, checked)}
            />
          ))}
        </div>
      </article>
    </form>
  );
}
