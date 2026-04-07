'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import {
  ArrowLeft, Star, TrendingUp, AlertCircle,
  CheckCircle2, Sparkles, Download, Share2, Package,
  Calendar, BarChart3, ThumbsUp, ThumbsDown, Minus,
  Twitter, Linkedin, Facebook, Mail
} from 'lucide-react';
import type { AnalysisResult, Review } from '@/types';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { apiClient } from '@/lib/api';

interface DetailedInsightsProps {
  analysis: AnalysisResult;
  onBack: () => void;
}

export default function DetailedInsights({ analysis, onBack }: DetailedInsightsProps) {
  const [isExporting, setIsExporting] = useState(false);
  const { toast } = useToast();

  const totalReviews = analysis.total_reviews || 0;
  const ratings = (analysis.reviews || [])
    .map((review) => {
      const primary = review.rating;
      const fallback = review.stars;
      const value = typeof primary === 'number' ? primary : (typeof fallback === 'number' ? fallback : 0);
      return Number.isFinite(value) ? value : 0;
    })
    .filter((value) => value > 0);
  const avgRating = analysis.average_rating > 0
    ? analysis.average_rating
    : (ratings.length > 0 ? ratings.reduce((sum, value) => sum + value, 0) / ratings.length : 0);
  const sentimentDist = analysis.sentiment_distribution || { positive: 0, neutral: 0, negative: 0 };
  const total = sentimentDist.positive + sentimentDist.neutral + sentimentDist.negative;

  const positivePercent = total > 0 ? (sentimentDist.positive / total) * 100 : 0;
  const neutralPercent = total > 0 ? (sentimentDist.neutral / total) * 100 : 0;
  const negativePercent = total > 0 ? (sentimentDist.negative / total) * 100 : 0;

  const themes = analysis.themes || [];
  const keywords = analysis.top_keywords || [];

  const rawInsights = analysis.insights || [];
  const insights = Array.isArray(rawInsights)
    ? rawInsights
    : (rawInsights.insights || []);
  const summaryFromSummaries = analysis.summaries?.overall || '';
  const summaryFromInsights = Array.isArray(rawInsights)
    ? ''
    : (rawInsights.summary || '');
  const summary = summaryFromSummaries || summaryFromInsights;

  const reviews = analysis.reviews || [];

  const getFilteredReviews = (targetSentiment: 'positive' | 'neutral' | 'negative') => {
    return reviews.filter(review => {
      if (review.sentiment === targetSentiment) return true;

      const rating = typeof review.rating === 'number' ? review.rating : (review.stars ?? 0);

      if (targetSentiment === 'positive') return rating >= 4;
      if (targetSentiment === 'negative') return rating <= 2;
      return rating === 3;
    });
  };

  const positiveReviews = getFilteredReviews('positive');
  const neutralReviews = getFilteredReviews('neutral');
  const negativeReviews = getFilteredReviews('negative');

  const getShareContent = () => {
    const title = analysis.product_info?.title || `ASIN ${analysis.asin || ''}`;
    const text = `Amazon Review Intelligence: ${title} - Avg Rating ${avgRating.toFixed(1)}/5 based on ${totalReviews} reviews. AI Analysis shows ${positivePercent.toFixed(0)}% positive sentiment.`;
    const url = typeof window !== 'undefined' ? window.location.href : '';
    return { title, text, url };
  };

  const handleWebShare = async () => {
    try {
      const { title, text, url } = getShareContent();

      if (navigator?.share) {
        await navigator.share({ title, text, url });
        toast({
          title: '✅ Shared successfully',
          description: 'Analysis shared via your device.',
        });
        return;
      }

      await navigator.clipboard.writeText(`${title}

${text}

${url}`);
      toast({
        title: '📋 Copied to clipboard',
        description: 'Analysis summary copied. Paste it anywhere to share.',
      });
    } catch {
      // silently fail
    }
  };

  const handleSocialShare = (platform: string) => {
    const { title, text, url } = getShareContent();
    let shareUrl = '';

    switch (platform) {
      case 'twitter':
        shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
        break;
      case 'linkedin':
        shareUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`;
        break;
      case 'facebook':
        shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
        break;
      case 'email':
        shareUrl = `mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(text + ' ' + url)}`;
        break;
    }

    if (shareUrl) {
      window.open(shareUrl, '_blank', 'noopener,noreferrer');
    }
  };

  const handleExport = async (format: string) => {
    setIsExporting(true);
    try {
      toast({
        title: `📥 Exporting ${format.toUpperCase()}`,
        description: 'Preparing your export file...',
      });
      const endpoint = format === 'xlsx' ? 'csv' : format;
      const fileExt = format === 'csv' ? 'xlsx' : format;
      const response = await apiClient.post(`/api/v1/export/${endpoint}`, { analysis_data: analysis }, {
        responseType: 'blob',
      });
      const blob = response.data as Blob;
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `detailed-analysis-${analysis.asin}-${Date.now()}.${fileExt}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast({
        title: '✅ Export Complete',
        description: `Downloaded ${format.toUpperCase()} file successfully`,
      });
    } catch (error: any) {
      console.error('Export error:', error);
      let message = error.message || 'Unable to export file. Please try again.';
      const maybeBlob = error?.response?.data;
      if (maybeBlob instanceof Blob) {
        try {
          const text = await maybeBlob.text();
          const parsed = JSON.parse(text);
          message = parsed?.detail || parsed?.error || message;
        } catch {
          message = 'Unable to export file. Please try again.';
        }
      }
      toast({ title: '❌ Export Failed', description: message, variant: 'destructive' });
    } finally {
      setIsExporting(false);
    }
  };
  const renderStarRating = (rating: number) => (
    <div className="flex">
      {[...Array(5)].map((_, i) => (
        <Star
          key={i}
          className={cn(
            "h-4 w-4",
            i < rating ? "fill-yellow-500 text-yellow-500" : "text-muted"
          )}
        />
      ))}
    </div>
  );

  const renderReviewCard = (review: Review, index: number, bgColor: string) => {
    const reviewRating = typeof review.rating === 'number' ? review.rating : (review.stars ?? 0);
    const reviewAuthor = 'Anonymous';
    const reviewDate = review.date || 'Unknown date';
    const reviewTitle = review.title || 'No title';
    const reviewText = review.text || 'No content';
    const reviewConfidence = review.sentiment_confidence ?? 0;
    const reviewVerified = review.verified ?? review.verified_purchase ?? false;

    return (
      <div key={index} className={cn("p-4 rounded-lg border", bgColor)}>
        <div className="flex items-start justify-between gap-4 mb-2">
          <div className="flex items-center gap-2">
            {renderStarRating(reviewRating)}
            <span className="text-xs text-muted-foreground">
              by {reviewAuthor}
            </span>
          </div>
          <Badge variant="outline" className="text-xs">
            {(reviewConfidence * 100).toFixed(0)}% confidence
          </Badge>
        </div>
        <h4 className="font-semibold text-sm mb-2">{reviewTitle}</h4>
        <p className="text-sm text-muted-foreground leading-relaxed">
          {reviewText}
        </p>
        <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
          <Calendar className="h-3 w-3" />
          {reviewDate}
          {reviewVerified && (
            <Badge variant="secondary" className="text-xs">
              Verified Purchase
            </Badge>
          )}
        </div>
      </div>
    );
  };

  return (
    <main className="flex-1 overflow-y-auto bg-transparent p-3 sm:p-4 md:p-6 lg:p-8">
      <div className="max-w-[1400px] mx-auto space-y-4 sm:space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={onBack} className="shrink-0">
              <ArrowLeft className="h-4 w-4 sm:h-5 sm:w-5" />
            </Button>
            <div>
              <h1 className="text-lg sm:text-xl md:text-2xl lg:text-3xl font-bold">Detailed Insights</h1>
              <p className="text-xs sm:text-sm text-muted-foreground mt-0.5 sm:mt-1">
                ASIN: {analysis.asin} • {totalReviews} reviews analyzed
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            {/* Share Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="gap-2">
                  <Share2 className="h-4 w-4" />
                  <span className="hidden sm:inline">Share</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem onClick={handleWebShare}>
                  <Share2 className="h-4 w-4 mr-2" />
                  Share Link
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleSocialShare('twitter')}>
                  <Twitter className="h-4 w-4 mr-2" />
                  Twitter
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleSocialShare('linkedin')}>
                  <Linkedin className="h-4 w-4 mr-2" />
                  LinkedIn
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleSocialShare('facebook')}>
                  <Facebook className="h-4 w-4 mr-2" />
                  Facebook
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleSocialShare('email')}>
                  <Mail className="h-4 w-4 mr-2" />
                  Email
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Export Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="gap-2" disabled={isExporting}>
                  <Download className={cn("h-4 w-4", isExporting && "animate-bounce")} />
                  <span className="hidden sm:inline">Export</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-40">
                <DropdownMenuItem onClick={() => handleExport('pdf')}>
                  <Download className="h-4 w-4 mr-2" />
                  Export PDF
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport('csv')}>
                  <Download className="h-4 w-4 mr-2" />
                  Export CSV
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport('xlsx')}>
                  <Download className="h-4 w-4 mr-2" />
                  Export Excel
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <Separator className="bg-border/80" />

        {/* Product Info */}
        {analysis.product_info && (
          <Card className="card-hover-lift border bg-card">
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-start gap-4">
                {analysis.product_info.image_url && (
                  <img
                    src={analysis.product_info.image_url}
                    alt={analysis.product_info.title || 'Product image'}
                    className="w-20 h-20 sm:w-24 sm:h-24 object-cover rounded-lg border"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <h2 className="text-base sm:text-lg md:text-xl font-bold mb-2">
                    {analysis.product_info.title || 'Product'}
                  </h2>
                  <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs sm:text-sm text-muted-foreground">
                    {analysis.product_info.asin && (
                      <div className="flex items-center gap-1.5">
                        <Package className="h-4 w-4" />
                        {analysis.product_info.asin}
                      </div>
                    )}
                    {analysis.product_info.average_rating && (
                      <div className="flex items-center gap-1.5">
                        <Star className="h-4 w-4 fill-yellow-500 text-yellow-500" />
                        {analysis.product_info.average_rating.toFixed(1)}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
        {/* Executive Summary */}
        <Card className="card-hover-lift border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Executive Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {summary || `Analysis of ${totalReviews} reviews shows ${positivePercent.toFixed(0)}% positive, ${neutralPercent.toFixed(0)}% neutral, and ${negativePercent.toFixed(0)}% negative sentiment. The average rating is ${avgRating.toFixed(1)}/5 stars.`}
            </p>
          </CardContent>
        </Card>

        {/* Sentiment Analysis */}
        <Card className="card-hover-lift border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Sentiment Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <ThumbsUp className="h-5 w-5 text-emerald-600" />
                    <span className="font-semibold">Positive</span>
                  </div>
                  <span className="text-2xl font-bold text-emerald-600">
                    {positivePercent.toFixed(0)}%
                  </span>
                </div>
                <Progress value={positivePercent} className="h-2 bg-emerald-500/20">
                  <div className="h-full bg-emerald-600" style={{ width: `${positivePercent}%` }} />
                </Progress>
                <p className="text-xs text-muted-foreground mt-2">
                  {sentimentDist.positive} reviews
                </p>
              </div>

              <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Minus className="h-5 w-5 text-amber-600" />
                    <span className="font-semibold">Neutral</span>
                  </div>
                  <span className="text-2xl font-bold text-amber-600">
                    {neutralPercent.toFixed(0)}%
                  </span>
                </div>
                <Progress value={neutralPercent} className="h-2 bg-amber-500/20">
                  <div className="h-full bg-amber-500" style={{ width: `${neutralPercent}%` }} />
                </Progress>
                <p className="text-xs text-muted-foreground mt-2">
                  {sentimentDist.neutral} reviews
                </p>
              </div>

              <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <ThumbsDown className="h-5 w-5 text-red-600" />
                    <span className="font-semibold">Negative</span>
                  </div>
                  <span className="text-2xl font-bold text-red-600">
                    {negativePercent.toFixed(0)}%
                  </span>
                </div>
                <Progress value={negativePercent} className="h-2 bg-red-500/20">
                  <div className="h-full bg-red-600" style={{ width: `${negativePercent}%` }} />
                </Progress>
                <p className="text-xs text-muted-foreground mt-2">
                  {sentimentDist.negative} reviews
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Key Insights */}
        <Card className="card-hover-lift border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              Key Insights
            </CardTitle>
            <CardDescription>
              AI-extracted patterns and important findings
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {insights.length > 0 ? (
                insights.map((insight: string, index: number) => (
                  <div
                    key={index}
                    className="flex items-start gap-3 p-4 rounded-lg border bg-muted/30 hover:bg-muted/50 transition-colors"
                  >
                    <div className="shrink-0 mt-0.5">
                      {insight.toLowerCase().includes('positive') || insight.toLowerCase().includes('strong') ? (
                        <TrendingUp className="h-5 w-5 text-green-500" />
                      ) : insight.toLowerCase().includes('negative') || insight.toLowerCase().includes('warning') ? (
                        <AlertCircle className="h-5 w-5 text-red-500" />
                      ) : (
                        <CheckCircle2 className="h-5 w-5 text-blue-500" />
                      )}
                    </div>
                    <p className="text-sm leading-relaxed">{insight}</p>
                  </div>
                ))
              ) : (
                <div className="col-span-2 text-center py-8 text-muted-foreground">
                  <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No AI insights available</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Keywords */}
        {keywords.length > 0 && (
          <Card className="card-hover-lift border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                Top Keywords
              </CardTitle>
              <CardDescription>
                Most frequently mentioned terms
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {keywords.map((keyword, index) => {
                  const freq = keyword.frequency ?? 0;
                  const size = freq > 20 ? 'large' : freq > 10 ? 'medium' : 'small';

                  return (
                    <Badge
                      key={index}
                      variant="outline"
                      className={cn(
                        "transition-all hover:scale-110",
                        size === 'large' && "text-base px-4 py-2",
                        size === 'medium' && "text-sm px-3 py-1.5",
                        size === 'small' && "text-xs px-2 py-1"
                      )}
                    >
                      {keyword.word}
                    </Badge>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {reviews.length > 0 && (
          <Card className="card-hover-lift border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-primary" />
                Review Samples
              </CardTitle>
              <CardDescription>
                Representative reviews grouped by sentiment.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <ThumbsUp className="h-4 w-4 text-emerald-600" />
                  <h3 className="text-sm font-semibold">Positive</h3>
                  <Badge variant="outline">{positiveReviews.length}</Badge>
                </div>
                <div className="grid grid-cols-1 gap-3">
                  {positiveReviews.slice(0, 2).map((review, index) =>
                    renderReviewCard(review, index, 'bg-emerald-500/5 border-emerald-500/20')
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Minus className="h-4 w-4 text-amber-600" />
                  <h3 className="text-sm font-semibold">Neutral</h3>
                  <Badge variant="outline">{neutralReviews.length}</Badge>
                </div>
                <div className="grid grid-cols-1 gap-3">
                  {neutralReviews.slice(0, 2).map((review, index) =>
                    renderReviewCard(review, index, 'bg-amber-500/5 border-amber-500/20')
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <ThumbsDown className="h-4 w-4 text-red-600" />
                  <h3 className="text-sm font-semibold">Negative</h3>
                  <Badge variant="outline">{negativeReviews.length}</Badge>
                </div>
                <div className="grid grid-cols-1 gap-3">
                  {negativeReviews.slice(0, 2).map((review, index) =>
                    renderReviewCard(review, index, 'bg-red-500/5 border-red-500/20')
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

      </div>
    </main>
  );
}
