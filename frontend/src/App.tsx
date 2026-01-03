import { PartSearch } from './components/PartSearch';

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4">
          <h1 className="text-3xl font-bold text-gray-900">TripleT KiCad Agent</h1>
        </div>
      </header>
      <main>
        <PartSearch />
      </main>
    </div>
  );
}

export default App;