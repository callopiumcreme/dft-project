'use client';

import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Send, Check, AlertCircle } from 'lucide-react';

type Status = 'idle' | 'loading' | 'success' | 'error';

export function Contact() {
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus('loading');
    setError(null);

    const formData = new FormData(e.currentTarget);
    const payload = {
      name: formData.get('name'),
      email: formData.get('email'),
      company: formData.get('company'),
      role: formData.get('role'),
      message: formData.get('message'),
      // honeypot
      website: formData.get('website'),
    };

    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error ?? 'Submission failed');
      }
      setStatus('success');
      e.currentTarget.reset();
    } catch (err) {
      setStatus('error');
      setError(err instanceof Error ? err.message : 'Submission failed');
    }
  }

  return (
    <section id="contact" className="relative py-24 md:py-32 bg-bg-deep text-bg">
      <div className="container-edit">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-12">
          <div className="md:col-span-5">
            <div
              className="font-mono text-[0.72rem] uppercase tracking-[0.18em] mb-4"
              style={{ color: '#A39A82' }}
            >
              § 09 — Get in touch
            </div>
            <h2 className="text-balance text-[clamp(2rem,5vw,3.6rem)] font-light leading-[1.04] !text-bg">
              Tell us about your{' '}
              <em className="not-italic" style={{ color: 'var(--olive-soft)' }}>
                plant.
              </em>
            </h2>
            <p
              className="mt-6 max-w-reading text-pretty text-lg leading-relaxed"
              style={{ color: '#C9C2B0' }}
            >
              Tonnage, suppliers, certifier, the refineries you ship to.
              Thirty-minute scoping call, no slides, no decks.
            </p>

            <div className="mt-12 space-y-5 font-mono text-sm" style={{ color: '#A39A82' }}>
              <div className="flex flex-col gap-1">
                <span
                  className="font-mono text-[0.7rem] uppercase tracking-[0.16em]"
                  style={{ color: '#7A7363' }}
                >
                  Email
                </span>
                <a
                  href="mailto:hello@dft-project.com"
                  className="text-bg hover:underline underline-offset-4"
                >
                  hello@dft-project.com
                </a>
              </div>
              <div className="flex flex-col gap-1">
                <span
                  className="font-mono text-[0.7rem] uppercase tracking-[0.16em]"
                  style={{ color: '#7A7363' }}
                >
                  Office
                </span>
                <span className="text-bg">Tenerife · Canary Islands · ES</span>
              </div>
              <div className="flex flex-col gap-1">
                <span
                  className="font-mono text-[0.7rem] uppercase tracking-[0.16em]"
                  style={{ color: '#7A7363' }}
                >
                  Reference site
                </span>
                <span className="text-bg">Girardot · Cundinamarca · CO</span>
              </div>
            </div>
          </div>

          <form
            onSubmit={handleSubmit}
            className="md:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-7"
          >
            {/* Honeypot */}
            <label className="sr-only" aria-hidden>
              Website
              <input
                type="text"
                name="website"
                tabIndex={-1}
                autoComplete="off"
              />
            </label>

            <Field name="name" label="Name" required />
            <Field name="email" type="email" label="Email" required />
            <Field name="company" label="Company" />
            <Field name="role" label="Role" placeholder="Operator · Compliance · CEO …" />

            <div className="sm:col-span-2 flex flex-col gap-2">
              <Label htmlFor="message" className="!text-[#A39A82]">
                Message
              </Label>
              <Textarea
                id="message"
                name="message"
                placeholder="Tonnage, suppliers, certifier, refinery destinations…"
                required
                className="!text-bg !border-[#33312A] focus-visible:!border-[var(--olive-soft)] !placeholder:text-[#7A7363]"
                rows={5}
              />
            </div>

            <div className="sm:col-span-2 flex items-center justify-between gap-4 pt-3 border-t" style={{ borderColor: '#33312A' }}>
              <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em]" style={{ color: '#7A7363' }}>
                We reply within one business day.
              </p>
              <Button
                type="submit"
                variant="accent"
                disabled={status === 'loading'}
                className="!bg-[var(--olive-soft)] !text-bg-deep !border-[var(--olive-soft)] hover:!bg-bg hover:!text-bg-deep hover:!border-bg"
              >
                {status === 'loading' ? (
                  'Sending…'
                ) : status === 'success' ? (
                  <>
                    Sent
                    <Check className="h-4 w-4" strokeWidth={1.6} />
                  </>
                ) : (
                  <>
                    Submit
                    <Send className="h-4 w-4" strokeWidth={1.6} />
                  </>
                )}
              </Button>
            </div>

            {status === 'error' && (
              <div
                role="alert"
                className="sm:col-span-2 flex items-start gap-3 text-accent font-mono text-[0.78rem]"
              >
                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}
            {status === 'success' && (
              <div
                role="status"
                className="sm:col-span-2 flex items-start gap-3 font-mono text-[0.78rem]"
                style={{ color: 'var(--olive-soft)' }}
              >
                <Check className="h-4 w-4 mt-0.5 shrink-0" />
                <span>Thanks. We&apos;ll be in touch shortly.</span>
              </div>
            )}
          </form>
        </div>
      </div>
    </section>
  );
}

function Field({
  name,
  label,
  type = 'text',
  required,
  placeholder,
}: {
  name: string;
  label: string;
  type?: string;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={name} className="!text-[#A39A82]">
        {label}
        {required && <span className="text-accent ml-1">*</span>}
      </Label>
      <Input
        id={name}
        name={name}
        type={type}
        required={required}
        placeholder={placeholder}
        className="!text-bg !border-[#33312A] focus-visible:!border-[var(--olive-soft)] !placeholder:text-[#7A7363]"
      />
    </div>
  );
}
