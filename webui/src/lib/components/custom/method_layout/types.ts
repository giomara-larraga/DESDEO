import type { BaseMethodState, BaseMethodHandlers } from '$lib/types/interactive-method';
import type { SvelteComponent } from 'svelte';

// Define slot types
export interface BaseLayoutSlots {
    leftSidebar: Record<string, never>;
    rightSidebar: Record<string, never>;
    menuRow: Record<string, never>;
    visualizationArea: Record<string, never>;
    bottomPanel: Record<string, never>;
    additionalControls: Record<string, never>;
}

// Define event types
export interface BaseLayoutEvents {
    preferenceChange: CustomEvent<PreferenceChangeEvent>;
    solutionSelect: CustomEvent<SolutionSelectEvent>;
}

export interface PreferenceChangeEvent {
    preferenceValues: number[];
    numSolutions: number;
}

export interface SolutionSelectEvent {
    index: number;
}

// Props for the base layout
export interface BaseLayoutProps {
    showLeftSidebar?: boolean;
    showRightSidebar?: boolean;
}

// Props specific to method layouts
export interface MethodLayoutProps {
    handlers: BaseMethodHandlers;
    state: BaseMethodState;
    allowIntermediate?: boolean;
    showRightSidebar?: boolean;
    leftSidebarComponent?: typeof SvelteComponent<Record<string, never>>;
    rightSidebarComponent?: typeof SvelteComponent<Record<string, never>>;
    visualizationComponent?: typeof SvelteComponent<Record<string, never>>;
    tableComponent?: typeof SvelteComponent<Record<string, never>>;
}

// Define component types with slots and events
export type BaseLayoutComponent = SvelteComponent<
    BaseLayoutProps,
    BaseLayoutEvents,
    BaseLayoutSlots
>;

export type MethodLayoutComponent = SvelteComponent<
    MethodLayoutProps,
    BaseLayoutEvents,
    BaseLayoutSlots
>;