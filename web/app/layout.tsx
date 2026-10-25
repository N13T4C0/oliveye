import type { Metadata, Viewport } from "next";

import "@fontsource-variable/inter";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";

import { THEME_BOOT_SCRIPT } from "@/lib/theme-boot";

export const metadata: Metadata = {
  title: "OlivEye · El olivar de Jaén y Granada visto desde el satélite",
  description:
    "Índices Sentinel-2 (NDVI, NDMI) del olivar de 86 municipios de Jaén y Granada desde 2016, y una estimación de la producción de aceite validada con honestidad frente al aforo oficial.",
};

export const viewport: Viewport = {
  themeColor: "#163300",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    // The boot script sets data-theme before React hydrates, hence suppressHydrationWarning.
    <html lang="es" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT_SCRIPT }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
