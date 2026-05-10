'use client';

import { useFormState, useFormStatus } from 'react-dom';
import type { UserFormState } from '@/lib/user-actions';
import type { components } from '@/lib/backend-types';

type User = components['schemas']['UserRead'];
type Role = 'admin' | 'operator' | 'viewer' | 'certifier';

const ROLES: Role[] = ['admin', 'operator', 'viewer', 'certifier'];
const ROLE_LABEL: Record<Role, string> = {
  admin: 'Admin (full access)',
  operator: 'Operator (data entry + production)',
  viewer: 'Viewer (read-only)',
  certifier: 'Certifier (audit access)',
};

type Action = (prev: UserFormState, fd: FormData) => Promise<UserFormState>;

interface Props {
  action: Action;
  initial?: User | null;
  mode: 'create' | 'edit';
  isSelf?: boolean;
  submitLabel: string;
  cancelHref: string;
}

const initialState: UserFormState = {};

function ErrorMsg({ msg }: { msg?: string }) {
  if (!msg) return null;
  return (
    <p className="mt-1 font-mono text-[0.65rem] uppercase tracking-[0.12em] text-accent">
      {msg}
    </p>
  );
}

function FieldLabel({
  htmlFor,
  required,
  children,
}: {
  htmlFor: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute"
    >
      {children}
      {required && <span className="ml-1 text-accent">*</span>}
    </label>
  );
}

function Submit({ label }: { label: string }) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft disabled:opacity-50"
    >
      {pending ? 'Saving…' : label}
    </button>
  );
}

export default function UserForm({
  action,
  initial,
  mode,
  isSelf,
  submitLabel,
  cancelHref,
}: Props) {
  const [state, formAction] = useFormState(action, initialState);
  const v = state.values ?? {};
  const errs = state.fieldErrors ?? {};

  const value = (k: string, fallback?: string | null): string => {
    if (v[k] !== undefined) return v[k];
    if (fallback === null || fallback === undefined) return '';
    return String(fallback);
  };

  const checked = (k: string, fallback?: boolean): boolean => {
    if (v[k] !== undefined)
      return v[k] === 'on' || v[k] === 'true' || v[k] === '1';
    return !!fallback;
  };

  return (
    <form action={formAction} className="mt-8 space-y-8 font-mono text-[0.78rem]">
      {state.error && (
        <p
          role="alert"
          className="border border-accent bg-accent/5 px-3 py-2 text-[0.7rem] uppercase tracking-[0.14em] text-accent"
        >
          {state.error}
        </p>
      )}

      <fieldset className="space-y-4 border border-rule bg-bg-soft p-4">
        <legend className="px-2 font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
          Identity
        </legend>

        <div>
          <FieldLabel htmlFor="email" required>
            Email
          </FieldLabel>
          {mode === 'create' ? (
            <input
              id="email"
              name="email"
              type="email"
              required
              maxLength={255}
              defaultValue={value('email', initial?.email)}
              className="mt-1 w-full border border-rule bg-bg px-2 py-1.5 text-ink lowercase"
              aria-invalid={!!errs.email}
            />
          ) : (
            <p className="mt-1 w-full border border-rule bg-bg px-2 py-1.5 text-ink-mute">
              {initial?.email ?? '—'}{' '}
              <span className="ml-2 text-[0.65rem] uppercase">(immutable)</span>
            </p>
          )}
          <ErrorMsg msg={errs.email} />
        </div>

        <div>
          <FieldLabel htmlFor="full_name">Full name</FieldLabel>
          <input
            id="full_name"
            name="full_name"
            maxLength={255}
            defaultValue={value('full_name', initial?.full_name)}
            className="mt-1 w-full border border-rule bg-bg px-2 py-1.5 text-ink"
            aria-invalid={!!errs.full_name}
          />
          <ErrorMsg msg={errs.full_name} />
        </div>
      </fieldset>

      <fieldset className="space-y-4 border border-rule bg-bg-soft p-4">
        <legend className="px-2 font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
          Access
        </legend>

        <div>
          <FieldLabel htmlFor="role" required>
            Role
          </FieldLabel>
          <select
            id="role"
            name="role"
            disabled={isSelf}
            defaultValue={value('role', initial?.role ?? 'viewer')}
            className="mt-1 w-full border border-rule bg-bg px-2 py-1.5 text-ink disabled:opacity-60"
            aria-invalid={!!errs.role}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABEL[r]}
              </option>
            ))}
          </select>
          <ErrorMsg msg={errs.role} />
          {isSelf && (
            <p className="mt-1 text-[0.65rem] uppercase tracking-[0.12em] text-ink-mute">
              You cannot change your own role.
            </p>
          )}
        </div>

        <label className="flex items-center gap-2 text-[0.72rem] text-ink-soft">
          <input
            type="checkbox"
            name="active"
            disabled={isSelf}
            defaultChecked={checked('active', initial?.active ?? true)}
          />
          Active (can log in)
          {isSelf && (
            <span className="ml-2 text-[0.65rem] uppercase tracking-[0.12em] text-ink-mute">
              · cannot deactivate self
            </span>
          )}
        </label>
      </fieldset>

      <fieldset className="space-y-4 border border-rule bg-bg-soft p-4">
        <legend className="px-2 font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
          Password
        </legend>
        <div>
          <FieldLabel htmlFor="password" required={mode === 'create'}>
            {mode === 'create' ? 'Password' : 'New password (leave empty to keep)'}
          </FieldLabel>
          <input
            id="password"
            name="password"
            type="password"
            minLength={mode === 'create' ? 8 : undefined}
            maxLength={72}
            autoComplete="new-password"
            placeholder={mode === 'edit' ? '(unchanged)' : ''}
            className="mt-1 w-full border border-rule bg-bg px-2 py-1.5 text-ink"
            aria-invalid={!!errs.password}
          />
          <ErrorMsg msg={errs.password} />
          <p className="mt-1 text-[0.65rem] uppercase tracking-[0.12em] text-ink-mute">
            8–72 chars. Bcrypt truncates at 72 bytes.
          </p>
        </div>
      </fieldset>

      <div className="flex items-center gap-3">
        <Submit label={submitLabel} />
        <a
          href={cancelHref}
          className="border border-rule px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-ink-soft hover:border-ink hover:text-ink"
        >
          Cancel
        </a>
      </div>
    </form>
  );
}
