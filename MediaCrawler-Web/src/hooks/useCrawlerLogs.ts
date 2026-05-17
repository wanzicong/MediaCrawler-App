import { useEffect, useRef, useState, useCallback } from 'react';
import type { CrawlerLogEntry } from '@/api/modules/crawler';
import { fetchCrawlerLogs } from '@/api/modules/crawler';

interface UseCrawlerLogsReturn {
  logs: CrawlerLogEntry[];
  connected: boolean;
  clearLogs: () => void;
  refreshLogs: () => void;
}

export function useCrawlerLogs(enabled: boolean): UseCrawlerLogsReturn {
  const [logs, setLogs] = useState<CrawlerLogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>();
  const mountedRef = useRef(true);

  const clearLogs = useCallback(() => setLogs([]), []);

  const refreshLogs = useCallback(() => {
    fetchCrawlerLogs(200)
      .then((res) => {
        if (mountedRef.current) setLogs(res.logs ?? []);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    if (!enabled) {
      setConnected(false);
      return;
    }

    // Load initial logs via REST
    fetchCrawlerLogs(200)
      .then((res) => {
        if (mountedRef.current) setLogs(res.logs ?? []);
      })
      .catch(() => {});

    // Build WS URL from current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8088/api/ws/logs`;

    const connect = () => {
      if (!mountedRef.current) return;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (mountedRef.current) setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const entry: CrawlerLogEntry = JSON.parse(event.data);
          if (mountedRef.current) {
            setLogs((prev) => {
              const next = [...prev, entry];
              return next.length > 500 ? next.slice(-500) : next;
            });
          }
        } catch {
          // ignore non-JSON messages (ping/pong)
        }
      };

      ws.onclose = () => {
        if (mountedRef.current) {
          setConnected(false);
          // Auto-reconnect after 3s
          reconnectRef.current = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [enabled]);

  return { logs, connected, clearLogs, refreshLogs };
}
