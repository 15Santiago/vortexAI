import { Link } from 'react-router-dom';
import type { Product } from '../../types/product';
import './ProductCard.css';

type ProductCardProps = {
  product: Product;
};

export default function ProductCard({ product }: ProductCardProps) {
  const p = product as Record<string, unknown>;
  
  // Obtenemos un identificador numérico seguro
  const rawId = p.id ?? p._id ?? 1;
  const numericId = typeof rawId === 'number' ? rawId : parseInt(String(rawId), 10) || 1;

  const discountedPrice = typeof p.discounted_price === 'number' ? p.discounted_price : null;
  const standardPrice = typeof p.price === 'number' ? p.price : null;
  const originalPrice = typeof p.original_price === 'number' ? p.original_price : null;
  
  const price = discountedPrice ?? standardPrice ?? originalPrice ?? (numericId * 15.99 + 10);

  // Función inteligente ultra precisa para evitar confusiones de categoría
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
    
    // 1. Validaciones muy específicas primero (para evitar falsos positivos con TV & Display)
    if (text.includes("watch") || text.includes("smartwatch")) {
      return "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&auto=format&fit=crop&q=60";
    }
    if (text.includes("roku") || text.includes("fire stick") || text.includes("chromecast") || text.includes("streaming stick") || text.includes("box")) {
      return "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&auto=format&fit=crop&q=60"; // dispositivo de streaming / control remoto
    }
    if (text.includes("mount") || text.includes("bracket") || text.includes("wall") || text.includes("soporte")) {
      return "https://images.unsplash.com/photo-1593784991095-a205069470b6?w=400&auto=format&fit=crop&q=60"; // soporte de TV / pantalla
    }
    if (text.includes("airpod") || text.includes("headphone") || text.includes("audio") || text.includes("sound") || text.includes("earbud")) {
      return "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&auto=format&fit=crop&q=60";
    }
    if (text.includes("phone") || text.includes("iphone") || text.includes("mobile") || text.includes("smartphone")) {
      return "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400&auto=format&fit=crop&q=60";
    }
    if (text.includes("laptop") || text.includes("computer") || text.includes("pc") || text.includes("macbook")) {
      return "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400&auto=format&fit=crop&q=60";
    }
    if (text.includes("shoe") || text.includes("sneaker") || text.includes("zapatilla")) {
      return "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&auto=format&fit=crop&q=60";
    }
    if (text.includes("camera") || text.includes("camara")) {
      return "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=400&auto=format&fit=crop&q=60";
    }

    // Imagen por defecto genérica de tecnología
    return "https://images.unsplash.com/photo-1526738549149-8e07eca6c147?w=400&auto=format&fit=crop&q=60";
  };

  const imageUrl = getSmartImage();
  const title = typeof p.product_title === 'string' ? p.product_title : (typeof p.title === 'string' ? p.title : 'Producto');
  const category = typeof p.product_category === 'string' ? p.product_category : (typeof p.category === 'string' ? p.category : 'General');
  const rating = typeof p.product_rating === 'number' ? p.product_rating : 4.5;
  const reviews = typeof p.total_reviews === 'number' ? p.total_reviews : 120;
  const productId = p.id ?? p._id ?? '';

  return (
    <article className="product-card">
      <div className="product-card__image-wrap">
        <img
          src={imageUrl}
          alt={title}
          style={{
            width: '100%',
            height: '200px',
            objectFit: 'cover',
            display: 'block',
            backgroundColor: '#f0f0f0'
          }}
        />
      </div>

      <div className="product-card__content">
        <span className="product-card__category">{category}</span>
        <h3>{title}</h3>

        <div className="product-card__meta">
          <span className="product-card__rating">★ {rating}</span>
          <span className="product-card__reviews">{reviews} reseñas</span>
        </div>

        <div className="product-card__price-row">
          <strong style={{ fontSize: '1.2rem', color: '#2563eb' }}>
            ${Number(price).toFixed(2)}
          </strong>
        </div>
      </div>

      <Link to={`/producto/${productId}`} className="product-card__button">
        Ver detalle
      </Link>
    </article>
  )
};