/** @type {import('next').NextConfig} */
const nextConfig = {
  // Transpile our TS workspace package; keep the Prisma engine external.
  transpilePackages: ["@proteinscraper/db"],
  serverExternalPackages: ["@prisma/client"],
};

export default nextConfig;
