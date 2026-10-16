import axios from "axios";

export const httpClient = axios.create({
    baseURL: import.meta.env.VITE_API_URL || "/",
    withCredentials: true,
    timeout: 15000,
    headers: {
        Accept: "application/json",
    },
});