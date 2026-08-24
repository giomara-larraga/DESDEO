<script lang="ts">
	/**
	 * +page.svelte (GDM-SCORE-bands method)
	 *
	 * @author Stina (Functionality) <palomakistina@gmail.com>
	 * @author Giomara Larraga (Base structure) <glarragw@jyu.fi>
	 * @created December 2025
	 *
	 * @description
	 * Group decision making interface using SCORE-bands method.
	 * Handles consensus phase (band voting) and decision phase (solution voting).
	 *
	 * @props
	 * @property {Object} data - Contains authentication token, group info, and problem data.
	 * @property {string} data.refreshToken - JWT refresh token for authentication.
	 * @property {GroupPublic} data.group - Group information including members and owner.
	 * @property {ProblemInfo} data.problem - Optimization problem definition and metadata.
	 *
	 * @features
	 * - Real-time collaboration via WebSocket
	 * - Two-phase process: consensus reaching and decision phase
	 * - SCORE-bands visualization for voting in consensus reaching phase
	 * - Parallel coordinates visualization for solution voting in decision phase
	 * - Configuration panel for method parameters (number of solutions, clusters, etc.) (group owner only)
	 * - History browser with possibility to revert to chosen iteration (group owner only)
	 * - Role-based access control (group owner vs decision makers)
	 * - Cluster visibility controls with solution count display
	 * - Agreement calculation and consensus indicators (axis colors)
	 * - Voted bands visible in bar chart visualization
	 * - Solution table with detailed objective and decision variable values for decision phase
	 *
	 * @dependencies
	 * - ScoreBands: Main visualization component for SCORE-bands method
	 * - ParallelCoordinates: Visualization for solution comparison
	 * - ScoreBandsSolutionTable: Table component for displaying solution details
	 * - HistoryBrowser: Component for browsing iteration history
	 * - ConfigPanel: Configuration interface for method parameters
	 * - WebSocketService: Real-time communication service for collaboration
	 * - Button: UI component for actions and controls
	 * - Alert: For displaying error messages and notifications
	 * - createObjectiveDimensions: Helper for visualization data transformation
	 * - Helper functions: drawVotesChart, calculateAxisAgreement, generate_axis_options, etc.
	 *
	 * @notes
	 * - WebSocket connection is established automatically when component mounts
	 * - User roles are determined from group membership and ownership
	 * - State is managed using Svelte's reactive $state and $derived declarations
	 * - Real-time updates are handled through WebSocket message processing
	 * - Consensus is calculated based on agreement thresholds and vote patterns
	 *
	 * @phases
	 * 1. Band Voting Phase (CRP):
	 *    - Decision makers vote on preferred objective value bands
	 *    - SCORE-bands visualization shows clusters and voting interface
	 *    - Real-time consensus tracking with agreement indicators
	 *    - Configuration panel allows adjusting method parameters
	 *
	 * 2. Solution Voting Phase (Decision phase):
	 *    - Activated after API returns different data without bands, meaning there are under 10 solutions
	 *    - Parallel coordinates show solutions within agreed bands
	 *    - Decision makers vote on specific solutions
	 *    - Final solution selected based on voting results
	 */

	import { Button } from '$lib/components/ui/button';
	import ScoreBands from '$lib/components/visualizations/score-bands/score-bands.svelte';
	import ParallelCoordinates from '$lib/components/visualizations/parallel-coordinates/parallel-coordinates.svelte';
	import ScoreBandsSolutionTable from './components/score-bands-solution-table.svelte';
	import ClusterBandTable from '$lib/components/custom/score-bands-table/solution-table.svelte';
	import HistoryBrowser from './components/history-browser.svelte';
	import ConfigPanel from './components/config-panel.svelte';
	import { onMount, onDestroy } from 'svelte';
	import type { GroupPublic, ProblemInfo, GDMSCOREBandsResponse, GDMSCOREBandsDecisionResponse, SCOREBandsResult, SCOREBandsConfig, GDMSCOREBandsFinalSelection, SCOREBandsGDMConfig } from '$lib/gen/endpoints/DESDEOFastAPI';
	import { auth } from '../../../stores/auth';
	import { errorMessage } from '../../../stores/uiState';
	import Alert from '$lib/components/custom/notifications/alert.svelte';
	import { createObjectiveDimensions } from '$lib/helpers/visualization-data-transform';

	import { WebSocketService } from './websocket-store';
	import Users from "@lucide/svelte/icons/users";

	import {
		drawVotesChart,
		callGSCOREBandsAPI,
		calculateAxisAgreement,
		generate_axis_options,
		generate_cluster_colors,
		calculateScales
	} from './helper-functions';
	import ScoreBandsLeftSidebar from './components/score-bands-left-sidebar.svelte';
	import ScoreBandsRightSidebar from './components/score-bands-right-sidebar.svelte';

	type GdmPhase = 'learning' | 'consensus' | 'decision';
	type ScoreBandsHistoryItem =
		| (GDMSCOREBandsResponse & { phase?: 'learning' | 'consensus' })
		| (GDMSCOREBandsDecisionResponse & { phase?: 'decision' });

	type LearningNote = {
		id: string;
		targetType: 'band' | 'sub-band' | 'solution';
		targetId: string;
		text: string;
		createdAt: string;
	};

	type LearningSubBand = {
		id: string;
		parentClusterId: number;
		label: string;
		solutionIndices: number[];
		color: string;
	};

	let learningState = $state({
		selectedBand: null as number | null,
		savedBands: [] as number[],
		comparedBands: [] as number[],
		notes: [] as LearningNote[],
		zoomedBand: null as number | null,
		subBands: [] as LearningSubBand[],
		subBandsHistory: [] as LearningSubBand[][] // stack for undo
	});
	let learningProgress = $state({
		completedUserIds: [] as number[],
		startedAt: null as string | null,
		durationSeconds: 900,
		lastWarningAt: null as string | null,
		lastWarningMessage: null as string | null
	});
	let learningNotice = $state<string | null>(null);
	let ownerWarningMessage = $state('');
	let isMarkingLearningComplete = $state(false);
	let isWarningUsers = $state(false);
	let isAdvancingToConsensus = $state(false);
	let learningNowMs = $state(Date.now());
	let learningClockTimer: ReturnType<typeof setInterval> | null = null;

	let minimumVotes: number | undefined = $state(1);

	const { data } = $props<{
		data: {
			refreshToken: string;
			group: GroupPublic;
			problem: ProblemInfo;
		};
	}>();

	// User authentication
	let userId = $auth.user?.id;
	let isOwner = $state(false);
	let isDecisionMaker = $state(false);

	// Initialize user roles
	$effect(() => {
		isOwner = userId === data.group.owner_id;
		isDecisionMaker = (data.group.users ?? []).some(
				(member:any) => member.id === userId
			);
	});

	// WebSocket service for real-time updates
	let wsService: WebSocketService | null = $state(null);

	//
	let data_loaded = $state(false);
	let loading_error: string | null = $state(null);

	// State of votes, confirms, and related data
	let vote_confirmed = $state(false);
	let votes_and_confirms = $state({
		confirms: [] as number[],
		votes: {} as Record<string, number>,
		phase: 'learning' as GdmPhase,

		completed_user_ids: [] as number[],
		started_at: null as string | null,
		duration_seconds: 900 as number | null,
		last_warning_at: null as string | null,
		last_warning_message: null as string | null,

		learning_completed_user_ids: [] as number[],
		learning_started_at: null as string | null,
		learning_duration_seconds: 900 as number | null,
		learning_last_warning_at: null as string | null,
		learning_last_warning_message: null as string | null
	});
	// If user has voted, usersVote is the id they voted for. If not, null.
	let usersVote: number | null = $derived.by(() => {
		if (userId == null) {
			return null;
		}

		const userKey = String(userId);

		if (
			Object.prototype.hasOwnProperty.call(
				votes_and_confirms.votes,
				userKey
			)
		) {
			return votes_and_confirms.votes[userKey];
		}

		return null;
	});
	const totalVoters = $derived((data.group.users ?? []).length);
	let have_all_voted = $derived.by(() => {
		return totalVoters === Object.keys(votes_and_confirms.votes || {}).length;
	});

	$effect(() => {
		if (userId) {
			vote_confirmed = votes_and_confirms.confirms.includes(userId);
		} else {
			vote_confirmed = false;
		}
	});

	let votes_per_cluster: Record<number, number> = $derived.by(() => {
		const counts: Record<number, number> = {};
		Object.values(votes_and_confirms.votes).forEach((bandId) => {
			if (!(bandId in counts)) {
				counts[bandId] = 0;
			}
			counts[bandId] += 1;
		});
		return counts;
	});

function setOwnerWarningMessage(value: string) {
	ownerWarningMessage = value;
}

function voteForSelectedBand() {
	return vote(selected_band);
}
function getClusterVoteCount(clusterId: number): number {
	return votes_per_cluster[clusterId] ?? 0;
}

function getClusterVotePercent(clusterId: number): number {
	if (totalVoters === 0) return 0;
	return Math.round((getClusterVoteCount(clusterId) / totalVoters) * 100);
}

function getConsensusLabel(axisName: string): string {
	const status = axis_agreement?.[axisName];

	if (status === 'agreement') return 'Agreement';
	if (status === 'disagreement') return 'Disagreement';
	return 'Neutral';
}

function getConsensusClasses(axisName: string): string {
	const status = axis_agreement?.[axisName];

	if (status === 'agreement') return 'text-green-700';
	if (status === 'disagreement') return 'text-red-700';
	return 'text-muted-foreground';
}

	// Calculate axis agreement when everyone has voted
	let axis_agreement = $derived.by(() => {
		// Only calculate if we're in consensus phase and have the necessary data
		if (!isConsensusPhase || !SCOREBands.medians || !SCOREBands.scales) {
			return {};
		}

		const votesCount = Object.keys(votes_and_confirms.votes || {}).length;

		// Calculate when everyone has voted
		if (votesCount === totalVoters) {
			return calculateAxisAgreement(
				votes_and_confirms,
				SCOREBands.medians,
				SCOREBands.scales,
				0.1, // agreement threshold
				0.9 // disagreement threshold
			);
		}

		return {}; // Return empty object when conditions aren't met
	});

	// Iteration info: history, current iteration, phase, etc.
	let history: ScoreBandsHistoryItem[] = $state([]);
	let currentPhase = $state<GdmPhase>('learning');
	let phase = $state('Learning Phase');

	let isLearningPhase = $derived(phase === 'Learning Phase');
	let isDecisionPhase = $derived(phase === 'Decision Phase');
	let isConsensusPhase = $derived(phase === 'Consensus Reaching Phase');
	let learningCompletedCount = $derived(learningProgress.completedUserIds.length);
	let hasCompletedLearning = $derived.by(() => {
		if (userId === undefined || userId === null) {
			return false;
		}

		return learningProgress.completedUserIds
			.map(String)
			.includes(String(userId));
	});
	let allDecisionMakersFinishedLearning = $derived(learningCompletedCount === totalVoters);
	let learningDeadlineMs = $derived.by(() => {
		if (!learningProgress.startedAt) {
			return null;
		}

		const startedAtMs = new Date(learningProgress.startedAt).getTime();
		if (Number.isNaN(startedAtMs)) {
			return null;
		}

		return startedAtMs + learningProgress.durationSeconds * 1000;
	});
	let learningSecondsRemaining = $derived.by(() => {
		if (!learningDeadlineMs) {
			return null;
		}

		return Math.max(0, Math.ceil((learningDeadlineMs - learningNowMs) / 1000));
	});
	let learningTimeLabel = $derived.by(() => {
		if (learningSecondsRemaining === null) {
			return 'Not started';
		}

		return formatDuration(learningSecondsRemaining);
	});

	
	//let iteration_id = $state(0); // for header and fetch_score_bands

	let groupIterationId = $state<number | null>(null); //Group iteration id from backend, used for history browser and fetch_score_bands
	let latestIteration = $state<number | null>(null);	//SCOREBandsGDMResult.iteration 

	// current iteration data for consensus reaching phase, when bands exist
	let scoreBandsResult: SCOREBandsResult | null = $state(null);

	// Configuration and latestIteration are used in initialization and configPanel
	//let latestIteration: number | null = $state(null);
	let scoreBandsConfig: SCOREBandsConfig = $state({
		clustering_algorithm: {
			name: 'KMeans',
			n_clusters: 5
		},
		distance_formula: 1,
		distance_parameter: 0.05,
		use_absolute_correlations: false,
		include_solutions: false,
		include_medians: true,
		interval_size: 0.25
	});
	// Current iteration data for decision phase, when solutions exist and not bands
	let decisionResult: GDMSCOREBandsFinalSelection | null = $state(null);

	// Derived state to determine which phase we're in, for conditional component rendering
	//let isDecisionPhase = $derived(phase === 'Decision Phase');
	//let isConsensusPhase = $derived(phase === 'Consensus Reaching Phase');

	// Map raw objective keys to display labels for SCORE-bands axes.
	// Prefer objective.name for readability, but keep robust fallbacks.
	let objectiveDisplayMap = $derived.by(() => {
		const map: Record<string, string> = {};
		(data.problem.objectives || []).forEach((objective: any) => {
			const displayLabel = objective.name || objective.symbol;
			if (!displayLabel) return;

			if (objective.name) {
				map[objective.name] = displayLabel;
			}
			if (objective.symbol) {
				map[objective.symbol] = displayLabel;
			}
		});
		return map;
	});

	// Data from scoreBandsResult stored in format that is actually used in UI
	let SCOREBands = $derived.by(() => {
		if (!scoreBandsResult || scoreBandsResult === null) {
			return {
				axisNames: [] as string[],
				clusterIds: [] as number[],
				axisPositions: [] as number[],
				axisSigns: [] as number[],
				data: [] as number[][],
				bands: {},
				medians: {},
				scales: undefined,
				solutions_per_cluster: {} as Record<string, number>
			};
		}

		const rawAxisNames = scoreBandsResult.ordered_dimensions;
		const displayAxisNames = rawAxisNames.map(
			(axisName) => objectiveDisplayMap[axisName] || axisName
		);

		const remapAxisKeyedObject = <T,>(
			obj: Record<string, Record<string, T>>
		): Record<string, Record<string, T>> => {
			return Object.fromEntries(
				Object.entries(obj).map(([clusterId, axisValues]) => [
					clusterId,
					Object.fromEntries(
						Object.entries(axisValues).map(([axisName, value]) => [
							objectiveDisplayMap[axisName] || axisName,
							value
						])
					)
				])
			);
		};

		const rawScales = calculateScales(data.problem, scoreBandsResult);
		const remappedScales = displayAxisNames.reduce(
			(acc, displayAxisName, index) => {
				const rawAxisName = rawAxisNames[index];
				acc[displayAxisName] =
					rawScales[rawAxisName] || rawScales[displayAxisName] || [0, 1];
				return acc;
			},
			{} as Record<string, [number, number]>
		);

		const derivedData = {
			axisNames: displayAxisNames,
			clusterIds: Object.keys(scoreBandsResult.bands)
				.sort((a, b) => parseInt(a) - parseInt(b))
				.map((id) => Number(id)),
			// Convert axis_positions dict to ordered array
			axisPositions: rawAxisNames.map(
				(objName) => scoreBandsResult?.axis_positions[objName]
			) as number[],

			// TODO: Visualization used axisSigns, but is the info from backend or user in UI? "Flip axes" -checkbox?
			axisSigns: new Array(rawAxisNames.length).fill(1),
			data: [], // TODO: This could be filled with solution data, if it will be a thing later. Visualization might not work: copy-paste from old function, not tested.
			bands: remapAxisKeyedObject(scoreBandsResult.bands),
			medians: remapAxisKeyedObject(scoreBandsResult.medians),
			scales: remappedScales,
			solutions_per_cluster: scoreBandsResult.cardinalities
		};
		return derivedData;
	});

	// Visualization options with checkboxes
	let show_bands = $state(true);
	let show_solutions = $state(false); // Disabled and hidden for now - no individual solutions
	let show_medians = $state(false); // Hide medians by default

	function setClusterVisibility(
		clusterId: number,
		visible: boolean
	) {
		cluster_visibility_map[clusterId] = visible;
	}

	function setShowBands(value: boolean) {
		if (value || canToggleBands()) {
			show_bands = value;
		}
	}

	function setShowMedians(value: boolean) {
		if (value || canToggleMedians()) {
			show_medians = value;
		}
	}

	// Helper functions to prevent deselecting all visualization options
	function canToggleBands() {
		// Can toggle bands off only if medians would remain on
		return !show_bands || show_medians || show_solutions;
	}

	function canToggleMedians() {
		// Can toggle medians off only if bands would remain on
		return !show_medians || show_bands || show_solutions;
	}

	// options for drawing score bands
	let options = $derived.by(() => {
		return {
			bands: show_bands,
			solutions: show_solutions,
			medians: show_medians
		};
	});

	// Cluster visibility controls
	let cluster_visibility_map: Record<number, boolean> = $state({});

	// Helper function to initialize all clusters as visible
	function clusters_to_visible() {
		if (SCOREBands && SCOREBands.clusterIds.length > 0) {
			SCOREBands.clusterIds.forEach((clusterId) => {
				cluster_visibility_map[clusterId] = true;
			});
		}
	}

	// Update cluster visibility when groups data changes
	$effect(() => {
		if (SCOREBands && SCOREBands.clusterIds.length > 0) {
			// Initialize all clusters as visible if not already set
			SCOREBands.clusterIds.forEach((clusterId) => {
				if (!(clusterId in cluster_visibility_map)) {
					cluster_visibility_map[clusterId] = true;
				}
			});
			// Remove clusters that no longer exist in the data
			Object.keys(cluster_visibility_map).forEach((clusterId) => {
				if (!SCOREBands.clusterIds.includes(Number(clusterId))) {
					delete cluster_visibility_map[Number(clusterId)];
				}
			});
		}
	});

	// Axis order control
	// TODO: not used now. Remove if unnecessary, use if needed
	let custom_axis_order: number[] = $state([]);
	let use_custom_order = $state(false);

	// For SCORE bands, the axisNames from the result are already in optimal order,
	// so we use the default sequential order [0, 1, 2, ...] unless custom order is specified
	let effective_axis_order = $derived.by(() => {
		const axisCount = SCOREBands.axisNames.length;
		if (use_custom_order && custom_axis_order.length === axisCount) {
			return custom_axis_order;
		}
		// Default sequential order [0, 1, 2, ...] is counted in component, no need here
		return [];
	});

	// visualization options not decided by user
	let cluster_colors = $derived(
		SCOREBands.clusterIds.length > 0 ? generate_cluster_colors(SCOREBands.clusterIds) : {}
	);

	// When a band is zoomed in the learning phase, show only that band in the plot.
	// Outside zoom mode the user's own visibility toggle map is used.
	let learningPlotVisibility = $derived.by((): Record<number, boolean> => {
		if (learningState.zoomedBand === null) return cluster_visibility_map;
		const m: Record<number, boolean> = {};
		SCOREBands.clusterIds.forEach((id) => {
			m[id] = id === learningState.zoomedBand;
		});
		return m;
	});

	let clusterBandRows = $derived.by(() => {
		if (
			!(isLearningPhase || isConsensusPhase) ||
			!SCOREBands.clusterIds.length ||
			!SCOREBands.scales ||
			!SCOREBands.bands ||
			!SCOREBands.medians
		) {
			return [];
		}

		const axisNames = SCOREBands.axisNames;

		return Object.keys(SCOREBands.bands).map((clusterId) => {
			const objectiveRanges: Record<string, any> = {};

			axisNames.forEach((axisName) => {
				const bandRange = SCOREBands.bands[clusterId]?.[axisName];
				const median = SCOREBands.medians[clusterId]?.[axisName];
				const axisScale = SCOREBands.scales?.[axisName];

				if (!bandRange || median === undefined) return;
				if (!axisScale || axisScale.length !== 2) return;

				const scaleMin = Math.min(axisScale[0], axisScale[1]);
				const scaleMax = Math.max(axisScale[0], axisScale[1]);

				objectiveRanges[axisName] = {
					min: Math.min(bandRange[0], bandRange[1]),
					max: Math.max(bandRange[0], bandRange[1]),
					median,
					scaleMin,
					scaleMax
				};
			});

			return {
				id: Number(clusterId),
				label: `Band ${clusterId}`,
				color: cluster_colors[Number(clusterId)] || '#64748b',
				numSolutions: SCOREBands.solutions_per_cluster[clusterId] ?? 0,
				objectiveRanges
			};
		});
	});

	let axis_options = $derived(
		SCOREBands.axisNames.length > 0
			? generate_axis_options(SCOREBands.axisNames, axis_agreement)
			: []
	);

	// Selection state
	let selected_band: number | null = $state(null);
	let selected_axis: number | null = $state(null); // not used, axis selection commented out
	let selected_solution: number | null = $state(null); // for decision phase

	// Selection handlers
	function selectLearningBand(clusterId: number | null) {
		learningState.selectedBand = clusterId;
	}

	function isBandVisible(clusterId: number | null): boolean {
		if (clusterId === null) return true;
		return cluster_visibility_map[clusterId] !== false;
	}

	function toggleSavedBand(clusterId: number) {
		learningState.savedBands = learningState.savedBands.includes(clusterId)
			? learningState.savedBands.filter((id) => id !== clusterId)
			: [...learningState.savedBands, clusterId];
	}

	function toggleCompareBand(clusterId: number) {
		if (learningState.comparedBands.includes(clusterId)) {
			learningState.comparedBands = learningState.comparedBands.filter((id) => id !== clusterId);
			return;
		}

		if (learningState.comparedBands.length >= 3) return;

		learningState.comparedBands = [...learningState.comparedBands, clusterId];
	}

	function zoomIntoBand(clusterId: number) {
		learningState.zoomedBand = clusterId;
		learningState.selectedBand = clusterId;
		// Automatically create sub-bands on zoom and record as first history entry
		learningState.subBands = [];
		learningState.subBandsHistory = [];
		createPersonalSubBands(3);
	}

	function exitBandZoom() {
		learningState.zoomedBand = null;
		learningState.subBands = [];
		learningState.subBandsHistory = [];
	}

	function undoSubBandChange() {
		if (learningState.subBandsHistory.length === 0) return;
		const prev = learningState.subBandsHistory[learningState.subBandsHistory.length - 1];
		learningState.subBands = prev;
		learningState.subBandsHistory = learningState.subBandsHistory.slice(0, -1);
	}

	function createPersonalSubBands(numberOfSubBands = 3) {
		if (learningState.zoomedBand === null || !scoreBandsResult) return;

		// Push current sub-bands to history before overwriting
		if (learningState.subBands.length > 0) {
			learningState.subBandsHistory = [...learningState.subBandsHistory, [...learningState.subBands]];
		}

		const visibleIndices = scoreBandsResult.clusters
			.map((clusterId, index) => ({ clusterId, index }))
			.filter((item) => item.clusterId === learningState.zoomedBand)
			.map((item) => item.index);

		const chunkSize = Math.ceil(visibleIndices.length / numberOfSubBands);
		const colors = ['#8b5cf6', '#06b6d4', '#f97316', '#22c55e'];

		learningState.subBands = Array.from({ length: numberOfSubBands }, (_, i) => ({
			id: `${learningState.zoomedBand}-${i + 1}`,
			parentClusterId: learningState.zoomedBand!,
			label: `Sub-band ${learningState.zoomedBand}.${i + 1}`,
			solutionIndices: visibleIndices.slice(i * chunkSize, (i + 1) * chunkSize),
			color: colors[i % colors.length]
		}));
	}
	function handle_band_select(clusterId: number | null) {
		if (!isBandVisible(clusterId)) {
			return;
		}
		selected_band = clusterId;
		
	}

	function handle_axis_select(axisIndex: number | null) {
		// TODO: Waiting until there is need to select an axis. Should happen if user will be able to move axes later.
		// selected_axis = axisIndex;
	}

	function handle_solution_select(index: number | null) {
		selected_solution = index;
	}

	// Check if group decision is reached
	let isGroupDecisionReached = $derived.by(() => {
		return !!(
			decisionResult?.winner_solution_objectives &&
			Object.keys(decisionResult.winner_solution_objectives).length > 0
		);
	});

	$effect(() => {
		if (learningState.selectedBand !== null && !isBandVisible(learningState.selectedBand)) {
			learningState.selectedBand = null;
		}

		if (selected_band !== null && !isBandVisible(selected_band)) {
			selected_band = null;
		}
	});

	// Get the index of the winning solution
	let winnerSolutionIndex = $derived.by(() => {
		if (
			!isGroupDecisionReached ||
			!decisionResult?.solution_objectives ||
			!decisionResult?.winner_solution_objectives
		) {
			return null;
		}

		// Find which solution matches the winner objectives
		const objectives = decisionResult.solution_objectives;
		const winnerObjectives = decisionResult.winner_solution_objectives;
		const numSolutions = Object.values(objectives)[0]?.length || 0;

		for (let i = 0; i < numSolutions; i++) {
			let matches = true;
			for (const [objName, winnerValue] of Object.entries(winnerObjectives)) {
				if (objectives[objName] && objectives[objName][i] !== winnerValue) {
					matches = false;
					break;
				}
			}
			if (matches) return i;
		}
		return 0; // fallback to first solution if no exact match found
	});

	// Transform solution data for parallel coordinates visualization in decision phase
	let decisionSolutions = $derived.by(() => {
		if (!decisionResult || !decisionResult.solution_objectives) {
			return [];
		}

		const objectives = decisionResult.solution_objectives;
		const numSolutions = Object.values(objectives)[0]?.length || 0;

		return Array.from({ length: numSolutions }, (_, index) => {
			const solution: { [key: string]: number } = {};
			Object.entries(objectives).forEach(([objectiveName, values]) => {
				solution[objectiveName] = values[index];
			});
			return solution;
		});
	});

	// Votes chart container
	let votesChartContainer: HTMLDivElement | undefined = $state();
	let waitingRefreshTimer: ReturnType<typeof setInterval> | null = null;
	let consensusVotesSyncTimer: ReturnType<typeof setInterval> | null = null;
	let isConsensusVoteSyncing = $state(false);
	let isConsensusIterationSyncing = $state(false);

	function setPhase(nextPhase: GdmPhase) {
		currentPhase = nextPhase;
		phase =
			nextPhase === 'learning'
				? 'Learning Phase'
				: nextPhase === 'consensus'
					? 'Consensus Reaching Phase'
					: 'Decision Phase';
	}

	function syncLearningMetadata(source: {
		phase?: GdmPhase;

		completed_user_ids?: Array<number | string>;
		started_at?: string | null;
		duration_seconds?: number | null;
		last_warning_at?: string | null;
		last_warning_message?: string | null;

		learning_completed_user_ids?: Array<number | string>;
		learning_started_at?: string | null;
		learning_duration_seconds?: number | null;
		learning_last_warning_at?: string | null;
		learning_last_warning_message?: string | null;
	}) {
		if (source.phase) {
			setPhase(source.phase);
		}

		const completedIds =
			source.learning_completed_user_ids?.length
				? source.learning_completed_user_ids
				: source.completed_user_ids ?? [];

		learningProgress.completedUserIds = completedIds
			.map(Number)
			.filter(Number.isFinite);

		console.log('Learning completion state:', {
			currentUserId: userId,
			completedUserIds: learningProgress.completedUserIds,
			hasCurrentUserCompleted: learningProgress.completedUserIds
				.map(String)
				.includes(String(userId))
		});

		learningProgress.startedAt =
			source.learning_started_at ??
			source.started_at ??
			null;

		learningProgress.durationSeconds =
			source.learning_duration_seconds ??
			source.duration_seconds ??
			900;

		learningProgress.lastWarningAt =
			source.learning_last_warning_at ??
			source.last_warning_at ??
			null;

		learningProgress.lastWarningMessage =
			source.learning_last_warning_message ??
			source.last_warning_message ??
			null;

		if (learningProgress.lastWarningMessage) {
			learningNotice =
				learningProgress.lastWarningMessage;
		}
	}
	function formatDuration(totalSeconds: number): string {
		const minutes = Math.floor(totalSeconds / 60);
		const seconds = totalSeconds % 60;
		return `${minutes}:${seconds.toString().padStart(2, '0')}`;
	}

	// Update votes chart when votes change
	$effect(() => {
		if (votesChartContainer) {
			drawVotesChart(votesChartContainer, votes_per_cluster, totalVoters, cluster_colors);
		}
	});

	$effect(() => {
		if (!isLearningPhase) {
			if (learningClockTimer) {
				clearInterval(learningClockTimer);
				learningClockTimer = null;
			}
			return;
		}

		if (!learningClockTimer) {
			learningNowMs = Date.now();
			learningClockTimer = setInterval(() => {
				learningNowMs = Date.now();
			}, 1000);
		}

		return () => {
			if (learningClockTimer) {
				clearInterval(learningClockTimer);
				learningClockTimer = null;
			}
		};
	});

	$effect(() => {
		const shouldSyncVotes =
			isConsensusPhase || (isDecisionPhase && !isGroupDecisionReached);

		if (!shouldSyncVotes) {
			if (consensusVotesSyncTimer) {
				clearInterval(consensusVotesSyncTimer);
				consensusVotesSyncTimer = null;
			}
			return;
		}

		if (!consensusVotesSyncTimer) {
			// Keep vote counts and "all voted" state in sync for every user
			// in active voting phases, even if websocket vote updates are missed.
			consensusVotesSyncTimer = setInterval(() => {
				if (isConsensusVoteSyncing) {
					return;
				}

				isConsensusVoteSyncing = true;
				fetch_votes_and_confirms().finally(() => {
					isConsensusVoteSyncing = false;
				});
			}, 2000);
		}

		return () => {
			if (consensusVotesSyncTimer) {
				clearInterval(consensusVotesSyncTimer);
				consensusVotesSyncTimer = null;
			}
			isConsensusVoteSyncing = false;
		};
	});

	$effect(() => {
		const shouldPollForNextIteration = isConsensusPhase;

		if (!shouldPollForNextIteration) {
			if (waitingRefreshTimer) {
				clearInterval(waitingRefreshTimer);
				waitingRefreshTimer = null;
			}
			isConsensusIterationSyncing = false;
			return;
		}

		if (!waitingRefreshTimer) {
			// Keep iteration header and phase in sync for every user during
			// consensus, even if websocket updates are delayed or missed.
			waitingRefreshTimer = setInterval(() => {
				if (isConsensusIterationSyncing) {
					return;
				}

				isConsensusIterationSyncing = true;
				fetch_score_bands().finally(() => {
					isConsensusIterationSyncing = false;
				});
			}, 3000);
		}

		return () => {
			if (waitingRefreshTimer) {
				clearInterval(waitingRefreshTimer);
				waitingRefreshTimer = null;
			}
			isConsensusIterationSyncing = false;
		};
	});

	onMount(async () => {
		// Initialize WebSocket connection
		if (data.group) {
			console.log('Initializing WebSocket for group:', data.group.id);
			wsService = wsService = new WebSocketService(
			data.groupSession.id,
			'gdm-score-bands',
			data.refreshToken,
			() => {
				// This runs when connection is re-established after disconnection
				console.log('WebSocket reconnected, refreshing gdm-score-bands state...');
				// TODO: Would be nice to have a pop up message to user: 'Reconnected to server'. At least exists in GNIMBUS.
				fetch_score_bands();
				fetch_votes_and_confirms(true);
			});

			// Subscribe to websocket messages
			wsService.messageStore.subscribe((store) => {
				// Handle different message types from the backend:
				const msg =
					typeof store.message === 'string'
						? store.message
						: JSON.stringify(store.message);
				console.log('WebSocket message received:', msg);

				// Handle update messages (messages don't show to user, just trigger state updates)
				if (msg.includes('UPDATE: A vote has been cast.')) {
					fetch_votes_and_confirms();
					return;
				} else if (msg.includes('NOTICE:')) {
					learningNotice = msg.replace(/NOTICE:\s*/gi, '');
					fetch_votes_and_confirms();
					return;
				} else if (msg.includes('UPDATE')) {
					fetch_score_bands();
					fetch_votes_and_confirms(true);
					clusters_to_visible();
					return;
				}

				// Handle error messages (show error message)
				if (msg.includes('ERROR')) {
					const errMsg = msg.replace(/ERROR: /gi, '');
					errorMessage.set(`${errMsg}`);
					return;
				}
			});
		}

		await fetch_score_bands();
		await fetch_votes_and_confirms(true);

		clusters_to_visible();
	});

	// Cleanup websocket connection when component is destroyed
	onDestroy(() => {
		if (consensusVotesSyncTimer) {
			clearInterval(consensusVotesSyncTimer);
			consensusVotesSyncTimer = null;
		}
		isConsensusVoteSyncing = false;

		if (waitingRefreshTimer) {
			clearInterval(waitingRefreshTimer);
			waitingRefreshTimer = null;
		}
		isConsensusIterationSyncing = false;

		if (learningClockTimer) {
			clearInterval(learningClockTimer);
			learningClockTimer = null;
		}

		if (wsService) {
			console.log('Closing WebSocket connection');
			wsService.close();
			wsService = null;
		}
	});

	/**
	 * Fetches current SCORE bands data and history from backend
	 */
	async function fetch_score_bands() {
		try {
			const previousIterationId = groupIterationId;
			const previousPhase = phase;

			const scoreResult = await callGSCOREBandsAPI<{ history: ScoreBandsHistoryItem[] }>(
				'fetch_score_bands',
				{
					group_session_id: data.groupSession.id,
					score_bands_config: scoreBandsConfig,
					minimum_votes: minimumVotes,
					from_iteration: latestIteration
				}
			);

			if (!scoreResult.success) {
				throw new Error(
					`Fetch score failed: ${scoreResult.error ?? 'Unknown error'}`
				);
			}

			history = scoreResult.data?.history ?? [];
			console.log('Raw fetch_score_bands response:', scoreResult);

			console.log('Full history received:', history);

			if (!Array.isArray(history) || history.length === 0) {
				throw new Error('SCORE Bands response contained no history entries.');
			}

			const currentResponse = history.at(-1);

			if (!currentResponse) {
				throw new Error('Could not determine the current SCORE Bands response.');
			}

			if (
				currentResponse.phase === 'learning' ||
				currentResponse.phase === 'consensus'
			) {
				const scoreBandsResponse =
					currentResponse as GDMSCOREBandsResponse & {
						phase: 'learning' | 'consensus';
					};

				latestIteration =
					scoreBandsResponse.latest_iteration ?? null;

				const scoreBandsData =
					scoreBandsResponse.result as SCOREBandsResult;

				scoreBandsResult = scoreBandsData;
				scoreBandsConfig = scoreBandsData.options;
				groupIterationId = scoreBandsResponse.group_iter_id;

				setPhase(scoreBandsResponse.phase);
				decisionResult = null;

				console.log(
					'SCORE bands fetched successfully:',
					scoreBandsResponse
				);
			} else if (currentResponse.phase === 'decision') {
				const finalDecisionData =
					currentResponse.result as GDMSCOREBandsFinalSelection;

				latestIteration = null;
				decisionResult = finalDecisionData;
				groupIterationId = currentResponse.group_iter_id;

				setPhase('decision');
				scoreBandsResult = null;

				console.log(
					'Decision phase data fetched successfully:',
					currentResponse
				);
			} else {
				throw new Error(
					`Unknown SCORE Bands phase: ${currentResponse.phase}`
				);
			}

			const iterationChanged =
				groupIterationId !== previousIterationId;

			const phaseChanged =
				phase !== previousPhase;

			if (iterationChanged || phaseChanged) {
				selected_band = null;
				selected_solution = null;
			}

			data_loaded = true;
			loading_error = null;
		} catch (error) {
			console.error('Error in fetch_score_bands:', error);
			errorMessage.set(`${error}`);
		}
	}
	/**
	 * Submits user vote for selected band or solution
	 */
	async function vote(selection: number | null) {
		if (selection === null) {
			errorMessage.set('Please select a band or solution to vote for.');
			return;
		}
		console.log('Selection to vote for:', selection);
		try {
			const voteResult = await callGSCOREBandsAPI<{ message: string }>('vote', {
				group_session_id: data.groupSession.id,
				vote: selection
			});

			if (voteResult.success) {
				console.log('Voted successfully:', voteResult.data?.message);
				// Refresh local voting state immediately so vote counters update without
				// waiting for a websocket update event.
				await fetch_votes_and_confirms();
			} else {
				throw new Error(`Vote failed: ${voteResult.error || 'Unknown error'}`);
			}
		} catch (error) {
			console.error('Error in vote:', error);
			errorMessage.set(`${error}`);
		}
	}

	/**
	 * Confirms user's current vote to proceed to next phase
	 */
	async function confirm_vote() {
		if (vote_confirmed) {
			return;
		}
		try {
			const confirmResult = await callGSCOREBandsAPI<{ message: string }>('confirm_vote', {
				group_session_id: data.groupSession.id
			});

			if (confirmResult.success) {
				console.log('Confirmed vote successfully:', confirmResult.data?.message);
			} else {
				throw new Error(`Confirm failed: ${confirmResult.error || 'Unknown error'}`);
			}
			// Refresh both vote status and iteration state locally so the UI updates
			// immediately even if websocket update delivery is delayed.
			await fetch_votes_and_confirms();
			await fetch_score_bands();
			clusters_to_visible();
		} catch (error) {
			console.error('Error in Confirm:', error);
			errorMessage.set(`${error}`);
		}
	}

	/**
	 * Fetches voting status and confirmations for all group members
	 */
	async function fetch_votes_and_confirms(selectVotedBand = false) {
		try {
			const result = await callGSCOREBandsAPI<typeof votes_and_confirms>(
				'get_votes_and_confirms',
				{
					group_session_id: data.groupSession.id
				}
			);

			if (result.success && result.data) {
				votes_and_confirms = result.data;
				syncLearningMetadata(result.data);
				// If user has voted already, select the band they voted for
				// selectVotedBand parameter controls whether to update selected_band: updates happen in different situations, some should not change selected_band
				if (userId != null && selectVotedBand) {
					const userKey = String(userId);

					if (
						Object.prototype.hasOwnProperty.call(
							votes_and_confirms.votes,
							userKey
						)
					) {
						selected_band = votes_and_confirms.votes[userKey];
					}
				}
			} else {
				throw new Error(`Get votes and confirms failed: ${result.error || 'Unknown error'}`);
			}
		} catch (error) {
			console.error('Error in get_votes_and_confirms:', error);
			errorMessage.set(`${error}`);
		}
	}

	async function complete_learning_phase() {
		if (hasCompletedLearning || isMarkingLearningComplete) {
			return;
		}

		isMarkingLearningComplete = true;
		try {
			const result = await callGSCOREBandsAPI<typeof votes_and_confirms>(
				'learning/complete',
				{
					group_session_id: data.groupSession.id
				}
			);

			if (!result.success) {
				throw new Error(`Finish exploring failed: ${result.error || 'Unknown error'}`);
			}

			if (result.data) {
				syncLearningMetadata(result.data);
			}
			// Fetch the authoritative shared status.
			// hasCompletedLearning will still be calculated for this specific user.
			await fetch_votes_and_confirms();
		} catch (error) {
			console.error('Error in complete_learning_phase:', error);
			errorMessage.set(`${error}`);
		} finally {
			isMarkingLearningComplete = false;
		}
	}

	async function warn_learning_time() {
		if (isWarningUsers) {
			return;
		}

		isWarningUsers = true;
		try {
			const result = await callGSCOREBandsAPI<typeof votes_and_confirms>(
				'learning/warn',
				{
					group_session_id: data.groupSession.id,
					message: ownerWarningMessage.trim() || undefined
				}
			);

			if (!result.success) {
				throw new Error(`Warn users failed: ${result.error || 'Unknown error'}`);
			}

			if (result.data) {
				syncLearningMetadata(result.data);
			}
			ownerWarningMessage = '';
		} catch (error) {
			console.error('Error in warn_learning_time:', error);
			errorMessage.set(`${error}`);
		} finally {
			isWarningUsers = false;
		}
	}

	async function advance_to_consensus() {
		if (isAdvancingToConsensus) {
			return;
		}

		isAdvancingToConsensus = true;
		try {
			const result = await callGSCOREBandsAPI<typeof votes_and_confirms>(
				'learning/advance',
				{
					group_session_id: data.groupSession.id
				}
			);

			if (!result.success) {
				throw new Error(`Start consensus failed: ${result.error || 'Unknown error'}`);
			}

			if (result.data) {
				syncLearningMetadata(result.data);
			}
			await fetch_score_bands();
			await fetch_votes_and_confirms(true);
			clusters_to_visible();
		} catch (error) {
			console.error('Error in advance_to_consensus:', error);
			errorMessage.set(`${error}`);
		} finally {
			isAdvancingToConsensus = false;
		}
	}

	/**
	 * Reverts group to specified iteration (owner only)
	 */
	async function revert_to(iteration: number) {
		try {
			const result = await callGSCOREBandsAPI<{ message: string }>('revert', {
				group_session_id: data.groupSession.id,
				group_iteration_id: iteration
			});

			if (result.success) {
				console.log('Reverted to previous iteration successfully:', result.data?.message);
				// Refresh score bands and votes after reverting
				await fetch_score_bands();
				await fetch_votes_and_confirms();
				clusters_to_visible();
			} else {
				throw new Error(`Revert iteration failed: ${result.error || 'Unknown error'}`);
			}
		} catch (error) {
			console.error('Error in revert_iteration:', error);
			errorMessage.set(`${error}`);
		}
	}

	/**
	 * Updates SCORE bands configuration and recalculates bands (owner only)
	 */
	async function configure(config: SCOREBandsGDMConfig) {
		try {
			const configureResult = await callGSCOREBandsAPI('configure', {
				// Group ID for which to apply the configuration
				group_session_id: data.groupSession.id,
				// Configuration object with all SCORE bands settings
				config: config
			});

			if (configureResult.success) {
				minimumVotes = config.minimum_votes;
				await fetch_score_bands();
				await fetch_votes_and_confirms(true);
				clusters_to_visible();
			} else {
				throw new Error(`Configure failed: ${configureResult.error || 'Unknown error'}`);
			}
		} catch (error) {
			console.error('Error in configure:', error);
			errorMessage.set(`${error}`);
		}
	}

	async function restartScoreBands() {
		try {
			const restartResult = await callGSCOREBandsAPI('restart', {
				group_session_id: data.groupSession.id
			});

			if (restartResult.success) {
				await fetch_score_bands();
				await fetch_votes_and_confirms(true);
				clusters_to_visible();
			} else {
				throw new Error(`Restart failed: ${restartResult.error || 'Unknown error'}`);
			}
		} catch (error) {
			console.error('Error in restartScoreBands:', error);
			errorMessage.set(`${error}`);
		}
	}
</script>

<svelte:head>
	<title>GDM-SCORE-bands | DESDEO</title>
	<meta name="description" content="Group decision making interface using Score-band method" />
</svelte:head>

<div class="container mx-auto p-6">
	{#if $errorMessage}
		<Alert title="Error" message={$errorMessage} variant="destructive" />
	{/if}

	{#if !data_loaded}
		<div class="flex h-96 items-center justify-center">
			<div class="text-center">
				<div class="loading loading-spinner loading-lg"></div>
				<p class="mt-4">Loading data...</p>
				{#if loading_error}
					<p class="text-error mt-2">Error: {loading_error}</p>
				{/if}
			</div>
		</div>
	{:else}
		{#if isLearningPhase && learningNotice}
			<div class="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
				{learningNotice}
			</div>
		{/if}
		<!-- Header and Instructions -->
		<div>
			<div class="mb-4 rounded-xl border border-blue-200 bg-blue-50 p-5">
				<div class="flex gap-4">
					<div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-blue-100">
						<Users class="h-6 w-6 text-blue-600" />
					</div>
					<div class="flex-1">
						<h2 class="text-md font-semibold text-slate-900">
							{phase === 'Learning Phase'
								? 'Learning Phase'
								: phase === 'Consensus Reaching Phase'
								? `Consensus Reaching Phase (Iteration ${latestIteration})`
								: phase === 'Decision Phase'
								? 'Decision Phase'
								: ''}
						</h2>
					<!-- Header Section -->
					{#if isDecisionMaker}
						<!-- Instructions Section -->
						{#if isLearningPhase}
							<p class="mt-2 text-sm text-slate-600">
								Explore the SCORE bands privately. Your saved bands, comparisons, and zoomed
								views do not affect the rest of the group. Mark yourself finished when you are
								done exploring.
							</p>
						{:else if isConsensusPhase && usersVote === null}


										<p class="mt-2 text-sm text-slate-600">
											Select one band that best matches your preferred objective ranges, then click
											Vote. Your vote helps the group narrow the solution space toward a shared
											region of interest. You can change your selection and vote again until you
											confirm your vote.
										</p>

						{:else if isDecisionPhase && usersVote === null && !isGroupDecisionReached}
							<div>Select the best solution from the solutions shown below and vote for it.</div>
						{/if}
						{#if isDecisionPhase && isGroupDecisionReached}
							<div>
								The group decision process is complete! The final solution selected is Solution {winnerSolutionIndex !==
								null
									? winnerSolutionIndex + 1
									: 'N/A'}.
							</div>
						{:else}
							{#if usersVote !== null && !have_all_voted}
								<div>
									You have voted for {isConsensusPhase ? 'band' : 'solution'}
									{isConsensusPhase ? usersVote : usersVote + 1}. You can still change your vote. To
									confirm your vote, please wait for other users to vote.
								</div>
							{/if}
							{#if usersVote !== null && have_all_voted && !vote_confirmed}
								<div>
									You have voted for {isConsensusPhase ? 'band' : 'solution'}
									{isConsensusPhase ? usersVote : usersVote + 1}. You can still change your vote, or
									confirm your vote to proceed.
								</div>
							{/if}
							{#if usersVote !== null && vote_confirmed}
								<div>
									You have confirmed your vote for {isConsensusPhase ? 'band' : 'solution'}
									{isConsensusPhase ? usersVote : usersVote + 1}. Please wait for other users to
									confirm their votes.
								</div>
							{/if}
						{/if}
					{/if}
					{#if isOwner}
						<div class="mt-2 text-sm text-gray-600">
							{isLearningPhase
								? 'You can monitor who has finished exploring, warn users before the timer expires, and manually start the consensus phase once everyone is ready.'
								: 'You can revert to a previous iteration using the History Browser.'}
							{isConsensusPhase
								? 'You can also adjust the SCORE Bands parameters and recalculate the bands below.'
								: ''}
						</div>
					{/if}
					</div>
					
				</div>
			</div>
		</div>

		{#if isLearningPhase}
	<div class="grid grid-cols-1 gap-4 xl:grid-cols-[280px_minmax(0,1fr)_340px]">
		<ScoreBandsLeftSidebar
			phase="learning"
			{isOwner}
			{isDecisionMaker}
			problemName={data.problem.name ?? 'Current problem'}
			{learningTimeLabel}
			clusterIds={SCOREBands.clusterIds}
			clusterColors={cluster_colors}
			clusterVisibilityMap={cluster_visibility_map}
			onVisibilityChange={setClusterVisibility}
			showBands={show_bands}
			showMedians={show_medians}
			canToggleBands={canToggleBands()}
			canToggleMedians={canToggleMedians()}
			onShowBandsChange={setShowBands}
			onShowMediansChange={setShowMedians}
			currentConfig={scoreBandsResult?.options ?? null}
			{latestIteration}
			{totalVoters}
			onRecalculate={configure}
			{history}
			currentIterationId={groupIterationId}
			onRevertToIteration={revert_to}
		/>

		<main class="space-y-4">
			<div class="rounded-lg border bg-card shadow-sm">
				<div class="flex items-center justify-between border-b px-4 py-3">
					<div>
						{#if learningState.zoomedBand !== null}
							<h2 class="text-sm font-semibold">
								Band {learningState.zoomedBand} — zoomed view
							</h2>
							<p class="mt-1 text-xs text-muted-foreground">
								Showing only this band. Sub-bands are listed on the right.
							</p>
						{:else}
							<h2 class="text-sm font-semibold">Explore the solution space</h2>
							<p class="mt-1 text-xs text-muted-foreground">
								Your exploration is private and does not affect the group.
							</p>
						{/if}
					</div>
					{#if learningState.zoomedBand !== null}
						<div class="flex gap-2">
							<button
								type="button"
								class="rounded-md border px-3 py-1.5 text-xs hover:bg-muted disabled:opacity-50"
								onclick={undoSubBandChange}
								disabled={learningState.subBandsHistory.length === 0}
							>
								Undo
							</button>
							<button
								type="button"
								class="rounded-md border px-3 py-1.5 text-xs hover:bg-muted"
								onclick={exitBandZoom}
							>
								← Back to all bands
							</button>
						</div>
					{/if}
				</div>

				<div class="h-[520px] p-4">
					<ScoreBands
						data={SCOREBands.data}
						axisNames={SCOREBands.axisNames}
						axisPositions={SCOREBands.axisPositions}
						axisSigns={SCOREBands.axisSigns}
						groups={SCOREBands.clusterIds}
						{options}
						bands={SCOREBands.bands}
						medians={SCOREBands.medians}
						scales={SCOREBands.scales}
						clusterVisibility={learningPlotVisibility}
						clusterColors={cluster_colors}
						axisOptions={axis_options}
						axisOrder={effective_axis_order}
						onBandSelect={selectLearningBand}
						onAxisSelect={handle_axis_select}
						selectedBand={learningState.selectedBand}
						selectedAxis={selected_axis}
					/>
				</div>
			</div>

			<ClusterBandTable
				axisNames={SCOREBands.axisNames}
				bands={clusterBandRows}
				selectedBand={learningState.selectedBand}
				onBandSelect={selectLearningBand}
			/>
		</main>

		<ScoreBandsRightSidebar
			phase="learning"
			{isOwner}
			{isDecisionMaker}
			learning={{
				totalVoters,
				learningCompletedCount,
				hasCompletedLearning,
				allDecisionMakersFinishedLearning,
				isMarkingLearningComplete,
				isWarningUsers,
				isAdvancingToConsensus,
				ownerWarningMessage,
				selectedLearningBand: learningState.selectedBand,
				zoomedBand: learningState.zoomedBand,
				savedBands: learningState.savedBands,
				subBands: learningState.subBands,
				subBandsHistoryLength:
					learningState.subBandsHistory.length,
				solutionsPerCluster:
					SCOREBands.solutions_per_cluster,
				onOwnerWarningMessageChange:
					setOwnerWarningMessage,
				onFinishExploring:
					complete_learning_phase,
				onSaveBand: toggleSavedBand,
				onZoomIntoBand: zoomIntoBand,
				onRemoveSavedBand: toggleSavedBand,
				onRecreateSubBands: () =>
					createPersonalSubBands(3),
				onUndoSubBandChange:
					undoSubBandChange,
				onExitBandZoom: exitBandZoom,
				onWarnUsers: warn_learning_time,
				onAdvanceToConsensus:
					advance_to_consensus
			}}
		/>
	</div>
		{:else if isConsensusPhase}
	<div class="grid grid-cols-1 gap-4 xl:grid-cols-[300px_minmax(0,1fr)_360px]">
		<!-- LEFT: Data & Settings -->
		<ScoreBandsLeftSidebar
			phase="consensus"
			{isOwner}
			{isDecisionMaker}
			problemName={data.problem.name ?? 'Current problem'}
			clusterIds={SCOREBands.clusterIds}
			clusterColors={cluster_colors}
			clusterVisibilityMap={cluster_visibility_map}
			onVisibilityChange={setClusterVisibility}
			showBands={show_bands}
			showMedians={show_medians}
			canToggleBands={canToggleBands()}
			canToggleMedians={canToggleMedians()}
			onShowBandsChange={setShowBands}
			onShowMediansChange={setShowMedians}
			currentConfig={scoreBandsResult?.options ?? null}
			{latestIteration}
			{totalVoters}
			onRecalculate={configure}
			{history}
			currentIterationId={groupIterationId}
			onRevertToIteration={revert_to}
		/>

		<!-- CENTER: Visualization + band table -->
		<main class="space-y-4">
			<div class="rounded-lg border bg-card shadow-sm">
				<div class="flex items-center justify-between border-b px-4 py-3">
					<div>
						<h2 class="text-sm font-semibold">Visualization</h2>
						<p class="mt-1 text-xs text-muted-foreground">
							Select a band in the chart or in the table below.
						</p>
					</div>
				</div>

				<div class="h-[520px] p-4">
					<ScoreBands
						data={SCOREBands.data}
						axisNames={SCOREBands.axisNames}
						axisPositions={SCOREBands.axisPositions}
						axisSigns={SCOREBands.axisSigns}
						groups={SCOREBands.clusterIds}
						{options}
						bands={SCOREBands.bands}
						medians={SCOREBands.medians}
						scales={SCOREBands.scales}
						clusterVisibility={cluster_visibility_map}
						clusterColors={cluster_colors}
						axisOptions={axis_options}
						axisOrder={effective_axis_order}
						onBandSelect={handle_band_select}
						onAxisSelect={handle_axis_select}
						selectedBand={selected_band}
						selectedAxis={selected_axis}
					/>
				</div>

				<div class="border-t px-4 py-3 text-sm text-muted-foreground">
					Bands show the regions of the Pareto front still available after the previous
					iteration.
				</div>
			</div>

			<ClusterBandTable
				axisNames={SCOREBands.axisNames}
				bands={clusterBandRows}
				selectedBand={selected_band}
				onBandSelect={handle_band_select}
			/>
		</main>

		<!-- RIGHT: Voting + consensus -->
		<ScoreBandsRightSidebar
			phase="consensus"
			{isOwner}
			{isDecisionMaker}
			consensus={{
				totalVoters,
				clusterIds: SCOREBands.clusterIds,
				clusterColors: cluster_colors,
				selectedBand: selected_band,
				voteConfirmed: vote_confirmed,
				haveAllVoted: have_all_voted,
				isConsensusVoteSyncing,
				axisNames: SCOREBands.axisNames,
				axisAgreement: axis_agreement,
				getClusterVoteCount,
				getClusterVotePercent,
				getConsensusLabel,
				getConsensusClasses,
				onBandSelect: handle_band_select,
				onVote: voteForSelectedBand,
				onConfirmVote: confirm_vote
			}}
		/>
	</div>
		{:else if isDecisionPhase}
			<!-- DECISION PHASE: Solution Selection Content -->
			<div class="grid grid-cols-1 gap-6 lg:grid-cols-4">
				<!-- Decision Controls -->
				<div class="lg:col-span-1">
					{#if isDecisionMaker}
						<!-- Voting -->
						<div class="card bg-base-100 shadow-xl">
							<div class="card-body">
								<h2 class="card-title">
									{isGroupDecisionReached ? 'Final Solution' : 'Solution Voting'}
								</h2>
								<div class="space-y-2 p-2">
									{#if !isGroupDecisionReached}
										<Button
											onclick={() => vote(selected_solution)}
											disabled={selected_solution === null || vote_confirmed}
										>
											Vote for Selected Solution
										</Button>
										<Button onclick={confirm_vote} disabled={!have_all_voted || vote_confirmed}>
											Confirm Final Decision
										</Button>
										{#if vote_confirmed}
											<div class="alert alert-info">
												<span>Decision Confirmed!</span>
											</div>
										{/if}
									{:else}
										<div class="alert alert-success">
											<span>Group decision reached!</span>
											<div class="mt-2 text-sm">
												Final solution: Solution {winnerSolutionIndex !== null
													? winnerSolutionIndex + 1
													: 'N/A'}
											</div>
										</div>
									{/if}
								</div>
							</div>
						</div>
					{:else if isOwner}
						<!-- Voting status for owner -->
						<div class="card bg-base-100 shadow-xl">
							<div class="card-body">
								<h2 class="card-title">
									{isGroupDecisionReached ? 'Final Solution' : 'Solution Voting'}
								</h2>
								<div class="space-y-2 p-2">
									{#if !isGroupDecisionReached}
										<div>Voting still ongoing or decision not found with these votes.</div>
									{:else}
										<div class="alert alert-success">
											<span>Group decision reached!</span>
											<div class="mt-2 text-sm">
												Final solution: Solution {winnerSolutionIndex !== null
													? winnerSolutionIndex + 1
													: 'N/A'}
											</div>
										</div>
									{/if}
								</div>
							</div>
						</div>
					{/if}

					<!-- History Browser Component -->
					<HistoryBrowser
						{history}
						currentIterationId={groupIterationId}
						onRevertToIteration={revert_to}
						{isOwner}
					/>
				</div>
				<!-- Visualization Area -->
				<div class="lg:col-span-3">
					<div class="card bg-base-100 shadow-xl">
						<div class="card-body">
							{#if decisionResult && decisionSolutions.length > 0}
								<div class="flex h-[600px] w-full items-center justify-center">
									<!-- Parallel Coordinates Component -->
									<ParallelCoordinates
										data={decisionSolutions}
										dimensions={createObjectiveDimensions(data.problem)}
										selectedIndex={selected_solution}
										onLineSelect={handle_solution_select}
										referenceData={{
											preferredSolutions:
												usersVote !== null
													? [
															{
																values: decisionSolutions[usersVote],
																label: `Your Vote: Solution ${usersVote + 1}`
															}
														]
													: []
										}}
									/>
								</div>
								<h2 class="card-title mb-4">Numerical values</h2>
								<ScoreBandsSolutionTable
									problem={data.problem}
									solutions={decisionSolutions}
									selectedSolution={selected_solution}
									onSolutionSelect={handle_solution_select}
									userVotedSolution={usersVote}
									groupVotes={votes_and_confirms.votes || {}}
								/>
							{:else}
								<div class="text-center">
									<h2 class="mb-4 text-2xl font-bold">Decision Phase</h2>
									<p class="mb-4 text-gray-600">Loading solutions...</p>
								</div>
							{/if}
						</div>
					</div>
				</div>
			</div>
		{:else}
			<!-- FALLBACK: Unknown phase -->
			<div class="alert alert-error">
				<span>Unknown phase: {phase}</span>
			</div>
		{/if}
	{/if}
</div>

<style>
	:global(.container) {
		max-width: 100%;
	}
</style>
