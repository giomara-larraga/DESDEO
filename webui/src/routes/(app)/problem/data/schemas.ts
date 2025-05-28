import { z } from "zod";

// We're keeping a simple non-relational schema here.
// IRL, you will have a schema for your data models.
export const problemSchema = z.object({
	id: z.string(),
	name: z.string(),
	objectives: z.number(),
	variables: z.number(),
	definedby: z.string(),
});

export type Problem = z.output<typeof problemSchema>;
