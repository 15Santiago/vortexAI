import { Link } from 'react-router-dom';
import type { Product } from '../../types/product';
import './ProductCard.css';

type ProductCardProps = {
  product: Product;
};

export default function ProductCard({ product }: ProductCardProps) {
  const price = product.discounted_price ?? product.original_price ?? 0;

  return (
    <article className="product-card">
      <div className="product-card__image-wrap">
        <img
          src={product.product_image_url}
          alt={product.product_title}
          className="product-card__image"
        />
      </div>

      <div className="product-card__content">
        <span className="product-card__category">{product.product_category}</span>
        <h3>{product.product_title}</h3>

        <div className="product-card__meta">
          <span className="product-card__rating">★ {product.product_rating ?? 'N/A'}</span>
          <span className="product-card__reviews">{product.total_reviews ?? 0} reseñas</span>
        </div>

        <div className="product-card__price-row">
          <strong>${Number(price).toFixed(2)}</strong>
          {product.original_price && product.discounted_price && product.original_price > product.discounted_price ? (
            <span>${Number(product.original_price).toFixed(2)}</span>
          ) : null}
        </div>
      </div>

      <Link to={`/producto/${product.id}`} className="product-card__button">
        Ver detalle
      </Link>
    </article>
  );
}
