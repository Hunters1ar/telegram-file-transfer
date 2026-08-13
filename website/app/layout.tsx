import { I18nProvider } from "@/lib/i18n"
import type React from "react"
import type { Metadata, Viewport } from "next"
import { ThemeProvider } from "@/components/theme-provider"
import { Analytics } from "@vercel/analytics/next"
import "./globals.css"

export const metadata: Metadata = {
  title: "Hunterstar — UX 2.0",
  description: "Luxury Crimson cloud storage. Upload, organize and share files with a refined dark or light interface.",
  generator: "v0.app",
}

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f4f4f6" },
    { media: "(prefers-color-scheme: dark)", color: "#050505" },
  ],
  userScalable: false,
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
}

const themeScript = `
(function() {
  try {
    var t = localStorage.getItem('hunterstar-theme');
    if (!t) t = 'dark';
    var root = document.documentElement;
    root.classList.remove('light','dark');
    root.classList.add(t);
    root.style.colorScheme = t;
  } catch (e) {}
})();
`

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="manifest" href="/site.webmanifest" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        {/* Removed legacy service worker registration */}
      </head>
      <body className="antialiased">
        <I18nProvider>
          <ThemeProvider>{children}</ThemeProvider>
        </I18nProvider>
        {process.env.NODE_ENV === "production" && <Analytics />}
      </body>
    </html>
  )
}
