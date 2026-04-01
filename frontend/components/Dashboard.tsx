'use client';
import React, { useState, useEffect } from 'react';
import Navbar from './Navbar';
import SidebarFilters from './SidebarFilters';
import GraphArea from './GraphArea';
import InsightsPanel from './InsightsPanel';
import DetailedInsights from './DetailedInsights';
import { useToast } from '@/hooks/use-toast';
import type { AnalysisResult, CachedAnalysisResult } from '@/types';
import {
  analyzeReviews,
  formatErrorMessage,
  login,
  signup,
  logout,
  getCurrentUser,
  getCachedResults,
  type AuthUser,
} from '@/lib/api';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export default function Dashboard() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authConfirmPassword, setAuthConfirmPassword] = useState('');
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');
  const [authSubmitting, setAuthSubmitting] = useState(false);
  const [cachedResults, setCachedResults] = useState<CachedAnalysisResult[]>([]);
  const [cachedLoading, setCachedLoading] = useState(false);
  const [cachedOpen, setCachedOpen] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [currentAsin, setCurrentAsin] = useState('');
  const [sidebarMobileOpen, setSidebarMobileOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [showDetailedView, setShowDetailedView] = useState(false);
  const [aiEnabled, setAiEnabled] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [mobileAsin, setMobileAsin] = useState('');

  const { toast } = useToast();

  // Detect mobile/tablet breakpoints
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth < 1024 && window.innerWidth >= 768) {
        setSidebarCollapsed(true);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    const initAuth = async () => {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      setAuthLoading(false);
    };
    initAuth();
  }, []);

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authEmail.trim() || !authPassword) {
      toast({
        title: '❌ Missing credentials',
        description: 'Please enter both email and password.',
        variant: 'destructive',
      });
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(authEmail.trim())) {
      toast({
        title: '❌ Invalid email',
        description: 'Please enter a valid email address.',
        variant: 'destructive',
      });
      return;
    }
    if (authMode === 'signup' && authPassword !== authConfirmPassword) {
      toast({
        title: '❌ Password mismatch',
        description: 'Password and confirm password must match.',
        variant: 'destructive',
      });
      return;
    }

    setAuthSubmitting(true);
    try {
      const authFn = authMode === 'login' ? login : signup;
      const loggedInUser = await authFn(authEmail.trim(), authPassword);
      setUser(loggedInUser);
      setAuthPassword('');
      setAuthConfirmPassword('');
      toast({
        title: authMode === 'login' ? '✅ Login successful' : '✅ Signup successful',
        description: `Welcome ${loggedInUser.email}`,
      });
    } catch (error: any) {
      toast({
        title: `❌ ${authMode === 'login' ? 'Login' : 'Signup'} failed`,
        description: formatErrorMessage(error),
        variant: 'destructive',
      });
    } finally {
      setAuthSubmitting(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      setUser(null);
      setAnalysis(null);
      setCurrentAsin('');
      setCachedResults([]);
      setCachedOpen(false);
      toast({
        title: '👋 Logged out',
        description: 'Session ended successfully.',
      });
    } catch (error: any) {
      toast({
        title: '❌ Logout failed',
        description: formatErrorMessage(error),
        variant: 'destructive',
      });
    }
  };

  const handleLoadCachedResults = async () => {
    setCachedLoading(true);
    try {
      const results = await getCachedResults(20);
      setCachedResults(results);
      setCachedOpen(true);
      toast({
        title: '🗂️ Cached results loaded',
        description: `Found ${results.length} cached analyses.`,
      });
    } catch (error: any) {
      toast({
        title: '❌ Failed to load cache',
        description: formatErrorMessage(error),
        variant: 'destructive',
      });
    } finally {
      setCachedLoading(false);
    }
  };

  const handleUseCachedResult = (item: CachedAnalysisResult) => {
    if (!item.analysis) {
      toast({
        title: '⚠️ Cached payload unavailable',
        description: 'This cached item does not include full analysis payload.',
        variant: 'destructive',
      });
      return;
    }
    setAnalysis(item.analysis);
    setCurrentAsin(item.asin);
    setShowDetailedView(false);
    toast({
      title: '⚡ Loaded from cache',
      description: `Opened cached analysis for ${item.asin}.`,
    });
  };

  const handleAnalyze = async (
    asin: string,
    maxReviews: number,
    enableAI: boolean,
    country: string = 'US'
  ) => {
    if (!user) {
      toast({
        title: '🔒 Login required',
        description: 'Please login or signup before running analysis.',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);
    setCurrentAsin(asin);
    setShowDetailedView(false);
    setAiEnabled(enableAI);

    if (isMobile) {
      setSidebarMobileOpen(false);
    }

    try {
      toast({
        title: enableAI ? '🧠 Starting AI Analysis' : '📋 Fetching Reviews',
        description: `Processing up to ${maxReviews} reviews for ASIN: ${asin}`,
      });

      const result = await analyzeReviews({
        asin: asin,
        max_reviews: maxReviews,
        enable_ai: enableAI,
        country: country,
      });

      console.log('✅ Analysis result received:', {
        success: result.success,
        total_reviews: result.total_reviews,
        has_reviews: (result.reviews?.length || 0) > 0,
        data_source: result.data_source,
      });

      if (result.success && result.total_reviews > 0) {
        setAnalysis(result);

        const dataSource = result.data_source || 'unknown';
        const sourceEmoji = dataSource === 'apify' ? '🌐' : dataSource === 'mock' ? '🎭' : '❓';

        toast({
          title: `✅ Analysis Complete!`,
          description: `${sourceEmoji} Analyzed ${result.total_reviews} reviews from ${dataSource}`,
        });
      } else {
        toast({
          title: '⚠️ No Reviews Found',
          description: `No reviews available for ASIN: ${asin}. Try a different product.`,
          variant: 'destructive',
        });
      }
    } catch (error: any) {
      console.error('❌ Analysis error:', error);
      const errorMessage = formatErrorMessage(error);

      toast({
        title: '❌ Analysis Failed',
        description: errorMessage,
        variant: 'destructive',
      });

      setAnalysis(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExport = async (format: 'csv' | 'pdf' | 'xlsx') => {
    if (!analysis) {
      toast({
        title: '⚠️ No Data',
        description: 'Please analyze reviews first',
        variant: 'destructive',
      });
      return;
    }

    try {
      toast({
        title: `📥 Exporting ${format.toUpperCase()}`,
        description: 'Preparing your file...',
      });

      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      // Map format to backend endpoint (csv endpoint generates xlsx)
      const endpoint = format === 'xlsx' ? 'csv' : format;
      const fileExt = format === 'csv' ? 'xlsx' : format;

      const response = await fetch(`${API_URL}/api/v1/export/${endpoint}`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ analysis_data: analysis }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `Export failed: ${response.statusText}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `amazon-review-analysis-${analysis.asin}-${Date.now()}.${fileExt}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast({
        title: '✅ Export Complete',
        description: `Downloaded ${format.toUpperCase()} file`,
      });
    } catch (error: any) {
      console.error('Export error:', error);
      toast({
        title: '❌ Export Failed',
        description: error.message || 'Unable to export file. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleReset = () => {
    setAnalysis(null);
    setCurrentAsin('');
    setShowDetailedView(false);
    setIsLoading(false);

    toast({
      title: '🔄 Reset Complete',
      description: 'Ready for new analysis',
    });
  };

  const handleShowDetails = () => {
    if (analysis) {
      setShowDetailedView(true);
    }
  };

  const handleBackFromDetails = () => {
    setShowDetailedView(false);
  };

  if (showDetailedView && analysis) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <Navbar
          onExport={handleExport}
          onToggleSidebar={() => {
            if (isMobile) {
              setSidebarMobileOpen(!sidebarMobileOpen);
            } else {
              setSidebarCollapsed(!sidebarCollapsed);
            }
          }}
          sidebarCollapsed={sidebarCollapsed}
          isMobile={isMobile}
        />
        <div className="px-4 md:px-6 py-2 border-b bg-muted/20 flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Logged in as <span className="font-medium text-foreground">{user?.email}</span></span>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleLoadCachedResults} disabled={cachedLoading}>
              {cachedLoading ? 'Loading…' : 'Cached Results'}
            </Button>
            <Button variant="outline" size="sm" onClick={handleLogout}>Logout</Button>
          </div>
        </div>
        <DetailedInsights
          analysis={analysis}
          onBack={handleBackFromDetails}
        />
      </div>
    );
  }

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-muted-foreground">Checking session...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <Navbar />
        <div className="flex-1 flex items-center justify-center p-4">
          <form onSubmit={handleAuthSubmit} className="w-full max-w-sm space-y-4 border rounded-lg p-6 bg-card">
            <div className="space-y-1">
              <h2 className="text-xl font-semibold">{authMode === 'login' ? 'Login' : 'Create Account'}</h2>
              <p className="text-sm text-muted-foreground">
                {authMode === 'login'
                  ? 'Login to access analysis and exports.'
                  : 'Signup to start using protected features.'}
              </p>
            </div>

            <div className="space-y-2">
              <Input
                type="email"
                placeholder="Email"
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                required
              />
              <Input
                type="password"
                placeholder="Password (min 8 chars)"
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                minLength={8}
                required
              />
              {authMode === 'signup' && (
                <Input
                  type="password"
                  placeholder="Confirm password"
                  value={authConfirmPassword}
                  onChange={(e) => setAuthConfirmPassword(e.target.value)}
                  minLength={8}
                  required
                />
              )}
            </div>

            <Button type="submit" className="w-full" disabled={authSubmitting}>
              {authSubmitting ? 'Please wait...' : authMode === 'login' ? 'Login' : 'Signup'}
            </Button>

            <Button
              type="button"
              variant="ghost"
              className="w-full"
              onClick={() => setAuthMode(authMode === 'login' ? 'signup' : 'login')}
              disabled={authSubmitting}
            >
              {authMode === 'login' ? 'Need an account? Signup' : 'Already have an account? Login'}
            </Button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar
        onExport={handleExport}
        onToggleSidebar={() => {
          if (isMobile) {
            setSidebarMobileOpen(!sidebarMobileOpen);
          } else {
            setSidebarCollapsed(!sidebarCollapsed);
          }
        }}
        sidebarCollapsed={sidebarCollapsed}
        isMobile={isMobile}
      />
      <div className="px-4 md:px-6 py-2 border-b bg-muted/20 flex items-center justify-between text-sm">
        <span className="text-muted-foreground">Logged in as <span className="font-medium text-foreground">{user.email}</span></span>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleLoadCachedResults} disabled={cachedLoading}>
            {cachedLoading ? 'Loading…' : 'Cached Results'}
          </Button>
          <Button variant="outline" size="sm" onClick={handleLogout}>Logout</Button>
        </div>
      </div>
      {cachedOpen && (
        <div className="px-4 md:px-6 py-3 border-b bg-background">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold">Recent Cached Results</h3>
            <Button variant="ghost" size="sm" onClick={() => setCachedOpen(false)}>Hide</Button>
          </div>
          {cachedResults.length === 0 ? (
            <p className="text-sm text-muted-foreground">No cached results found.</p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {cachedResults.map((item) => (
                <div key={item.key} className="border rounded-md p-3 bg-muted/10">
                  <div className="text-sm font-medium">{item.asin} ({item.country})</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    Reviews: {item.total_reviews} | Rating: {Number(item.average_rating || 0).toFixed(1)}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {item.timestamp ? new Date(item.timestamp).toLocaleString() : 'Unknown time'}
                  </div>
                  <Button
                    size="sm"
                    className="mt-2 w-full"
                    onClick={() => handleUseCachedResult(item)}
                    disabled={!item.analysis}
                  >
                    {item.analysis ? 'Open Cached Analysis' : 'No Payload'}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        <div
          className={cn(
            "fixed top-14 bottom-0 left-0 z-40 flex-shrink-0 bg-background border-r transition-all duration-300 ease-in-out",
            "lg:relative lg:top-0 lg:z-0",
            isMobile
              ? sidebarMobileOpen
                ? "translate-x-0 w-[85vw] max-w-80"
                : "-translate-x-full w-0"
              : sidebarCollapsed
                ? "w-0 lg:w-16"
                : "w-80"
          )}
        >
          {(isMobile ? sidebarMobileOpen : true) && (
            <SidebarFilters
              onAnalyze={handleAnalyze}
              onReset={handleReset}
              isLoading={isLoading}
              isCollapsed={!isMobile && sidebarCollapsed}
            />
          )}
        </div>

        {isMobile && sidebarMobileOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-30 lg:hidden"
            onClick={() => setSidebarMobileOpen(false)}
          />
        )}

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className={cn(
            "flex-1 flex flex-col min-h-0 overflow-auto",
            "bg-gradient-to-br from-background via-background to-muted/20"
          )}>
            {!analysis && !isLoading && (
              <div className="flex-1 flex items-center justify-center p-4">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (mobileAsin.trim()) {
                      handleAnalyze(mobileAsin.trim(), 50, true, 'US');
                    }
                  }}
                  className="w-full max-w-md space-y-4"
                >
                  <div className="text-center space-y-2 mb-6">
                    <h2 className="text-xl sm:text-2xl font-bold">Start Analysis</h2>
                    <p className="text-muted-foreground text-sm">
                      Enter an Amazon ASIN or use the sidebar filters
                    </p>
                  </div>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <input
                      type="text"
                      value={mobileAsin}
                      onChange={(e) => setMobileAsin(e.target.value)}
                      placeholder="Enter Amazon ASIN"
                      className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                    <button
                      type="submit"
                      disabled={isLoading || !mobileAsin.trim()}
                      className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
                    >
                      {isLoading ? 'Analyzing…' : 'Analyze Reviews'}
                    </button>
                  </div>
                </form>
              </div>
            )}

            <GraphArea
              analysis={analysis}
              isLoading={isLoading}
              aiEnabled={aiEnabled}
              onViewDetails={handleShowDetails}
            />
          </div>

          {/* Insights Panel - stacks below graph on mobile/tablet, side panel on lg+ */}
          {analysis && (
            <div className={cn(
              "w-full border-t bg-background overflow-auto",
              "lg:hidden",
              "max-h-[50vh]"
            )}>
              <InsightsPanel
                analysis={analysis}
                isLoading={isLoading}
                aiEnabled={aiEnabled}
              />
            </div>
          )}
        </div>

        {/* Desktop-only side InsightsPanel */}
        <div className={cn(
          "hidden lg:block lg:w-80 xl:w-96 border-l bg-background overflow-auto flex-shrink-0"
        )}>
          <InsightsPanel
            analysis={analysis}
            isLoading={isLoading}
            aiEnabled={aiEnabled}
          />
        </div>
      </div>
    </div>
  );
}
