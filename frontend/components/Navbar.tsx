'use client';

import React, { useState, useEffect } from 'react';
import {
  Download,
  Moon,
  Sun,
  Menu,
  X,
  BarChart3,
  ChevronRight,
  ChevronLeft,
  PanelLeftClose,
  PanelLeftOpen
} from 'lucide-react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

interface NavbarProps {
  onExport?: (format: 'csv' | 'pdf' | 'xlsx') => void;
  onToggleSidebar?: () => void;
  sidebarCollapsed?: boolean;
  isMobile?: boolean;
}

export default function Navbar({
  onExport,
  onToggleSidebar,
  sidebarCollapsed,
  isMobile = false
}: NavbarProps) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  };

  return (
    <nav className="sticky top-0 z-30 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center px-3 sm:px-4 md:px-6">

        {/* Mobile Menu Button (Hamburger) */}
        {onToggleSidebar && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleSidebar}
            className={cn(
              "mr-2 sm:mr-3 transition-all duration-300",
              isMobile ? "hover:bg-primary/10" : [
                sidebarCollapsed ? "hover:bg-green-500/10" : "hover:bg-primary/10"
              ]
            )}
            aria-label={isMobile ? 'Open menu' : (sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar')}
          >
            {isMobile ? (
              <Menu className="h-5 w-5" />
            ) : sidebarCollapsed ? (
              <PanelLeftOpen className="h-5 w-5 text-green-600 dark:text-green-400" />
            ) : (
              <PanelLeftClose className="h-5 w-5 text-primary" />
            )}
          </Button>
        )}

        {/* Logo - Responsive */}
        <div className="flex items-center gap-2 mr-auto">
          <div className="relative">
            <BarChart3 className="h-5 w-5 sm:h-6 sm:w-6 text-primary" />
            <span className="absolute -top-1 -right-1 flex h-2 w-2 sm:h-3 sm:w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 sm:h-3 sm:w-3 bg-primary"></span>
            </span>
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-xs sm:text-sm md:text-base bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
              Review Intelligence
            </span>
            <span className="text-[9px] sm:text-[10px] md:text-xs text-muted-foreground hidden sm:block">
              AI-Powered Analytics
            </span>
          </div>
        </div>

        {/* Desktop Actions */}
        <div className="hidden md:flex items-center gap-2">

          {/* Export Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="gap-2 hover:bg-primary/10 transition-colors"
              >
                <Download className="h-4 w-4" />
                Export
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem
                onClick={() => onExport?.('csv')}
                className="cursor-pointer"
              >
                <span className="mr-2">📊</span> Export as CSV
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => onExport?.('xlsx')}
                className="cursor-pointer"
              >
                <span className="mr-2">📋</span> Export as Excel
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => onExport?.('pdf')}
                className="cursor-pointer"
              >
                <span className="mr-2">📄</span> Export as PDF
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Theme Toggle */}
          {mounted && (
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              aria-label="Toggle theme"
              className="hover:bg-primary/10 transition-colors"
            >
              {theme === 'dark' ? (
                <Sun className="h-4 w-4 text-yellow-500" />
              ) : (
                <Moon className="h-4 w-4 text-blue-600" />
              )}
            </Button>
          )}
        </div>

        {/* Mobile Menu */}
        <div className="flex items-center gap-2 md:hidden">
          {/* Mobile Theme Toggle */}
          {mounted && (
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              aria-label="Toggle theme"
              className="hover:bg-primary/10"
            >
              {theme === 'dark' ? (
                <Sun className="h-4 w-4 text-yellow-500" />
              ) : (
                <Moon className="h-4 w-4 text-blue-600" />
              )}
            </Button>
          )}

          {/* Mobile Export Menu */}
          <DropdownMenu open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="hover:bg-primary/10"
              >
                <Download className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem
                onClick={() => {
                  onExport?.('csv');
                  setMobileMenuOpen(false);
                }}
                className="cursor-pointer"
              >
                <span className="mr-2">📊</span> Export CSV
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => {
                  onExport?.('xlsx');
                  setMobileMenuOpen(false);
                }}
                className="cursor-pointer"
              >
                <span className="mr-2">📋</span> Export Excel
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => {
                  onExport?.('pdf');
                  setMobileMenuOpen(false);
                }}
                className="cursor-pointer"
              >
                <span className="mr-2">📄</span> Export PDF
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </nav>
  );
}
