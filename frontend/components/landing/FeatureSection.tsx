"use client";

/**
 * FeatureSection.tsx — Three feature blocks, each with a real embedded chart.
 *
 * Charts:
 * 1. Risk Contribution vs. Allocation — BarChart (Recharts)
 *    Same visual language as RiskContributionList.tsx (token colors).
 * 2. EVT vs. Monte Carlo tail — static two-number comparison block
 *    styled exactly like EVTComparisonRow.tsx.
 * 3. Historical Replay breach marker — ComposedChart with ReferenceLine
 *    same chart type used in replay/page.tsx.
 *
 * No icons, no illustrations. All charts are real Recharts instances.
 * All colors reference CSS token variables — no hardcoded hex.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ComposedChart,
  Line,
  Scatter,
  ReferenceLine,
  CartesianGrid,
} from "recharts";

// ── Static illustrative data ──────────────────────────────────────────────────

const RISK_CONTRIBUTION_DATA = [
  { symbol: "NVDA", allocation: 15, riskContrib: 34 },
  { symbol: "AAPL", allocation: 28, riskContrib: 22 },
  { symbol: "MSFT", allocation: 25, riskContrib: 19 },
  { symbol: "AMZN", allocation: 20, riskContrib: 16 },
  { symbol: "META", allocation: 12, riskContrib: 9 },
];

const REPLAY_DATA = [
  { day: "D-25", var: -1.8, ret: -0.9 },
  { day: "D-22", var: -1.7, ret: -1.1 },
  { day: "D-19", var: -2.1, ret: -0.7 },
  { day: "D-16", var: -2.3, ret: -0.5 },
  { day: "D-13", var: -1.9, ret: -3.1, breach: -3.1 }, // breach day
  { day: "D-10", var: -2.2, ret: -1.4 },
  { day: "D-7",  var: -2.5, ret: -0.8 },
  { day: "D-4",  var: -2.0, ret: -1.2 },
  { day: "D-1",  var: -1.8, ret: -0.6 },
];

// ── Shared styles ─────────────────────────────────────────────────────────────

const SECTION_LABEL: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "var(--text-xs)",
  color: "var(--color-accent)",
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  marginBottom: "var(--sp-2)",
};

const HEADING: React.CSSProperties = {
  fontFamily: "var(--font-ui)",
  fontSize: "var(--text-lg)",
  fontWeight: "var(--fw-semibold)",
  color: "var(--color-text-primary)",
  marginBottom: "var(--sp-2)",
  lineHeight: 1.3,
};

const COPY: React.CSSProperties = {
  fontFamily: "var(--font-ui)",
  fontSize: "var(--text-sm)",
  color: "var(--color-text-secondary)",
  lineHeight: 1.6,
  marginBottom: "var(--sp-6)",
};

const CHART_BOX: React.CSSProperties = {
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-lg)",
  backgroundColor: "var(--color-bg-elevated)",
  padding: "var(--sp-4)",
  height: 200,
};

const DIVIDER: React.CSSProperties = {
  borderTop: "1px solid var(--color-border)",
  margin: "var(--sp-12) 0",
};

// ── Tooltip customisation ─────────────────────────────────────────────────────

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: {name: string; value: number; color: string}[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: "var(--color-bg-elevated)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-md)",
        padding: "var(--sp-2) var(--sp-3)",
        fontFamily: "var(--font-mono)",
        fontSize: "var(--text-xs)",
        color: "var(--color-text-primary)",
      }}
    >
      <p style={{ marginBottom: 4, color: "var(--color-text-secondary)" }}>{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: {p.value}%
        </p>
      ))}
    </div>
  );
}

// ── Feature 1: Risk Contribution ──────────────────────────────────────────────

function RiskContributionFeature() {
  return (
    <div>
      <p style={SECTION_LABEL}>Risk Contribution</p>
      <h2 style={HEADING}>
        See which position is actually driving your risk — not just which one
        you own the most of.
      </h2>
      <p style={COPY}>
        Your largest allocation is AAPL at 28%. But NVDA, at only 15%, is
        responsible for 34% of your total portfolio volatility. Concentration
        in allocation doesn&apos;t mean concentration in risk.
      </p>
      <div style={CHART_BOX} aria-label="Risk contribution vs allocation bar chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={RISK_CONTRIBUTION_DATA}
            margin={{ top: 4, right: 4, left: -28, bottom: 0 }}
            barCategoryGap="30%"
            barGap={2}
          >
            <CartesianGrid
              vertical={false}
              stroke="var(--color-border-subtle)"
              strokeDasharray="3 3"
            />
            <XAxis
              dataKey="symbol"
              tick={{ fill: "var(--color-text-tertiary)", fontSize: 10, fontFamily: "var(--font-mono)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "var(--color-text-tertiary)", fontSize: 10, fontFamily: "var(--font-mono)" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--color-bg-hover)" }} />
            <Bar dataKey="allocation" name="Allocation" fill="var(--color-accent)" opacity={0.4} radius={[2,2,0,0]} />
            <Bar dataKey="riskContrib" name="Risk Contrib" fill="var(--color-breach)" opacity={0.7} radius={[2,2,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ── Feature 2: EVT vs Monte Carlo ────────────────────────────────────────────

function EVTFeature() {
  return (
    <div>
      <p style={SECTION_LABEL}>Tail Risk</p>
      <h2 style={HEADING}>
        Gaussian models underestimate tail losses. EVT shows you what they
        miss.
      </h2>
      <p style={COPY}>
        Monte Carlo assumes returns follow a bell curve. Extreme Value Theory
        fits the actual tails of your historical distribution. When markets
        crash, the difference is not academic.
      </p>
      {/* Two-number EVT comparison — same layout as EVTComparisonRow.tsx */}
      <div
        style={{
          ...CHART_BOX,
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "var(--sp-4)",
          height: "auto",
          padding: "var(--sp-4)",
        }}
        aria-label="EVT vs Monte Carlo tail risk comparison"
      >
        <div
          style={{
            background: "var(--color-bg)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-md)",
            padding: "var(--sp-4)",
          }}
        >
          <p style={{ fontFamily: "var(--font-ui)", fontSize: "var(--text-xs)", color: "var(--color-text-tertiary)", marginBottom: "var(--sp-1)" }}>
            Monte Carlo (Gaussian)
          </p>
          <p
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--text-xl)",
              fontWeight: "var(--fw-semibold)",
              color: "var(--color-high)",
            }}
          >
            −$8,240
          </p>
          <p style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--color-text-tertiary)", marginTop: "var(--sp-1)" }}>
            95% VaR (5th percentile P&amp;L)
          </p>
        </div>
        <div
          style={{
            background: "var(--color-breach-muted)",
            border: "1px solid rgba(217,72,61,0.2)",
            borderRadius: "var(--radius-md)",
            padding: "var(--sp-4)",
          }}
        >
          <p style={{ fontFamily: "var(--font-ui)", fontSize: "var(--text-xs)", color: "var(--color-breach)", marginBottom: "var(--sp-1)", opacity: 0.8 }}>
            Extreme Value Theory (POT)
          </p>
          <p
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--text-xl)",
              fontWeight: "var(--fw-semibold)",
              color: "var(--color-breach)",
            }}
          >
            −$14,900
          </p>
          <p style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--color-breach)", marginTop: "var(--sp-1)", opacity: 0.6 }}>
            Expected Shortfall (CVaR 95%)
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Feature 3: Historical Replay ──────────────────────────────────────────────

function ReplayFeature() {
  return (
    <div>
      <p style={SECTION_LABEL}>Historical Replay</p>
      <h2 style={HEADING}>
        Did your VaR model actually hold during the last drawdown? Now you can
        check.
      </h2>
      <p style={COPY}>
        Replay reconstructs your portfolio&apos;s risk through a historical period
        day by day, without look-ahead bias. The Kupiec backtest tells you
        whether your model is calibrated to reality.
      </p>
      <div style={CHART_BOX} aria-label="Historical replay VaR vs actual returns with breach marker">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={REPLAY_DATA} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
            <CartesianGrid
              vertical={false}
              stroke="var(--color-border-subtle)"
              strokeDasharray="3 3"
            />
            <XAxis
              dataKey="day"
              tick={{ fill: "var(--color-text-tertiary)", fontSize: 10, fontFamily: "var(--font-mono)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "var(--color-text-tertiary)", fontSize: 10, fontFamily: "var(--font-mono)" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                return (
                  <div style={{ background: "var(--color-bg-elevated)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "var(--sp-2) var(--sp-3)", fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", color: "var(--color-text-primary)" }}>
                    <p style={{ marginBottom: 4, color: "var(--color-text-secondary)" }}>{label}</p>
                    {payload.map((p) => (
                      <p key={p.name as string} style={{ color: p.color as string }}>{p.name as string}: {p.value as number}%</p>
                    ))}
                  </div>
                );
              }}
            />
            {/* VaR prediction line */}
            <Line
              type="monotone"
              dataKey="var"
              name="VaR (predicted)"
              stroke="var(--color-accent)"
              strokeWidth={1.5}
              dot={false}
              strokeDasharray="4 2"
            />
            {/* Actual returns */}
            <Line
              type="monotone"
              dataKey="ret"
              name="Actual return"
              stroke="var(--color-text-secondary)"
              strokeWidth={1.5}
              dot={{ r: 2, fill: "var(--color-text-secondary)" }}
            />
            {/* Breach scatter point */}
            <Scatter
              dataKey="breach"
              name="Breach"
              fill="var(--color-breach)"
              shape={(props: { cx?: number; cy?: number }) => {
                if (props.cy === undefined || props.cx === undefined) return <g />;
                return (
                  <circle
                    cx={props.cx}
                    cy={props.cy}
                    r={5}
                    fill="var(--color-breach)"
                    stroke="var(--color-bg)"
                    strokeWidth={1.5}
                  />
                );
              }}
            />
            {/* Breach reference line */}
            <ReferenceLine x="D-13" stroke="var(--color-breach)" strokeDasharray="3 3" strokeWidth={1} label={{ value: "Breach", fill: "var(--color-breach)", fontSize: 9, fontFamily: "var(--font-mono)" }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ── Assembled feature section ─────────────────────────────────────────────────

export default function FeatureSection() {
  return (
    <section
      style={{ maxWidth: 1100, margin: "0 auto", padding: "var(--sp-12) var(--sp-6)" }}
      aria-label="Product features"
    >
      <RiskContributionFeature />
      <div style={DIVIDER} />
      <EVTFeature />
      <div style={DIVIDER} />
      <ReplayFeature />
    </section>
  );
}
