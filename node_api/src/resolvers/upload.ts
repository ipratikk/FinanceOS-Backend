import { parseFile, importTransactions } from '../services/python';
import { decryptPassword, EncryptedPassword } from '../services/passwordCrypto';
import prisma from '../prisma/client';

interface FileUpload {
  filename: string;
  mimetype: string;
  encoding: string;
  createReadStream: () => NodeJS.ReadableStream;
}

export const uploadResolvers = {
  Mutation: {
    uploadStatement: async (
      _: unknown,
      {
        ledgerId,
        file,
        password,
      }: { ledgerId: string; file: Promise<FileUpload>; password?: EncryptedPassword },
    ) => {
      const { filename, createReadStream } = await file;

      const chunks: Buffer[] = [];
      await new Promise<void>((resolve, reject) => {
        const stream = createReadStream();
        stream.on('data', (chunk: Buffer) => chunks.push(chunk));
        stream.on('end', resolve);
        stream.on('error', reject);
      });
      const buffer = Buffer.concat(chunks);

      const plaintextPassword = password ? decryptPassword(password) : undefined;
      const parsed = await parseFile(buffer, filename, undefined, plaintextPassword);
      if (parsed.password_required) {
        throw new Error('Incorrect or missing password for this file');
      }
      const imported = await importTransactions(ledgerId, parsed.transactions);

      const ledger = await prisma.ledger.findUniqueOrThrow({
        where: { id: ledgerId },
        include: { bank: true },
      });

      return {
        imported: imported.imported,
        duplicates: imported.duplicates,
        errors: imported.errors,
        ledger,
      };
    },
  },
};
