import type { NextConfig } from "next";

// Print which backend URL the UI bundle will use in dev.
if (process.env.NODE_ENV !== "production") {
  // eslint-disable-next-line no-console
  console.log(
    `[firestarter] NEXT_PUBLIC_BACKEND_URL (dev): ${
      process.env.NEXT_PUBLIC_BACKEND_URL || "(unset - using Next.js API routes)"
    }`
  );
}

const nextConfig: NextConfig = {
  // Remove assetPrefix to fix image loading issues
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'www.google.com',
        pathname: '/s2/favicons**',
      },
      {
        protocol: 'https',
        hostname: '**',
      },
      {
        protocol: 'http',
        hostname: '**',
      },
    ],
  },
};

export default nextConfig;
