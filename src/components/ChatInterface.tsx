'use client';

import { useState, useRef, useEffect } from 'react';
import LoadingSpinner from './LoadingSpinner';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  sources?: Array<{
    title: string;
    url: string;
    snippet: string;
  }>;
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m your research assistant. What would you like to research today? I can help with literature reviews, paper analysis, research planning, and more.',
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [researchType, setResearchType] = useState<'quick' | 'comprehensive' | 'literature'>('quick');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/research', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: input,
          research_type: researchType,
          options: {
            include_sources: true,
            include_citations: true,
            format: 'structured',
          },
        }),
      });

      if (!response.ok) {
        throw new Error('Research request failed');
      }

      const data = await response.json();

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.result,
        timestamp: new Date(),
        sources: data.sources?.slice(0, 3), // Show top 3 sources
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'I apologize, but I encountered an error while processing your research request. Please try again or rephrase your question.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickPrompt = async (prompt: string) => {
    setInput(prompt);
    // Trigger submit after a short delay to allow input to update
    setTimeout(() => {
      const fakeEvent = { preventDefault: () => {} } as React.FormEvent;
      handleSubmit(fakeEvent);
    }, 100);
  };

  return (
    <div className="flex flex-col h-[600px] bg-white rounded-xl shadow-xl overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-4 text-white">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold">Research Chat</h2>
            <p className="text-blue-100 text-sm">Powered by AI • Real-time analysis</p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={researchType}
              onChange={(e) => setResearchType(e.target.value as any)}
              className="bg-white/20 border border-white/30 rounded-lg px-3 py-1 text-sm focus:outline-none"
            >
              <option value="quick">Quick Search</option>
              <option value="comprehensive">Comprehensive</option>
              <option value="literature">Literature Review</option>
            </select>
            <div className="flex gap-2">
              <button
                onClick={() => setMessages(messages.slice(0, 1))}
                className="bg-white/20 hover:bg-white/30 p-2 rounded-lg transition duration-200"
                title="Clear conversation"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
              <button
                onClick={() => window.print()}
                className="bg-white/20 hover:bg-white/30 p-2 rounded-lg transition duration-200"
                title="Export conversation"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${message.role === 'user'
                  ? 'bg-blue-500 text-white rounded-br-none'
                  : 'bg-gray-100 text-gray-900 rounded-bl-none'
                }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs font-medium ${message.role === 'user' ? 'text-blue-100' : 'text-gray-500'}`}>
                  {message.role === 'user' ? 'You' : 'Research Assistant'}
                </span>
                <span className="text-xs opacity-75">
                  {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <div className="whitespace-pre-wrap">{message.content}</div>

              {message.sources && message.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200/50">
                  <p className="text-xs font-medium mb-2">Sources:</p>
                  <div className="space-y-2">
                    {message.sources.map((source, index) => (
                      <div key={index} className="text-xs bg-white/30 p-2 rounded">
                        <div className="font-medium truncate">{source.title}</div>
                        <div className="text-gray-600 truncate">{source.snippet}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-900 rounded-2xl rounded-bl-none px-4 py-3 max-w-[80%]">
              <div className="flex items-center gap-3">
                <LoadingSpinner size="sm" />
                <span className="text-sm">Researching...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts */}
      <div className="border-t border-gray-200 p-3">
        <div className="flex gap-2 overflow-x-auto pb-2">
          {[
            "Summarize latest AI papers",
            "Create research plan for climate change",
            "Find papers about quantum computing",
            "Analyze this research data"
          ].map((prompt, index) => (
            <button
              key={index}
              onClick={() => handleQuickPrompt(prompt)}
              className="flex-shrink-0 bg-blue-50 hover:bg-blue-100 text-blue-700 text-sm px-3 py-1.5 rounded-full border border-blue-200 transition duration-200"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="border-t border-gray-200 p-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Enter your research question or topic..."
            className="flex-1 border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-3 rounded-lg font-medium hover:opacity-90 transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <LoadingSpinner size="sm" light />
            ) : (
              <>
                <svg className="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Research
              </>
            )}
          </button>
        </div>
        <div className="flex justify-between items-center mt-2 text-xs text-gray-500">
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-1">
              <input type="checkbox" defaultChecked className="rounded" />
              Include sources
            </label>
            <label className="flex items-center gap-1">
              <input type="checkbox" defaultChecked className="rounded" />
              Generate citations
            </label>
          </div>
          <div>Press Enter to send • Shift+Enter for new line</div>
        </div>
      </form>
    </div>
  );
}