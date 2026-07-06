import { parseFile } from '../services/python';
import { decryptPassword, EncryptedPassword } from '../services/passwordCrypto';

interface FileUpload {
  filename: string;
  mimetype: string;
  encoding: string;
  createReadStream: () => NodeJS.ReadableStream;
}

export const previewResolvers = {
  Mutation: {
    previewStatement: async (
      _: unknown,
      { file, password }: { file: Promise<FileUpload>; password?: EncryptedPassword },
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

      return {
        bankCode: parsed.bank_code,
        last4: parsed.last4,
        transactionCount: parsed.count,
        passwordRequired: parsed.password_required,
      };
    },
  },
};
