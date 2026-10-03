import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import type { Product } from '../types/product';
import DetalleProducto from './DetalleProducto';
import './ProductDetailPage.css';

export default function ProductDetailPage() {
  const { id } = useParams();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadProduct() {
      try {
        const response = await fetch('http://localhost:8000/api/productos');
        const data = await response.json();

        let products: Product[] = [];
        if (Array.isArray(data)) {
          products = data;
        } else if (data && typeof data === 'object') {
          const payload = data as { productos?: Product[]; data?: Product[] };
          products = payload.productos ?? payload.data ?? [];
        }

        const found = products.find((item) => {
          const pItem = item as Record<string, unknown>;
          const itemId = String(pItem.id ?? pItem._id ?? '');
          return itemId === String(id);
        });

        if (found) {
          setProduct(found);
        } else if (products.length > 0) {
          setProduct(products[0]);
        } else {
          setProduct(null);
        }

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
        <a href="/catalogo">Volver al catálogo</a>
      </div>
    );
  }

  // Renderizamos el componente visual y le pasamos el producto
  return <DetalleProducto product={product} />;
};