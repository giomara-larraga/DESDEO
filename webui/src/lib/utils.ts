import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { ResponseNIMBUS as Response } from '$lib/types/nimbus'; //TODO:Modify to accept any tipe of solution and not only NIMBUS
import type { SolutionType } from '$lib/types/general';

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type WithoutChild<T> = T extends { child?: any } ? Omit<T, "child"> : T;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type WithoutChildren<T> = T extends { children?: any } ? Omit<T, "children"> : T;
export type WithoutChildrenOrChild<T> = WithoutChildren<WithoutChild<T>>;
export type WithElementRef<T, U extends HTMLElement = HTMLElement> = T & { ref?: U | null };


export function getSolutions(state: Response | null, type: SolutionType) {
  if (!state) return [];
  if (type === 'current') return state.current_solutions || [];
  if (type === 'best') return state.saved_solutions || [];
  return state.all_solutions || [];
}

export function getSolutionsLabel(type: SolutionType) {
  if (type === 'current') return 'Current solutions';
  if (type === 'best') return 'Best candidate solutions';
  return 'All solutions';
}