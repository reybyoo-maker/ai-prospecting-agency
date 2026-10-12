"use client";
import { useEffect, useRef, useState } from "react";
import { T } from "./T";
import { CATS, TOPICS } from "@/lib/consult";
import { wa } from "@/lib/data";

/** Pop up konsultasi: muncul saat tombol KONSULTASI SEKARANG diklik. Mengumpulkan kategori dan topik, lalu membuka WhatsApp dengan pesan siap kirim. */
export default function ConsultModal() {
  const [open, setOpen] = useState(false);
  const card = useRef<HTMLDivElement>(null);
  const [cat, setCat] = useState(-1), [tp, setTp] = useState<number[]>([]), [name, setName] = useState(""), [note, setNote] = useState("");
  useEffect(() => {
    const on = (e: MouseEvent) => { const a = (e.target as HTMLElement).closest("[data-chat]"); if (a) { e.preventDefault(); const k = a.getAttribute("data-cat"); if (k !== null && CATS[Number(k)]) setCat(Number(k)); const tk = a.getAttribute("data-topic"); if (tk !== null && TOPICS[Number(tk)]) setTp([Number(tk)]); setOpen(true); } };
    document.addEventListener("click", on, true); return () => document.removeEventListener("click", on, true);
  }, []);
  useEffect(() => {
    if (!open) return; document.body.style.overflow = "hidden";
    const back = document.activeElement as HTMLElement | null; card.current?.focus();
    const k = (e: KeyboardEvent) => {
      if (e.key === "Escape") { setOpen(false); return; }
      if (e.key !== "Tab" || !card.current) return;
      const f = Array.from(card.current.querySelectorAll<HTMLElement>("button:not([disabled]),a[href],input,textarea")); if (!f.length) return;
      const a = f[0], z = f[f.length - 1];
      if (e.shiftKey && (document.activeElement === a || document.activeElement === card.current)) { e.preventDefault(); z.focus(); }
      else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); }
    };
    addEventListener("keydown", k); return () => { document.body.style.overflow = ""; removeEventListener("keydown", k); back?.focus?.(); };
  }, [open]);
  if (!open) return null;
  const go = () => {
    const en = document.documentElement.dataset.lang === "en", c = cat >= 0 ? CATS[cat][en ? 1 : 0] : "", ts = tp.map((i) => TOPICS[i][en ? 1 : 0]).join(", ");
    const msg = en
      ? `Hello Rey${name ? `, I'm ${name}` : ""}. ${c ? `I'm a ${c}. ` : ""}${ts ? `I'd like to consult about: ${ts}. ` : ""}${note ? `Notes: ${note}` : ""}`
      : `Halo Rey${name ? `, aku ${name}` : ""}. ${c ? `Aku seorang ${c}. ` : ""}${ts ? `Aku mau konsultasi soal: ${ts}. ` : ""}${note ? `Catatan: ${note}` : ""}`;
    (window as unknown as { aaiTrack?: (l: string) => void }).aaiTrack?.("Konsultasi: " + (tp.length ? tp.map((i) => TOPICS[i][0]).join(", ") : "umum"));
    window.open(wa(msg.trim()), "_blank", "noopener"); setOpen(false);
  };
  const toggle = (i: number) => setTp((s) => (s.includes(i) ? s.filter((x) => x !== i) : [...s, i]));
  return (
    <div className="cm" role="dialog" aria-modal="true" aria-label="Konsultasi">
      <div className="ibg" onClick={() => setOpen(false)} />
      <div className="cmcard" ref={card} tabIndex={-1} aria-labelledby="cm-h">
        <button className="cmx" onClick={() => setOpen(false)} aria-label="Tutup / Close">×</button>
        <h2 id="cm-h"><T id="Yuk, ceritakan sedikit dulu" en="Tell us a little first" /></h2>
        <p className="isub"><T id="Supaya kami bisa langsung membantu dengan tepat. Cuma sebentar." en="So we can help you properly right away. It only takes a moment." /></p>
        <h3><T id="Kamu sebagai apa?" en="Who are you?" /></h3>
        <div className="opts">{CATS.map((c, i) => <button type="button" key={c[0]} className={cat === i ? "on" : ""} aria-pressed={cat === i} onClick={() => setCat(i)}><T id={c[0]} en={c[1]} /></button>)}</div>
        <h3><T id="Mau konsultasi tentang apa? (boleh lebih dari satu)" en="What would you like to consult about? (pick any)" /></h3>
        <div className="opts">{TOPICS.map((c, i) => <button type="button" key={c[0]} className={tp.includes(i) ? "on" : ""} aria-pressed={tp.includes(i)} onClick={() => toggle(i)}><T id={c[0]} en={c[1]} /></button>)}</div>
        <label className="fld"><T id="Namamu (boleh dikosongkan)" en="Your name (optional)" /><input value={name} onChange={(e) => setName(e.target.value)} maxLength={60} autoComplete="given-name" /></label>
        <label className="fld"><T id="Ada yang mau ditambahkan? (boleh dikosongkan)" en="Anything to add? (optional)" /><textarea value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} rows={2} /></label>
        <div className="row"><button type="button" className="btn" disabled={cat < 0} onClick={go}><T id="Lanjut ke WhatsApp" en="Continue to WhatsApp" /></button></div>
        <p className="cmskip">{cat < 0 && <span className="cmhint"><T id="Pilih salah satu dulu ya. " en="Please pick one first. " /></span>}<a href={wa()} target="_blank" rel="noopener" onClick={() => setOpen(false)}><T id="Lewati, langsung chat" en="Skip, just chat" /></a></p>
      </div>
    </div>
  );
}
