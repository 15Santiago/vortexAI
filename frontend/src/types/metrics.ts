export type CategoryMetric = {
  name: string;
  product_count: number;
  share_percent: number;
  average_rating: number | null;
  average_price: number | null;
};

export type PriceBucket = {
  label: string;
  product_count: number;
};

export type ReviewedProduct = {
  id: number;
  product_title: string;
  product_category: string;
  product_rating: number | null;
  total_reviews: number;
  discounted_price: number | null;
  original_price: number | null;
};

export type Metrics = {
  total_products: number;
  total_categories: number;
  average_rating: number | null;
  total_reviews: number;
  average_price: number | null;
  categories: CategoryMetric[];
  price_distribution: PriceBucket[];
  top_products: ReviewedProduct[];
};