"""Home page with deals and recommendations"""

import { Suspense } from "react";
import { Metadata } from "next";
import { Hero } from "@/components/hero";
import { DealGrid } from "@/components/deal-grid";
import { CategoryFilter } from "@/components/category-filter";
import { SearchBar } from "@/components/search-bar";
import { AIRecommendations } from "@/components/ai-recommendations";

export const metadata: Metadata = {
  title: "AppAdvice - Discover Free iOS Apps & Price Drops",
};

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-50">
      {/* Hero Section */}
      <Hero />

      {/* Search & Filter Section */}
      <section className="sticky top-0 z-40 bg-slate-50/95 backdrop-blur border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col md:flex-row gap-4">
            <SearchBar />
            <CategoryFilter />
          </div>
        </div>
      </section>

      {/* AI Recommendations */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Recommended For You
          <span className="ml-2 text-sm font-normal text-slate-500">AI-Powered</span>
        </h2>
        <Suspense fallback={<DealGrid.Skeleton />}>
          <AIRecommendations />
        </Suspense>
      </section>

      {/* Today's Deals */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Today&apos;s Deals
          <span className="ml-2 text-sm font-normal text-emerald-600">Free & Price Drops</span>
        </h2>
        <Suspense fallback={<DealGrid.Skeleton />}>
          <DealGrid type="deals" />
        </Suspense>
      </section>

      {/* All Apps */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-16">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">Browse All Apps</h2>
        <Suspense fallback={<DealGrid.Skeleton />}>
          <DealGrid type="all" />
        </Suspense>
      </section>
    </main>
  );
}
