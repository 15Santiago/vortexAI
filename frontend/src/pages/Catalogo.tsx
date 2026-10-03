import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

interface Producto {
  id?: number;
  product_title: string;
  discounted_price: number | string;
  product_image_url?: string;
  image_url?: string;
  product_rating?: number;
}

export default function Catalogo() {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [busqueda, setBusqueda] = useState('');
  const [categoriaSel, setCategoriaSel] = useState('');

  useEffect(() => {
    // Consulta directa al backend
    fetch('http://127.0.0.1:8000/api/productos')
      .then((res) => res.json())
      .then((data) => {
        // Garantiza la lectura si vienen como [...] o { productos: [...] }
        const lista = Array.isArray(data) ? data : (data.productos || data.data || []);
        setProductos(lista);
      })
      .catch((err) => console.error('Error al cargar productos:', err));
  }, []);

  // Filtrado local en el cliente por término de búsqueda
  const productosFiltrados = productos.filter((prod) =>
    prod.product_title?.toLowerCase().includes(busqueda.toLowerCase())
  );

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
        {/* Filtros */}
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

        {/* Listado de Productos */}
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
            Resultados encontrados: <strong>{productosFiltrados.length}</strong> productos
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '20px' }}>
            {productosFiltrados.map((prod: Producto, index: number) => {
              // Determina la URL de la imagen comprobando todas las opciones posibles
              const imageUrl = prod.product_image_url || prod.image_url || 'https://via.placeholder.com/200?text=Sin+Imagen';

              return (
                <div key={prod.id || index} style={{ 
                  background: '#1e293b', 
                  border: '1px solid #334155', 
                  borderRadius: '12px', 
                  padding: '15px', 
                  display: 'flex', 
                  flexDirection: 'column', 
                  justifyContent: 'space-between'
                }}>
                  <div style={{ 
                    background: '#ffffff', 
                    borderRadius: '8px', 
                    padding: '12px', 
                    marginBottom: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '160px'
                  }}>
                    <img 
                      src={imageUrl} 
                      alt={prod.product_title} 
                      style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} 
                      onError={(e) => {
                        // Imagen de respaldo en caso de que falle la carga del link
                        (e.target as HTMLImageElement).src = 'https://via.placeholder.com/200?text=Sin+Imagen';
                      }}
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
                  <Link 
                    to={`/producto/${prod.id || index}`} 
                    state={{ producto: prod }}
                    style={{ 
                      textAlign: 'center', 
                      background: '#2563eb', 
                      color: '#ffffff',
                      padding: '10px', 
                      borderRadius: '8px', 
                      textDecoration: 'none', 
                      fontWeight: '600',
                      fontSize: '13px'
                    }}
                  >
                    Ver Detalle
                  </Link>
                </div>
              );
            })}
          </div>
        </main>
      </div>
    </div>
  );
}