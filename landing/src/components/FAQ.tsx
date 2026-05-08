import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';

const FAQ_ITEMS = [
  {
    q: 'How long does deployment take?',
    a: 'Two to four weeks for a single-plant pilot, including schema seeding, supplier onboarding, role provisioning and a first dry-run mass-balance closure. Multi-plant rollouts are scoped separately.',
  },
  {
    q: 'On-premise or cloud?',
    a: 'Both. The reference deployment ships as a Docker compose stack you can run on Hetzner, AWS, GCP or your own metal. We also offer a managed installation on dedicated infrastructure if you prefer not to run it yourselves.',
  },
  {
    q: 'Is there an API?',
    a: 'Yes. Every operation in the UI is backed by a documented REST endpoint. Auth is OAuth2 / JWT; webhook callbacks are available for POS issuance, mass-balance closure events and C14 sign-off.',
  },
  {
    q: 'Multi-plant support?',
    a: 'On the 2026 roadmap. The schema is already plant-scoped and the audit log is partitioned per plant — what is missing is the consolidated dashboard, cross-plant balance and centralised certifier workflows.',
  },
  {
    q: 'What happens if a C14 sample fails?',
    a: 'The lot transitions to a rejected state and is excluded from EU output mass balance automatically. Operators can either rerun the sample, downgrade the lot to non-EU, or void it — every transition is logged.',
  },
  {
    q: 'Can we use a lab other than Saybolt?',
    a: 'Yes. Saybolt NL is the default integration partner, but the certifier model is multi-org. Add any accredited lab as a certifier organisation, provision their accounts, and they can sign off C14 results directly.',
  },
];

export function FAQ() {
  return (
    <section id="faq" className="relative py-24 md:py-32">
      <div className="container-edit">
        <div className="section-head">
          <div>
            <div className="eyebrow mb-4">§ 08 — FAQ</div>
          </div>
          <div>
            <h2 className="text-balance text-[clamp(1.9rem,4.5vw,3.4rem)] font-light leading-[1.05]">
              Things people <em className="not-italic text-olive">ask first</em>.
            </h2>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-8">
          <div className="col-span-12 md:col-span-10 md:col-start-3">
            <Accordion type="single" collapsible className="border-b border-rule">
              {FAQ_ITEMS.map((item, i) => (
                <AccordionItem
                  key={item.q}
                  value={`item-${i}`}
                  className={i === 0 ? 'border-t border-rule' : ''}
                >
                  <AccordionTrigger>
                    <span className="flex items-baseline gap-5">
                      <span className="font-mono text-sm text-ink-mute tabular hidden sm:inline">
                        {String(i + 1).padStart(2, '0')}
                      </span>
                      <span>{item.q}</span>
                    </span>
                  </AccordionTrigger>
                  <AccordionContent>{item.a}</AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        </div>
      </div>
    </section>
  );
}
