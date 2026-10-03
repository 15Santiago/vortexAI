import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import type { Product } from '../types/product';
import { API_BASE_URL } from '../data/api';
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
        const payload = (await response.json()) as { productos?: Product[] };
        const products = payload.productos ?? [];
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
        <a href="/catalogo">Volver al catálogo</a>
      </div>
    );
  }

  // Renderizamos el componente visual y le pasamos el producto
  return <DetalleProducto product={product} />;
};