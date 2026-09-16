import './SearchInput.css';

type SearchInputProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
};

export default function SearchInput({
  value,
  onChange,
  placeholder = 'Buscar productos...',
}: SearchInputProps) {
  return (
    <label className="search-input" aria-label="Buscar productos">
      <span className="search-input__icon">⌕</span>
      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
    </label>
  );
}
