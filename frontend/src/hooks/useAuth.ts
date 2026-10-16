import { authApi } from "../api/endpoints/authApi";
import { useAuthStore } from "../store/authStore";

import type {
    LoginPayload,
    RegisterPayload,
} from "../types/auth";

let initializePromise: Promise<void> | null = null;

async function initializeAuth(): Promise<void> {
    if (!initializePromise) {
        initializePromise = (async () => {
            try {
                const user = await authApi.me();
                useAuthStore.getState().setUser(user);
            } catch {
                useAuthStore.getState().setUser(null);
            } finally {
                useAuthStore.getState().setInitialized(true);
            }
        })().finally(() => {
            initializePromise = null;
        });
    }

    return initializePromise;
}

export function useAuth() {
    const user = useAuthStore((state) => state.user);
    const initialized = useAuthStore(
        (state) => state.initialized
    );

    const login = async (payload: LoginPayload) => {
        await initializePromise;
        const user = await authApi.login(payload);

        useAuthStore.getState().setUser(user);
        useAuthStore.getState().setInitialized(true);

        return user;
    };

    const register = async (payload: RegisterPayload) => {
        await initializePromise;
        const user = await authApi.register(payload);
        useAuthStore.getState().setUser(user);
        useAuthStore.getState().setInitialized(true);
        return user;
    };

    const logout = async () => {
        await initializePromise;
        await authApi.logout();
        useAuthStore.getState().reset();
    };

    return {
        user,
        initialized,
        isAuthenticated: user !== null,
        login,
        register,
        logout,
        initialize: initializeAuth,
    };
}
