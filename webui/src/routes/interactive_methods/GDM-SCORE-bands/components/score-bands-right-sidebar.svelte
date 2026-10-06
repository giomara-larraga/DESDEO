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

		onExploreBand: (clusterId: number) => void | Promise<void>;

		onBackOneLevel: () => void;

		onExitExploration: () => void;
	};

	type ConsensusSidebarContext = {
		totalVoters: number;
		clusterIds: number[];
		clusterColors: Record<number, string>;

		selectedBand: number | null;
		voteConfirmed: boolean;
		haveAllVoted: boolean;
		haveAllConfirmed: boolean;
		isConsensusVoteSyncing: boolean;
		isAdvancingToDecision: boolean;
		isContinuingConsensus: boolean;

		voters: Array<{
			id: number;
			username: string;
			votedClusterId: number | null;
			hasVoted: boolean;
			hasConfirmed: boolean;
		}>;

		getClusterVoteCount: (clusterId: number) => number;
		getClusterVotePercent: (clusterId: number) => number;

		onBandSelect: (clusterId: number) => void;
		onVote: () => void | Promise<void>;
		onConfirmVote: () => void | Promise<void>;
		onAdvanceToDecision: () => void | Promise<void>;
		onContinueConsensus: () => void | Promise<void>;

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

	let { phase, isOwner, isDecisionMaker, learning, consensus }: Props = $props();
</script>

<aside class="space-y-4">
	{#if phase === 'learning' && learning}
		<section class="bg-card rounded-lg border shadow-sm">
			<header class="border-b px-4 py-3">
				<h2 class="text-sm font-semibold">
					{#if isOwner}Learning progress{:else}My exploration{/if}
				</h2>

				{#if isDecisionMaker}
					<p class="text-muted-foreground mt-1 text-xs">Visible only to you.</p>
				{/if}
			</header>

			<div class="space-y-3 p-4">
				<div class="rounded-md border p-3 text-sm">
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
							<span class="font-medium">Selected band: </span><span
								>{learning.selectedLearningBand}</span
							>
							<br />
							<span class="font-medium">Depth: </span><span>{learning.explorationDepth}</span>
						</div>
					</div>
				{/if}

				{#if learning.selectedLearningBand !== null}
					{#if isDecisionMaker}
						<Button
							class="w-full"
							onclick={() => learning.onExploreBand(learning.selectedLearningBand!)}
							disabled={learning.isExploringBand}
						>
							{learning.isExploringBand ? 'Generating bands...' : 'Explore inside band'}
						</Button>
					{/if}
				{:else}
					{#if isDecisionMaker}
						<p
							class="
			text-muted-foreground text-sm
		"
						>
							Select a band to inspect or explore it.
						</p>
					{/if}
				{/if}

				{#if learning.explorationDepth > 0}
					<div class="flex gap-2">
						<Button class="flex-1" variant="outline" size="sm" onclick={learning.onBackOneLevel}>
							← Back
						</Button>

						<Button class="flex-1" variant="outline" size="sm" onclick={learning.onExitExploration}>
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
			<section class="bg-card rounded-lg border shadow-sm">
				<header class="border-b px-4 py-3">
					<h2 class="text-sm font-semibold">Saved bands</h2>
				</header>

				<div class="space-y-2 p-4">
					{#each learning.savedBands as clusterId}
						<div class="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
							<span>Band {clusterId}</span>
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

		<section class="bg-card rounded-lg border shadow-sm">
			<header class="border-b px-4 py-3">
				<h2 class="text-sm font-semibold">What’s next?</h2>
			</header>

			<div class="text-muted-foreground space-y-3 p-4 text-sm">
				<p>Once the group is ready, you can move to the consensus phase.</p>

				{#if isOwner}
					<Button
						class="w-full"
						onclick={learning.onAdvanceToConsensus}
						disabled={!learning.allDecisionMakersFinishedLearning ||
							learning.isAdvancingToConsensus}
					>
						{learning.isAdvancingToConsensus
							? 'Starting consensus...'
							: 'Continue to consensus phase'}
					</Button>
				{/if}
			</div>
		</section>
	{:else if phase === 'consensus' && consensus}
		<section class="bg-card rounded-lg border shadow-sm">
			<header class="border-b px-4 py-3">
				<h2 class="text-sm font-semibold">Group voting</h2>
				<p class="text-muted-foreground mt-1 text-xs">
					{consensus.totalVoters} decision makers
				</p>
				<p class="text-muted-foreground mt-1 text-xs">
					Vote sync: {consensus.isConsensusVoteSyncing ? 'updating...' : 'live'}
				</p>
			</header>

			<div class="space-y-2 p-4">
				<div class="text-sm font-medium">
					{#if isDecisionMaker}Select your preferred band{:else}Votes per band{/if}
				</div>

				{#each consensus.clusterIds as clusterId}
					<button
						type="button"
						class="hover:bg-muted flex w-full items-center justify-between rounded-md border px-3 py-3 text-left text-sm {consensus.selectedBand ===
						clusterId
							? 'border-primary bg-muted'
							: ''}"
						onclick={() => consensus.onBandSelect(clusterId)}
						disabled={consensus.voteConfirmed || !isDecisionMaker}
					>
						<span class="flex items-center gap-2">
							<span
								class="h-3 w-3 rounded-full"
								style:background-color={consensus.clusterColors[clusterId] ?? '#64748b'}
							></span>
							Band {clusterId}
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
						<!-- If the user confirmed their vote, show a confirmation message and to wait until the others confirm theirs -->
						<p class="text-muted-foreground pt-2 text-sm">
							{#if consensus.voteConfirmed}
								You have confirmed your vote. Please wait for the other decision makers to confirm
								theirs.
							{:else if consensus.haveAllVoted}
								All decision makers have voted. You can now confirm your vote. You can also change
								your vote before confirming.
							{:else}
								Waiting for all decision makers to vote.
							{/if}
						</p>
					</div>
				{:else if isOwner}
					<p class="text-muted-foreground pt-3 text-sm">You can monitor the voting progress.</p>
					<!-- Show the status of each decision maker: which band (if any) they voted for and whether they confirmed it -->
					<div class="space-y-2">
						{#each consensus.voters as voter (voter.id)}
							<div class="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
								<span class="font-medium">{voter.username}</span>
								<span class="text-muted-foreground flex items-center gap-2">
									{#if voter.hasVoted}
										<span
											class="h-2.5 w-2.5 rounded-full"
											style:background-color={consensus.clusterColors[voter.votedClusterId ?? -1] ??
												'#64748b'}
										></span>
										Band {voter.votedClusterId}
										{#if voter.hasConfirmed}
											<span class="text-green-600">(Confirmed)</span>
										{:else}
											<span>(Not confirmed)</span>
										{/if}
									{:else}
										Not voted
									{/if}
								</span>
							</div>
						{/each}
					</div>

					<div class="bg-card rounded-lg border shadow-sm">
						<div class="border-b px-4 py-3">
							<h2 class="text-sm font-semibold">Moderator controls</h2>
						</div>

						<div class="space-y-3 p-4">
							{#if consensus.haveAllConfirmed}
								<p class="text-muted-foreground text-sm">
									All decision makers have confirmed their votes. You can continue consensus
									reaching or proceed directly to the decision phase.
								</p>
							{:else}
								<p class="text-muted-foreground text-sm">
									Waiting for all decision makers to confirm their votes.
								</p>
							{/if}

							<Button
								class="w-full"
								onclick={consensus.onContinueConsensus}
								disabled={!consensus.haveAllConfirmed ||
									consensus.isContinuingConsensus ||
									consensus.isAdvancingToDecision}
							>
								{consensus.isContinuingConsensus ? 'Continuing consensus...' : 'Continue consensus'}
							</Button>

							<Button
								class="w-full"
								variant="outline"
								onclick={consensus.onAdvanceToDecision}
								disabled={!consensus.haveAllConfirmed ||
									consensus.isContinuingConsensus ||
									consensus.isAdvancingToDecision}
							>
								{consensus.isAdvancingToDecision
									? 'Starting decision phase...'
									: 'Continue to decision phase'}
							</Button>
						</div>
					</div>
				{/if}
			</div>
		</section>

		<!-- 		<section class="rounded-lg border bg-card shadow-sm">
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
		</section> -->
	{:else}
		<div class="bg-card text-muted-foreground rounded-lg border p-4 text-sm shadow-sm">
			Sidebar information is unavailable.
		</div>
	{/if}
</aside>
