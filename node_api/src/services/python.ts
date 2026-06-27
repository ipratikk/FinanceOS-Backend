import axios from 'axios';
import FormData from 'form-data';

const PYTHON_URL = process.env.PYTHON_SERVICE_URL ?? 'http://localhost:8000';

export interface ParsedTransaction {
  postedAt: string;
  description: string;
  amountMinorUnits: number;
  currencyCode: string;
  sourceFingerprint: string;
  rewardPoints?: number;
  closingBalanceMinorUnits?: number;
  statementRowIndex?: number;
}

export interface ParseResponse {
  bank_code: string;
  count: number;
  transactions: ParsedTransaction[];
}

export interface ImportResponse {
  imported: number;
  duplicates: number;
  errors: string[];
}

export async function parseFile(
  fileBuffer: Buffer,
  filename: string,
  bankCode?: string,
): Promise<ParseResponse> {
  const form = new FormData();
  form.append('file', fileBuffer, { filename });
  if (bankCode) form.append('bank_code', bankCode);

  const res = await axios.post<ParseResponse>(`${PYTHON_URL}/parse`, form, {
    headers: form.getHeaders(),
  });
  return res.data;
}

export async function importTransactions(
  ledgerId: string,
  transactions: ParsedTransaction[],
): Promise<ImportResponse> {
  const res = await axios.post<ImportResponse>(`${PYTHON_URL}/import`, {
    ledger_id: ledgerId,
    transactions,
  });
  return res.data;
}

export async function getAnalytics(
  ledgerId?: string,
  from?: string,
  to?: string,
): Promise<unknown> {
  const params: Record<string, string> = {};
  if (ledgerId) params.ledger_id = ledgerId;
  if (from) params.from = from;
  if (to) params.to = to;

  const res = await axios.get(`${PYTHON_URL}/analytics`, { params });
  return res.data;
}
