import './FilterSidebar.css';

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
          <span>Todas</span>
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
              <span>{category}</span>
            </label>
          ))}
      </div>
    </aside>
  );
}
