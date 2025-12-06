import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import { Analytics } from "@vercel/analytics/next";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MintAgents - Custom AI Chatbots",
  description:  "Create custom AI chatbots for your website with MintAgents. MintAgents is a platform that allows you to create custom AI chatbots for your website.",
  metadataBase: new URL(process.env.NEXT_PUBLIC_URL || "https://firecrawl.dev"),
  openGraph: {
    title: "MintAgents - Custom AI Chatbots",
    description: "Create custom AI chatbots for your website with MintAgents. MintAgents is a platform that allows you to create custom AI chatbots for your website.",
    url: "/",
    siteName: "MintAgents",
    images: [
      {
        url: "/firecrawl-logo-with-fire.png",
        width: 1200,
        height: 630,
        alt: "MintAgents - Custom AI Chatbots",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "MintAgents - Custom AI Chatbots",
    description: "Transform websites into structured data with AI",
    images: ["/firecrawl-logo-with-fire.png"],
    creator: "@firecrawl_dev",
  },
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon.ico",
    apple: "/favicon.ico",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        suppressHydrationWarning={true}
        className={cn(
          "min-h-screen bg-background font-sans antialiased",
          inter.variable
        )}
      >
        <main className="">
          {children}
        </main>
        <Analytics />
      </body>
    </html>
  );
}
