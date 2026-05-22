import { Nav } from '@/components/Nav';
import { Hero } from '@/components/Hero';
import { Problem } from '@/components/Problem';
import { Solution } from '@/components/Solution';
import { Compliance } from '@/components/Compliance';
import { Stack } from '@/components/Stack';
import { CaseStudy } from '@/components/CaseStudy';
import { Pricing } from '@/components/Pricing';
import { FAQ } from '@/components/FAQ';
import { Contact } from '@/components/Contact';
import { Footer } from '@/components/Footer';

export default function Home() {
  return (
    <>
      <Nav />
      <main className="relative isolate">
        <Hero />
        <Problem />
        <Solution />
        <Compliance />
        <Stack />
        <CaseStudy />
        <Pricing />
        <FAQ />
        <Contact />
      </main>
      <Footer />
    </>
  );
}
