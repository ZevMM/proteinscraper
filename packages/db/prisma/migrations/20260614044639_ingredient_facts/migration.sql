-- CreateTable
CREATE TABLE "ingredient_facts" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "variantId" UUID NOT NULL,
    "ingredientsText" TEXT,
    "dietaryLabels" TEXT[],
    "allergens" TEXT[],
    "sweeteners" TEXT[],
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "ingredient_facts_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "ingredient_facts_variantId_key" ON "ingredient_facts"("variantId");

-- AddForeignKey
ALTER TABLE "ingredient_facts" ADD CONSTRAINT "ingredient_facts_variantId_fkey" FOREIGN KEY ("variantId") REFERENCES "variants"("id") ON DELETE CASCADE ON UPDATE CASCADE;
