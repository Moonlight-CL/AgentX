import { create } from 'zustand';
import { configAPI } from '../services/api';

export interface UseCaseItem {
  key: string;
  key_display_name: string;
  value: string;
  record_id?: string;
  desc?: string;
  tags?: string[];
}

export interface UseCaseCategory {
  key: string;
  key_display_name: string;
  children: UseCaseCategory[];
}

interface UseCaseState {
  // Categories
  primaryCategories: UseCaseCategory[];
  secondaryCategories: UseCaseCategory[];
  selectedPrimaryCategory: string | null;
  selectedSecondaryCategory: string | null;
  
  // Use case items
  useCaseItems: UseCaseItem[];
  loading: boolean;
  error: string | null;
  
  // Actions
  setPrimaryCategories: (categories: UseCaseCategory[]) => void;
  setSecondaryCategories: (categories: UseCaseCategory[]) => void;
  setSelectedPrimaryCategory: (category: string | null) => void;
  setSelectedSecondaryCategory: (category: string | null) => void;
  setUseCaseItems: (items: UseCaseItem[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  
  // API Actions
  fetchPrimaryCategories: () => Promise<void>;
  fetchSecondaryCategories: (parent: string) => Promise<void>;
  fetchUseCaseItems: (parent: string) => Promise<void>;
}

export const useUseCaseStore = create<UseCaseState>((set) => ({
  // Initial state
  primaryCategories: [],
  secondaryCategories: [],
  selectedPrimaryCategory: null,
  selectedSecondaryCategory: null,
  useCaseItems: [],
  loading: false,
  error: null,
  
  // Actions
  setPrimaryCategories: (categories) => set({ primaryCategories: categories }),
  setSecondaryCategories: (categories) => set({ secondaryCategories: categories }),
  setSelectedPrimaryCategory: (category) => set({ selectedPrimaryCategory: category }),
  setSelectedSecondaryCategory: (category) => set({ selectedSecondaryCategory: category }),
  setUseCaseItems: (items) => set({ useCaseItems: items }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  
  // API Actions
  fetchPrimaryCategories: async () => {
    try {
      set({ loading: true, error: null });
      
      // Get the use_cases root category
      const response = await configAPI.getConfig('use_cases');
      
      if (response.success && response.data) {
        // Convert to category format
        const category: UseCaseCategory = {
          key: response.data.key,
          key_display_name: response.data.key_display_name || response.data.key,
          children: []
        };
        
        set({ primaryCategories: [category] });
      }
    } catch (error) {
      console.error('Error fetching primary categories:', error);
      set({ error: 'Failed to fetch primary categories' });
    } finally {
      set({ loading: false });
    }
  },
  
  fetchSecondaryCategories: async (parent: string) => {
    try {
      set({ loading: true, error: null });
      
      // Get secondary categories under the parent
      const response = await configAPI.getConfigsByParent(parent);
      
      if (response.success) {
        // Convert to category format
        const categories: UseCaseCategory[] = response.data
          .filter(item => item.type === 'category')
          .map(item => ({
            key: item.key,
            key_display_name: item.key_display_name || item.key,
            children: []
          }));
        
        set({ secondaryCategories: categories });
      }
    } catch (error) {
      console.error('Error fetching secondary categories:', error);
      set({ error: 'Failed to fetch secondary categories' });
    } finally {
      set({ loading: false });
    }
  },
  
  fetchUseCaseItems: async (parent: string) => {
    try {
      set({ loading: true, error: null });
      
      // Get use case items under the parent
      const response = await configAPI.getConfigsByParent(parent);
      
      if (response.success) {
        // Parse the use case items
        const items: UseCaseItem[] = response.data
          .filter(item => item.type === 'item')
          .map(item => {
            let parsedValue: any = {};
            try {
              parsedValue = JSON.parse(item.value);
            } catch (e) {
              console.warn('Failed to parse value for item:', item.key);
            }
            
            return {
              key: item.key,
              key_display_name: item.key_display_name || item.key,
              value: item.value,
              record_id: parsedValue.record_id,
              desc: parsedValue.desc,
              tags: parsedValue.tags || []
            };
          });
        
        set({ useCaseItems: items });
      }
    } catch (error) {
      console.error('Error fetching use case items:', error);
      set({ error: 'Failed to fetch use case items' });
    } finally {
      set({ loading: false });
    }
  }
}));
