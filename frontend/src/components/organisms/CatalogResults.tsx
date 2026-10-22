import ProductCard from '../atoms/ProductCard';
import type { Product } from '../../types/product';

type CatalogResultsProps = {
  products: Product[];
  loading: boolean;
};

export default function CatalogResults({ products, loading }: CatalogResultsProps) {
  return (
    <main className="catalog-page__content">
      <div className="catalog-page__summary">
        Resultados encontrados: <strong>{products.length}</strong> productos
      </div>

      {loading ? (
        <div className="catalog-page__empty">Cargando catálogo...</div>
      ) : products.length === 0 ? (
        <div className="catalog-page__empty">No hay productos que coincidan con tu búsqueda.</div>
      ) : (
        <div className="catalog-page__grid">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </main>
  );
}
