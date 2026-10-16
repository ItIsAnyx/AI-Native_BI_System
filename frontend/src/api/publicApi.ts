import type { AxiosRequestConfig } from "axios";
import { httpClient } from "./httpClient";

export const publicApi = {
    get: <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
        httpClient.get<T>(url, config).then(res => res.data),

    post: <T, D = unknown>(url: string, body?: D, config?: AxiosRequestConfig): Promise<T> =>
        httpClient.post<T>(url, body, config).then(res => res.data),

    put: <T, D = unknown>(url: string, body?: D, config?: AxiosRequestConfig): Promise<T> =>
        httpClient.put<T>(url, body, config).then(res => res.data),

    patch: <T, D = unknown>(url: string, body?: D, config?: AxiosRequestConfig): Promise<T> =>
        httpClient.patch<T>(url, body, config).then(res => res.data),

    delete: <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
        httpClient.delete<T>(url, config).then(res => res.data),
};
