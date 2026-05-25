import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import axios from 'axios';
import type { Part } from '../types/Part';

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) || '';

export interface BomRecord extends Part {
    id: number;
    project_id: number;
    quantity: number;
    created_at: string;
}

interface ProjectRecord {
    id: number;
    name: string;
    created_at: string;
}

interface BOMContextType {
    items: BomRecord[];
    projectId: number | null;
    loading: boolean;
    error: string | null;
    addToBOM: (part: Part) => Promise<void>;
    removeFromBOM: (itemId: number) => Promise<void>;
    updateQuantity: (itemId: number, newQty: number) => Promise<void>;
    refresh: () => Promise<void>;
}

const BOMContext = createContext<BOMContextType | undefined>(undefined);

export const BOMProvider = ({ children }: { children: ReactNode }) => {
    const [items, setItems] = useState<BomRecord[]>([]);
    const [projectId, setProjectId] = useState<number | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    const fetchBom = useCallback(async (pid: number) => {
        const res = await axios.get<BomRecord[]>(`${API_BASE}/api/projects/${pid}/bom`);
        setItems(res.data);
    }, []);

    const bootstrap = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await axios.get<ProjectRecord[]>(`${API_BASE}/api/projects`);
            const defaultProject =
                res.data.find((p) => p.name === 'Default') ?? res.data[0];
            if (!defaultProject) {
                setProjectId(null);
                setItems([]);
                return;
            }
            setProjectId(defaultProject.id);
            await fetchBom(defaultProject.id);
        } catch (err) {
            console.error('Failed to load BOM', err);
            setError('Failed to load BOM from server');
        } finally {
            setLoading(false);
        }
    }, [fetchBom]);

    useEffect(() => {
        void bootstrap();
    }, [bootstrap]);

    const addToBOM = useCallback(
        async (part: Part) => {
            if (projectId === null) return;
            if (items.some((item) => item.mpn === part.mpn)) return;
            try {
                await axios.post(`${API_BASE}/api/projects/${projectId}/bom`, {
                    mpn: part.mpn,
                    manufacturer: part.manufacturer,
                    description: part.description,
                    price: part.price ?? null,
                    stock: part.stock ?? null,
                    supplier: part.supplier,
                    supplier_part_number: part.supplier_part_number,
                    datasheet_url: part.datasheet_url ?? null,
                    attributes: part.attributes ?? {},
                    quantity: 1,
                });
                await fetchBom(projectId);
            } catch (err) {
                console.error('Failed to add BOM item', err);
                setError('Failed to add BOM item');
            }
        },
        [projectId, items, fetchBom],
    );

    const removeFromBOM = useCallback(
        async (itemId: number) => {
            if (projectId === null) return;
            try {
                await axios.delete(
                    `${API_BASE}/api/projects/${projectId}/bom/${itemId}`,
                );
                await fetchBom(projectId);
            } catch (err) {
                console.error('Failed to remove BOM item', err);
                setError('Failed to remove BOM item');
            }
        },
        [projectId, fetchBom],
    );

    const updateQuantity = useCallback(
        async (itemId: number, newQty: number) => {
            if (projectId === null) return;
            if (newQty < 1) return;
            try {
                await axios.put(
                    `${API_BASE}/api/projects/${projectId}/bom/${itemId}`,
                    { quantity: newQty },
                );
                await fetchBom(projectId);
            } catch (err) {
                console.error('Failed to update BOM item quantity', err);
                setError('Failed to update BOM item quantity');
            }
        },
        [projectId, fetchBom],
    );

    const refresh = useCallback(async () => {
        if (projectId !== null) {
            await fetchBom(projectId);
        }
    }, [projectId, fetchBom]);

    return (
        <BOMContext.Provider
            value={{
                items,
                projectId,
                loading,
                error,
                addToBOM,
                removeFromBOM,
                updateQuantity,
                refresh,
            }}
        >
            {children}
        </BOMContext.Provider>
    );
};

export const useBOM = () => {
    const context = useContext(BOMContext);
    if (!context) throw new Error('useBOM must be used within a BOMProvider');
    return context;
};
