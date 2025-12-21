import ResearchDashboard from '@/components/ResearchDashboard';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Research Assistant AI - Academic & Scientific Research',
  description: 'An AI-powered research assistant with web search, document analysis, and academic literature review capabilities.',
};

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="mb-8 md:mb-12">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                {/* Using your public/globe.svg */}
                <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                </svg>
              </div>
              <h1 className="text-3xl md:text-4xl font-bold text-gray-900">
                Research<span className="text-blue-600">Assistant</span>.ai
              </h1>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span>AI Online</span>
            </div>
          </div>

          <p className="text-gray-600 text-lg max-w-3xl">
            An intelligent research assistant powered by AI. Analyze papers, search academic databases,
            synthesize information, and generate research plans with citations.
          </p>
        </header>

        {/* Main Dashboard */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Left Panel - Stats */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">Research Capabilities</h2>
              <ul className="space-y-3">
                {[
                  'Academic Literature Search',
                  'Paper Summarization',
                  'Citation Generation',
                  'Research Planning',
                  'Data Analysis',
                  'Source Validation'
                ].map((capability, index) => (
                  <li key={index} className="flex items-center gap-3">
                    <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    <span className="text-gray-700">{capability}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl shadow-lg p-6 text-white">
              <h3 className="text-lg font-semibold mb-2">Quick Actions</h3>
              <div className="space-y-3">
                <button className="w-full bg-white/20 hover:bg-white/30 text-white py-2 px-4 rounded-lg transition duration-200 flex items-center justify-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  New Research Project
                </button>
                <button className="w-full bg-white/20 hover:bg-white/30 text-white py-2 px-4 rounded-lg transition duration-200 flex items-center justify-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Upload Documents
                </button>
              </div>
            </div>
          </div>

          {/* Main Chat Area */}
          <div className="lg:col-span-2">
            <ResearchDashboard />
          </div>
        </div>

        {/* Features Section */}
        <div className="mt-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Advanced Research Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                title: 'Smart Literature Review',
                description: 'Automated analysis of academic papers with citation tracking',
                icon: '📚',
                color: 'bg-blue-100'
              },
              {
                title: 'Multi-Source Search',
                description: 'Search across arXiv, PubMed, Google Scholar simultaneously',
                icon: '🔍',
                color: 'bg-green-100'
              },
              {
                title: 'Research Synthesis',
                description: 'Connect findings across multiple sources and identify patterns',
                icon: '🧠',
                color: 'bg-purple-100'
              }
            ].map((feature, index) => (
              <div key={index} className={`${feature.color} rounded-xl p-6 shadow-md hover:shadow-lg transition duration-300`}>
                <div className="text-3xl mb-4">{feature.icon}</div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">{feature.title}</h3>
                <p className="text-gray-700">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-12 pt-6 border-t border-gray-200 text-center text-gray-500 text-sm">
          <p>Research Assistant AI • Powered by LangChain, OpenAI, and Pinecone • Deployed on Vercel</p>
          <p className="mt-2">
            API Status: <span className="text-green-600 font-medium">Operational</span> •
            Last Updated: {new Date().toLocaleDateString()}
          </p>
        </footer>
      </div>
    </main>
  );
}