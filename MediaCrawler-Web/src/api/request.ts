import axios, { type AxiosError, type AxiosRequestConfig, type AxiosResponse } from 'axios';
import { message } from 'antd';

/** 统一 HTTP 客户端：开发走 Vite 代理 /api，生产读 VITE_API_BASE_URL */
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 60_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

request.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<{ detail?: string; message?: string }>) => {
    const msg =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      '请求失败';
    if (error.response?.status !== 401) {
      message.error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return Promise.reject(error);
  },
);

export async function httpGet<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const { data } = await request.get<T>(url, config);
  return data;
}

export async function httpPost<T>(
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const { data } = await request.post<T>(url, body, config);
  return data;
}

export async function httpDelete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const { data } = await request.delete<T>(url, config);
  return data;
}

export default request;
