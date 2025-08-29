import type { components } from '$lib/api/client-types';

export type DialogConfig = {
	open: boolean;
	title: string;
	description: string;
	confirmText: string;
	cancelText: string;
	onConfirm: () => void;
	onCancel?: () => void;
	confirmVariant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
};
	
export type PeriodKey = 'period1' | 'period2' | 'period3';

export type ProblemInfo = components['schemas']['ProblemInfo'];
export type Solution = components['schemas']['UserSavedSolutionAddress'];
export type ObjectiveInfo = components['schemas']['ProblemInfo']['objectives'][0];
export type SolutionType = 'current' | 'best' | 'all';
