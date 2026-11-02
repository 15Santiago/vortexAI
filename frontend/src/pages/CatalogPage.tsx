import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import SearchInput from '../components/atoms/SearchInput';
import ProductCard from '../components/atoms/ProductCard';
import FilterSidebar from '../components/molecules/FilterSidebar';
import CatalogResults from '../components/organisms/CatalogResults';
import { API_BASE_URL } from '../data/api';
import type { Product } from '../types/product';
import './CatalogPage.css';

const FILTERS_STORAGE_KEY = 'vortexai.catalogo.filtros';

type AssistantCatalogSelection = {
  productIds: number[];
  query: string;
};

function assistantSelectionFromState(state: unknown): AssistantCatalogSelection | null {
  if (!state || typeof state !== 'object') return null;
  const record = state as Record<string, unknown>;
  if (!Array.isArray(record.assistantProductIds)) return null;

  const productIds = record.assistantProductIds.filter(
    (id): id is number => typeof id === 'number' && Number.isInteger(id) && id > 0,
  );
  if (productIds.length === 0 && record.assistantSearchExecuted !== true) return null;

  return {
    productIds,
    query: typeof record.assistantQuery === 'string' ? record.assistantQuery : '',
  };
}

function readSavedFilters(): { category: string; search: string } {
  try {
    const raw = sessionStorage.getItem(FILTERS_STORAGE_KEY);
    if (!raw) return { category: 'all', search: '' };
    const parsed = JSON.parse(raw) as { category?: unknown; search?: unknown };
    return {
      category: typeof parsed.category === 'string' ? parsed.category : 'all',
      search: typeof parsed.search === 'string' ? parsed.search : '',
    };
  } catch {
    return { category: 'all', search: '' };
  }
}

function looksLikeBatteryProduct(title: string) {
  const normalized = title.toLowerCase();
  const batteryKeywords = [
    'battery',
    'batteries',
    'power bank',
    'aa battery',
    'aaa battery',
    '9v battery',
    'alkaline',
    'lithium battery',
    'rechargeable',
    'duracell',
    'energizer',
  ];

  return batteryKeywords.some((keyword) => normalized.includes(keyword));
}

export default function CatalogPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const assistantSelection = useMemo(
    () => assistantSelectionFromState(location.state),
    [location.state],
  );
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState(() => readSavedFilters().search);
  const [selectedCategory, setSelectedCategory] = useState(() => readSavedFilters().category);
  const [loading, setLoading] = useState(true);
  const [suggestions, setSuggestions] = useState<Product[]>([]);
  const [suggestionsMode, setSuggestionsMode] = useState<'historial' | 'populares'>('populares');

  useEffect(() => {
    async function loadProducts() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/productos`);
        const payload = (await response.json()) as { productos?: Product[] };
        setProducts(payload.productos ?? []);
      } catch (error) {
        console.error('Error al cargar productos:', error);
      } finally {
        setLoading(false);
      }
    }

    void loadProducts();
  }, []);

  // Sugerencias basadas en el historial del usuario (solo con sesión iniciada)
  useEffect(() => {
    async function loadSuggestions() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/recomendaciones`, {
          credentials: 'include',
        });
        if (!response.ok) {
          setSuggestions([]);
          return;
        }
        const payload = (await response.json()) as {
          modo?: 'historial' | 'populares';
          productos?: Product[];
        };
        setSuggestions((payload.productos ?? []).slice(0, 4));
        setSuggestionsMode(payload.modo === 'historial' ? 'historial' : 'populares');
      } catch (error) {
        console.error('Error al cargar sugerencias:', error);
        setSuggestions([]);
      }
    }

    void loadSuggestions();
  }, []);

  // Guarda el filtro y la búsqueda para recuperarlos al volver desde el detalle de un producto
  useEffect(() => {
    try {
      sessionStorage.setItem(
        FILTERS_STORAGE_KEY,
        JSON.stringify({ category: selectedCategory, search }),
      );
    } catch {
      // Si el navegador no permite guardar, el filtro simplemente no se recuerda
    }
  }, [selectedCategory, search]);

  const categories = useMemo(() => {
    const unique = Array.from(new Set(products.map((product) => product.product_category)));
    return ['all', ...unique];
  }, [products]);

  // Categoría que realmente se aplica: si la guardada ya no existe en los datos, se usa "Todas"
  const activeCategory = assistantSelection
    ? 'all'
    : loading || categories.includes(selectedCategory)
      ? selectedCategory
      : 'all';

  const filteredProducts = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();

    return products.filter((product) => {
      if (assistantSelection) {
        return assistantSelection.productIds.includes(Number(product.id));
      }

      const categoryMatches =
        activeCategory === 'all' || product.product_category === activeCategory;

      const isBatteryHiddenFromPhones =
        activeCategory === 'Phones' &&
        product.product_category === 'Phones' &&
        looksLikeBatteryProduct(product.product_title);

      const matchesSearch =
        normalizedSearch.length === 0 ||
        product.product_title.toLowerCase().includes(normalizedSearch) ||
        product.product_category.toLowerCase().includes(normalizedSearch);

      return categoryMatches && !isBatteryHiddenFromPhones && matchesSearch;
    });
  }, [products, search, activeCategory, assistantSelection]);

  function handleSearchChange(value: string) {
    if (assistantSelection) {
      navigate(location.pathname, { replace: true, state: null });
    }
    setSearch(value);
  }

  function showFullCatalog() {
    navigate(location.pathname, { replace: true, state: null });
    setSearch('');
    setSelectedCategory('all');
  }

  return (
    <div className="catalog-page">
      <div className="catalog-page__toolbar">
        <SearchInput
          value={assistantSelection ? '' : search}
          onChange={handleSearchChange}
          placeholder="Buscar productos..."
        />
      </div>

      {assistantSelection ? (
        <div className="catalog-page__assistant-search">
          <span>
            <strong>Resultados del asistente</strong>
            {assistantSelection.query ? ` para “${assistantSelection.query}”` : ''}
          </span>
          <button type="button" onClick={showFullCatalog}>
            Ver catálogo completo
          </button>
        </div>
      ) : null}

      {suggestions.length > 0 ? (
        <section
          className="catalog-page__suggestions"
          aria-label="Sugerencias para ti"
          style={{ margin: '0 0 24px 0' }}
        >
          <div className="catalog-page__summary">
            <strong>
              {suggestionsMode === 'historial' ? 'Sugerencias para ti' : 'Productos populares'}
            </strong>
            {suggestionsMode === 'historial'
              ? ' · basadas en los productos que has visto'
              : ' · explora productos para recibir sugerencias personalizadas'}
          </div>
          <div className="catalog-page__grid">
            {suggestions.map((product) => (
              <ProductCard key={`sugerencia-${product.id}`} product={product} />
            ))}
          </div>
        </section>
      ) : null}

      <div className="catalog-page__body">
        {assistantSelection ? null : (
          <FilterSidebar
            categories={categories}
            selectedCategory={activeCategory}
            onSelectCategory={setSelectedCategory}
          />
        )}

        <CatalogResults products={filteredProducts} loading={loading} />
      </div>
    </div>
  );
};