import { useEffect, useState } from 'react';
import { useParams, useLocation, Link } from 'react-router-dom';

interface Producto {
  product_title: string;
  discounted_price: number;
  product_image_url: string;
  product_rating: number;
}

export default function DetalleProducto() {
  const { id } = useParams();
  const location = useLocation();
  const [producto, setProducto] = useState<Producto | null>(location.state?.producto || null);
  const [cargando, setCargando] = useState(!location.state?.producto);

  useEffect(() => {
    if (!producto) {
      fetch('http://127.0.0.1:8000/api/productos')
        .then((res) => res.json())
        .then((data) => {
          const lista: Producto[] = data.productos || [];
          const index = parseInt(id || '0', 10);
          setProducto(lista[index] || lista[0] || null);
          setCargando(false);
        })
        .catch(() => setCargando(false));
    }
  }, [id, producto]);

  if (cargando) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#94a3b8' }}>
        Cargando detalles del producto...
      </div>
    );
  }

  if (!producto) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#f8fafc' }}>
        <h2>No se encontró información del producto.</h2>
        <Link to="/catalogo" style={{ color: '#38bdf8', textDecoration: 'underline' }}>Volver al catálogo</Link>
      </div>
    );
  }

  return (
    <div style={{ padding: '30px 20px', fontFamily: 'sans-serif', color: '#f8fafc', maxWidth: '1000px', margin: '0 auto' }}>
      {/* Botón superior limpio que solo mantiene Inicio */}
      <p style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '20px' }}>
        <Link to="/catalogo" style={{ color: '#38bdf8', textDecoration: 'none', fontWeight: '500' }}>
          ← Inicio
        </Link>
      </p>

      <div style={{ display: 'flex', gap: '40px', flexWrap: 'wrap', alignItems: 'flex-start' }}>
        {/* Contenedor claro para la imagen */}
        <div style={{ 
          flex: '1 1 350px', 
          height: '350px', 
          background: '#f8fafc', 
          border: '1px solid #334155', 
          borderRadius: '12px', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center', 
          padding: '20px'
        }}>
          <img 
            src={producto.product_image_url} 
            alt={producto.product_title} 
            style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
          />
        </div>

        {/* Información del Producto */}
        <div style={{ flex: '1 1 400px' }}>
          <h1 style={{ fontSize: '24px', color: '#f8fafc', marginBottom: '10px', lineHeight: '1.3' }}>
            {producto.product_title}
          </h1>
          
          <p style={{ color: '#f59e0b', fontSize: '14px', marginBottom: '15px' }}>
            ★ {producto.product_rating || '4.5'} <span style={{ color: '#94a3b8' }}>(Calificación del producto)</span>
          </p>

          <h2 style={{ fontSize: '32px', color: '#38bdf8', marginBottom: '20px' }}>
            $ {producto.discounted_price}
          </h2>
          
          <div style={{ 
            border: '1px solid #334155', 
            background: '#1e293b', 
            padding: '8px 16px', 
            borderRadius: '8px', 
            width: 'fit-content', 
            marginBottom: '25px', 
            display: 'flex', 
            gap: '15px', 
            alignItems: 'center',
            color: '#f8fafc'
          }}>
            <span style={{ fontSize: '14px', color: '#94a3b8' }}>Cantidad:</span>
            <button style={{ border: 'none', background: 'none', color: '#f8fafc', fontSize: '18px', cursor: 'pointer' }}>-</button>
            <strong>1</strong>
            <button style={{ border: 'none', background: 'none', color: '#f8fafc', fontSize: '18px', cursor: 'pointer' }}>+</button>
          </div>

          <div style={{ display: 'flex', gap: '15px' }}>
            <Link to="/carrito" style={{ 
              flex: 1, 
              textAlign: 'center', 
              padding: '12px', 
              border: '1px solid #3b82f6', 
              borderRadius: '8px', 
              color: '#38bdf8', 
              background: 'transparent', 
              fontWeight: 'bold' 
            }}>
              Agregar al carrito
            </Link>
            <Link to="/carrito" style={{ 
              flex: 1, 
              textAlign: 'center', 
              padding: '12px', 
              background: '#2563eb', 
              border: '1px solid #2563eb', 
              borderRadius: '8px', 
              color: '#ffffff', 
              fontWeight: 'bold' 
            }}>
              Comprar ahora
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}