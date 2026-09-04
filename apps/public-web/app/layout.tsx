import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KnK Capital",
  description: "Public website and research portal for KnK Capital."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
