import path from "node:path";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Monorepo: trace files from the repo root so the Prisma query engine binary
  // (in the pnpm store at ../../node_modules/.pnpm) is bundled into the
  // serverless functions.
  outputFileTracingRoot: path.join(import.meta.dirname, "../../"),
  transpilePackages: ["@proteinscraper/db"],
  serverExternalPackages: ["@prisma/client"],
};

export default nextConfig;
