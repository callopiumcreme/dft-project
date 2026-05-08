type Props = { title: string; sprintRef: string };

export function Placeholder({ title, sprintRef }: Props) {
  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <h1 className="font-display text-3xl tracking-editorial text-ink">{title}</h1>
        <p className="mt-3 font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          In arrivo · {sprintRef}
        </p>
      </header>
    </div>
  );
}
