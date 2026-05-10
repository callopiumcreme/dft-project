import Link from 'next/link';
import { redirect } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';

type Page = components['schemas']['AuditLogPage'];
type Entry = components['schemas']['AuditLogEntry'];
type UserRead = components['schemas']['UserRead'];
type Action = 'insert' | 'update' | 'delete' | 'soft_delete' | 'restore';

const ACTIONS: Action[] = ['insert', 'update', 'delete', 'soft_delete', 'restore'];

const ACTION_LABEL: Record<Action, string> = {
  insert: 'Insert',
  update: 'Update',
  delete: 'Delete',
  soft_delete: 'Soft delete',
  restore: 'Restore',
};

const ACTION_PILL: Record<Action, string> = {
  insert: 'border-olive-deep bg-olive-deep/10 text-olive-deep',
  update: 'border-ink bg-ink/10 text-ink',
  delete: 'border-accent bg-accent/5 text-accent',
  soft_delete: 'border-accent bg-bg text-accent',
  restore: 'border-olive-deep bg-bg text-olive-deep',
};

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Audit log — DFT' };

const dtFmt = new Intl.DateTimeFormat('en-GB', {
  dateStyle: 'short',
  timeStyle: 'medium',
});

function fmtDateTime(v: string): string {
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dtFmt.format(d);
}

function sanitizeAction(v: string | undefined): Action | undefined {
  return v && (ACTIONS as string[]).includes(v) ? (v as Action) : undefined;
}

function sanitizePosInt(v: string | undefined): number | undefined {
  if (!v) return undefined;
  const n = Number.parseInt(v, 10);
  return Number.isInteger(n) && n > 0 ? n : undefined;
}

function sanitizeIsoDate(v: string | undefined): string | undefined {
  if (!v) return undefined;
  return /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : undefined;
}

function diffKeys(
  oldV: Record<string, unknown> | null | undefined,
  newV: Record<string, unknown> | null | undefined,
): string[] {
  if (!oldV || !newV) return [];
  const keys = new Set([...Object.keys(oldV), ...Object.keys(newV)]);
  const out: string[] = [];
  for (const k of keys) {
    if (JSON.stringify(oldV[k]) !== JSON.stringify(newV[k])) out.push(k);
  }
  return out.sort();
}

function fmtVal(v: unknown): string {
  if (v === null || v === undefined) return '∅';
  if (typeof v === 'string') return v.length > 80 ? v.slice(0, 77) + '…' : v;
  return JSON.stringify(v);
}

interface PageProps {
  searchParams: {
    table?: string;
    record?: string;
    action?: string;
    user?: string;
    from?: string;
    to?: string;
    page?: string;
  };
}

const PAGE_SIZE = 50;

export default async function AuditLogPage({ searchParams }: PageProps) {
  let me: UserRead | null = null;
  try {
    me = await apiGet<UserRead>('/auth/me');
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
  }

  if (!me || me.role !== 'admin') {
    return (
      <div className="mx-auto max-w-editorial">
        <header className="border-b border-rule pb-6">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
            Admin
          </p>
          <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">Audit log</h1>
        </header>
        <p className="mt-6 border border-accent bg-accent/5 px-3 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-accent">
          Admin role required.
        </p>
      </div>
    );
  }

  const table = (searchParams.table ?? '').trim() || undefined;
  const record = sanitizePosInt(searchParams.record);
  const action = sanitizeAction(searchParams.action);
  const userId = sanitizePosInt(searchParams.user);
  const dateFrom = sanitizeIsoDate(searchParams.from);
  const dateTo = sanitizeIsoDate(searchParams.to);
  const pageNum = Math.max(1, sanitizePosInt(searchParams.page) ?? 1);
  const offset = (pageNum - 1) * PAGE_SIZE;

  let pageData: Page = { items: [], total: 0, limit: PAGE_SIZE, offset };
  let tables: string[] = [];
  let fetchError: string | null = null;

  try {
    const [pageRes, tablesRes] = await Promise.all([
      apiGet<Page>('/admin/audit-log', {
        query: {
          ...(table ? { table_name: table } : {}),
          ...(record !== undefined ? { record_id: record } : {}),
          ...(action ? { action } : {}),
          ...(userId !== undefined ? { changed_by: userId } : {}),
          ...(dateFrom ? { date_from: dateFrom } : {}),
          ...(dateTo ? { date_to: dateTo } : {}),
          limit: PAGE_SIZE,
          offset,
        },
      }),
      apiGet<string[]>('/admin/audit-log/tables'),
    ]);
    pageData = pageRes;
    tables = tablesRes;
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'unknown error';
  }

  const totalPages = Math.max(1, Math.ceil(pageData.total / PAGE_SIZE));
  const baseQuery = (extra: Record<string, string>) => {
    const params = new URLSearchParams();
    if (table) params.set('table', table);
    if (record !== undefined) params.set('record', String(record));
    if (action) params.set('action', action);
    if (userId !== undefined) params.set('user', String(userId));
    if (dateFrom) params.set('from', dateFrom);
    if (dateTo) params.set('to', dateTo);
    if (pageNum > 1) params.set('page', String(pageNum));
    for (const [k, v] of Object.entries(extra)) {
      if (v === '') params.delete(k);
      else params.set(k, v);
    }
    const s = params.toString();
    return s ? `?${s}` : '';
  };

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">Admin</p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">Audit log</h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          {pageData.total} entries
          {table ? ` · table = ${table}` : ''}
          {record !== undefined ? ` · record #${record}` : ''}
          {action ? ` · action = ${ACTION_LABEL[action]}` : ''}
          {userId !== undefined ? ` · user #${userId}` : ''}
          {dateFrom || dateTo
            ? ` · ${dateFrom ?? '…'} → ${dateTo ?? '…'}`
            : ''}
        </p>
      </header>

      <form
        method="GET"
        action="/app/audit"
        className="mt-6 grid grid-cols-1 sm:grid-cols-6 gap-3 border-b border-rule pb-6 font-mono text-[0.7rem] uppercase tracking-[0.14em]"
      >
        <label className="flex flex-col gap-1 sm:col-span-2">
          <span className="text-ink-mute">Table</span>
          <select
            name="table"
            defaultValue={table ?? ''}
            className="border border-rule bg-bg-soft px-2 py-1 text-ink"
          >
            <option value="">All tables</option>
            {tables.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-ink-mute">Record ID</span>
          <input
            type="number"
            name="record"
            defaultValue={record ?? ''}
            min={1}
            className="border border-rule bg-bg-soft px-2 py-1 text-ink"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-ink-mute">Action</span>
          <select
            name="action"
            defaultValue={action ?? ''}
            className="border border-rule bg-bg-soft px-2 py-1 text-ink"
          >
            <option value="">All</option>
            {ACTIONS.map((a) => (
              <option key={a} value={a}>
                {ACTION_LABEL[a]}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-ink-mute">User ID</span>
          <input
            type="number"
            name="user"
            defaultValue={userId ?? ''}
            min={1}
            className="border border-rule bg-bg-soft px-2 py-1 text-ink"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-ink-mute">From</span>
          <input
            type="date"
            name="from"
            defaultValue={dateFrom ?? ''}
            className="border border-rule bg-bg-soft px-2 py-1 text-ink"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-ink-mute">To</span>
          <input
            type="date"
            name="to"
            defaultValue={dateTo ?? ''}
            className="border border-rule bg-bg-soft px-2 py-1 text-ink"
          />
        </label>
        <div className="flex items-end gap-2 sm:col-span-6">
          <button
            type="submit"
            className="border border-ink bg-ink px-3 py-1.5 text-bg hover:bg-ink-soft"
          >
            Apply
          </button>
          <Link
            href="/app/audit"
            className="border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink"
          >
            Reset
          </Link>
        </div>
      </form>

      {fetchError && (
        <div className="mt-6 border border-rule bg-bg-soft p-4 font-mono text-[0.75rem] text-accent">
          Loading error: {fetchError}
        </div>
      )}

      <section className="mt-6 space-y-3">
        {pageData.items.length === 0 && !fetchError && (
          <p className="border border-rule bg-bg-soft p-6 text-center font-mono text-[0.75rem] text-ink-mute">
            No audit entries match the filter.
          </p>
        )}
        {pageData.items.map((e) => (
          <EntryCard key={e.id} entry={e} />
        ))}
      </section>

      {pageData.total > PAGE_SIZE && (
        <nav className="mt-6 flex items-center justify-between border-t border-rule pt-4 font-mono text-[0.7rem] uppercase tracking-[0.14em]">
          <span className="text-ink-soft">
            Page {pageNum} of {totalPages} · {pageData.total} entries
          </span>
          <div className="flex gap-2">
            {pageNum > 1 ? (
              <Link
                href={`/app/audit${baseQuery({ page: String(pageNum - 1) })}`}
                className="border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink"
              >
                ← Prev
              </Link>
            ) : (
              <span className="border border-rule/40 px-3 py-1.5 text-ink-mute">← Prev</span>
            )}
            {pageNum < totalPages ? (
              <Link
                href={`/app/audit${baseQuery({ page: String(pageNum + 1) })}`}
                className="border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink"
              >
                Next →
              </Link>
            ) : (
              <span className="border border-rule/40 px-3 py-1.5 text-ink-mute">Next →</span>
            )}
          </div>
        </nav>
      )}
    </div>
  );
}

function EntryCard({ entry }: { entry: Entry }) {
  const action = (ACTIONS as string[]).includes(entry.action)
    ? (entry.action as Action)
    : 'update';
  const changed = diffKeys(entry.old_values, entry.new_values);

  return (
    <article className="border border-rule bg-bg-soft p-4 font-mono text-[0.72rem]">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-rule/40 pb-2">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-block border px-2 py-0.5 text-[0.65rem] uppercase ${ACTION_PILL[action]}`}
          >
            {ACTION_LABEL[action]}
          </span>
          <span className="text-ink">{entry.table_name}</span>
          <span className="text-ink-mute">·</span>
          <span className="text-ink-soft">record #{entry.record_id}</span>
        </div>
        <div className="flex items-center gap-2 text-ink-mute">
          <span>{fmtDateTime(entry.changed_at)}</span>
          <span>·</span>
          <span>{entry.changed_by_email ?? `user #${entry.changed_by ?? '∅'}`}</span>
          <span>·</span>
          <span className="text-ink-mute">#{entry.id}</span>
        </div>
      </header>

      {action === 'insert' && entry.new_values && (
        <ValuesTable title="Inserted values" values={entry.new_values} />
      )}

      {(action === 'update' || action === 'soft_delete' || action === 'restore') &&
        entry.old_values &&
        entry.new_values && (
          <DiffTable
            old={entry.old_values}
            next={entry.new_values}
            changedKeys={changed}
          />
        )}

      {action === 'delete' && entry.old_values && (
        <ValuesTable title="Deleted values" values={entry.old_values} />
      )}

      {changed.length === 0 && (action === 'update' || action === 'soft_delete' || action === 'restore') && (
        <p className="mt-2 text-[0.7rem] text-ink-mute">No field changes recorded.</p>
      )}
    </article>
  );
}

function ValuesTable({
  title,
  values,
}: {
  title: string;
  values: Record<string, unknown>;
}) {
  const keys = Object.keys(values).sort();
  return (
    <div className="mt-2">
      <p className="mb-1 text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">{title}</p>
      <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1">
        {keys.map((k) => (
          <div key={k} className="flex items-baseline gap-2 border-b border-rule/30 py-1">
            <dt className="min-w-[8rem] text-ink-mute">{k}</dt>
            <dd className="text-ink-soft break-all">{fmtVal(values[k])}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function DiffTable({
  old,
  next,
  changedKeys,
}: {
  old: Record<string, unknown>;
  next: Record<string, unknown>;
  changedKeys: string[];
}) {
  if (changedKeys.length === 0) return null;
  return (
    <div className="mt-2">
      <p className="mb-1 text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">
        Changes ({changedKeys.length})
      </p>
      <table className="w-full border-collapse">
        <thead>
          <tr className="text-left text-[0.65rem] uppercase tracking-[0.12em] text-ink-mute">
            <th className="px-2 py-1 font-normal">Field</th>
            <th className="px-2 py-1 font-normal">Before</th>
            <th className="px-2 py-1 font-normal">After</th>
          </tr>
        </thead>
        <tbody>
          {changedKeys.map((k) => (
            <tr key={k} className="border-t border-rule/30">
              <td className="px-2 py-1 text-ink">{k}</td>
              <td className="px-2 py-1 text-accent break-all">{fmtVal(old[k])}</td>
              <td className="px-2 py-1 text-olive-deep break-all">{fmtVal(next[k])}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
