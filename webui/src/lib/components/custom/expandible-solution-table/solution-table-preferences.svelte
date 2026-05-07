<script lang="ts">
    import * as Table from '$lib/components/ui/table/index.js';
    import * as Tooltip from '$lib/components/ui/tooltip/index.js';
    import { formatNumber } from '$lib/helpers';
    import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';

    let {
        problem,
        previousPreferences,
        displayAccuracy,
        columnsLength,
        differenceFromSolution = [],
    }: {
        problem: ProblemInfo;
        previousPreferences: number[][];
        displayAccuracy: number[];
        columnsLength: number;
        differenceFromSolution?: number[];
    } = $props();

    function isImprovement(diff: number, maximize: boolean): boolean | null {
        if (!Number.isFinite(diff) || diff === 0) {
            return null;
        }
        return maximize ? diff > 0 : diff < 0;
    }

    function relativePercentFromRange(
        diff: number,
        idealValue?: number | null,
        nadirValue?: number | null
    ): number | null {
        if (!Number.isFinite(diff) || idealValue == null || nadirValue == null) {
            return null;
        }

        const objectiveRange = Math.abs(idealValue - nadirValue);
        if (!Number.isFinite(objectiveRange) || objectiveRange === 0) {
            return null;
        }

        return (Math.abs(diff) / objectiveRange) * 100;
    }
</script>

{#if previousPreferences && previousPreferences.length > 0}
    <Table.Row class="pointer-events-none">
        <Table.Cell colspan={columnsLength}>
        </Table.Cell>
    </Table.Row>
    {#if differenceFromSolution?.length>0}
        <Table.Row class='pointer-events-none'>
            <Table.Cell ></Table.Cell>
            <Table.Cell class="italic">
                <div>
                    <span class="text-gray-500">Difference from preferences</span>
                </div>
            </Table.Cell>
            <Table.Cell></Table.Cell>
            {#each problem.objectives as objective, idx}
                <Table.Cell class="text-gray-500 text-right pr-6">
                    {@const diff = differenceFromSolution[idx] ?? 0}
                    {@const improvement = isImprovement(diff, Boolean(objective.maximize))}
                    {@const percent = relativePercentFromRange(diff, objective.ideal, objective.nadir)}
                    <div
                        class="inline-flex items-center gap-1"
                        title={improvement === null
                            ? 'No change compared to reference point'
                            : improvement
                                ? 'Improvement compared to reference point'
                                : 'Impairment compared to reference point'}
                    >
                        {#if improvement === true}
                            <span class="font-semibold text-emerald-700">↑</span>
                        {:else if improvement === false}
                            <span class="font-semibold text-rose-700">↓</span>
                        {/if}
                        <span
                            class={improvement === null
                                ? 'text-gray-500'
                                : improvement
                                    ? 'text-emerald-700'
                                    : 'text-rose-700'}
                        >
                            <Tooltip.Provider>
                                <Tooltip.Root>
                                    <Tooltip.Trigger class="pointer-events-auto underline decoration-dotted underline-offset-2">
                                        {formatNumber(diff, displayAccuracy[idx])}
                                    </Tooltip.Trigger>
                                    <Tooltip.Content sideOffset={6}>
                                        <p>
                                            Relative change over objective range (ideal-nadir): {percent === null ? 'n/a' : `${formatNumber(percent, 2)}%`}
                                        </p>
                                    </Tooltip.Content>
                                </Tooltip.Root>
                            </Tooltip.Provider>
                        </span>
                    </div>
                </Table.Cell>
            {/each}
        </Table.Row>
    {/if}
    {#each previousPreferences as previousPreference}
        <Table.Row class='pointer-events-none'>
            <Table.Cell class="border-l-10 border-red-400"></Table.Cell>
            <Table.Cell class="italic">
                <div>
                    <span class="text-gray-500">Previous preferences</span>
                </div>
            </Table.Cell>
            <Table.Cell></Table.Cell>
            {#each problem.objectives as objective, idx}
                <Table.Cell class="text-gray-500 text-right pr-6">
                    {formatNumber(previousPreference[idx], displayAccuracy[idx])}
                </Table.Cell>
            {/each}
        </Table.Row>
    {/each}

{/if}
