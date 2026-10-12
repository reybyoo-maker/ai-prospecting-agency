import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans, Fredoka } from "next/font/google";
import "./globals.css";
import Scene from "@/components/Scene";
import ConsultModal from "@/components/ConsultModal";
import Dock from "@/components/Dock";
import Fx from "@/components/Fx";
import ScrollBubble from "@/components/ScrollBubble";
import { PeekBot } from "@/components/Robot";
import { T } from "@/components/T";
import { SITE, SITE_NAME, pageMeta } from "@/lib/seo";
import { SOCIALS, WA_NUMBER } from "@/lib/data";
const HQ = process.env.NEXT_PUBLIC_HQ_URL || "https://agencyai-hq.reybyoo.workers.dev";
const disp = Fredoka({ subsets: ["latin"], weight: ["600", "700"], variable: "--font-display" });
const sora = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--font" });
const DESC = "Asisten AI yang membalas chat, mencari calon pelanggan, membuat konten, dan mengurus kerjaan berulang untuk bisnis, belajar, dan kerja sehari-hari.";
export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  applicationName: SITE_NAME,
  ...pageMeta("AGENCY AI by Reynaldi — Asisten AI untuk Bisnis dan Belajar", DESC, "/"),
};
export const viewport: Viewport = { themeColor: "#e0f2fe", width: "device-width", initialScale: 1, viewportFit: "cover" };
// Data terstruktur untuk mesin pencari. Hanya berisi fakta yang sudah ada di website (nama, alamat, WhatsApp, akun sosmed bisnis).
const LD = { "@context": "https://schema.org", "@type": "ProfessionalService", name: SITE_NAME, url: SITE, description: DESC, telephone: `+${WA_NUMBER}`, sameAs: SOCIALS.filter((s) => s.k !== "wa" && s.n !== "Instagram Pribadi").map((s) => s.h) };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="id" data-lang="id" suppressHydrationWarning className={`${sora.variable} ${disp.variable}`}><head><script dangerouslySetInnerHTML={{ __html: `try{var l=localStorage.getItem("lang")||"id";document.documentElement.dataset.lang=l;document.documentElement.lang=l;var n=navigator;if(matchMedia("(max-width:900px)").matches||matchMedia("(hover:none)").matches||(n.hardwareConcurrency||8)<=4||(n.deviceMemory||8)<=4)document.documentElement.classList.add("lite");if(sessionStorage.getItem("intro"))document.documentElement.classList.add("seen");}catch(e){}` }} /><script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(LD).replace(/</g, "\\u003c") }} /></head><body><a className="skip" href="#top"><T id="Lewati ke konten utama" en="Skip to main content" /></a><Scene /><Fx />{children}<PeekBot /><ScrollBubble /><Dock /><ConsultModal /><script async src={`${HQ}/embed.js`} /></body></html>;
}
