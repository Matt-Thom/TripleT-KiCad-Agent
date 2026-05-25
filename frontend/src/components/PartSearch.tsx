import React, { useState } from 'react';
import axios from 'axios';
import type { Part } from '../types/Part';
import { Search, Loader2, Check } from 'lucide-react';
import { useBOM } from '../context/BOMContext';

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) || '';

export const PartSearch: React.FC = () => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<Part[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const { addToBOM, items } = useBOM();

    const isPartInBOM = (mpn: string) => items.some(p => p.mpn === mpn);

    const handleGenerateSchematic = async (mpn: string, supplierId: string) => {
        try {
            const response = await axios.post(
                `${API_BASE}/api/generate/schematic`, 
                null, 
                {
                    params: { mpn, supplier_id: supplierId },
                    responseType: 'blob'
                }
            );
            
            // Create download link
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `${mpn}.kicad_sch`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error(err);
            alert('Failed to generate schematic.');
        }
    };

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setError('');
        setResults([]);

        try {
            const response = await axios.get<Part[]>(`${API_BASE}/api/search/lcsc`, {
                params: { q: query }
            });
            setResults(response.data);
        } catch (err) {
            console.error(err);
            setError('Failed to fetch results. Ensure backend is running.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-4 max-w-4xl mx-auto">
            <h2 className="text-2xl font-bold mb-4">Component Search</h2>
            
            <form onSubmit={handleSearch} className="flex gap-2 mb-6">
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search for parts (e.g., STM32, 10k Resistor)..."
                    className="flex-1 p-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-black"
                />
                <button 
                    type="submit" 
                    disabled={loading}
                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 flex items-center gap-2 disabled:opacity-50"
                >
                    {loading ? <Loader2 className="animate-spin h-4 w-4" /> : <Search className="h-4 w-4" />}
                    Search
                </button>
            </form>

            {error && (
                <div className="bg-red-50 text-red-700 p-3 rounded-md mb-4">
                    {error}
                </div>
            )}

            <div className="space-y-2">
                {results.length > 0 ? (
                    results.map((part) => (
                        <div key={part.supplier_part_number} className="bg-white p-4 rounded-lg shadow border border-gray-200 flex justify-between items-center text-black">
                            <div>
                                <h3 className="font-bold text-lg">{part.mpn}</h3>
                                <p className="text-sm text-gray-600">{part.description}</p>
                                <div className="text-xs text-gray-500 mt-1">
                                    Supplier: <span className="font-semibold">{part.supplier}</span> | 
                                    Stock: <span className="font-semibold">{part.stock ?? 0}</span>
                                </div>
                            </div>
                            <div className="text-right flex flex-col gap-2">
                                <div className="text-xl font-bold text-green-600">${(part.price ?? 0).toFixed(4)}</div>
                                <button 
                                    onClick={() => handleGenerateSchematic(part.mpn, part.supplier_part_number)}
                                    className="text-xs bg-blue-50 hover:bg-blue-100 text-blue-700 px-2 py-1 rounded border border-blue-200"
                                >
                                    Generate Schematic
                                </button>
                                <button 
                                    onClick={() => addToBOM(part)}
                                    disabled={isPartInBOM(part.mpn)}
                                    className={`text-xs px-2 py-1 rounded flex items-center justify-center gap-1 ${
                                        isPartInBOM(part.mpn) 
                                        ? 'bg-green-100 text-green-800 cursor-default' 
                                        : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
                                    }`}
                                >
                                    {isPartInBOM(part.mpn) ? <><Check className="h-3 w-3"/> Added</> : 'Add to BOM'}
                                </button>
                            </div>
                        </div>
                    ))
                ) : (
                    !loading && <div className="text-center text-gray-500 mt-10">No results found.</div>
                )}
            </div>
        </div>
    );
};
