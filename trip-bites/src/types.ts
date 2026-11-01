import type { Rankings } from './ranking.ts';

export interface Trip {
  id: string;
  name: string;
  place: string;
  startDate: string;
  endDate: string;
  createdAt: number;
}

export interface Category {
  id: string;
  tripId: string;
  name: string;
  createdAt: number;
  rankings: Rankings;
}

export interface Item {
  id: string;
  tripId: string;
  categoryId: string;
  name: string;
  notes: string;
  /** Where you had it (restaurant, stall, city…). */
  place: string;
  imageId: string | null;
  createdAt: number;
}

export interface ImageRecord {
  id: string;
  full: Blob;
  thumb: Blob;
}

export const DEFAULT_CATEGORIES = ['Foods', 'Teas', 'Drinks', 'Desserts'];
export const SUGGESTED_CATEGORIES = ['Foods', 'Teas', 'Drinks', 'Desserts', 'Snacks', 'Coffee', 'Street food', 'Breakfast'];
