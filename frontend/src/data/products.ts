import type { Product } from '../types/product';

export async function getProducts(): Promise<Product[]> {
  const response = await fetch('/data/products.json');

  if (!response.ok) {
    throw new Error('No se pudo cargar el catálogo de productos.');
  }

  return (await response.json()) as Product[];
}

export async function getProductById(id: string): Promise<Product | undefined> {
  const products = await getProducts();
  return products.find((product) => product.id === id);
}
