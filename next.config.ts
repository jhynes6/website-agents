import type { NextConfig } from "next";

/**
 * Load env vars from backend/.env (and backend/.env.local) into the Next.js
 * process at startup, without requiring duplicate root .env files.
 *
 * - Does not override already-set process.env keys
 * - Intentionally simple parser (KEY=VALUE, supports quoted values)
 */
function loadBackendEnvFile(filename: string) {
  try {
    const fs = require("node:fs") as typeof import("node:fs");
    const path = require("node:path") as typeof import("node:path");

    const envPath = path.join(process.cwd(), "backend", filename);
    if (!fs.existsSync(envPath)) return;

    const raw = fs.readFileSync(envPath, "utf8");
    for (const line of raw.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;

      const idx = trimmed.indexOf("=");
      if (idx <= 0) continue;

      const key = trimmed.slice(0, idx).trim();
      let value = trimmed.slice(idx + 1).trim();

      // Strip surrounding quotes
      if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        value = value.slice(1, -1);
      }

      if (process.env[key] === undefined) {
        process.env[key] = value;
      }
    }
  } catch {
    // best-effort; never block Next startup
  }
}

// Load backend env first so mintagent.config.ts sees AI keys during SSR.
loadBackendEnvFile(".env.local");
loadBackendEnvFile(".env");

// Print which backend URL the UI bundle will use in dev.
if (process.env.NODE_ENV !== "production") {
  // eslint-disable-next-line no-console
  console.log(
    `[mintagent] NEXT_PUBLIC_BACKEND_URL (dev): ${
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
