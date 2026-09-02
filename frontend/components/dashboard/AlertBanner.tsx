"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Info, X } from "lucide-react";

interface AlertMessage {
  type: "alert";
  portfolio_id: string;
  from_state: string;
  to_state: string;
  utilization: number;
  cvar: number;
  fired_at: string;
}

interface Props {
  alertMsg: AlertMessage | null;
}

export default function AlertBanner({ alertMsg }: Props) {
  const [activeAlert, setActiveAlert] = useState<AlertMessage | null>(null);

  useEffect(() => {
    if (alertMsg) {
      setActiveAlert(alertMsg);

      // Auto-dismiss non-BREACH alerts after 5 seconds
      if (alertMsg.to_state !== "BREACH") {
        const timer = setTimeout(() => {
          setActiveAlert(null);
        }, 5000);
        return () => clearTimeout(timer);
      }
    }
  }, [alertMsg]);

  if (!activeAlert) return null;

  const isBreach = activeAlert.to_state === "BREACH";
  const bgColor = isBreach ? "bg-red-500/20" : activeAlert.to_state === "HIGH" ? "bg-orange-500/20" : "bg-yellow-500/20";
  const borderColor = isBreach ? "border-red-500/50" : activeAlert.to_state === "HIGH" ? "border-orange-500/50" : "border-yellow-500/50";
  const textColor = isBreach ? "text-red-400" : activeAlert.to_state === "HIGH" ? "text-orange-400" : "text-yellow-400";
  const Icon = isBreach ? AlertTriangle : Info;

  return (
    <div className={`flex items-start gap-3 p-4 border rounded-xl shadow-lg mb-4 backdrop-blur-sm animate-in slide-in-from-top-2 duration-300 ${bgColor} ${borderColor}`}>
      <Icon className={`w-5 h-5 mt-0.5 shrink-0 ${textColor}`} />
      
      <div className="flex-1">
        <h4 className={`text-sm font-bold ${textColor} uppercase tracking-wider`}>
          Risk State: {activeAlert.to_state}
        </h4>
        <p className="text-sm text-gray-300 mt-1">
          CVaR utilization has reached <span className="font-mono text-gray-200">{(activeAlert.utilization * 100).toFixed(1)}%</span> 
          {" "}(${activeAlert.cvar.toLocaleString()}).
        </p>
        <p className="text-xs text-gray-500 mt-2">
          Transitioned from {activeAlert.from_state} at {new Date(activeAlert.fired_at).toLocaleTimeString()}
        </p>
      </div>

      <button
        onClick={() => setActiveAlert(null)}
        className="p-1 rounded-md hover:bg-white/10 transition-colors"
        aria-label="Dismiss alert"
      >
        <X className={`w-5 h-5 ${textColor}`} />
      </button>
    </div>
  );
}
