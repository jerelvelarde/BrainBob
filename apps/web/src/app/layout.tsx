import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BrainBob — A little world inside your memory",
  description: "Watch the little workers in your brain remember, retrieve, and rethink. An interactive 3D memory office.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
