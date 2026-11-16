-- CreateTable
CREATE TABLE "StatementImport" (
    "id" TEXT NOT NULL,
    "ledgerId" TEXT NOT NULL,
    "imported" INTEGER NOT NULL,
    "duplicates" INTEGER NOT NULL,
    "importedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "StatementImport_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "StatementImport_ledgerId_importedAt_idx" ON "StatementImport"("ledgerId", "importedAt");

-- AddForeignKey
ALTER TABLE "StatementImport" ADD CONSTRAINT "StatementImport_ledgerId_fkey" FOREIGN KEY ("ledgerId") REFERENCES "Ledger"("id") ON DELETE CASCADE ON UPDATE CASCADE;
