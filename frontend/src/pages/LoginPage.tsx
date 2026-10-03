import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      const response = await fetch('http://localhost:8000/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (data.success) {
        // Guardamos los datos del usuario en el almacenamiento local
        localStorage.setItem('user', JSON.stringify(data.user));
        
        // Redirigir al panel de administración / dashboard
        navigate('/admin/dashboard'); 
      } else {
        setError(data.message || 'Credenciales incorrectas');
      }
    } catch {
      setError('Error de conexión con el servidor');
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#0b0f19' }}>
      <form onSubmit={handleLogin} style={{ padding: '2rem', background: '#ffffff', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', width: '100%', maxWidth: '400px' }}>
        <h2 style={{ marginBottom: '1.5rem', color: '#111827', textAlign: 'center' }}>Iniciar Sesión - VortexAI</h2>
        
        {error && <p style={{ color: 'red', marginBottom: '1rem', fontSize: '14px', textAlign: 'center' }}>{error}</p>}
        
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: '#374151', fontWeight: '500' }}>Correo electrónico:</label>
          <input 
            type="email" 
            value={email} 
            onChange={(e) => setEmail(e.target.value)} 
            required 
            style={{ width: '100%', padding: '10px', boxSizing: 'border-box', border: '1px solid #d1d5db', borderRadius: '4px' }}
          />
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: '#374151', fontWeight: '500' }}>Contraseña:</label>
          <input 
            type="password" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)} 
            required 
            style={{ width: '100%', padding: '10px', boxSizing: 'border-box', border: '1px solid #d1d5db', borderRadius: '4px' }}
          />
        </div>

        <button type="submit" style={{ width: '100%', padding: '10px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '4px', fontWeight: 'bold', cursor: 'pointer' }}>
          Ingresar
        </button>
      </form>
    </div>
  );
};