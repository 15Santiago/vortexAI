import type { Product } from '../types/product';
import { API_BASE_URL } from './api';

export async function getProducts(): Promise<Product[]> {
  const response = await fetch(`${API_BASE_URL}/api/productos`);

  if (!response.ok) {
    throw new Error('No se pudo cargar el catálogo de productos.');
  }

  const data = await response.json();
  
  // Soporta tanto si la API devuelve un arreglo plano como si viene dentro de { productos: [...] }
  return Array.isArray(data) ? data : (data.productos ?? []);
}

export async function getProductById(id: string): Promise<Product | undefined> {
  const products = await getProducts();
  return products.find((p) => String(p.id) === String(id));
}