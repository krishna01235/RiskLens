import { useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/api-client";

export interface RiskUpdate {
  portfolio_id: string;
  portfolio_value: string;
  daily_pnl: string;
  timestamp: number;
}

export function useRiskSocket(portfolioId: string | null) {
  const [riskData, setRiskData] = useState<RiskUpdate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!portfolioId) return;

    let isMounted = true;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = async () => {
      try {
        const { ticket } = await apiClient.post<{ ticket: string }>("/ws/ticket");
        
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const wsUrl = new URL("/ws", apiUrl);
        wsUrl.protocol = wsProtocol;
        wsUrl.searchParams.set("ticket", ticket);

        const socket = new WebSocket(wsUrl.toString());
        ws.current = socket;

        socket.onopen = () => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "subscribe", portfolio_id: portfolioId }));
            setError(null);
          }
        };

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "risk_update" && data.portfolio_id === portfolioId) {
              setRiskData(data);
            }
          } catch (e) {
            console.error("WS parse error:", e);
          }
        };

        socket.onerror = (e) => {
          console.error("WS error:", e);
          setError("WebSocket error");
        };

        socket.onclose = () => {
          if (isMounted) {
            reconnectTimeout = setTimeout(connect, 3000);
          }
        };

      } catch (err) {
        console.error("Error connecting ws:", err);
        setError("Failed to connect WS");
        if (isMounted) {
          reconnectTimeout = setTimeout(connect, 3000);
        }
      }
    };

    connect();

    return () => {
      isMounted = false;
      clearTimeout(reconnectTimeout);
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [portfolioId]);

  return { riskData, error };
}
