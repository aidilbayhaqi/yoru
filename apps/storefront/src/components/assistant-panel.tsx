"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";

import { Icon } from "@/components/icons";
import { products, services } from "@/lib/storefront-data";

type Message = {
  id: string;
  role: "assistant" | "user";
  text: string;
  links?: Array<{ href: string; label: string }>;
};

const initialMessages: Message[] = [
  {
    id: "welcome",
    role: "assistant",
    text: "Ceritakan kebutuhanmu, budget, atau waktu yang tersedia. Demo ini memberi rekomendasi deterministik dari katalog Yoru.",
  },
];

function recommendationFor(text: string): Message {
  const value = text.toLowerCase();
  if (value.includes("rambut") || value.includes("hair")) {
    return {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      text: "Untuk rambut kering atau sering di-styling, mulai dari Silk Repair Hair Mask. Bila ingin treatment lengkap di rumah, Hair Spa at Home lebih sesuai.",
      links: [
        { href: `/products/${products[2].slug}`, label: products[2].name },
        { href: `/services/${services[1].slug}`, label: services[1].name },
      ],
    };
  }
  if (value.includes("acara") || value.includes("wisuda") || value.includes("makeup")) {
    return {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      text: "Untuk wisuda atau acara formal, Event Makeup at Home mencakup brief look, complexion, eye makeup, dan basic hair styling.",
      links: [{ href: `/services/${services[2].slug}`, label: services[2].name }],
    };
  }
  if (value.includes("kusam") || value.includes("barrier") || value.includes("kulit")) {
    return {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      text: "Untuk rutinitas sederhana, kombinasikan Glow Reset Serum dan Barrier Cloud Moisturizer. Home Facial Reset cocok bila ingin assessment langsung.",
      links: [
        { href: `/products/${products[0].slug}`, label: products[0].name },
        { href: `/products/${products[1].slug}`, label: products[1].name },
        { href: `/services/${services[0].slug}`, label: services[0].name },
      ],
    };
  }
  return {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    text: "Kamu bisa memilih produk untuk rutinitas mandiri, atau home service untuk bantuan profesional.",
    links: [
      { href: "/products", label: "Jelajahi produk" },
      { href: "/services", label: "Jelajahi home service" },
    ],
  };
}

export function AssistantPanel() {
  const [messages, setMessages] = useState<Message[]>(initialMessages);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const text = String(data.get("message") ?? "").trim();
    if (!text) return;
    setMessages((current) => [
      ...current,
      { id: `user-${Date.now()}`, role: "user", text },
      recommendationFor(text),
    ]);
    form.reset();
  }

  return (
    <main className="assistant-page">
      <section className="assistant-intro">
        <p className="section-eyebrow">Customer AI Advisor</p>
        <h1>Bantu aku memilih.</h1>
        <p>
          Advisor ini tidak mendiagnosis kondisi medis. Rekomendasi production wajib memiliki
          consent, evidence, policy version, dan jalur eskalasi.
        </p>
      </section>
      <section className="assistant-workspace">
        <div className="assistant-messages">
          {messages.map((message) => (
            <div className={`assistant-message message-${message.role}`} key={message.id}>
              <span className="message-avatar">
                {message.role === "assistant" ? <Icon name="wand" width="18" /> : "You"}
              </span>
              <div>
                <p>{message.text}</p>
                {message.links ? (
                  <div className="assistant-links">
                    {message.links.map((link) => (
                      <Link href={link.href} key={link.href}>
                        {link.label}
                        <Icon name="arrow" width="15" />
                      </Link>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          ))}
        </div>
        <form className="assistant-form" onSubmit={submit}>
          <input
            aria-label="Pesan untuk Yoru Advisor"
            name="message"
            placeholder="Contoh: kulitku terlihat kusam, budget 400 ribu"
          />
          <button className="primary-button" type="submit">
            Kirim
            <Icon name="arrow" width="17" />
          </button>
        </form>
      </section>
    </main>
  );
}
