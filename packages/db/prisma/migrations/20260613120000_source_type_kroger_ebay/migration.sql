-- AlterEnum: add new source types for the Kroger and eBay connectors.
ALTER TYPE "SourceType" ADD VALUE IF NOT EXISTS 'kroger';
ALTER TYPE "SourceType" ADD VALUE IF NOT EXISTS 'ebay';
