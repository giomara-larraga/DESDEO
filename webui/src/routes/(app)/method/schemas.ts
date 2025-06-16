import { z } from "zod";

// Variant schema: each variant can have its own preferencesType and problemtypes
const variantSchema = z.object({
    name: z.string(),
    preferencesType: z.array(z.string()),
    problemtypes: z.array(z.string())
});

// Method schema: if variants exist, use them; otherwise, method has its own preferencesType and problemtypes
export const methodSchema = z.object({
    name: z.string(),
    shortName: z.string().optional(),
    preferencesType: z.array(z.string()).optional(),
    problemtypes: z.array(z.string()).optional(),
    variants: z.array(variantSchema).optional()
});

export type Method = z.infer<typeof methodSchema>;
export type Variant = z.infer<typeof variantSchema>;