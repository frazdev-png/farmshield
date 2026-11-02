import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import type { User, LoginPayload, RegisterPayload } from '../types';
import { api, tokenStorage } from '../services/api';
import { AuthContext } from './auth-context-def';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(tokenStorage.get());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Restore authenticated session on app initialization
  useEffect(() => {
    let isMounted = true;

    const restoreSession = async () => {
      const storedToken = tokenStorage.get();
      if (!storedToken) {
        if (isMounted) setIsLoading(false);
        return;
      }

      try {
        const currentUser = await api.auth.getMe();
        if (isMounted) {
          setUser(currentUser);
          setToken(storedToken);
        }
      } catch {
        // Token expired or invalid
        tokenStorage.remove();
        if (isMounted) {
          setUser(null);
          setToken(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    restoreSession();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (payload: LoginPayload): Promise<User> => {
    setError(null);
    try {
      const authRes = await api.auth.login(payload);
      tokenStorage.set(authRes.access_token);
      setToken(authRes.access_token);
      setUser(authRes.user);
      return authRes.user;
    } catch (err: any) {
      const msg = err.message || 'Login failed. Please check your credentials.';
      setError(msg);
      throw err;
    }
  };

  const register = async (payload: RegisterPayload): Promise<User> => {
    setError(null);
    try {
      const registeredUser = await api.auth.register(payload);
      return registeredUser;
    } catch (err: any) {
      const msg = err.message || 'Registration failed. Please check form inputs.';
      setError(msg);
      throw err;
    }
  };

  const logout = () => {
    api.auth.logout();
    setToken(null);
    setUser(null);
    setError(null);
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        error,
        login,
        register,
        logout,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
