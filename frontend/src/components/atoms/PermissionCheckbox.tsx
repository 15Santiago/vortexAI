type PermissionCheckboxProps = {
  name: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (checked: boolean) => void;
};

export default function PermissionCheckbox({
  name,
  description,
  checked,
  disabled = false,
  onChange,
}: PermissionCheckboxProps) {
  return (
    <label className="permission-option">
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span className="permission-option__copy">
        <strong>{name}</strong>
        <small>{description}</small>
      </span>
    </label>
  );
}