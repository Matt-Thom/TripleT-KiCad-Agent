import React from 'react';
import { useBOM } from '../context/BOMContext';
import { Trash2, Download } from 'lucide-react';

export const BOMPage: React.FC = () => {
    const { items, removeFromBOM } = useBOM();

    const handleExportCSV = () => {
        const headers = ["MPN", "Supplier", "Part Number", "Description", "Price", "Stock"];
        const rows = items.map(p => [
            p.mpn,
            p.supplier,
            p.supplier_part_number,
            `"${p.description}"`, // Escape quotes
            (p.price ?? 0).toString(),
            (p.stock ?? 0).toString()
        ]);
        
        const csvContent = [headers, ...rows].map(e => e.join(",")).join("\n");
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", "bom.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    return (
        <div className="p-6 max-w-4xl mx-auto bg-white rounded-lg shadow border border-gray-200 text-gray-800">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">Bill of Materials (BOM)</h2>
                {items.length > 0 && (
                    <button 
                        onClick={handleExportCSV}
                        className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 flex items-center gap-2"
                    >
                        <Download className="h-4 w-4" /> Export CSV
                    </button>
                )}
            </div>

            {items.length === 0 ? (
                <div className="text-center text-gray-500 py-10">
                    Your BOM is empty. Search for parts to add them.
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">MPN</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Supplier P/N</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stock</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Price</th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {items.map((part) => (
                                <tr key={part.supplier_part_number}>
                                    <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{part.mpn}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">{part.supplier_part_number}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">{part.stock ?? 0}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-green-600 font-bold">${(part.price ?? 0).toFixed(4)}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                        <button 
                                            onClick={() => removeFromBOM(part.mpn)}
                                            className="text-red-600 hover:text-red-900"
                                            title="Remove"
                                        >
                                            <Trash2 className="h-5 w-5" />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};
