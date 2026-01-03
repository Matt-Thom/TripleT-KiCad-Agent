import React, { createContext, useContext, useState, ReactNode } from 'react';
import type { Part } from '../types/Part';

interface BOMContextType {
    items: Part[];
    addToBOM: (part: Part) => void;
    removeFromBOM: (mpn: string) => void;
}

const BOMContext = createContext<BOMContextType | undefined>(undefined);

export const BOMProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [items, setItems] = useState<Part[]>([]);

    const addToBOM = (part: Part) => {
        console.log("Adding to BOM:", part);
        setItems(prev => {
            if (prev.find(p => p.mpn === part.mpn)) {
                console.log("Part already in BOM");
                return prev;
            }
            return [...prev, part];
        });
    };

    const removeFromBOM = (mpn: string) => {
        setItems(prev => prev.filter(p => p.mpn !== mpn));
    };

    return (
        <BOMContext.Provider value={{ items, addToBOM, removeFromBOM }}>
            {children}
        </BOMContext.Provider>
    );
};

export const useBOM = () => {
    const context = useContext(BOMContext);
    if (!context) throw new Error('useBOM must be used within a BOMProvider');
    return context;
};
