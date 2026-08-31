<script lang="ts">
	import { Button } from '$lib/components/ui/button';

	type Phase = 'learning' | 'consensus';

	type LearningSidebarContext = {
		totalVoters: number;
		learningCompletedCount: number;
		hasCompletedLearning: boolean;
		allDecisionMakersFinishedLearning: boolean;

		isMarkingLearningComplete: boolean;
		isWarningUsers: boolean;
		isAdvancingToConsensus: boolean;

		ownerWarningMessage: string;
		onOwnerWarningMessageChange: (value: string) => void;

		selectedLearningBand: number | null;
		savedBands: number[];

		solutionsPerCluster: Record<string, number>;

		onFinishExploring: () => void | Promise<void>;
		onSaveBand: (clusterId: number) => void;
		onRemoveSavedBand: (clusterId: number) => void;
		onWarnUsers: () => void | Promise<void>;
		onAdvanceToConsensus: () => void | Promise<void>;

		isExploringBand: boolean;
		explorationDepth: number;

		onExploreBand:
			(clusterId: number) =>
				void | Promise<void>;

		onBackOneLevel:
			() => void;

		onExitExploration:
			() => void;
	};

	type ConsensusSidebarContext = {
		totalVoters: number;
		clusterIds: number[];
		clusterColors: Record<number, string>;

		selectedBand: number | null;
		voteConfirmed: boolean;
		haveAllVoted: boolean;
		isConsensusVoteSyncing: boolean;

		getClusterVoteCount: (clusterId: number) => number;
		getClusterVotePercent: (clusterId: number) => number;

		onBandSelect: (clusterId: number) => void;
		onVote: () => void | Promise<void>;
		onConfirmVote: () => void | Promise<void>;

		axisNames: string[];
		getConsensusLabel: (axisName: string) => string;
		getConsensusClasses: (axisName: string) => string;
		axisAgreement: Record<string, string>;
	};

	type Props = {
		phase: Phase;
		isOwner: boolean;
		isDecisionMaker: boolean;
		learning?: LearningSidebarContext;
		consensus?: ConsensusSidebarContext;
	};

	let {
		phase,
		isOwner,
		isDecisionMaker,
		learning,
		consensus
	}: Props = $props();

	function handleWarningInput(event: Event) {
		if (!learning) return;

		const target = event.currentTarget as HTMLInputElement;
		learning.onOwnerWarningMessageChange(target.value);
	}
</script>

<aside class="space-y-4">
	{#if phase === 'learning' && learning}
		<section class="rounded-lg border bg-card shadow-sm">
			<header class="border-b px-4 py-3">
				<h2 class="text-sm font-semibold">My exploration</h2>

				{#if isDecisionMaker}
					<p class="mt-1 text-xs text-muted-foreground">Visible only to you.</p>
				{/if}
			</header>

			<div class="space-y-3 p-4">
				<div class="rounded-md border p-3 text-sm">
					<div class="font-medium">Learning progress</div>
					<div class="text-muted-foreground">
						{learning.learningCompletedCount} / {learning.totalVoters} decision makers finished
					</div>
				</div>



			    {#if learning.explorationDepth > 0}
	<div
		class="
			rounded-md border border-violet-200
			bg-violet-50 p-3 text-sm
		"
	>
		<div
			class="
				font-medium text-violet-900
			"
		>
			Private exploration
		</div>

		<div class="text-muted-foreground">
			<span class="font-medium">Selected band: </span><span>{learning.selectedLearningBand}</span>
			<br />
			<span class="font-medium">Depth: </span><span>{learning.explorationDepth}</span>
		</div>
	</div>
{/if}

{#if learning.selectedLearningBand !== null}
	{#if isDecisionMaker}
<!-- 		<Button
			class="w-full"
			onclick={() =>
				learning.onSaveBand(
					learning
						.selectedLearningBand!
				)}
		>
			{learning.savedBands.includes(
				learning.selectedLearningBand
			)
				? 'Remove saved band'
				: 'Save band'}
		</Button> -->

		<Button
			class="w-full"
			onclick={() =>
				learning.onExploreBand(
					learning
						.selectedLearningBand!
				)}
			disabled={
				learning.isExploringBand
			}
		>
			{learning.isExploringBand
				? 'Generating bands...'
				: 'Explore inside band'}
		</Button>
	{/if}
{:else}
	<p
		class="
			text-sm text-muted-foreground
		"
	>
		Select a band to inspect or
		explore it.
	</p>
{/if}

{#if learning.explorationDepth > 0}
	<div class="flex gap-2">
		<Button
			class="flex-1"
			variant="outline"
			size="sm"
			onclick={
				learning.onBackOneLevel
			}
		>
			← Back
		</Button>

		<Button
			class="flex-1"
			variant="outline"
			size="sm"
			onclick={
				learning.onExitExploration
			}
		>
			All bands
		</Button>
		
	</div>
	<div>
							<Button
						class="w-full"
						variant={learning.hasCompletedLearning ? 'outline' : 'default'}
						onclick={learning.onFinishExploring}
						disabled={learning.hasCompletedLearning || learning.isMarkingLearningComplete}
					>
						{#if learning.isMarkingLearningComplete}
							Finishing...
						{:else if learning.hasCompletedLearning}
							Exploration finished
						{:else}
							Finish exploring
						{/if}
					</Button>
	</div>
{/if}
			</div>
		</section>

		{#if isDecisionMaker && learning.savedBands.length > 0}
			<section class="rounded-lg border bg-card shadow-sm">
				<header class="border-b px-4 py-3">
					<h2 class="text-sm font-semibold">Saved bands</h2>
				</header>

				<div class="space-y-2 p-4">
					{#each learning.savedBands as clusterId}
						<div class="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
							<span>Cluster {clusterId}</span>
							<button
								type="button"
								class="text-muted-foreground hover:text-foreground"
								onclick={() => learning.onRemoveSavedBand(clusterId)}
							>
								Remove
							</button>
						</div>
					{/each}
				</div>
			</section>
		{/if}

		<section class="rounded-lg border bg-card shadow-sm">
			<header class="border-b px-4 py-3">
				<h2 class="text-sm font-semibold">What’s next?</h2>
			</header>

			<div class="space-y-3 p-4 text-sm text-muted-foreground">
				<p>Once the group is ready, the process moves to the consensus phase.</p>

				{#if isOwner}
					<div class="rounded-md border p-3 text-sm">
						<div class="font-medium text-foreground">Group readiness</div>
						<div class="text-muted-foreground">
							{learning.learningCompletedCount} / {learning.totalVoters} finished exploring
						</div>
					</div>

					<input
						type="text"
						value={learning.ownerWarningMessage}
						placeholder="Optional warning message"
						class="input input-bordered w-full"
						oninput={handleWarningInput}
					/>

					<Button
						class="w-full"
						variant="outline"
						onclick={learning.onWarnUsers}
						disabled={learning.isWarningUsers}
					>
						{learning.isWarningUsers
							? 'Sending warning...'
							: 'Warn users time is expiring'}
					</Button>

					<Button
						class="w-full"
						onclick={learning.onAdvanceToConsensus}
						disabled={
							!learning.allDecisionMakersFinishedLearning ||
							learning.isAdvancingToConsensus
						}
					>
						{learning.isAdvancingToConsensus
							? 'Starting consensus...'
							: 'Continue to consensus phase'}
					</Button>
				{/if}
			</div>
		</section>
	{:else if phase === 'consensus' && consensus}
		<section class="rounded-lg border bg-card shadow-sm">
			<header class="border-b px-4 py-3">
				<h2 class="text-sm font-semibold">Group voting</h2>
				<p class="mt-1 text-xs text-muted-foreground">
					{consensus.totalVoters} decision makers
				</p>
				<p class="mt-1 text-xs text-muted-foreground">
					Vote sync: {consensus.isConsensusVoteSyncing ? 'updating...' : 'live'}
				</p>
			</header>

			<div class="space-y-2 p-4">
				<div class="text-sm font-medium">Select your preferred band</div>

				{#each consensus.clusterIds as clusterId}
					<button
						type="button"
						class="flex w-full items-center justify-between rounded-md border px-3 py-3 text-left text-sm hover:bg-muted {consensus.selectedBand === clusterId ? 'border-primary bg-muted' : ''}"
						onclick={() => consensus.onBandSelect(clusterId)}
						disabled={consensus.voteConfirmed || !isDecisionMaker}
					>
						<span class="flex items-center gap-2">
							<span
								class="h-3 w-3 rounded-full"
								style:background-color={consensus.clusterColors[clusterId] ?? '#64748b'}
							></span>
							Cluster {clusterId}
						</span>

						<span class="text-muted-foreground">
							{consensus.getClusterVoteCount(clusterId)} / {consensus.totalVoters}
							({consensus.getClusterVotePercent(clusterId)}%)
						</span>
					</button>
				{/each}

				{#if isDecisionMaker}
					<div class="pt-4">
						<Button
							class="w-full"
							onclick={consensus.onVote}
							disabled={consensus.selectedBand === null || consensus.voteConfirmed}
						>
							Vote
						</Button>

						<Button
							class="mt-2 w-full"
							variant="outline"
							onclick={consensus.onConfirmVote}
							disabled={!consensus.haveAllVoted || consensus.voteConfirmed}
						>
							Confirm vote
						</Button>
					</div>
				{:else if isOwner}
					<p class="pt-3 text-sm text-muted-foreground">
						You can monitor the voting progress.
					</p>
				{/if}
			</div>
		</section>

		<section class="rounded-lg border bg-card shadow-sm">
			<header class="flex items-center justify-between border-b px-4 py-3">
				<h2 class="text-sm font-semibold">Consensus status</h2>
				<span class="text-xs text-muted-foreground">Updates after all votes</span>
			</header>

			<div class="divide-y">
				{#each consensus.axisNames as axisName}
					<div class="flex items-center justify-between px-4 py-3">
						<div>
							<div class="font-medium">{axisName}</div>
							<div class={`text-sm ${consensus.getConsensusClasses(axisName)}`}>
								{consensus.getConsensusLabel(axisName)}
							</div>
						</div>

						<div
							class="h-2 w-24 rounded-full bg-muted"
							title={consensus.getConsensusLabel(axisName)}
						>
							<div
								class="h-2 rounded-full {consensus.axisAgreement[axisName] === 'agreement'
									? 'bg-green-600'
									: consensus.axisAgreement[axisName] === 'disagreement'
										? 'bg-red-600'
										: 'bg-muted-foreground/40'}"
								style:width={consensus.axisAgreement[axisName] === 'neutral' ? '40%' : '80%'}
							></div>
						</div>
					</div>
				{/each}
			</div>
		</section>
	{:else}
		<div class="rounded-lg border bg-card p-4 text-sm text-muted-foreground shadow-sm">
			Sidebar information is unavailable.
		</div>
	{/if}
</aside>
