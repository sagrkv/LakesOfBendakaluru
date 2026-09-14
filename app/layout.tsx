import type { Metadata, Viewport } from "next";
import { Instrument_Sans, Instrument_Serif, Noto_Serif_Kannada } from "next/font/google";
import { share, SITE_HOST, SITE_NAME } from "@/lib/share";
import "./globals.css";

const serif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  variable: "--font-serif-face",
  display: "swap",
});

const sans = Instrument_Sans({
  subsets: ["latin"],
  variable: "--font-sans-face",
  display: "swap",
});

const kannada = Noto_Serif_Kannada({
  subsets: ["kannada"],
  weight: "600",
  variable: "--font-kannada-face",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(`https://${SITE_HOST}`),
  ...share(
    SITE_NAME,
    "Every lake in Bengaluru: how big it is, who looks after it, how clean its water is, how much of it is built over, and every map and report of it since 1800.",
  ),
  authors: [{ name: "filtercoffee.dev", url: "https://filtercoffee.dev" }],
  publisher: "filtercoffee.dev",
};

export const viewport: Viewport = {
  themeColor: "#F6EEDB",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      data-scroll-behavior="smooth"
      className={`${serif.variable} ${sans.variable} ${kannada.variable}`}
    >
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
