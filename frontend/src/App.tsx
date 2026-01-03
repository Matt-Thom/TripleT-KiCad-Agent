import { PartSearch } from './components/PartSearch';
import { ChatInterface } from './components/ChatInterface';

function App() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-4 px-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">TripleT KiCad Agent</h1>
          <div className="text-sm text-gray-500 font-mono">KiCad 9 Native</div>
        </div>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full p-4 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="flex flex-col gap-6">
          <ChatInterface />
        </div>
        <div className="flex flex-col gap-6">
          <PartSearch />
        </div>
      </main>
    </div>
  );
}

export default App;