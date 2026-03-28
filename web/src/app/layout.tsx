import type { Metadata, Viewport } from "next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import LiveKitGate from "@/components/LiveKitGate";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ω OmegA",
  description: "Sovereign Intelligence. Engineered by R.W. Yett.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#02020c",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        {children}
        <LiveKitGate />
        <SpeedInsights />
      </body>
    </html>
  );
}
