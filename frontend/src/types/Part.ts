export interface Part {
    mpn: string;
    manufacturer: string;
    description: string;
    price?: number;
    stock?: number;
    supplier: string;
    supplier_part_number: string;
    datasheet_url?: string | null;
    attributes?: Record<string, unknown>;
}
