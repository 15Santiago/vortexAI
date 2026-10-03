import { Link } from 'react-router-dom';
import type { Product } from '../types/product';

interface DetalleProductoProps {
  product: Product;
}

export default function DetalleProducto({ product }: DetalleProductoProps) {
  const p = product as Record<string, unknown>;
  const rawId = p.id ?? p._id ?? 1;
  const numericId = typeof rawId === 'number' ? rawId : parseInt(String(rawId), 10) || 1;

  const discountedPrice = typeof p.discounted_price === 'number' ? p.discounted_price : null;
  const standardPrice = typeof p.price === 'number' ? p.price : null;
  const originalPrice = typeof p.original_price === 'number' ? p.original_price : null;
  const price = discountedPrice ?? standardPrice ?? originalPrice ?? (numericId * 15.99 + 10);
  const fakeOriginal = originalPrice ?? (price * 1.25);

  // Función inteligente de imágenes según la categoría o título
  const getSmartImage = () => {
    const imageUrlVal = p.product_image_url ?? p.image ?? p.imageUrl;
    if (
      typeof imageUrlVal === 'string' && 
      imageUrlVal.trim() !== "" && 
      !imageUrlVal.includes("placeholder.com")
    ) {
      return imageUrlVal;
    }

    const title = typeof p.product_title === 'string' ? p.product_title : (typeof p.title === 'string' ? p.title : '');
    const category = typeof p.product_category === 'string' ? p.product_category : (typeof p.category === 'string' ? p.category : '');
    const text = (title + " " + category).toLowerCase();
    
    if (text.includes("airpod") || text.includes("headphone") || text.includes("earbud") || text.includes("audifono") || text.includes("sound") || text.includes("audio") || text.includes("wireless")) {
      return "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=60";
    }
    if (text.includes("fitbit") || text.includes("tracker") || text.includes("band") || text.includes("pulsera") || text.includes("watch") || text.includes("smartwatch")) {
      return "https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?w=600&auto=format&fit=crop&q=60";
    }
    if (text.includes("roku") || text.includes("fire stick") || text.includes("chromecast") || text.includes("streaming") || text.includes("box")) {
      return "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop&q=60";
    }
    if (text.includes("mount") || text.includes("bracket") || text.includes("wall") || text.includes("soporte")) {
      return "https://images.unsplash.com/photo-1593784991095-a205069470b6?w=600&auto=format&fit=crop&q=60";
    }
    if (text.includes("phone") || text.includes("iphone") || text.includes("mobile") || text.includes("smartphone") || text.includes("galaxy")) {
      return "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&auto=format&fit=crop&q=60";
    }
    if (text.includes("laptop") || text.includes("computer") || text.includes("pc") || text.includes("macbook")) {
      return "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&auto=format&fit=crop&q=60";
    }
    if (text.includes("camera") || text.includes("camara") || text.includes("lens")) {
      return "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=600&auto=format&fit=crop&q=60";
    }

    return "https://images.unsplash.com/photo-1526738549149-8e07eca6c147?w=600&auto=format&fit=crop&q=60";
  };

  const imageUrl = getSmartImage();
  const title = typeof p.product_title === 'string' ? p.product_title : (typeof p.title === 'string' ? p.title : 'Producto');
  const category = typeof p.product_category === 'string' ? p.product_category : (typeof p.category === 'string' ? p.category : 'General');
  const rating = typeof p.product_rating === 'number' ? p.product_rating : 4.5;
  const reviewsCount = typeof p.total_reviews === 'number' ? p.total_reviews : 120;
  const availability = typeof p.buy_box_availability === 'string' ? p.buy_box_availability : 'Disponible en stock';
  const delivery = typeof p.delivery_date === 'string' ? p.delivery_date : 'Envío estándar en 2 días hábiles';

  return (
    <div className="product-detail">
      <div className="product-detail__back">
        <Link to="/catalogo">← Volver al catálogo</Link>
      </div>

      <div className="product-detail__layout">
        <div className="product-detail__image-wrap">
          <img src={imageUrl} alt={title} className="product-detail__image" />
        </div>

        <div className="product-detail__info">
          <span className="product-detail__category">{category}</span>
          <h1>{title}</h1>

          <p className="product-detail__rating">★ {rating} · {reviewsCount} reseñas</p>

          <div className="product-detail__price-block">
            <strong>${Number(price).toFixed(2)}</strong>
            <span style={{ textDecoration: 'line-through', color: '#888', marginLeft: '10px', fontSize: '1rem' }}>
              ${Number(fakeOriginal).toFixed(2)}
            </span>
          </div>

          <div className="product-detail__meta">
            <div>
              <span>Disponibilidad</span>
              <strong>{availability}</strong>
            </div>
            <div>
              <span>Entrega</span>
              <strong>{delivery}</strong>
            </div>
          </div>

          <div className="product-detail__actions">
            {/* Enlace directo hacia tu Dashboard analítico */}
            <Link 
              to="/admin/dashboard" 
              className="product-detail__button product-detail__button--primary"
              style={{ textAlign: 'center', textDecoration: 'none', display: 'inline-block' }}
            >
              Ver métricas
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}