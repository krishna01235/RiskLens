import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RiskLens",
  description:
    "Event-driven quantitative risk monitoring platform. Continuous VaR, CVaR, Monte Carlo, and AI-explained alerts for your portfolio.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
