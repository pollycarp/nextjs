'use client';

import { useState, useEffect, useRef } from 'react';
import ChatInterface from './ChatInterface';
import LoadingSpinner from './LoadingSpinner';

interface ResearchProject {
  id: string;
  title: string;
  description: string;
  status: 'active' | 'completed' | 'draft';
  progress: number;
  createdAt: string;
  updatedAt: string;
  tags: string[];
}

interface RecentSearch {
  id: string;
  query: string;
  results: number;
  timestamp: string;
}

interface Document {
  id: string;
  name: string;
  type: 'pdf' | 'arxiv' | 'webpage' | 'note';
  size: string;
  uploadedAt: string;
  status: 'processed' | 'processing' | 'pending';
}

export default function ResearchDashboard() {
  const [activeTab, setActiveTab] = useState<'chat' | 'projects' | 'documents' | 'analytics'>('chat');
  const [researchProjects, setResearchProjects] = useState<ResearchProject[]>([
    {
      id: '1',
      title: 'AI in Healthcare Diagnostics',
      description: 'Review of machine learning applications in medical imaging',
      status: 'active',
      progress: 75,
      createdAt: '2024-01-15',
      updatedAt: '2024-01-28',
      tags: ['AI', 'Healthcare', 'Medical Imaging'],
    },
    {
      id: '2',
      title: 'Quantum Computing Algorithms',
      description: 'Comparative analysis of quantum vs classical algorithms',
      status: 'active',
      progress: 40,
      createdAt: '2024-01-20',
      updatedAt: '2024-01-28',
      tags: ['Quantum', 'Algorithms', 'Computing'],
    },
    {
      id: '3',
      title: 'Climate Change Mitigation Tech',
      description: 'Emerging technologies for carbon capture and storage',
      status: 'completed',
      progress: 100,
      createdAt: '2024-01-05',
      updatedAt: '2024-01-25',
      tags: ['Climate', 'Technology', 'Sustainability'],
    },
  ]);

  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([
    { id: '1', query: 'transformer architecture improvements 2024', results: 42, timestamp: '10 min ago' },
    { id: '2', query: 'large language model benchmarks', results: 28, timestamp: '1 hour ago' },
    { id: '3', query: 'reinforcement learning applications', results: 35, timestamp: '3 hours ago' },
  ]);

  const [documents, setDocuments] = useState<Document[]>([
    { id: '1', name: 'attention_is_all_you_need.pdf', type: 'pdf', size: '2.4 MB', uploadedAt: '2024-01-26', status: 'processed' },
    { id: '2', name: 'arxiv_2401.12345.pdf', type: 'arxiv', size: '1.8 MB', uploadedAt: '2024-01-27', status: 'processing' },
    { id: '3', name: 'research_notes_jan.md', type: 'note', size: '156 KB', uploadedAt: '2024-01-28', status: 'processed' },
  ]);

  const [isUploading, setIsUploading] = useState(false);
  const [stats, setStats] = useState({
    totalSearches: 156,
    papersAnalyzed: 42,
    citationsGenerated: 189,
    hoursSaved: 78,
  });

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setStats(prev => ({
        ...prev,
        papersAnalyzed: prev.papersAnalyzed + Math.floor(Math.random() * 2),
      }));
    }, 30000); // Update every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    const newDocs: Document[] = [];

    for (const file of Array.from(files)) {
      try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/upload', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const err = await response.json().catch(() => ({ detail: response.statusText }));
          console.error(`Upload failed for ${file.name}:`, err.detail);
          continue;
        }

        const data = await response.json();
        newDocs.push({
          id: data.doc_id,
          name: data.filename,
          type: file.name.endsWith('.pdf') ? 'pdf' :
                file.name.includes('arxiv') ? 'arxiv' : 'note',
          size: `${(file.size / 1024 / 1024).toFixed(1)} MB`,
          uploadedAt: new Date().toISOString().split('T')[0],
          status: 'processed',
        });
      } catch (err) {
        console.error(`Upload error for ${file.name}:`, err);
      }
    }

    setDocuments(prev => [...newDocs, ...prev]);
    setIsUploading(false);

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleCreateProject = () => {
    const title = prompt('Enter project title:');
    if (!title) return;

    const newProject: ResearchProject = {
      id: Date.now().toString(),
      title,
      description: 'New research project',
      status: 'draft',
      progress: 0,
      createdAt: new Date().toISOString().split('T')[0],
      updatedAt: new Date().toISOString().split('T')[0],
      tags: ['New'],
    };

    setResearchProjects(prev => [newProject, ...prev]);
    setActiveTab('projects');
  };

  const handleDeleteDocument = (id: string) => {
    setDocuments(prev => prev.filter(doc => doc.id !== id));
  };

  const handleExportProject = (project: ResearchProject) => {
    const data = {
      project,
      exportedAt: new Date().toISOString(),
      format: 'research-assistant-v1',
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${project.title.replace(/\s+/g, '_')}_research.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'completed': return 'bg-blue-100 text-blue-800';
      case 'draft': return 'bg-yellow-100 text-yellow-800';
      case 'processed': return 'bg-green-100 text-green-800';
      case 'processing': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getProgressColor = (progress: number) => {
    if (progress < 30) return 'bg-red-500';
    if (progress < 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className="bg-white rounded-xl shadow-xl overflow-hidden">
      {/* Dashboard Header */}
      <div className="border-b border-gray-200">
        <div className="px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Research Dashboard</h1>
              <p className="text-gray-600">Your AI-powered research workspace</p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white px-4 py-2.5 rounded-lg hover:opacity-90 transition duration-200 disabled:opacity-50"
              >
                {isUploading ? (
                  <>
                    <LoadingSpinner size="sm" light />
                    <span>Uploading...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <span>Upload Documents</span>
                  </>
                )}
              </button>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                className="hidden"
                multiple
                accept=".pdf,.txt,.md,.doc,.docx"
              />
              <button
                onClick={handleCreateProject}
                className="flex items-center gap-2 bg-gradient-to-r from-purple-500 to-pink-600 text-white px-4 py-2.5 rounded-lg hover:opacity-90 transition duration-200"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                <span>New Project</span>
              </button>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="px-6">
          <div className="flex border-b border-gray-200">
            {[
              { id: 'chat', label: 'Research Chat', icon: '💬' },
              { id: 'projects', label: 'Projects', icon: '📁' },
              { id: 'documents', label: 'Documents', icon: '📄' },
              { id: 'analytics', label: 'Analytics', icon: '📊' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-3 font-medium text-sm border-b-2 transition duration-200 ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
                {tab.id === 'projects' && researchProjects.length > 0 && (
                  <span className="bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded-full">
                    {researchProjects.length}
                  </span>
                )}
                {tab.id === 'documents' && documents.length > 0 && (
                  <span className="bg-purple-100 text-purple-800 text-xs px-2 py-0.5 rounded-full">
                    {documents.length}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Dashboard Content */}
      <div className="p-6">
        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Total Searches', value: stats.totalSearches, icon: '🔍', color: 'bg-blue-500' },
            { label: 'Papers Analyzed', value: stats.papersAnalyzed, icon: '📚', color: 'bg-green-500' },
            { label: 'Citations Generated', value: stats.citationsGenerated, icon: '📝', color: 'bg-purple-500' },
            { label: 'Hours Saved', value: `${stats.hoursSaved}+`, icon: '⏱️', color: 'bg-orange-500' },
          ].map((stat, index) => (
            <div key={index} className="bg-gradient-to-br from-gray-50 to-white border border-gray-200 rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 mb-1">{stat.label}</p>
                  <p className="text-2xl font-bold text-gray-900">{stat.value.toLocaleString()}</p>
                </div>
                <div className={`${stat.color} w-12 h-12 rounded-full flex items-center justify-center`}>
                  <span className="text-xl">{stat.icon}</span>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-gray-100">
                <div className="flex items-center text-xs text-gray-500">
                  <svg className="w-4 h-4 mr-1 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z" clipRule="evenodd" />
                  </svg>
                  <span>+12% from last week</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'chat' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Research Assistant Chat</h2>
              <div className="text-sm text-gray-500">
                Real-time AI-powered research assistance
              </div>
            </div>
            <ChatInterface />
          </div>
        )}

        {activeTab === 'projects' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Research Projects</h2>
              <button
                onClick={() => setResearchProjects([])}
                className="text-sm text-red-600 hover:text-red-800"
              >
                Clear All
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {researchProjects.map((project) => (
                <div key={project.id} className="border border-gray-200 rounded-xl p-5 hover:shadow-md transition duration-200">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-bold text-gray-900 text-lg mb-1">{project.title}</h3>
                      <p className="text-gray-600 text-sm">{project.description}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(project.status)}`}>
                      {project.status.charAt(0).toUpperCase() + project.status.slice(1)}
                    </span>
                  </div>

                  <div className="mb-4">
                    <div className="flex justify-between text-sm text-gray-600 mb-1">
                      <span>Progress</span>
                      <span>{project.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`${getProgressColor(project.progress)} h-2 rounded-full transition-all duration-500`}
                        style={{ width: `${project.progress}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex gap-2">
                      {project.tags.map((tag, index) => (
                        <span key={index} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                          {tag}
                        </span>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleExportProject(project)}
                        className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition duration-200"
                        title="Export project"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => setActiveTab('chat')}
                        className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg transition duration-200"
                      >
                        Continue
                      </button>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-gray-100 text-xs text-gray-500 flex justify-between">
                    <span>Created: {project.createdAt}</span>
                    <span>Updated: {project.updatedAt}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'documents' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Research Documents</h2>
              <div className="text-sm text-gray-500">
                {documents.length} document{documents.length !== 1 ? 's' : ''}
              </div>
            </div>

            <div className="border border-gray-200 rounded-xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Document</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Type</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Size</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Status</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Uploaded</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-gray-50 transition duration-150">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg ${
                            doc.type === 'pdf' ? 'bg-red-100 text-red-600' :
                            doc.type === 'arxiv' ? 'bg-green-100 text-green-600' :
                            'bg-blue-100 text-blue-600'
                          }`}>
                            {doc.type === 'pdf' ? '📄' : doc.type === 'arxiv' ? '📚' : '📝'}
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{doc.name}</p>
                            <p className="text-xs text-gray-500">ID: {doc.id}</p>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          doc.type === 'pdf' ? 'bg-red-100 text-red-800' :
                          doc.type === 'arxiv' ? 'bg-green-100 text-green-800' :
                          'bg-blue-100 text-blue-800'
                        }`}>
                          {doc.type.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-gray-700">{doc.size}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(doc.status)}`}>
                            {doc.status}
                          </span>
                          {doc.status === 'processing' && <LoadingSpinner size="xs" />}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-gray-700">{doc.uploadedAt}</td>
                      <td className="py-3 px-4">
                        <div className="flex gap-2">
                          <button className="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition duration-200">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                          </button>
                          <button className="p-1.5 text-gray-600 hover:text-green-600 hover:bg-green-50 rounded transition duration-200">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleDeleteDocument(doc.id)}
                            className="p-1.5 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded transition duration-200"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-900">Research Analytics</h2>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Recent Searches */}
              <div className="border border-gray-200 rounded-xl p-5">
                <h3 className="font-semibold text-gray-900 mb-4">Recent Searches</h3>
                <div className="space-y-3">
                  {recentSearches.map((search) => (
                    <div key={search.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition duration-150">
                      <div>
                        <p className="font-medium text-gray-900">{search.query}</p>
                        <p className="text-xs text-gray-500 mt-1">{search.results} results found</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-gray-600">{search.timestamp}</p>
                        <button className="text-xs text-blue-600 hover:text-blue-800 mt-1">
                          Rerun search →
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Productivity Metrics */}
              <div className="border border-gray-200 rounded-xl p-5">
                <h3 className="font-semibold text-gray-900 mb-4">Productivity Metrics</h3>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700">Research Efficiency</span>
                      <span className="text-sm font-bold text-green-600">87%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div className="bg-green-500 h-2 rounded-full" style={{ width: '87%' }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700">Source Accuracy</span>
                      <span className="text-sm font-bold text-blue-600">92%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div className="bg-blue-500 h-2 rounded-full" style={{ width: '92%' }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700">Time Saved</span>
                      <span className="text-sm font-bold text-purple-600">78 hrs</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div className="bg-purple-500 h-2 rounded-full" style={{ width: '85%' }} />
                    </div>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-gray-200">
                  <div className="text-center">
                    <p className="text-sm text-gray-600 mb-2">Weekly Performance</p>
                    <div className="flex justify-center items-end h-20 gap-1">
                      {[65, 72, 80, 78, 85, 82, 87].map((value, index) => (
                        <div key={index} className="flex flex-col items-center">
                          <div
                            className="w-8 bg-gradient-to-t from-blue-500 to-blue-400 rounded-t"
                            style={{ height: `${value}%` }}
                          />
                          <span className="text-xs text-gray-500 mt-1">{['M', 'T', 'W', 'T', 'F', 'S', 'S'][index]}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-200 px-6 py-4 bg-gray-50">
        <div className="flex justify-between items-center text-sm text-gray-600">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span>AI Assistant: Online</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span>Vector Database: Connected</span>
            </div>
          </div>
          <div>
            Last updated: {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      </div>
    </div>
  );
}