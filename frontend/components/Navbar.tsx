'use client';

import React, { useEffect, useState } from 'react';
import { Moon, Sun, BarChart3 } from 'lucide-react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';

interface NavbarProps {
  onExport?: (format: 'csv' | 'pdf' | 'xlsx') => void;
  onToggleSidebar?: () => void;
  sidebarCollapsed?: boolean;
  isMobile?: boolean;
}

export default function Navbar({}: NavbarProps) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <nav className="sticky top-0 z-40 w-full border-b border-border/80 bg-background/85 backdrop-blur-xl">
      <div className="flex h-14 items-center gap-2 px-3 sm:px-4 md:px-6">
        <div className="mr-auto flex min-w-0 items-center gap-2">
          <div className="relative grid h-9 w-9 place-items-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
            <BarChart3 className="h-4 w-4" />
            <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-primary/85" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-foreground">
              Amazon Review Intelligence
            </p>
            <p className="hidden text-[11px] text-muted-foreground sm:block">
              Executive Intelligence Console
            </p>
          </div>
        </div>

        {mounted && (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            aria-label="Toggle theme"
            className="h-9 w-9"
          >
            {theme === 'dark' ? (
              <Sun className="h-4 w-4 text-amber-400" />
            ) : (
              <Moon className="h-4 w-4 text-indigo-600" />
            )}
          </Button>
        )}
      </div>
    </nav>
  );
}
