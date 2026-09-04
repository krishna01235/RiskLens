import { useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/api-client";

export interface RiskMetrics {
  var_95: number;
  cvar_95: number;
  volatility: number;
  sharpe: number | null;
  max_drawdown: number;
  n_obs: number;
}

export interface AlertMessage {
  type: "alert";
  portfolio_id: string;
  from_state: string;
  to_state: string;
  utilization: number;
  cvar: number;
  fired_at: string;
}

export interface DecisionCandidate {
  label: string;
  expected_return: number;
  cvar: number;
  p_loss: number;
  score: number;
  is_fallback: boolean;
}

export interface DecisionUpdate {
  type: "decision_update";
  portfolio_id: string;
  decision_id: string;
  alert_id: string;
  candidates: DecisionCandidate[];
  created_at: string;
}

export interface RiskContribution {
  symbol: string;
  weight: number;
  mcr: number;
  rc: number;
  rc_pct: number;
}

export interface RiskUpdate {
  portfolio_id: string;
  portfolio_value: string;
  daily_pnl: string;
  timestamp: number;
  data_status?: "pending" | "ready" | "insufficient_data";
  metrics?: RiskMetrics | null;
  risk_contributions?: RiskContribution[];
  correlation_flags?: string[][];
  risk_updated_at?: number;
}

export function useRiskSocket(portfolioId: string | null) {
  const [riskData, setRiskData] = useState<RiskUpdate | null>(null);
  const [alertMsg, setAlertMsg] = useState<AlertMessage | null>(null);
  const [decisionMsg, setDecisionMsg] = useState<DecisionUpdate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!portfolioId) return;

    let isMounted = true;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = async () => {
      try {
        // Initial REST fetch
        try {
          const initialData = await apiClient.get<RiskUpdate>(`/portfolios/${portfolioId}/risk`);
          if (isMounted && initialData) {
            setRiskData(initialData);
          }
        } catch (e) {
          console.error("Failed to fetch initial risk data", e);
        }

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
            } else if (data.type === "alert" && data.portfolio_id === portfolioId) {
              setAlertMsg(data);
              // Clear old decision when a new alert fires
              setDecisionMsg(null);
            } else if (data.type === "decision_update" && data.portfolio_id === portfolioId) {
              setDecisionMsg(data);
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

  return { riskData, alertMsg, decisionMsg, error };
}
