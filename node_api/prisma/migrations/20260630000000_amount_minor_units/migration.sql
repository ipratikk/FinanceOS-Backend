ALTER TABLE "Transaction" ADD COLUMN "amountMinorUnits" INTEGER;
UPDATE "Transaction" SET "amountMinorUnits" = ROUND(amount * 100)::INTEGER;
ALTER TABLE "Transaction" ALTER COLUMN "amountMinorUnits" SET NOT NULL;
ALTER TABLE "Transaction" ADD COLUMN "currencyCode" TEXT NOT NULL DEFAULT 'INR';
ALTER TABLE "Transaction" DROP COLUMN amount;
