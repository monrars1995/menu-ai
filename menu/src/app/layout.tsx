import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth";
import { ChunkErrorHandler } from "./chunk-handler";
import "./globals.css";

export const metadata: Metadata = {
  title: "Menu.AI — Planejamento inteligente de cardápios",
  description: "Crie cardápios nutricionais com inteligência artificial",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Outfit:wght@300;400;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-canvas font-sans text-ink antialiased">
        <AuthProvider>
          <ChunkErrorHandler />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
