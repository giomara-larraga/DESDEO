import { z } from "zod";

// Objective schema
export const objectiveSchema = z.object({
    name: z.string(),
    direction: z.enum(["minimize", "maximize"]),
    ideal: z.number().nullable(),
    nadir: z.number().nullable(),
});

export type Objective = z.infer<typeof objectiveSchema>;

// Variable schema
export const variableSchema = z.object({
    name: z.string(),
    lower: z.number().nullable().optional(),
    upper: z.number().nullable().optional(),
    type: z.enum(["integer", "binary", "continuous"]),
});

export type Variable = z.infer<typeof variableSchema>;

// Constraint schema
export const constraintSchema = z.object({
    name: z.string(),
    type: z.enum(["inequality", "equation"]),
    simulated: z.boolean(),
    convex: z.boolean(),
    expensive: z.boolean(),
});

export type Constraint = z.infer<typeof constraintSchema>;

// Solution schema
export const solutionSchema = z.object({
    id: z.string(),
    createdAt: z.string().datetime(),
    createdBy: z.string(),
    createdByName: z.string(),
});

export type Solution = z.infer<typeof solutionSchema>;

export const problemSchema = z.object({
	id: z.string(),
	name: z.string(),
	description: z.string(),
	objectives: z.array(objectiveSchema),
	variables: z.array(variableSchema),
	constraints: z.array(constraintSchema),
	definedby: z.string(),
	isLinear: z.boolean(),
	createdAt: z.string().datetime(),
	isConvex: z.boolean(),
	isTwiceDifferentiable: z.boolean(),
	isSurrogateAvailable: z.boolean(),
	solutions: z.array(solutionSchema).optional(),
});

export type Problem = z.output<typeof problemSchema>;

