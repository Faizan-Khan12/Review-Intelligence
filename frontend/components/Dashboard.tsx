'use client';
import React, { useState, useEffect, useRef } from 'react';
import Navbar from './Navbar';
import SidebarFilters from './SidebarFilters';
import GraphArea from './GraphArea';
import InsightsPanel from './InsightsPanel';
import DetailedInsights from './DetailedInsights';
import { useToast } from '@/hooks/use-toast';
import type { AnalysisResult, CachedAnalysisResult } from '@/types';
import {
  analyzeReviews,
  bootstrapAuthFromUrl,
  formatErrorMessage,
  login,
  signup,
  logout,
  getCurrentUser,
  getCachedResults,
  requestEmailVerification,
  requestPasswordReset,
  confirmPasswordReset,
  type AuthUser,
} from '@/lib/api';
import { cn, extractAsin } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export default function Dashboard() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authConfirmPassword, setAuthConfirmPassword] = useState('');
  const [authMode, setAuthMode] = useState<'login' | 'signup' | 'forgot'>('login');
  const [authSubmitting, setAuthSubmitting] = useState(false);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [resetPassword, setResetPassword] = useState('');
  const [resetConfirmPassword, setResetConfirmPassword] = useState('');
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
  const cacheRequestInFlightRef = useRef(false);
  const lastCacheFetchAtRef = useRef(0);

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
      try {
        const bootstrap = await bootstrapAuthFromUrl();

        if (bootstrap.user) {
          setUser(bootstrap.user);
          toast({
            title: '✅ Email verified',
            description: 'Your account is now verified.',
          });
        }

        if (bootstrap.resetToken) {
          setResetToken(bootstrap.resetToken);
          setAuthMode('forgot');
        }

        const currentUser = bootstrap.user || (await getCurrentUser());
        setUser(currentUser);
      } catch (error: any) {
        toast({
          title: '❌ Authentication link failed',
          description: formatErrorMessage(error),
          variant: 'destructive',
        });
        try {
          const currentUser = await getCurrentUser();
          setUser(currentUser);
        } catch {
          setUser(null);
        }
      } finally {
        setAuthLoading(false);
      }
    };
    initAuth();
  }, []);

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(authEmail.trim())) {
      toast({
        title: '❌ Invalid email',
        description: 'Please enter a valid email address.',
        variant: 'destructive',
      });
      return;
    }
    if (authMode === 'forgot') {
      setAuthSubmitting(true);
      try {
        await requestPasswordReset(authEmail.trim());
        toast({
          title: '📩 Reset email sent',
          description: 'If the account exists, a reset link has been sent.',
        });
      } catch (error: any) {
        toast({
          title: '❌ Password reset request failed',
          description: formatErrorMessage(error),
          variant: 'destructive',
        });
      } finally {
        setAuthSubmitting(false);
      }
      return;
    }

    if (!authPassword) {
      toast({
        title: '❌ Missing credentials',
        description: 'Please enter both email and password.',
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
      if (!loggedInUser.email_verified) {
        toast({
          title: '📧 Email verification required',
          description: 'Check your inbox for the verification link.',
        });
      }
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

  const handleResendVerification = async () => {
    try {
      await requestEmailVerification(user?.email);
      toast({
        title: '📧 Verification email sent',
        description: 'Please check your inbox.',
      });
    } catch (error: any) {
      toast({
        title: '❌ Unable to send verification email',
        description: formatErrorMessage(error),
        variant: 'destructive',
      });
    }
  };

  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetToken) {
      toast({
        title: '❌ Missing reset token',
        description: 'Use the reset link from your email.',
        variant: 'destructive',
      });
      return;
    }
    if (!resetPassword || !resetConfirmPassword) {
      toast({
        title: '❌ Missing password',
        description: 'Enter and confirm your new password.',
        variant: 'destructive',
      });
      return;
    }
    if (resetPassword !== resetConfirmPassword) {
      toast({
        title: '❌ Password mismatch',
        description: 'Password and confirm password must match.',
        variant: 'destructive',
      });
      return;
    }

    setAuthSubmitting(true);
    try {
      const nextUser = await confirmPasswordReset(resetToken, resetPassword);
      setUser(nextUser);
      setResetPassword('');
      setResetConfirmPassword('');
      setResetToken(null);
      setAuthMode('login');
      toast({
        title: '✅ Password reset successful',
        description: 'You are now logged in with your new password.',
      });
    } catch (error: any) {
      toast({
        title: '❌ Password reset failed',
        description: formatErrorMessage(error),
        variant: 'destructive',
      });
    } finally {
      setAuthSubmitting(false);
    }
  };

  const handleLoadCachedResults = async () => {
    if (cacheRequestInFlightRef.current) {
      return;
    }

    if (!user?.email_verified) {
      toast({
        title: '📧 Verify your email',
        description: 'Please verify your email before loading cached protected data.',
        variant: 'destructive',
      });
      return;
    }

    const now = Date.now();
    const recentlyFetched = now - lastCacheFetchAtRef.current < 8000;
    if (cachedOpen && cachedResults.length > 0 && recentlyFetched) {
      toast({
        title: '🗂️ Cached results already up to date',
        description: `Showing ${cachedResults.length} cached analyses.`,
      });
      return;
    }

    cacheRequestInFlightRef.current = true;
    setCachedLoading(true);
    try {
      const results = await getCachedResults(20);
      setCachedResults(results);
      setCachedOpen(true);
      lastCacheFetchAtRef.current = Date.now();
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
      cacheRequestInFlightRef.current = false;
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
    asinInput: string,
    maxReviews: number,
    enableAI: boolean,
    country: string = 'IN'
  ) => {
    const normalizedAsin = extractAsin(asinInput);
    if (!normalizedAsin) {
      toast({
        title: '❌ Invalid product input',
        description: 'Enter a valid 10-character ASIN or Amazon product URL.',
        variant: 'destructive',
      });
      return;
    }

    if (!user) {
      toast({
        title: '🔒 Login required',
        description: 'Please login or signup before running analysis.',
        variant: 'destructive',
      });
      return;
    }
    if (!user.email_verified) {
      toast({
        title: '📧 Verify your email',
        description: 'Please verify your email before using analysis or export.',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);
    setCurrentAsin(normalizedAsin);
    setShowDetailedView(false);
    setAiEnabled(enableAI);

    if (isMobile) {
      setSidebarMobileOpen(false);
    }

    try {
      toast({
        title: enableAI ? '🧠 Starting AI Analysis' : '📋 Fetching Reviews',
        description: `Processing up to ${maxReviews} reviews for ASIN: ${normalizedAsin}`,
      });

      const result = await analyzeReviews({
        asin: normalizedAsin,
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
          description: `No reviews available for ASIN: ${normalizedAsin}. Try a different product.`,
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
  const analysisProductTitle = analysis?.product_info?.title?.trim()
    || (analysis?.asin ? `Product ${analysis.asin}` : currentAsin ? `Product ${currentAsin}` : 'Product');

  if (showDetailedView && analysis) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <Navbar />
        <DetailedInsights
          analysis={analysis}
          onBack={handleBackFromDetails}
        />
      </div>
    );
  }

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <div className="executive-surface w-full max-w-sm rounded-xl p-8 text-center">
          <div className="mx-auto mb-4 h-9 w-9 animate-spin rounded-full border-2 border-primary border-b-transparent" />
          <p className="text-sm text-muted-foreground">Checking session...</p>
        </div>
      </div>
    );
  }

  if (resetToken) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <Navbar />
        <div className="flex flex-1 items-center justify-center p-4">
          <form
            onSubmit={handleResetPasswordSubmit}
            className="executive-surface w-full max-w-sm space-y-4 rounded-xl p-6 sm:p-7"
          >
            <div className="space-y-1">
              <h2 className="text-xl font-semibold">Set New Password</h2>
              <p className="text-sm text-muted-foreground">
                Create a strong password for your executive workspace.
              </p>
            </div>
            <div className="space-y-2.5">
              <Input
                type="password"
                placeholder="New password"
                value={resetPassword}
                onChange={(e) => setResetPassword(e.target.value)}
                required
              />
              <Input
                type="password"
                placeholder="Confirm new password"
                value={resetConfirmPassword}
                onChange={(e) => setResetConfirmPassword(e.target.value)}
                required
              />
              <p className="text-[11px] text-muted-foreground">
                Use at least 8 characters including a number and symbol.
              </p>
            </div>
            <Button type="submit" className="w-full" disabled={authSubmitting}>
              {authSubmitting ? 'Please wait...' : 'Update Password'}
            </Button>
          </form>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <Navbar />
        <div className="flex flex-1 items-center justify-center p-4">
          <form
            onSubmit={handleAuthSubmit}
            className="executive-surface w-full max-w-sm space-y-4 rounded-xl p-6 sm:p-7"
          >
            <div className="space-y-1">
              <h2 className="text-xl font-semibold">
                {authMode === 'login' ? 'Sign In' : authMode === 'signup' ? 'Create an account' : 'Forgot Password'}
              </h2>
              <p className="text-sm text-muted-foreground">
                {authMode === 'login'
                  ? 'Sign in to access analysis and export actions.'
                  : authMode === 'signup'
                    ? 'Create an account to start using protected features.'
                    : 'Enter your email to receive a password reset link.'}
              </p>
            </div>

            <div className="space-y-2.5">
              <Input
                type="email"
                placeholder="name@company.com"
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                required
              />
              {authMode !== 'forgot' && (
                <Input
                  type="password"
                  placeholder="Password (min 8 chars)"
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  minLength={8}
                  required
                />
              )}
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
              {authSubmitting
                ? 'Please wait...'
                : authMode === 'login'
                  ? 'Sign In'
                  : authMode === 'signup'
                    ? 'Create Account'
                    : 'Send Reset Link'}
            </Button>

            <div className="grid grid-cols-1 gap-1.5">
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                onClick={() => setAuthMode(authMode === 'login' ? 'signup' : 'login')}
                disabled={authSubmitting || authMode === 'forgot'}
              >
                {authMode === 'login' ? 'Need an account? Sign up' : 'Already have an account? Sign in'}
              </Button>

              <Button
                type="button"
                variant="ghost"
                className="w-full"
                onClick={() => setAuthMode(authMode === 'forgot' ? 'login' : 'forgot')}
                disabled={authSubmitting}
              >
                {authMode === 'forgot' ? 'Back to Sign in' : 'Forgot password?'}
              </Button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />
      {!user.email_verified && (
        <div className="border-b border-amber-200 bg-amber-50/80 px-4 py-2 text-sm text-amber-900 dark:border-amber-900/30 dark:bg-amber-500/10 dark:text-amber-100 sm:px-6">
          Email verification is required for analysis and export.
        </div>
      )}
      {cachedOpen && (
        <div className="border-b border-border/80 bg-card/65 px-4 py-3 sm:px-6">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold">Recent Cached Results</h3>
            <Button variant="ghost" size="sm" onClick={() => setCachedOpen(false)}>Hide</Button>
          </div>
          {cachedResults.length === 0 ? (
            <p className="text-sm text-muted-foreground">No cached results found.</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {cachedResults.map((item) => (
                <div key={item.key} className="card-hover-lift executive-surface rounded-xl p-3">
                  <div className="text-sm font-medium line-clamp-2">
                    {item.product_title || item.analysis?.product_info?.title || `Product ${item.asin}`}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {item.asin} ({item.country})
                  </div>
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
            "fixed bottom-0 left-0 top-14 z-40 flex-shrink-0 bg-card/95 transition-all duration-300 ease-in-out backdrop-blur lg:relative lg:top-0 lg:z-0",
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
              onLoadCachedResults={handleLoadCachedResults}
              onLogout={handleLogout}
              onResendVerification={handleResendVerification}
              userEmail={user.email}
              emailVerified={user.email_verified}
              cachedLoading={cachedLoading}
              isLoading={isLoading}
              isCollapsed={!isMobile && sidebarCollapsed}
              onToggleCollapse={() => {
                if (isMobile) {
                  setSidebarMobileOpen(false);
                } else {
                  setSidebarCollapsed((prev) => !prev);
                }
              }}
              isMobile={isMobile}
            />
          )}
        </div>

        {isMobile && !sidebarMobileOpen && (
          <div className="pointer-events-none fixed bottom-4 left-4 z-20 lg:hidden">
            <Button
              className="pointer-events-auto"
              onClick={() => setSidebarMobileOpen(true)}
            >
              Filters
            </Button>
          </div>
        )}

        {isMobile && sidebarMobileOpen && (
          <div
            className="fixed inset-0 z-30 bg-slate-950/50 lg:hidden"
            onClick={() => setSidebarMobileOpen(false)}
          />
        )}

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className={cn(
            "flex-1 flex flex-col min-h-0 overflow-auto",
            "bg-gradient-to-br from-background via-background to-muted/20"
          )}>
            {analysis && (
              <div className="px-4 sm:px-6 pt-4 pb-2">
                <div className="executive-surface rounded-xl px-4 py-3">
                  <div className="text-base sm:text-lg font-semibold truncate">
                    {analysisProductTitle}
                  </div>
                  <div className="text-xs sm:text-sm text-muted-foreground mt-1">
                    ASIN: {analysis.asin || currentAsin}
                  </div>
                </div>
              </div>
            )}

            {!analysis && !isLoading && (
              <div className="flex-1 flex items-center justify-center p-4">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (mobileAsin.trim()) {
                      const normalizedAsin = extractAsin(mobileAsin.trim());
                      if (!normalizedAsin) {
                        toast({
                          title: '❌ Invalid product input',
                          description: 'Enter a valid 10-character ASIN or Amazon product URL.',
                          variant: 'destructive',
                        });
                        return;
                      }
                      setMobileAsin(normalizedAsin);
                      handleAnalyze(normalizedAsin, 50, true, 'IN');
                    }
                  }}
                  className="executive-surface w-full max-w-md space-y-4 rounded-xl p-6"
                >
                  <div className="text-center space-y-2 mb-6">
                    <h2 className="text-xl sm:text-2xl font-bold">Start Analysis</h2>
                    <p className="text-muted-foreground text-sm">
                      Enter an Amazon ASIN or use the sidebar filters
                    </p>
                  </div>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <Input
                      type="text"
                      value={mobileAsin}
                      onChange={(e) => setMobileAsin(e.target.value)}
                      placeholder="Enter ASIN or Amazon URL"
                      className="flex-1"
                    />
                    <Button
                      type="submit"
                      disabled={isLoading || !mobileAsin.trim()}
                      className="whitespace-nowrap"
                    >
                      {isLoading ? 'Analyzing…' : 'Analyze Reviews'}
                    </Button>
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
