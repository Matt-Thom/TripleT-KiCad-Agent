import { useState } from 'react';
import { PartSearch } from './components/PartSearch';
import { ChatInterface } from './components/ChatInterface';
import { SettingsPage } from './components/SettingsPage';
import { Settings, Home } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState<'home' | 'settings'>('home');

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-4 px-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">TripleT KiCad Agent</h1>
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setActiveTab('home')}
              className={`p-2 rounded hover:bg-gray-100 ${activeTab === 'home' ? 'text-blue-600' : 'text-gray-500'}`}
              title="Home"
            >
              <Home className="h-6 w-6" />
            </button>
            <button 
              onClick={() => setActiveTab('settings')}
              className={`p-2 rounded hover:bg-gray-100 ${activeTab === 'settings' ? 'text-blue-600' : 'text-gray-500'}`}
              title="Settings"
            >
              <Settings className="h-6 w-6" />
            </button>
            <div className="text-sm text-gray-500 font-mono border-l pl-4 ml-2">KiCad 9 Native</div>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full p-4">
        {activeTab === 'home' ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="flex flex-col gap-6">
              <ChatInterface />
            </div>
            <div className="flex flex-col gap-6">
              <PartSearch />
            </div>
          </div>
        ) : (
          <SettingsPage />
        )}
      </main>
    </div>
  );
}

export default App;