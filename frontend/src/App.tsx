import { useState } from 'react';
import { PartSearch } from './components/PartSearch';
import { ChatInterface } from './components/ChatInterface';
import { SettingsPage } from './components/SettingsPage';
import { BOMPage } from './components/BOMPage';
import { Settings, Home, ShoppingCart } from 'lucide-react';
import { useBOM } from './context/BOMContext';

function MainLayout() {
  const [activeTab, setActiveTab] = useState<'home' | 'bom' | 'settings'>('home');
  const { items } = useBOM();

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
              onClick={() => setActiveTab('bom')}
              className={`p-2 rounded hover:bg-gray-100 relative ${activeTab === 'bom' ? 'text-blue-600' : 'text-gray-500'}`}
              title="BOM"
            >
              <ShoppingCart className="h-6 w-6" />
              {items.length > 0 && (
                <span className="absolute top-0 right-0 bg-red-500 text-white text-xs rounded-full h-4 w-4 flex items-center justify-center">
                  {items.length}
                </span>
              )}
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
        {activeTab === 'home' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="flex flex-col gap-6">
              <ChatInterface />
            </div>
            <div className="flex flex-col gap-6">
              <PartSearch />
            </div>
          </div>
        )}
        {activeTab === 'bom' && <BOMPage />}
        {activeTab === 'settings' && <SettingsPage />}
      </main>
    </div>
  );
}

function App() {
  return <MainLayout />;
}

export default App;