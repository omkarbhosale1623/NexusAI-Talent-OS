"use client";

import { useState } from "react";
import { Bell, Search, ChevronDown, LogOut, User, Settings } from "lucide-react";
import { cn, getInitials } from "@/lib/utils";
import ThemeToggle from "@/components/layout/theme-toggle";
import LocaleSwitcher from "@/components/layout/locale-switcher";

const MOCK_USER = {
  name: "Omkar Bhosale",
  email: "omkarbhosale1623@gmail.com",
  role: "Admin",
};

const MOCK_NOTIFICATIONS = [
  { id: 1, text: "New application from Priya Singh", time: "2m ago", unread: true },
  { id: 2, text: "Interview completed — Rahul Kumar", time: "15m ago", unread: true },
  { id: 3, text: "Report ready for Ananya Mehta", time: "1h ago", unread: false },
];

interface HeaderProps {
  title?: string;
}

export default function Header({ title = "Dashboard" }: HeaderProps) {
  const [notifOpen, setNotifOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);

  const unreadCount = MOCK_NOTIFICATIONS.filter((n) => n.unread).length;

  return (
    <header className="flex h-16 items-center gap-4 bg-surface border-b border-border px-6 shrink-0">
      {/* Page title */}
      <h1 className="text-lg font-semibold text-text-primary mr-auto">{title}</h1>

      {/* Search */}
      <div className="hidden md:flex items-center gap-2 h-9 w-64 rounded-full border border-border bg-bg px-3 text-sm text-text-muted focus-within:border-brand focus-within:ring-1 focus-within:ring-brand/20 transition-all duration-100">
        <Search className="h-4 w-4 shrink-0" />
        <input
          type="text"
          placeholder="Search candidates, jobs..."
          className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted focus:outline-none"
        />
      </div>

      {/* Locale + Theme */}
      <LocaleSwitcher />
      <ThemeToggle />

      {/* Notifications */}
      <div className="relative">
        <button
          onClick={() => {
            setNotifOpen((prev) => !prev);
            setUserOpen(false);
          }}
          className="relative flex h-9 w-9 items-center justify-center rounded-full text-text-muted hover:bg-bg hover:text-text-primary transition-colors duration-100"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute top-1.5 right-1.5 flex h-2 w-2 rounded-full bg-brand" />
          )}
        </button>

        {notifOpen && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setNotifOpen(false)}
            />
            <div className="absolute right-0 top-11 z-20 w-80 rounded-lg border border-border bg-surface shadow-lg">
              <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <span className="text-sm font-semibold text-text-primary">
                  Notifications
                </span>
                {unreadCount > 0 && (
                  <span className="text-xs text-brand font-medium">
                    {unreadCount} new
                  </span>
                )}
              </div>
              <ul className="divide-y divide-border">
                {MOCK_NOTIFICATIONS.map((n) => (
                  <li
                    key={n.id}
                    className={cn(
                      "flex items-start gap-3 px-4 py-3 hover:bg-bg transition-colors duration-100 cursor-pointer",
                      n.unread && "bg-brand-light/30"
                    )}
                  >
                    {n.unread && (
                      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand" />
                    )}
                    {!n.unread && <span className="mt-1.5 h-2 w-2 shrink-0" />}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-text-primary">{n.text}</p>
                      <p className="text-xs text-text-muted mt-0.5">{n.time}</p>
                    </div>
                  </li>
                ))}
              </ul>
              <div className="px-4 py-2.5 border-t border-border">
                <button className="text-sm text-brand hover:text-brand-hover font-medium transition-colors duration-100">
                  View all notifications
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* User avatar dropdown */}
      <div className="relative">
        <button
          onClick={() => {
            setUserOpen((prev) => !prev);
            setNotifOpen(false);
          }}
          className="flex items-center gap-2 rounded-full pl-1 pr-2 py-1 hover:bg-bg transition-colors duration-100"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand text-white text-xs font-semibold">
            {getInitials(MOCK_USER.name)}
          </div>
          <span className="hidden sm:block text-sm font-medium text-text-primary max-w-28 truncate">
            {MOCK_USER.name.split(" ")[0]}
          </span>
          <ChevronDown className="h-3.5 w-3.5 text-text-muted" />
        </button>

        {userOpen && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setUserOpen(false)}
            />
            <div className="absolute right-0 top-11 z-20 w-52 rounded-lg border border-border bg-surface shadow-lg py-1">
              <div className="px-4 py-3 border-b border-border">
                <p className="text-sm font-semibold text-text-primary">
                  {MOCK_USER.name}
                </p>
                <p className="text-xs text-text-muted mt-0.5">{MOCK_USER.email}</p>
              </div>
              <ul className="py-1">
                <li>
                  <button className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-text-muted hover:bg-bg hover:text-text-primary transition-colors duration-100">
                    <User className="h-4 w-4" />
                    Profile
                  </button>
                </li>
                <li>
                  <button className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-text-muted hover:bg-bg hover:text-text-primary transition-colors duration-100">
                    <Settings className="h-4 w-4" />
                    Settings
                  </button>
                </li>
              </ul>
              <div className="border-t border-border pt-1">
                <button className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-error hover:bg-bg transition-colors duration-100">
                  <LogOut className="h-4 w-4" />
                  Sign out
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </header>
  );
}
