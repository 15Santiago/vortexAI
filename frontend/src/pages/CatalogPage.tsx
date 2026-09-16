import { useEffect, useMemo, useState } from 'react';
import SearchInput from '../components/atoms/SearchInput';
import ProductCard from '../components/atoms/ProductCard';
import FilterSidebar from '../components/molecules/FilterSidebar';
import type { Product } from '../types/product';
import './CatalogPage.css';

export default function CatalogPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadProducts() {
      try {
        const response = await fetch('http://localhost:8000/api/productos');
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

  const categories = useMemo(() => {
    const unique = Array.from(new Set(products.map((product) => product.product_category)));
    return ['all', ...unique];
  }, [products]);

  const filteredProducts = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();

    return products.filter((product) => {
      const matchesCategory = selectedCategory === 'all' || product.product_category === selectedCategory;
      const matchesSearch =
        normalizedSearch.length === 0 ||
        product.product_title.toLowerCase().includes(normalizedSearch) ||
        product.product_category.toLowerCase().includes(normalizedSearch);

      return matchesCategory && matchesSearch;
    });
  }, [products, search, selectedCategory]);

  return (
    <div className="catalog-page">
      <div className="catalog-page__toolbar">
        <SearchInput value={search} onChange={setSearch} placeholder="Buscar productos..." />
      </div>

      <div className="catalog-page__body">
        <FilterSidebar
          categories={categories}
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
        />

        <main className="catalog-page__content">
          <div className="catalog-page__summary">
            Resultados encontrados: <strong>{filteredProducts.length}</strong> productos
          </div>

          {loading ? (
            <div className="catalog-page__empty">Cargando catálogo...</div>
          ) : filteredProducts.length === 0 ? (
            <div className="catalog-page__empty">No hay productos que coincidan con tu búsqueda.</div>
          ) : (
            <div className="catalog-page__grid">
              {filteredProducts.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
