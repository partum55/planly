import Store from 'electron-store';

const store = new Store({ name: 'planly-auth' });

const KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
} as const;

export class AuthStore {
  getAccessToken(): string | null {
    return (store.get(KEYS.ACCESS_TOKEN) as string) ?? null;
  }

  getRefreshToken(): string | null {
    return (store.get(KEYS.REFRESH_TOKEN) as string) ?? null;
  }

  setTokens(accessToken: string, refreshToken: string): void {
    store.set(KEYS.ACCESS_TOKEN, accessToken);
    store.set(KEYS.REFRESH_TOKEN, refreshToken);
  }

  clear(): void {
    store.delete(KEYS.ACCESS_TOKEN);
    store.delete(KEYS.REFRESH_TOKEN);
  }

  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }
}
