import { Link } from 'react-router-dom';
import type { Metrics } from '../../types/metrics';

type MetricsOverviewProps = {
  metrics: Metrics;
};

const numberFormat = new Intl.NumberFormat('es-MX');

export default function MetricsOverview({ metrics }: MetricsOverviewProps) {
  const largestCategory = Math.max(...metrics.categories.map((category) => category.product_count), 1);
  const largestPriceBucket = Math.max(...metrics.price_distribution.map((bucket) => bucket.product_count), 1);

  return (
    <>
      <section className="metrics-panels" aria-label="Distribución del catálogo">
        <article className="metrics-panel metrics-panel--categories">
          <div className="metrics-panel__heading">
            <div>
              <span className="metrics-panel__eyebrow">CATÁLOGO</span>
              <h2>Productos por categoría</h2>
            </div>
            <span className="metrics-panel__count">{metrics.total_categories} categorías</span>
          </div>

          <div className="category-list">
            {metrics.categories.slice(0, 8).map((category, index) => (
              <div className="category-row" key={category.name}>
                <div className="category-row__meta">
                  <span className="category-row__name">
                    <span className={`category-row__index category-row__index--${index % 4}`}>
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    {category.name}
                  </span>
                  <span className="category-row__count">
                    {numberFormat.format(category.product_count)}
                    <small>{category.share_percent}%</small>
                  </span>
                </div>
                <div
                  className="category-row__track"
                  role="img"
                  aria-label={`${category.name}: ${category.share_percent}% del catálogo`}
                >
                  <span style={{ width: `${(category.product_count / largestCategory) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="metrics-panel metrics-panel--prices">
          <div className="metrics-panel__heading">
            <div>
              <span className="metrics-panel__eyebrow">PRECIO ACTUAL</span>
              <h2>Rangos de precio</h2>
            </div>
            <span className="metrics-panel__mark" aria-hidden="true">$</span>
          </div>

          <div className="price-list">
            {metrics.price_distribution.map((bucket, index) => (
              <div className="price-row" key={bucket.label}>
                <div className="price-row__meta">
                  <span>{bucket.label}</span>
                  <strong>{numberFormat.format(bucket.product_count)}</strong>
                </div>
                <div className={`price-row__track price-row__track--${index}`}>
                  <span style={{ width: `${(bucket.product_count / largestPriceBucket) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
          <p className="metrics-panel__footnote">Basado en el precio vigente más reciente por producto.</p>
        </article>
      </section>

      <section className="metrics-panel metrics-panel--ranking">
        <div className="metrics-panel__heading">
          <div>
            <span className="metrics-panel__eyebrow">INTERÉS DEL CATÁLOGO</span>
            <h2>Productos con más reseñas</h2>
          </div>
          <span className="metrics-panel__count">Top 5</span>
        </div>

        <div className="review-ranking">
          {metrics.top_products.map((product, index) => (
            <Link className="review-ranking__item" to={`/producto/${product.id}`} key={product.id}>
              <span className={`review-ranking__number review-ranking__number--${index + 1}`}>
                {String(index + 1).padStart(2, '0')}
              </span>
              <span className="review-ranking__product">
                <strong>{product.product_title}</strong>
                <small>{product.product_category}</small>
              </span>
              <span className="review-ranking__rating">
                <span aria-hidden="true">★</span> {product.product_rating ?? 'N/D'}
              </span>
              <strong className="review-ranking__reviews">
                {numberFormat.format(product.total_reviews)} <small>reseñas</small>
              </strong>
              <span className="review-ranking__arrow" aria-hidden="true">↗</span>
            </Link>
          ))}
        </div>
      </section>
    </>
  );
}