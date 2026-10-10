import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/hooks/useAuth";
import { ThemeProvider } from "@/hooks/useTheme";
import { I18nProvider } from "@/hooks/useI18n";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "NexusAI Talent OS — The Operating System for Intelligent Hiring",
  description:
    "Automate your entire hiring pipeline — from resume screening to multi-round AI interviews — and make data-driven hiring decisions in minutes, not weeks.",
  keywords: [
    "AI interview",
    "hiring automation",
    "recruitment AI",
    "candidate screening",
    "video interviews",
    "NexusAI",
  ],
  openGraph: {
    title: "NexusAI Talent OS — The Operating System for Intelligent Hiring",
    description:
      "Automate your entire hiring pipeline with AI-powered interviews and data-driven hiring decisions.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                  document.documentElement.classList.add('dark')
                } else {
                  document.documentElement.classList.remove('dark')
                }
              } catch (_) {}
            `,
          }}
        />
      </head>
      <body className="font-sans antialiased bg-bg text-text-primary transition-colors duration-150">
        <ThemeProvider>
          <I18nProvider>
            <AuthProvider>
              {children}
            </AuthProvider>
          </I18nProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
