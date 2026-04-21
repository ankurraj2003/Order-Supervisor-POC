import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import DashboardIcon from "@mui/icons-material/Dashboard";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import SyncIcon from "@mui/icons-material/Sync";
import Image from "next/image";

export const metadata: Metadata = {
  title: "Order Supervisor — AI-Powered Order Monitoring",
  description: "Long-running AI supervisor that oversees orders from creation to completion",
};

function Sidebar() {
  return (
    <aside className="hidden md:flex fixed left-0 top-0 h-full w-[240px] border-r border-border bg-surface/80 backdrop-blur-xl z-50 flex-col">
      {/* Logo */}
      <div className="p-5 border-b border-border">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-8 h-8 flex items-center justify-center transition-transform group-hover:scale-105">
            <Image src="/parcel.png" alt="OS Logo" width={32} height={32} className="object-contain" />
          </div>
          <div>
            <div className="text-sm font-semibold text-foreground">Order Supervisor</div>
            <div className="text-xs text-muted">AI Monitoring</div>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        <NavItem href="/" icon={<DashboardIcon fontSize="small" />} label="Dashboard" />
        <NavItem href="/supervisors" icon={<SmartToyIcon fontSize="small" />} label="Supervisors" />
        <NavItem href="/runs" icon={<SyncIcon fontSize="small" />} label="Runs" />
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <div className="text-xs text-muted">
          <div>Order Supervisor POC</div>
          <div className="text-muted/60 mt-1">v1.0.0</div>
        </div>
      </div>
    </aside>
  );
}

function BottomNav() {
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 border-t border-border bg-surface/90 backdrop-blur-xl z-50 flex justify-around p-2">
      <BottomNavItem href="/" icon={<DashboardIcon />} label="Dashboard" />
      <BottomNavItem href="/supervisors" icon={<SmartToyIcon />} label="Supervisors" />
      <BottomNavItem href="/runs" icon={<SyncIcon />} label="Runs" />
    </nav>
  );
}

function NavItem({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-muted-light hover:text-foreground hover:bg-surface-hover transition-all duration-150"
    >
      <span className="text-base flex items-center">{icon}</span>
      <span>{label}</span>
    </Link>
  );
}

function BottomNavItem({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link
      href={href}
      className="flex flex-col items-center justify-center p-2 text-muted-light hover:text-primary transition-colors"
    >
      <span className="mb-1">{icon}</span>
      <span className="text-[10px] font-medium">{label}</span>
    </Link>
  );
}

function MobileHeader() {
  return (
    <header className="md:hidden sticky top-0 left-0 right-0 border-b border-border bg-surface/90 backdrop-blur-xl z-50 flex items-center gap-3 p-4">
      <div className="w-8 h-8 flex items-center justify-center">
        <Image src="/parcel.png" alt="OS Logo" width={32} height={32} className="object-contain" />
      </div>
      <div className="text-sm font-semibold text-foreground">Order Supervisor</div>
    </header>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
      </head>
      <body className="antialiased">
        <Sidebar />
        <MobileHeader />
        <BottomNav />
        <main className="md:ml-[240px] min-h-screen pb-16 md:pb-0">
          <div className="max-w-[1400px] mx-auto p-4 md:p-6">
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}
