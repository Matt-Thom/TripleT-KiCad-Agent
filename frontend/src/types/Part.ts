export interface Part {
    mpn: string;
    manufacturer: string;
    description: string;
    price: number;
    stock: number;
    supplier_part_number: string;
    supplier: string;
    datasheet_url?: string;
    attributes: Record<string, any>;
}
