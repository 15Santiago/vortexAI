import { Link, useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import type { Product } from '../types/product';
import './ProductDetailPage.css';

export default function ProductDetailPage() {
  const { id } = useParams();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadProduct() {
      try {
        const response = await fetch('/data/products.json');
        const products = (await response.json()) as Product[];
        const found = products.find((item) => item.id === id) ?? products[0] ?? null;
        setProduct(found);
      } catch (error) {
        console.error('Error al cargar detalle:', error);
      } finally {
        setLoading(false);
      }
    }

    void loadProduct();
  }, [id]);

  if (loading) {
    return <div className="page-state">Cargando detalle del producto...</div>;
  }

  if (!product) {
    return (
      <div className="page-state">
        <h2>No se encontró el producto.</h2>
        <Link to="/catalogo">Volver al catálogo</Link>
      </div>
    );
  }

  return (
    <div className="product-detail">
      <div className="product-detail__back">
        <Link to="/catalogo">← Volver al catálogo</Link>
      </div>

      <div className="product-detail__layout">
        <div className="product-detail__image-wrap">
          <img src={product.product_image_url} alt={product.product_title} className="product-detail__image" />
        </div>

        <div className="product-detail__info">
          <span className="product-detail__category">{product.product_category}</span>
          <h1>{product.product_title}</h1>

          <p className="product-detail__rating">★ {product.product_rating ?? 'N/A'} · {product.total_reviews ?? 0} reseñas</p>

          <div className="product-detail__price-block">
            <strong>${Number(product.discounted_price ?? product.original_price ?? 0).toFixed(2)}</strong>
            {product.original_price && product.discounted_price && product.original_price > product.discounted_price ? (
              <span>${Number(product.original_price).toFixed(2)}</span>
            ) : null}
          </div>

          <div className="product-detail__meta">
            <div>
              <span>Disponibilidad</span>
              <strong>{product.buy_box_availability ?? 'Sin información'}</strong>
            </div>
            <div>
              <span>Entrega</span>
              <strong>{product.delivery_date ?? 'No disponible'}</strong>
            </div>
          </div>

          <div className="product-detail__actions">
            <Link to="/carrito" className="product-detail__button product-detail__button--secondary">
              Agregar al carrito
            </Link>
            <Link to="/carrito" className="product-detail__button product-detail__button--primary">
              Comprar ahora
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
