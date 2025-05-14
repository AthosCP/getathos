import { writable, get } from 'svelte/store';

export interface User {
  email: string;
  user_id: string;
  role: string;
  tenant_id?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
}

function createAuthStore() {
  const { subscribe, set, update } = writable<AuthState>({
    user: null,
    token: null
  });

  return {
    subscribe,
    login: (user: User, token: string) => {
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
      set({ user, token });
    },
    logout: () => {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      set({ user: null, token: null });
    },
    init: () => {
      const token = localStorage.getItem('token');
      const userRaw = localStorage.getItem('user');
      if (token && userRaw) {
        try {
          const user = JSON.parse(userRaw);
          set({ user, token });
        } catch (e) {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          set({ user: null, token: null });
        }
      }
    },
    get token() {
      return get({ subscribe }).token;
    },
    get user() {
      return get({ subscribe }).user;
    }
  };
}

export const auth = createAuthStore(); 