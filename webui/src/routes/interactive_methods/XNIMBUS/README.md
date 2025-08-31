# XNIMBUS Implementation

## Overview

XNIMBUS is an extension of the NIMBUS method that includes explainability features. This implementation uses a modular approach based on the base method structure.

## Folder Structure and Contents

### Core Library (`src/lib/`)

```
src/lib/
├── components/
│   └── method_layout/
│       ├── base-method-layout.svelte  # Base layout component for all methods
│       ├── index.ts                   # Exports for method layout components
│       ├── layout-types.ts            # Types for layout props and slots
│       └── README.md                  # Documentation for base layout usage
└── types/
    └── interactive-method.ts          # Core type definitions shared across methods
```

### Shared Components (`src/routes/interactive_methods/shared/`)

```
shared/
├── services/
│   ├── api-service.ts       # Base API service with common HTTP handling
│   └── types.ts            # Shared API types and interfaces
├── utils/
│   ├── solution-utils.ts   # Common utilities for solution handling
│   └── validation.ts       # Shared validation functions
└── components/            # Reusable components across methods
    ├── solution-table/
    ├── preference-bar/
    └── visualization/
```

### XNIMBUS Implementation (`src/routes/interactive_methods/XNIMBUS/`)

```
XNIMBUS/
├── components/                        # XNIMBUS-specific components
│   ├── sidebar/
│   │   ├── xnimbus-sidebar.svelte    # Main preference input sidebar
│   │   ├── explanation-sidebar.svelte # Explainability features sidebar
│   │   └── types.ts                  # Sidebar component types
│   ├── visualization/
│   │   ├── xnimbus-visualization.svelte   # Main visualization component
│   │   ├── explanation-view.svelte        # Explainability visualizations
│   │   └── types.ts                       # Visualization component types
│   └── table/
│       ├── xnimbus-table.svelte      # Solution table with explanations
│       └── types.ts                  # Table component types
├── handlers/
│   ├── xnimbus-handlers.ts          # XNIMBUS-specific method handlers
│   └── explanation-handlers.ts       # Handlers for explainability features
├── stores/
│   ├── xnimbus-store.ts             # Main XNIMBUS state management
│   └── explanation-store.ts          # State for explainability features
├── types/
│   └── xnimbus-types.ts             # XNIMBUS-specific type definitions
├── utils/
│   ├── explanation-utils.ts          # Utilities for explainability features
│   └── data-processing.ts           # Data processing helpers
├── +page.svelte                     # Main XNIMBUS page component
├── +page.server.ts                  # Server-side logic
└── README.md                        # XNIMBUS documentation
```

### File Contents Overview

#### Base Layout Components

- `base-method-layout.svelte`: Base layout structure with slots for customization
- `layout-types.ts`: Type definitions for layout props and slots
- `index.ts`: Exports and re-exports of layout components

#### Core Types

- `interactive-method.ts`: Shared interfaces and types for all methods
  - `BaseMethodState`
  - `BaseMethodHandlers`
  - `PreferenceData`
  - `Solution`

#### XNIMBUS Components

1. **Sidebar Components**

   - `xnimbus-sidebar.svelte`: Main preference input interface
   - `explanation-sidebar.svelte`: Explainability controls and information

2. **Visualization Components**

   - `xnimbus-visualization.svelte`: Main solution visualization
   - `explanation-view.svelte`: Explainability visualizations

3. **Table Components**
   - `xnimbus-table.svelte`: Enhanced solution table with explanation features

#### State Management

- `xnimbus-store.ts`: Main state store with XNIMBUS-specific features
- `explanation-store.ts`: Dedicated store for explainability data

#### Handlers

- `xnimbus-handlers.ts`: Method-specific operation handlers
- `explanation-handlers.ts`: Handlers for explainability features

#### Types and Utilities

- `xnimbus-types.ts`: XNIMBUS-specific type definitions
- `explanation-utils.ts`: Helper functions for explainability features

````

Each component and file should follow these guidelines:
- Use TypeScript for type safety
- Include proper documentation and comments
- Follow the project's coding standards
- Include unit tests where appropriate

## Implementation Details

### Handlers and API Integration

Handlers in XNIMBUS serve as intermediaries between the UI components and the API service. They encapsulate the business logic and state management for specific operations.

#### Handler Structure
```typescript
// Example handler structure
export class XNimbusHandler implements BaseMethodHandler {
    constructor(
        private store: XNimbusStore,
        private apiService: ApiService
    ) {}

    async handlePreferenceUpdate(preferences: PreferenceData): Promise<void> {
        // 1. Update local state
        this.store.setPreferences(preferences);

        // 2. Make API call
        const response = await this.apiService.updatePreferences({
            methodId: this.store.getMethodId(),
            preferences
        });

        // 3. Process response
        if (response.solutions) {
            this.store.updateSolutions(response.solutions);
        }
    }
}
```

#### API Integration
The API service follows a consistent pattern:

1. **Base Service Setup**
```typescript
// api-service.ts
export class ApiService {
    private readonly baseUrl: string;

    async makeRequest<T>(endpoint: string, options: RequestOptions): Promise<T> {
        // Common request handling logic
    }
}
```

2. **Method-Specific Endpoints**
```typescript
// xnimbus-specific API calls
export class XNimbusApiService extends ApiService {
    async getExplanation(solutionId: string): Promise<ExplanationData> {
        return this.makeRequest('/xnimbus/explain', {
            method: 'POST',
            body: { solutionId }
        });
    }
}
```

### Store Implementation

XNIMBUS uses Svelte 5's state management with a modular store structure:

#### Main Store Structure
```typescript
// xnimbus-store.ts
export class XNimbusStore {
    // Core state
    private methodState = $state({
        currentStep: 0,
        solutions: [],
        preferences: null
    });

    // Derived state
    get currentSolution() {
        return this.methodState.solutions[this.methodState.currentStep];
    }

    // State updates
    setPreferences(preferences: PreferenceData) {
        this.methodState.preferences = preferences;
    }
}
```

#### Store Usage in Components
```typescript
// xnimbus-sidebar.svelte
<script lang="ts">
    import { xnimbusStore } from '../stores/xnimbus-store';
    import type { PreferenceData } from '../types';

    function updatePreferences(data: PreferenceData) {
        xnimbusStore.setPreferences(data);
    }
</script>
```

#### Explanation Store Integration
```typescript
// explanation-store.ts
export class ExplanationStore {
    private explanationState = $state({
        explanations: new Map<string, ExplanationData>(),
        activeExplanation: null
    });

    async loadExplanation(solutionId: string) {
        const data = await apiService.getExplanation(solutionId);
        this.explanationState.explanations.set(solutionId, data);
        this.explanationState.activeExplanation = data;
    }
}
```

### Data Flow

1. **User Interaction**
   - Component triggers handler method
   - Handler updates local state
   - Handler makes API call

2. **API Response**
   - Handler receives response
   - Updates relevant stores
   - Components react to store changes

3. **State Updates**
   - Stores emit changes
   - Components subscribe to relevant state
   - UI updates automatically

4. **Error Handling**
   - Handlers catch and process errors
   - Store maintains error state
   - Components display appropriate error UI

## Completed Changes

1. ✅ Base method layout structure
2. ✅ Basic type definitions
3. ✅ Store setup
4. ✅ Basic handler structure
5. ✅ Integration with shared API service

## Pending Tasks

### High Priority

1. 🔴 Fix current TypeScript errors:

   - `Object literal may only specify known properties, and 'children' does not exist in type 'Props'`
   - `Cannot find name 'state'. Did you mean '$state'`
   - `Type 'Response' is not assignable to type 'Response'`
   - `Object literal may only specify known properties, and '"value"' does not exist`

2. 🔴 Essential Implementation Tasks:
   - Implement proper slot types in base layout
   - Complete XNIMBUS-specific handler implementations
   - Add proper store type definitions
   - Fix component prop type definitions

### Medium Priority

1. 🟡 XNIMBUS-Specific Features:

   - Implement explainability visualization components
   - Add explanation data handling in store
   - Create explanation sidebar component
   - Add explanation data processing utilities

2. 🟡 Component Implementation:
   - Complete XNimbusSidebar implementation
   - Complete XNimbusVisualization implementation
   - Complete XNimbusTable implementation
   - Add proper component documentation

### Low Priority

1. 🟢 Enhancement Features:
   - Add state persistence
   - Implement undo/redo functionality
   - Add proper error boundaries
   - Improve accessibility

## Current Errors and Solutions

### 1. Layout Component Props Error

```typescript
Error: Object literal may only specify known properties, and 'children' does not exist in type 'Props'
Solution: Need to properly define slot types in base-method-layout.svelte
````

### 2. State Management Error

```typescript
Error: Cannot find name 'state'. Did you mean '$state'
Solution: Update store implementation to use proper Svelte store syntax
```

### 3. Type Definition Conflict

```typescript
Error: Type 'Response' is not assignable to type 'Response'
Solution: Need to consolidate Response type definitions and remove duplicates
```

### 4. Component Prop Validation

```typescript
Error: Object literal may only specify known properties, and '"value"' does not exist
Solution: Add proper prop type definitions for all components
```

## Required API Endpoints

- `/api/xnimbus/initialize`
- `/api/xnimbus/iterate`
- `/api/xnimbus/intermediate`
- `/api/xnimbus/save`
- `/api/xnimbus/remove_saved`
- `/api/xnimbus/explain` (new endpoint)

## Next Steps

1. Fix TypeScript errors in order of priority
2. Complete basic XNIMBUS functionality
3. Add explainability features
4. Implement proper error handling
5. Add tests
6. Add documentation

## Notes

- All API endpoints should follow the same structure as NIMBUS
- Explainability features should be modular and easy to disable
- Component props should be properly typed
- Need to maintain backwards compatibility with base method structure

## Dependencies

- Svelte 5
- TypeScript
- SvelteKit
- TailwindCSS
- DaisyUI

## Questions or Issues?

Contact: Giomara Larraga (glarragw@jyu.fi)
