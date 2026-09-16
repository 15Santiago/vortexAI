import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

interface Producto {
  product_title: string;
  discounted_price: number;
  product_image_url: string;
  product_rating: number;
}

export default function Catalogo() {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [busqueda, setBusqueda] = useState('');
  const [categoriaSel, setCategoriaSel] = useState('');

  useEffect(() => {
    // Petición a la API pasando parámetros de búsqueda y filtro
    const params = new URLSearchParams();
    if (busqueda) params.append('q', busqueda);
    if (categoriaSel) params.append('categoria', categoriaSel);

    fetch(`http://127.0.0.1:8000/api/productos?${params.toString()}`)
      .then((res) => res.json())
      .then((data) => setProductos(data.productos || []))
      .catch((err) => console.error('Error al cargar productos:', err));
  }, [busqueda, categoriaSel]);

  return (
    <div>
      {/* Buscador Interactivo */}
      <div style={{ marginBottom: '25px' }}>
        <input 
          type="text" 
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder="🔍 Buscar productos por nombre, marca o categoría..." 
          style={{ 
            width: '100%', 
            padding: '14px 20px', 
            borderRadius: '12px', 
            border: '1px solid #334155', 
            outline: 'none',
            fontSize: '15px',
            background: '#1e293b',
            color: '#f8fafc'
          }}
        />
      </div>

      <div style={{ display: 'flex', gap: '25px', alignItems: 'flex-start' }}>
        {/* Filtros Activos */}
        <aside style={{ 
          width: '230px', 
          background: '#1e293b', 
          padding: '20px', 
          borderRadius: '12px', 
          border: '1px solid #334155'
        }}>
          <h4 style={{ color: '#f8fafc', marginBottom: '15px', fontSize: '15px', fontWeight: 'bold' }}>FILTROS</h4>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <label style={{ color: '#94a3b8', fontSize: '14px', cursor: 'pointer', display: 'flex', gap: '8px' }}>
              <input 
                type="radio" 
                name="cat" 
                value="" 
                checked={categoriaSel === ''} 
                onChange={() => setCategoriaSel('')}
                style={{ accentColor: '#3b82f6' }}
              />
              Todas las categorías
            </label>
            {['Electrónica', 'Accesorios', 'Audio', 'Cables'].map((cat, i) => (
              <label key={i} style={{ color: '#94a3b8', fontSize: '14px', cursor: 'pointer', display: 'flex', gap: '8px' }}>
                <input 
                  type="radio" 
                  name="cat" 
                  value={cat} 
                  checked={categoriaSel === cat} 
                  onChange={() => setCategoriaSel(cat)}
                  style={{ accentColor: '#3b82f6' }}
                />
                {cat}
              </label>
            ))}
          </div>
        </aside>

        {/* Listado Filtrado */}
        <main style={{ flex: 1 }}>
          <div style={{ 
            background: 'rgba(59, 130, 246, 0.1)', 
            border: '1px solid rgba(59, 130, 246, 0.3)', 
            color: '#93c5fd',
            padding: '14px 20px', 
            borderRadius: '10px', 
            marginBottom: '20px',
            fontWeight: '500',
            fontSize: '14px'
          }}>
            Resultados encontrados: <strong>{productos.length}</strong> productos
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '20px' }}>
            {productos.map((prod: Producto, index: number) => (
              <div key={index} style={{ 
                background: '#1e293b', 
                border: '1px solid #334155', 
                borderRadius: '12px', 
                padding: '15px', 
                display: 'flex', 
                flexDirection: 'column', 
                justifyContent: 'space-between'
              }}>
                <div style={{ 
                  background: '#f8fafc', 
                  borderRadius: '8px', 
                  padding: '12px', 
                  marginBottom: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '160px'
                }}>
                  <img 
                    src={prod.product_image_url} 
                    alt={prod.product_title} 
                    style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} 
                  />
                </div>
                <div>
                  <h4 style={{ fontSize: '13px', color: '#cbd5e1', lineHeight: '1.4', height: '38px', overflow: 'hidden', margin: '0 0 10px 0' }}>
                    {prod.product_title}
                  </h4>
                  <p style={{ margin: '0 0 12px 0', fontWeight: 'bold', fontSize: '18px', color: '#38bdf8' }}>
                    $ {prod.discounted_price}
                  </p>
                </div>
                <Link to="/producto/1024" style={{ 
                  textAlign: 'center', 
                  background: '#2563eb', 
                  color: '#ffffff',
                  padding: '10px', 
                  borderRadius: '8px', 
                  textDecoration: 'none', 
                  fontWeight: '600',
                  fontSize: '13px'
                }}>
                  Ver Detalle
                </Link>
              </div>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}