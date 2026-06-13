-- AlterEnum
ALTER TYPE "ExtractionMethod" ADD VALUE 'open_food_facts';

-- AlterTable
ALTER TABLE "variants" ADD COLUMN     "compareAtPriceCents" INTEGER,
ADD COLUMN     "upc" TEXT;

-- CreateIndex
CREATE INDEX "variants_upc_idx" ON "variants"("upc");
