export default function Carrito() {
  return (
    <div style={{ padding: '30px 20px', fontFamily: 'sans-serif', color: '#1a1a1a', maxWidth: '1000px', margin: '0 auto' }}>
      <h2 style={{ textAlign: 'center', marginBottom: '25px', fontSize: '24px' }}>Tu carrito de compras</h2>

      {/* Indicador de pasos */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginBottom: '35px', flexWrap: 'wrap' }}>
        <span style={{ padding: '8px 18px', background: '#e0e0e0', border: '1px solid #111', borderRadius: '20px', fontSize: '13px', fontWeight: 'bold' }}>1. Carrito</span>
        <span style={{ padding: '8px 18px', border: '1px solid #ccc', borderRadius: '20px', fontSize: '13px', color: '#777' }}>2. Envío</span>
        <span style={{ padding: '8px 18px', border: '1px solid #ccc', borderRadius: '20px', fontSize: '13px', color: '#777' }}>3. Pago</span>
        <span style={{ padding: '8px 18px', border: '1px solid #ccc', borderRadius: '20px', fontSize: '13px', color: '#777' }}>4. Confirmación</span>
      </div>

      <div style={{ display: 'flex', gap: '30px', flexWrap: 'wrap' }}>
        {/* Lista de productos */}
        <div style={{ flex: '2 1 500px', border: '1px solid #e0e0e0', borderRadius: '12px', padding: '20px', background: '#fff' }}>
          <h3 style={{ marginBottom: '15px', fontSize: '16px' }}>Productos (3)</h3>
          {[1, 2, 3].map((item) => (
            <div key={item} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #eee', padding: '15px 0' }}>
              <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
                <div style={{ width: '50px', height: '50px', background: '#f0f0f2', borderRadius: '6px' }}></div>
                <div>
                  <p style={{ margin: 0, fontWeight: 'bold', fontSize: '14px' }}>Producto {item}</p>
                  <p style={{ margin: '3px 0 0 0', color: '#666', fontSize: '13px' }}>$ 000.000</p>
                </div>
              </div>
              <div style={{ border: '1px solid #ccc', padding: '4px 10px', borderRadius: '6px' }}>- 1 +</div>
              <button style={{ color: '#e74c3c', border: 'none', background: 'none', fontSize: '13px' }}>Eliminar</button>
            </div>
          ))}
        </div>

        {/* Resumen */}
        <div style={{ flex: '1 1 280px', border: '1px solid #e0e0e0', borderRadius: '12px', padding: '20px', background: '#fff', height: 'fit-content' }}>
          <h3 style={{ marginBottom: '15px', fontSize: '16px' }}>Resumen del pedido</h3>
          <div style={{ display: 'flex', justifyContent: 'space-between', margin: '8px 0', fontSize: '14px', color: '#555' }}><span>Subtotal</span><span>$ 000.000</span></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', margin: '8px 0', fontSize: '14px', color: '#555' }}><span>Envío</span><span>$ 000.000</span></div>
          <hr style={{ border: 'none', borderTop: '1px solid #eee', margin: '15px 0' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', margin: '15px 0', fontWeight: 'bold', fontSize: '16px' }}><span>Total</span><span>$ 000.000</span></div>
          <button style={{ width: '100%', padding: '12px', background: '#fff', border: '1px solid #111', borderRadius: '8px', fontWeight: 'bold' }}>
            Ir a pagar
          </button>
        </div>
      </div>
    </div>
  );
}