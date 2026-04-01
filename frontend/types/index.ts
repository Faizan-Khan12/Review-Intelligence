// frontend/types/index.ts - COMPLETE REPLACEMENT
export interface ProductInfo {
  title: string | null;
  image_url: string | null;
  asin: string | null;
  average_rating: number | null;
}

export interface Review {
  title: string | null;
  text: string | null;
  stars: number | null;
  date: string | null;
  verified: boolean | null;
  sentiment: string | null;
  sentiment_score: number | null;
  sentiment_confidence?: number | null;
  verified_purchase?: boolean | null;
}

export interface ReviewSamples {
  positive: Review[];
  negative: Review[];
  neutral: Review[];
}

export interface Summaries {
  overall: string;
  positive_highlights: string;
  negative_highlights: string;
}

export interface Keyword {
  word: string;
  frequency: number;
}

export interface Theme {
  theme: string;
  mentions: number;
  sentiment: string;
}

export interface AnalysisResult {
  success: boolean;
  error?: string;
  product_info: ProductInfo | null;
  asin: string;
  total_reviews: number;
  average_rating: number;
  rating_distribution: Record<string, number>;
  sentiment_distribution: Record<string, number> | null;
  reviews: Review[];
  review_samples: ReviewSamples | null;
  ai_enabled: boolean;
  top_keywords: Keyword[] | null;
  themes: (string | Theme)[] | null;
  emotions: Record<string, number> | null;
  summaries: Summaries | null;
  insights: any;
  timestamp: string;
  processing_time: number | null;
  data_source: string;
  from_cache?: boolean;
}

export interface CachedAnalysisResult {
  key: string;
  asin: string;
  country: string;
  max_reviews: number;
  enable_ai: boolean;
  total_reviews: number;
  average_rating: number;
  timestamp: string | null;
  data_source: string;
  analysis?: AnalysisResult;
}

export const MAX_REVIEWS_LIMIT = 100;
export const DEFAULT_MAX_REVIEWS = 50;

export const SUPPORTED_COUNTRIES = [
  { code: 'US', label: '🇺🇸 United States' },
  { code: 'UK', label: '🇬🇧 United Kingdom' },
  { code: 'IN', label: '🇮🇳 India' },
  { code: 'CA', label: '🇨🇦 Canada' },
  { code: 'DE', label: '🇩🇪 Germany' },
  { code: 'FR', label: '🇫🇷 France' },
  { code: 'JP', label: '🇯🇵 Japan' },
  { code: 'AU', label: '🇦🇺 Australia' },
  { code: 'IT', label: '🇮🇹 Italy' },
  { code: 'ES', label: '🇪🇸 Spain' },
] as const;

export const SENTIMENT_COLORS = {
  positive: '#10b981',
  neutral: '#f59e0b',
  negative: '#ef4444',
} as const;

export const EMOTION_COLORS = {
  joy: '#10b981',
  trust: '#3b82f6',
  anticipation: '#8b5cf6',
  surprise: '#ec4899',
  sadness: '#64748b',
  fear: '#f59e0b',
  anger: '#ef4444',
  disgust: '#b45309',
} as const;

export const RATING_COLORS = {
  '5': '#10b981',
  '4': '#84cc16',
  '3': '#f59e0b',
  '2': '#fb923c',
  '1': '#ef4444',
} as const;
