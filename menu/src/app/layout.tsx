import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { AuthProvider } from "@/lib/auth";
import { ChunkErrorHandler } from "./chunk-handler";
import "./globals.css";

export const dynamic = "force-dynamic";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Menu.AI — Planejamento inteligente de cardápios",
  description: "Crie cardápios nutricionais com inteligência artificial",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className={inter.variable}>
      <body className={`${inter.className} min-h-screen bg-canvas font-sans text-ink antialiased`}>
        <AuthProvider>
          <ChunkErrorHandler />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
