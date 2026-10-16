
import { privateApi } from "../privateApi";
import type { User, RegisterPayload, LoginPayload } from "../../types/auth";
import { publicApi } from "../publicApi";


export const authApi = {
    login(payload: LoginPayload): Promise<User> {
        return publicApi.post<User>("/api/auth/login", payload);
    },

    register(payload: RegisterPayload): Promise<User> {
        return publicApi.post<User>("/api/auth/register", payload);
    },

    refresh(): Promise<void> {
        return publicApi.post<{ message: string }>("/api/auth/refresh").then(() => undefined);
    },

    me(): Promise<User> {
        return privateApi.get<User>("/api/auth/me");
    },

    logout(): Promise<void> {
        return publicApi.post<{ message: string }>("/api/auth/logout").then(() => undefined);
    },
};
