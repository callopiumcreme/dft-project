import { redirect } from 'next/navigation';

export default function ReportsIndex(): never {
  redirect('/app/reports/mass-balance');
}
