import type { Product } from '../types/product';
import { API_BASE_URL } from './api';

export async function getProducts(): Promise<Product[]> {
  const response = await fetch(`${API_BASE_URL}/api/productos`);

  if (!response.ok) {
    throw new Error('No se pudo cargar el catálogo de productos.');
  }

  const payload = (await response.json()) as { productos?: Product[] };
  return payload.productos ?? [];
}

export async function getProductById(id: string): Promise<Product | undefined> {
  const products = await getProducts();
  return products.find((product) => product.id === id);
}
