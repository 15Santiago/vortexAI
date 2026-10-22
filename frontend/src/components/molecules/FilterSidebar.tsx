import './FilterSidebar.css';

const categoryLabels: Record<string, string> = {
  Cameras: 'Cámaras',
  'Chargers & Cables': 'Cargadores y cables',
  Gaming: 'Videojuegos',
  Headphones: 'Auriculares',
  Laptops: 'Portátiles',
  Networking: 'Redes',
  'Other Electronics': 'Otros electrónicos',
  Phones: 'Teléfonos',
  'Power & Batteries': 'Energía y baterías',
  'Printers & Scanners': 'Impresoras y escáneres',
  'Smart Home': 'Hogar inteligente',
  Speakers: 'Altavoces',
  Storage: 'Almacenamiento',
  'TV & Display': 'Televisores y pantallas',
  Wearables: 'Relojes y dispositivos wearables',
};

function getCategoryLabel(category: string): string {
  return categoryLabels[category] ?? category;
}

type FilterSidebarProps = {
  categories: string[];
  selectedCategory: string;
  onSelectCategory: (category: string) => void;
};

export default function FilterSidebar({
  categories,
  selectedCategory,
  onSelectCategory,
}: FilterSidebarProps) {
  return (
    <aside className="filter-sidebar">
      <h4>Filtros</h4>
      <div className="filter-sidebar__list">
        <label className="filter-option">
          <input
            type="radio"
            name="category"
            checked={selectedCategory === 'all'}
            onChange={() => onSelectCategory('all')}
          />
          <span>Todas las categorías</span>
        </label>

        {categories
          .filter((category) => category !== 'all')
          .map((category) => (
            <label key={category} className="filter-option">
              <input
                type="radio"
                name="category"
                checked={selectedCategory === category}
                onChange={() => onSelectCategory(category)}
              />
              <span>{getCategoryLabel(category)}</span>
            </label>
          ))}
      </div>
    </aside>
  );
}
