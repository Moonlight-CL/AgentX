import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface User {
  user_id: string;
  username: string;
  email?: string;
  status: string;
}

interface UserState {
  // Authentication state
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  
  // Actions
  login: (user: User, token: string) => void;
  logout: () => void;
  updateUser: (user: User) => void;
  setToken: (token: string) => void;
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      // Initial state
      isAuthenticated: false,
      user: null,
      token: null,
      
      // Actions
      login: (user: User, token: string) => {
        set({
          isAuthenticated: true,
          user,
          token
        });
      },
      
      logout: () => {
        set({
          isAuthenticated: false,
          user: null,
          token: null
        });
      },
      
      updateUser: (user: User) => {
        set({ user });
      },
      
      setToken: (token: string) => {
        set({ token });
      }
    }),
    {
      name: 'user-storage', // unique name for localStorage key
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        user: state.user,
        token: state.token
      })
    }
  )
);
