'use client';

import React from 'react';
import {
  Sparkles,
  TrendingUp,
  AlertCircle,
  Star,
  CheckCircle2
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import type { AnalysisResult } from '@/types';
import { cn } from '@/lib/utils';

interface InsightsPanelProps {
  analysis: AnalysisResult | null;
  isLoading?: boolean;
  aiEnabled?: boolean;
}

export default function InsightsPanel({
  analysis,
  isLoading = false,
  aiEnabled = true
}: InsightsPanelProps) {
  if (isLoading) {
    return (
      <aside className={cn(
        "w-full",
        "p-3 sm:p-4 md:p-6 space-y-3 md:space-y-4",
        "bg-card/60 lg:h-full overflow-y-auto"
      )}>
        <Card className="animate-pulse border">
          <CardHeader className="pb-2 md:pb-3">
            <div className="h-4 bg-muted rounded w-24" />
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="h-3 bg-muted rounded w-full" />
            <div className="h-3 bg-muted rounded w-3/4" />
            <div className="h-3 bg-muted rounded w-1/2" />
          </CardContent>
        </Card>
      </aside>
    );
  }

  if (!analysis) {
    return (
      <aside className={cn(
        "w-full",
        "p-3 sm:p-4 md:p-6 space-y-3 md:space-y-4",
        "bg-card/60 lg:h-full"
      )}>
        <Card className="border bg-muted/50">
          <CardContent className="p-4 sm:p-6 text-center">
            <Sparkles className="h-8 w-8 sm:h-10 sm:w-10 mx-auto mb-3 text-muted-foreground/50" />
            <p className="text-xs sm:text-sm text-muted-foreground">
              Insights will appear here after analysis
            </p>
          </CardContent>
        </Card>
      </aside>
    );
  }

  // Extract data with safe defaults
  const totalReviews = analysis.total_reviews || 0;
  const ratings = (analysis.reviews || [])
    .map((review) => {
      const primary = review.rating;
      const fallback = review.stars;
      const value = typeof primary === 'number' ? primary : (typeof fallback === 'number' ? fallback : 0);
      return Number.isFinite(value) ? value : 0;
    })
    .filter((value) => value > 0);
  const averageRating = analysis.average_rating > 0
    ? analysis.average_rating
    : (ratings.length > 0 ? ratings.reduce((sum, value) => sum + value, 0) / ratings.length : 0);
  const sentimentDist = analysis.sentiment_distribution || { positive: 0, neutral: 0, negative: 0 };
  const themes = analysis.themes || [];
  const keywords = analysis.top_keywords || [];
  const insights: string[] = Array.isArray(analysis.insights) ? analysis.insights as string[] : (analysis.insights?.insights as string[] || []);
  const summary = analysis.summaries?.overall
    || (Array.isArray(analysis.insights) ? '' : (analysis.insights?.summary || ''))
    || 'Analysis complete';

  // Calculate percentages
  const total = sentimentDist.positive + sentimentDist.neutral + sentimentDist.negative;
  const positivePercent = total > 0 ? (sentimentDist.positive / total) * 100 : 0;
  const neutralPercent = total > 0 ? (sentimentDist.neutral / total) * 100 : 0;
  const negativePercent = total > 0 ? (sentimentDist.negative / total) * 100 : 0;

  return (
    <aside className={cn(
      "w-full",
      "p-3 sm:p-4 md:p-6 space-y-3 md:space-y-4",
      "bg-card/60 lg:h-full overflow-y-auto"
    )}>

      {/* Summary Card - Mobile Optimized */}
      <Card className="card-hover-lift border">
        <CardHeader className="pb-2 md:pb-3 px-3 sm:px-4">
          <CardTitle className="text-xs sm:text-sm md:text-base font-semibold flex items-center gap-2">
            <Sparkles className="h-3 w-3 sm:h-4 sm:w-4 text-primary flex-shrink-0" />
            Summary
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 md:space-y-3 px-3 sm:px-4">
          <div className="flex items-center justify-between">
            <span className="text-[10px] sm:text-xs md:text-sm text-muted-foreground">
              Total Reviews
            </span>
            <span className="text-xs sm:text-sm md:text-base font-semibold">
              {totalReviews.toLocaleString()}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[10px] sm:text-xs md:text-sm text-muted-foreground">
              Avg Rating
            </span>
            <div className="flex items-center gap-1">
              <Star className="h-2.5 w-2.5 sm:h-3 sm:w-3 md:h-4 md:w-4 fill-yellow-400 text-yellow-400" />
              <span className="text-xs sm:text-sm md:text-base font-semibold">
                {averageRating > 0 ? averageRating.toFixed(1) : 'N/A'}
              </span>
            </div>
          </div>

          <div className="h-px bg-border" />

          <p className="text-[10px] sm:text-xs md:text-sm leading-relaxed text-muted-foreground">
            {summary}
          </p>
        </CardContent>
      </Card>

      {/* Sentiment Breakdown - Mobile Optimized */}
      <Card className="card-hover-lift border">
        <CardHeader className="pb-2 md:pb-3 px-3 sm:px-4">
          <CardTitle className="text-xs sm:text-sm md:text-base font-semibold">
            Sentiment Breakdown
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 md:space-y-3 px-3 sm:px-4">
          {/* Positive */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] sm:text-xs md:text-sm">Positive</span>
              <span className="text-[10px] sm:text-xs md:text-sm font-semibold status-positive">
                {positivePercent.toFixed(0)}%
              </span>
            </div>
            <Progress value={positivePercent} className="h-1 sm:h-1.5 bg-muted">
              <div
                className="h-full rounded-full bg-emerald-600 transition-all"
                style={{ width: `${positivePercent}%` }}
              />
            </Progress>
          </div>

          {/* Neutral */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] sm:text-xs md:text-sm">Neutral</span>
              <span className="text-[10px] sm:text-xs md:text-sm font-semibold status-neutral">
                {neutralPercent.toFixed(0)}%
              </span>
            </div>
            <Progress value={neutralPercent} className="h-1 sm:h-1.5 bg-muted">
              <div
                className="h-full rounded-full bg-amber-500 transition-all"
                style={{ width: `${neutralPercent}%` }}
              />
            </Progress>
          </div>

          {/* Negative */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] sm:text-xs md:text-sm">Negative</span>
              <span className="text-[10px] sm:text-xs md:text-sm font-semibold status-negative">
                {negativePercent.toFixed(0)}%
              </span>
            </div>
            <Progress value={negativePercent} className="h-1 sm:h-1.5 bg-muted">
              <div
                className="h-full rounded-full bg-red-600 transition-all"
                style={{ width: `${negativePercent}%` }}
              />
            </Progress>
          </div>
        </CardContent>
      </Card>

      {/* Themes - Mobile Optimized */}
      {themes.length > 0 && (
        <Card className="card-hover-lift border">
          <CardHeader className="pb-2 md:pb-3 px-3 sm:px-4">
            <CardTitle className="text-xs sm:text-sm md:text-base font-semibold">
              Key Themes
            </CardTitle>
          </CardHeader>
          <CardContent className="px-3 sm:px-4">
            <div className="flex flex-wrap gap-1 sm:gap-1.5 md:gap-2">
              {themes.slice(0, 6).map((theme, index) => {
                if (typeof theme === 'string') {
                  // Render string theme differently if needed or just as a plain badge
                  return (
                    <Badge key={index} variant="secondary" className="text-xs px-2 py-1">
                      {theme}
                    </Badge>
                  );
                }

                // Now theme is guaranteed to be of type Theme
                return (
                  <div key={index} className="flex items-center">
                    <Badge
                      variant={
                        theme.sentiment === 'positive' ? 'default' :
                          theme.sentiment === 'negative' ? 'destructive' :
                            'secondary'
                      }
                      className="text-[9px] sm:text-[10px] md:text-xs px-1.5 sm:px-2 py-0 sm:py-0.5"
                    >
                      {theme.theme}
                    </Badge>
                    <Badge
                      variant="outline"
                      className="ml-1 text-[8px] sm:text-[9px] md:text-[10px] px-1 py-0"
                    >
                      {theme.mentions}
                    </Badge>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Keywords - Mobile Optimized */}
      {keywords.length > 0 && (
        <Card className="card-hover-lift border">
          <CardHeader className="pb-2 md:pb-3 px-3 sm:px-4">
            <CardTitle className="text-xs sm:text-sm md:text-base font-semibold">
              Top Keywords
            </CardTitle>
          </CardHeader>
          <CardContent className="px-3 sm:px-4">
            <div className="flex flex-wrap gap-1 sm:gap-1.5">
              {keywords.slice(0, 8).map((keyword, index) => (
                <Badge
                  key={index}
                  variant="outline"
                  className="text-[9px] sm:text-[10px] md:text-xs px-1.5 sm:px-2 py-0 sm:py-0.5"
                >
                  {keyword.word} ({keyword.frequency})
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* AI Insights - Mobile Optimized */}
      {insights.length > 0 && aiEnabled && (
        <Card className="card-hover-lift border">
          <CardHeader className="pb-2 md:pb-3 px-3 sm:px-4">
            <CardTitle className="text-xs sm:text-sm md:text-base font-semibold flex items-center gap-2">
              <TrendingUp className="h-3 w-3 sm:h-4 sm:w-4 text-primary flex-shrink-0" />
              Key Insights
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5 md:space-y-2 px-3 sm:px-4">
            {insights.slice(0, 4).map((insight: string, index) => (
              <div key={index} className="flex gap-1.5 sm:gap-2">
                <CheckCircle2 className="h-2.5 w-2.5 sm:h-3 sm:w-3 flex-shrink-0 mt-0.5 text-green-500" />
                <p className="text-[9px] sm:text-[10px] md:text-xs leading-relaxed">
                  {insight}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Data Source Info - Mobile Optimized */}
      <Card className="border bg-muted/50">
        <CardContent className="pt-3 md:pt-4 px-3 sm:px-4">
          <div className="text-[9px] sm:text-[10px] md:text-xs space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Data Source:</span>
              <span className="font-medium">{analysis.data_source || 'Apify'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">AI Provider:</span>
              <span className="font-medium">{aiEnabled ? 'OpenAI' : 'Disabled'}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </aside>
  );
}
