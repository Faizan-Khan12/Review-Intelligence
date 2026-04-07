'use client';

import React, { useState } from 'react';
import {
  Search,
  Package,
  TrendingUp,
  Globe,
  Filter,
  Sparkles,
  ChevronRight,
  PanelLeftClose,
  LogOut,
  Database,
  X,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn, extractAsin } from '@/lib/utils';

interface SidebarFiltersProps {
  onAnalyze: (asin: string, maxReviews: number, enableAI: boolean, country: string) => void;
  onReset: () => void;
  onLoadCachedResults?: () => void;
  onLogout?: () => void;
  onResendVerification?: () => void;
  userEmail?: string;
  emailVerified?: boolean;
  cachedLoading?: boolean;
  isLoading?: boolean;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  mobileOpen?: boolean;
  isMobile?: boolean;
}

const EXAMPLE_ASINS = [
  { asin: 'B0CHX3TYK1', label: 'Popular Headphones' },
  { asin: 'B07ZPKN6Y9', label: 'Smart Watch' },
  { asin: 'B09G9BL5CP', label: 'Kitchen Appliance' },
];

const COUNTRIES = [
  { code: 'US', label: 'United States' },
  { code: 'UK', label: 'United Kingdom' },
  { code: 'DE', label: 'Germany' },
  { code: 'FR', label: 'France' },
  { code: 'JP', label: 'Japan' },
  { code: 'CA', label: 'Canada' },
  { code: 'IN', label: 'India' },
];

const REGION_FLAG: Record<string, string> = {
  US: 'US',
  UK: 'UK',
  DE: 'DE',
  FR: 'FR',
  JP: 'JP',
  CA: 'CA',
  IN: 'IN',
};

export default function SidebarFilters({
  onAnalyze,
  onReset,
  onLoadCachedResults,
  onLogout,
  onResendVerification,
  userEmail,
  emailVerified = false,
  cachedLoading = false,
  isLoading = false,
  isCollapsed = false,
  onToggleCollapse,
  isMobile = false,
}: SidebarFiltersProps) {
  const [asin, setAsin] = useState('');
  const [maxReviews, setMaxReviews] = useState(50);
  const [country, setCountry] = useState('IN');
  const [enableAI, setEnableAI] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const extractedAsin = extractAsin(asin.trim());
    if (!extractedAsin) {
      return;
    }

    setAsin(extractedAsin);
    onAnalyze(extractedAsin, maxReviews, enableAI, country);
  };

  const handleExampleClick = (exampleAsin: string) => {
    setAsin(exampleAsin);
    onAnalyze(exampleAsin, maxReviews, enableAI, country);
  };

  if (!isMobile && isCollapsed) {
    return (
      <aside className="flex h-full flex-col items-center gap-4 border-r bg-card/80 px-2 py-4 backdrop-blur">
        <Button
          variant="outline"
          size="icon"
          onClick={onToggleCollapse}
          className="h-9 w-9"
          aria-label="Expand filters"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Separator className="w-10" />
        <Search className="h-4 w-4 text-muted-foreground" />
        <Filter className="h-4 w-4 text-muted-foreground" />
        <Globe className="h-4 w-4 text-muted-foreground" />
      </aside>
    );
  }

  return (
    <aside
      className={cn(
        'flex h-full flex-col overflow-y-auto border-r bg-card/80 p-4 backdrop-blur sm:p-5',
        isMobile && 'rounded-none border-r-0'
      )}
    >
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-foreground">Filters</h2>
          <p className="text-xs text-muted-foreground">Configure your analysis scope</p>
        </div>
        {isMobile && onToggleCollapse && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleCollapse}
            className="h-9 w-9"
            aria-label="Close filters"
          >
            <X className="h-4 w-4" />
          </Button>
        )}
        {!isMobile && onToggleCollapse && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleCollapse}
            className="h-9 w-9"
            aria-label="Collapse filters"
          >
            <PanelLeftClose className="h-4 w-4" />
          </Button>
        )}
      </div>

      <div className="mt-5 space-y-3">
        <div className="flex items-center gap-2 text-sm font-medium text-foreground">
          <Search className="h-4 w-4 text-primary" />
          Product Search
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-2">
            <Input
              type="text"
              placeholder="Enter ASIN or Amazon URL"
              value={asin}
              onChange={(e) => setAsin(e.target.value)}
              disabled={isLoading}
              className="font-mono text-xs"
            />
            <p className="text-[11px] text-muted-foreground">
              ASIN (e.g., B0CHX3TYK1) or full Amazon product URL
            </p>
          </div>

          <div className="rounded-lg border bg-muted/40 p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium">AI Analysis</span>
              </div>
              <Switch
                checked={enableAI}
                onCheckedChange={setEnableAI}
                disabled={isLoading}
                aria-label="Toggle AI analysis"
              />
            </div>
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={isLoading || !asin.trim() || asin.trim().length < 10}
          >
            {isLoading ? 'Analyzing...' : 'Analyze Reviews'}
          </Button>
        </form>
      </div>

      <Separator />

      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm font-medium text-foreground">
          <Package className="h-4 w-4 text-primary" />
          Quick Examples
        </div>

        <div className="space-y-2">
          {EXAMPLE_ASINS.map((example) => (
            <Button
              key={example.asin}
              variant="outline"
              size="sm"
              className="h-auto w-full justify-start px-3 py-2.5 text-left"
              onClick={() => handleExampleClick(example.asin)}
              disabled={isLoading}
            >
              <div className="flex min-w-0 flex-col">
                <span className="truncate font-mono text-[11px] font-semibold">{example.asin}</span>
                <span className="truncate text-[11px] text-muted-foreground">{example.label}</span>
              </div>
            </Button>
          ))}
        </div>
      </div>

      <Separator />

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-medium text-foreground">
            <TrendingUp className="h-4 w-4 text-primary" />
            Max Reviews
          </div>
          <Badge variant="outline">{maxReviews}</Badge>
        </div>

        <Slider
          value={[maxReviews]}
          onValueChange={(value) => setMaxReviews(value[0])}
          min={10}
          max={100}
          step={10}
          disabled={isLoading}
        />
        <p className="text-[11px] text-muted-foreground">More reviews improve trend and theme reliability.</p>
      </div>

      <Separator />

      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm font-medium text-foreground">
          <Globe className="h-4 w-4 text-primary" />
          Region
        </div>
        <Select value={country} onValueChange={setCountry} disabled={isLoading}>
          <SelectTrigger>
            <SelectValue placeholder="Select region" />
          </SelectTrigger>
          <SelectContent>
            {COUNTRIES.map((item) => (
              <SelectItem key={item.code} value={item.code}>
                <span className="flex items-center gap-2">
                  <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full border border-border bg-muted px-1 text-[10px] font-semibold">
                    {REGION_FLAG[item.code]}
                  </span>
                  {item.label}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="border-t pt-4">
        <Button variant="outline" className="w-full" onClick={onReset} disabled={isLoading}>
          Reset All
        </Button>
      </div>

      <div className="mt-auto border-t pt-4">
        {userEmail && (
          <p className="mb-3 truncate text-xs text-muted-foreground">
            Signed in as <span className="font-medium text-foreground">{userEmail}</span>
          </p>
        )}
        {!emailVerified && onResendVerification && (
          <Button
            variant="outline"
            className="mb-2 w-full"
            onClick={onResendVerification}
            disabled={isLoading}
          >
            Verify Email
          </Button>
        )}
        {onLoadCachedResults && (
          <Button
            variant="outline"
            className="mb-2 w-full"
            onClick={onLoadCachedResults}
            disabled={cachedLoading || isLoading}
          >
            <Database className="mr-2 h-4 w-4" />
            {cachedLoading ? 'Loading...' : 'Cached Results'}
          </Button>
        )}
        {onLogout && (
          <Button variant="outline" className="w-full" onClick={onLogout} disabled={isLoading}>
            <LogOut className="mr-2 h-4 w-4" />
            Logout
          </Button>
        )}
      </div>
    </aside>
  );
}
