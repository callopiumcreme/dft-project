import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Terms of Use',
  description:
    'Terms governing access to and use of the DFT mass-balance and traceability platform, including jurisdiction-specific provisions for the United Kingdom, European Union, Switzerland and Colombia.',
  alternates: { canonical: '/terms' },
};

const LAST_UPDATED = '28 May 2026';
const VERSION = '1.0';

export default function TermsPage() {
  return (
    <main className="mx-auto max-w-reading px-6 py-16 text-ink">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Legal
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
          Terms of Use
        </h1>
        <p className="mt-3 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-ink-mute">
          Version {VERSION} · Last updated {LAST_UPDATED}
        </p>
      </header>

      <section className="mt-10 space-y-4 text-ink-soft">
        <h2 className="font-display text-xl tracking-editorial text-ink">
          1. Scope and acceptance
        </h2>
        <p>
          These Terms of Use (the &ldquo;Terms&rdquo;) govern access to and use
          of the DFT mass-balance and traceability platform (the
          &ldquo;Platform&rdquo;), operated for and on behalf of OisteBio GmbH,
          Oberneuhofstrasse 5, 6340 Baar, Switzerland (MWSt CHE-234.625.162)
          (the &ldquo;Operator&rdquo;). By accessing the Platform you accept
          these Terms in full. If you do not accept them, you must not use the
          Platform.
        </p>
      </section>

      <section className="mt-8 space-y-4 text-ink-soft">
        <h2 className="font-display text-xl tracking-editorial text-ink">
          2. Authorised users
        </h2>
        <p>
          The Platform is provided strictly for the use of the Operator&rsquo;s
          staff, designated buyers, authorised regulators (including the United
          Kingdom Department for Transport and accredited ISCC EU auditors) and
          third parties expressly invited by the Operator. Account credentials
          are personal, non-transferable, and must not be shared.
        </p>
      </section>

      <section className="mt-8 space-y-4 text-ink-soft">
        <h2 className="font-display text-xl tracking-editorial text-ink">
          3. Permitted use and intellectual property
        </h2>
        <p>
          All content, records, certificates, technical layouts and software
          components forming part of the Platform are the property of the
          Operator or its licensors, and are protected under the Berne
          Convention for the Protection of Literary and Artistic Works (1886,
          as revised) and the WIPO Copyright Treaty (1996). You are granted a
          limited, revocable, non-exclusive licence to access the Platform for
          audit, compliance, contractual or commercial purposes consistent with
          your role. Any other use &mdash; including reproduction, public
          disclosure, redistribution, reverse engineering, or training of
          machine-learning models &mdash; is prohibited save where expressly
          permitted in writing.
        </p>
      </section>

      <section className="mt-8 space-y-4 text-ink-soft">
        <h2 className="font-display text-xl tracking-editorial text-ink">
          4. Confidentiality
        </h2>
        <p>
          Mass-balance ledgers, commercial pricing, supplier identities and any
          information designated as confidential are protected under the
          Operator&rsquo;s confidentiality obligations and may be disclosed only
          to the extent strictly necessary for audit, regulatory or contractual
          purposes. You agree to maintain the confidentiality of such
          information consistent with the standards of Article 39 of the WTO
          TRIPS Agreement (1994) on the protection of undisclosed information.
        </p>
      </section>

      <section className="mt-8 space-y-4 text-ink-soft">
        <h2 className="font-display text-xl tracking-editorial text-ink">
          5. Compliance framework
        </h2>
        <p>
          Records generated through the Platform are produced in support of
          obligations under:
        </p>
        <ul className="ml-5 list-disc space-y-1">
          <li>
            <span className="font-mono text-ink">United Kingdom</span> &mdash;
            Renewable Transport Fuel Obligations Order 2007 (as amended,
            S.I. 2007/3072), in particular Articles 4, 8 and 17; Renewable
            Transport Fuels and Greenhouse Gas Emissions Regulations 2018
            (S.I. 2018/374).
          </li>
          <li>
            <span className="font-mono text-ink">European Union</span> &mdash;
            Directive (EU) 2018/2001 of the European Parliament and of the
            Council of 11 December 2018 on the promotion of the use of energy
            from renewable sources (RED II), Articles 29 and 30 on sustainability
            and traceability of biofuels and bioliquids; ISCC EU voluntary
            scheme as recognised under Commission Implementing Regulation (EU)
            2022/996.
          </li>
          <li>
            <span className="font-mono text-ink">Switzerland</span> &mdash;
            Swiss Code of Obligations (CO/OR) of 30 March 1911, Articles 1, 19
            and 957&ndash;963b on commercial books and records; nLPD (Federal Act
            on Data Protection) of 25 September 2020, in force 1 September 2023.
          </li>
          <li>
            <span className="font-mono text-ink">Colombia</span> &mdash;
            Resoluci&oacute;n 40177 de 2020 of the Ministry of Mines and Energy
            on biofuel quality and traceability; Ley 527 de 1999 on electronic
            commerce, Articles 5 to 13 on the legal effect of electronic
            documents; Ley 1581 de 2012 and Decreto 1377 de 2013 on personal
            data protection.
          </li>
        </ul>
      </section>

      <section className="mt-8 space-y-4 text-ink-soft">
        <h2 className="font-display text-xl tracking-editorial text-ink">
          6. Data protection
        </h2>
        <p>
          Personal data processed through the Platform is handled in accordance
          with Regulation (EU) 2016/679 (GDPR), in particular Articles 5, 6,
          13, 15 and 32; the United Kingdom General Data Protection Regulation
          (UK GDPR) as retained by the Data Protection Act 2018; the Swiss
          nLPD; and, for Colombian data subjects, Ley 1581 de 2012 and Decreto
          1377 de 2013. Lawful bases for processing include compliance with
          legal obligations (Article 6(1)(c) GDPR) and the legitimate
          interests of the Operator (Article 6(1)(f) GDPR). Requests under
          Articles 15 to 22 GDPR may be addressed to the contact below.
        </p>
      </section>

      <section className="mt-8 space-y-4 text-ink-soft">
        <h2 className="font-display text-xl tracking-editorial text-ink">
          7. Audit trail and electronic records
        </h2>
        <p>
          The Platform maintains an immutable audit log of user actions.
          Electronic records produced by the Platform are intended to satisfy
          the requirements of Regulation (EU) No 910/2014 (eIDAS) for
          electronic documents within the EU, Section 7 of the United Kingdom
          Electronic Communications Act 2000, Articles 14 and 14a of the Swiss
          Code of Obligations on electronic signatures and books, and Articles
          6 to 10 of Ley 527 de 1999 of Colombia on the legal validity of data
          messages.
        </p>
      </section>

      <section className="mt-8 space-y-4 text-ink-soft">
        <h2 className="font-display text-xl tracking-editorial text-ink">
          8. No warranty &middot; Limitation of liability
        </h2>
        <p>
          The Platform is provided on an &ldquo;as is&rdquo; and &ldquo;as
          available&rdquo; basis. To the maximum extent permitted by applicable
          law, the Operator excludes all implied warranties, including those
          of merchantability and fitness for a particular purpose. The
          Operator&rsquo;s aggregate liability arising out of or in connection
          with these Terms shall not exceed the lower of (a) the fees paid to
          the Operator in the twelve months preceding the event giving rise to
          the claim and (b) CHF 10,000. Nothing in these Terms limits liability
          which cannot be limited by law, including liability for fraud, gross
          negligence or wilful misconduct.
        </p>
      </section>

      <section className="mt-8 space-y-4 text-ink-soft">
        <h2 className="font-display text-xl tracking-editorial text-ink">
          9. Governing law and jurisdiction
        </h2>
        <p>
          These Terms are governed by the substantive law of Switzerland,
          excluding its conflict-of-laws rules and the United Nations
          Convention on Contracts for the International Sale of Goods (Vienna,
          1980). The ordinary courts of the Canton of Zug, Switzerland, shall
          have exclusive jurisdiction over any dispute, subject to mandatory
          consumer-protection provisions of the user&rsquo;s habitual residence
          where applicable. Nothing in this clause prevents the Operator from
          seeking interim or protective relief in any court of competent
          jurisdiction.
        </p>
      </section>

      <section className="mt-8 space-y-4 text-ink-soft">
        <h2 className="font-display text-xl tracking-editorial text-ink">
          10. Amendments
        </h2>
        <p>
          The Operator may amend these Terms at any time. The version in force
          at the moment of access governs the use of the Platform. The current
          version number and update date are shown at the top of this page.
        </p>
      </section>

      <section className="mt-8 space-y-4 text-ink-soft">
        <h2 className="font-display text-xl tracking-editorial text-ink">
          11. Contact
        </h2>
        <p>
          OisteBio GmbH &mdash; Oberneuhofstrasse 5, 6340 Baar, Switzerland.
          MWSt CHE-234.625.162. For data-protection requests or legal notices:{' '}
          <a
            href="mailto:export@oistebio.ch"
            className="font-mono text-ink underline decoration-rule underline-offset-4 hover:decoration-ink"
          >
            export@oistebio.ch
          </a>
          .
        </p>
      </section>

      <p className="mt-10 border-t border-rule pt-6 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
        This document is published for transparency. It does not constitute
        legal advice. Where translation is provided, the English version
        prevails.
      </p>
    </main>
  );
}
