import axios, {
    type AxiosRequestConfig,
} from "axios";

import { httpClient } from "./httpClient";
import { useAuthStore } from "../store/authStore";

let refreshPromise: Promise<void> | null = null;

function refreshToken(): Promise<void> {
    if (!refreshPromise) {
        refreshPromise = httpClient
            .post("/api/auth/refresh")
            .then(() => undefined)
            .finally(() => {
                refreshPromise = null;
            });
    }

    return refreshPromise;
}

async function request<T>(config: AxiosRequestConfig): Promise<T> {
    try {
        const { data } = await httpClient.request<T>(config);
        return data;
    } catch (error) {
        if (!axios.isAxiosError(error) || error.response?.status !== 401) {
            throw error;
        }

        try {
            await refreshToken();
        } catch (refreshError) {
            if (axios.isAxiosError(refreshError) && refreshError.response?.status === 401) {
                useAuthStore.getState().reset();
            }
            throw refreshError;
        }

        try {
            const { data } = await httpClient.request<T>(config);
            return data;
        } catch (retryError) {
            if (axios.isAxiosError(retryError) && retryError.response?.status === 401) {
                useAuthStore.getState().reset();
            }
            throw retryError;
        }
    }
}

export const privateApi = {
    get: <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
        request<T>({...config, url, method: "GET"}),

    post: <T, D = unknown>(url: string, body?: D, config?: AxiosRequestConfig): Promise<T> =>
        request<T>({...config, url, method: "POST", data: body}),

    put: <T, D = unknown>(url: string, body?: D, config?: AxiosRequestConfig): Promise<T> =>
        request<T>({...config, url, method: "PUT", data: body}),

    patch: <T, D = unknown>(url: string, body?: D, config?: AxiosRequestConfig): Promise<T> =>
        request<T>({...config, url, method: "PATCH", data: body}),

    delete: <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
        request<T>({...config, url, method: "DELETE"}),
};
