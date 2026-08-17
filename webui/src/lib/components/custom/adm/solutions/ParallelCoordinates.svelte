<script lang="ts">
  import { onMount } from "svelte";
  import * as d3 from "d3";

  import type { ADMLog, PopulationSolution } from "$lib/adm/types";

  import {
    getIteration,
    getObjectives
  } from "$lib/adm/adapters";


  export let log: ADMLog;
  export let populationHistory: PopulationSolution[] = [];

  export let selectedIteration: number;
  export let selectedGeneration: number | null = null;

  // Interaction-level ADM information only.
  export let selectedVector: string | null = null;

  export let width = 900;
  export let height = 360;

  let svgEl: SVGSVGElement;

  let hoveredSolution: PopulationSolution | null = null;
  let selectedSolution: PopulationSolution | null = null;

  let tooltipVisible = false;
  let tooltipX = 0;
  let tooltipY = 0;

  let visibleMethods: string[] = [];

  // --------------------------------------------------
  // Benchmark context
  // --------------------------------------------------

  $: iteration =
    getIteration(log, selectedIteration);

  $: objectives =
    getObjectives(log);

  $: objectiveCount =
    log.problem.objectives;

  $: if (
    visibleMethods.length === 0 &&
    log.methods.length > 0
  ) {
    visibleMethods = [...log.methods];
  }

  // --------------------------------------------------
  // Population filtering
  // --------------------------------------------------

  $: interactionRows =
    populationHistory.filter(
      (row) =>
        row.adm_iteration === selectedIteration
    );

  $: availableGenerations = [
    ...new Set(
      interactionRows.map(
        (row) =>
          row.generation_in_iteration
      )
    )
  ].sort((a, b) => a - b);

  $: effectiveGeneration =
    selectedGeneration ??
    (
      availableGenerations.length
        ? availableGenerations[
            availableGenerations.length - 1
          ]
        : null
    );

  $: generationRows =
    effectiveGeneration === null
      ? []
      : interactionRows.filter(
          (row) =>
            row.generation_in_iteration ===
              effectiveGeneration &&
            visibleMethods.includes(row.method)
        );

  $: methodCounts =
    log.methods.map((method) => ({
      method,
      count: generationRows.filter(
        (row) => row.method === method
      ).length
    }));

  // --------------------------------------------------
  // ADM context
  // --------------------------------------------------

  $: referencePoint =
    iteration.preference_information.reference_point;

  $: activeVector =
    selectedVector ??
    iteration.preference_information
      .selected_reference_vector;

  // --------------------------------------------------
  // Helpers
  // --------------------------------------------------

  function toggleMethod(method: string) {
    if (visibleMethods.includes(method)) {
      if (visibleMethods.length === 1) {
        return;
      }

      visibleMethods =
        visibleMethods.filter(
          (item) => item !== method
        );
    } else {
      visibleMethods = [
        ...visibleMethods,
        method
      ];
    }
  }

  function previousGeneration() {
    if (effectiveGeneration === null) {
      return;
    }

    const index =
      availableGenerations.indexOf(
        effectiveGeneration
      );

    if (index > 0) {
      selectedGeneration =
        availableGenerations[index - 1];
    }
  }

  function nextGeneration() {
    if (effectiveGeneration === null) {
      return;
    }

    const index =
      availableGenerations.indexOf(
        effectiveGeneration
      );

    if (
      index >= 0 &&
      index < availableGenerations.length - 1
    ) {
      selectedGeneration =
        availableGenerations[index + 1];
    }
  }

  function showFinalGeneration() {
    selectedGeneration = null;
  }

  // --------------------------------------------------
  // Drawing
  // --------------------------------------------------

  function draw() {
    if (!svgEl) return;

    const svg =
      d3.select(svgEl);

    svg.selectAll("*").remove();

    if (
      generationRows.length === 0 ||
      objectiveCount === 0
    ) {
      svg
        .attr(
          "viewBox",
          `0 0 ${width} ${height}`
        )
        .append("text")
        .attr("x", width / 2)
        .attr("y", height / 2)
        .attr(
          "text-anchor",
          "middle"
        )
        .attr("fill", "#8a91a3")
        .attr("font-size", 12)
        .text(
          "No population available for this generation."
        );

      return;
    }

    const margin = {
      top: 34,
      right: 34,
      bottom: 28,
      left: 38
    };

    const innerWidth =
      width -
      margin.left -
      margin.right;

    const innerHeight =
      height -
      margin.top -
      margin.bottom;

    // ------------------------------------------------
    // Objective positions
    // ------------------------------------------------

    const objectiveIndices =
      d3.range(objectiveCount);

    const x =
      d3
        .scalePoint<number>()
        .domain(objectiveIndices)
        .range([0, innerWidth]);

    // ------------------------------------------------
    // One Y scale per objective
    //
    // Use every population from the selected
    // interaction so axes remain fixed when moving
    // through generations.
    // ------------------------------------------------

    const yScales =
      objectiveIndices.map(
        (objectiveIndex) => {
          const values =
            interactionRows
              .map(
                (row) =>
                  row.objectives[
                    objectiveIndex
                  ]
              )
              .filter(
                (value) =>
                  Number.isFinite(value)
              );

          const referenceValue =
            referencePoint[
              objectiveIndex
            ];

          if (
            Number.isFinite(
              referenceValue
            )
          ) {
            values.push(
              referenceValue
            );
          }

          let min =
            d3.min(values) ?? 0;

          let max =
            d3.max(values) ?? 1;

          min =
            Math.min(0, min);

          if (min === max) {
            max = min + 1;
          }

          const padding =
            (max - min) * 0.04;

          return d3
            .scaleLinear()
            .domain([
              Math.max(
                0,
                min - padding
              ),
              max + padding
            ])
            .nice()
            .range([
              innerHeight,
              0
            ]);
        }
      );

    // ------------------------------------------------
    // Method colors
    // ------------------------------------------------

    const colors = [
      "#6546e8",
      "#ef4444",
      "#0284c7",
      "#f59e0b",
      "#16a34a",
      "#db2777",
      "#0891b2",
      "#84cc16"
    ];

    const methodColor =
      d3
        .scaleOrdinal<string, string>()
        .domain(log.methods)
        .range(colors);

    const root =
      svg
        .attr(
          "viewBox",
          `0 0 ${width} ${height}`
        )
        .attr(
          "preserveAspectRatio",
          "xMidYMid meet"
        )
        .append("g")
        .attr(
          "transform",
          `translate(${margin.left},${margin.top})`
        );

    root
      .append("rect")
      .attr("width", innerWidth)
      .attr("height", innerHeight)
      .attr("rx", 5)
      .attr("fill", "#fcfcfe");

    // ------------------------------------------------
    // Generic parallel-coordinate line
    // ------------------------------------------------

    const line =
      d3
        .line<number>()
        .defined(
          (value) =>
            Number.isFinite(value)
        )
        .x(
          (_, index) =>
            x(index) ?? 0
        )
        .y(
          (value, index) =>
            yScales[index](value)
        )
        .curve(d3.curveLinear);

    // ------------------------------------------------
    // Solutions
    // ------------------------------------------------

    const paths =
      root
        .append("g")
        .attr(
          "class",
          "solution-lines"
        )
        .selectAll("path")
        .data(generationRows)
        .join("path")
        .attr(
          "d",
          (solution) =>
            line(
              solution.objectives
            )
        )
        .attr("fill", "none")
        .attr(
          "stroke",
          (solution) =>
            methodColor(
              solution.method
            )
        )
        .attr(
          "stroke-width",
          1
        )
        .attr(
          "stroke-opacity",
          0.16
        )
        .style(
          "cursor",
          "pointer"
        )
        .on(
          "mouseenter",
          function (
            event,
            solution
          ) {
            hoveredSolution =
              solution;

            d3
              .select(this)
              .raise()
              .attr(
                "stroke-width",
                2.8
              )
              .attr(
                "stroke-opacity",
                1
              );

            const bounds =
              svgEl.getBoundingClientRect();

            tooltipX =
              event.clientX -
              bounds.left +
              12;

            tooltipY =
              event.clientY -
              bounds.top +
              10;

            tooltipVisible = true;
          }
        )
        .on(
          "mousemove",
          function (event) {
            const bounds =
              svgEl.getBoundingClientRect();

            tooltipX =
              event.clientX -
              bounds.left +
              12;

            tooltipY =
              event.clientY -
              bounds.top +
              10;
          }
        )
        .on(
          "mouseleave",
          function (
            _event,
            solution
          ) {
            hoveredSolution = null;
            tooltipVisible = false;

            const isSelected =
              selectedSolution === solution;

            d3
              .select(this)
              .attr(
                "stroke-width",
                isSelected ? 3 : 1
              )
              .attr(
                "stroke-opacity",
                isSelected
                  ? 1
                  : 0.16
              );
          }
        )
        .on(
          "click",
          function (
            event,
            solution
          ) {
            event.stopPropagation();

            selectedSolution =
              solution;

            paths
              .attr(
                "stroke-width",
                1
              )
              .attr(
                "stroke-opacity",
                0.07
              );

            d3
              .select(this)
              .raise()
              .attr(
                "stroke-width",
                3
              )
              .attr(
                "stroke-opacity",
                1
              );
          }
        );

    // ------------------------------------------------
    // ADM reference point
    // ------------------------------------------------

    if (
      referencePoint.length ===
      objectiveCount
    ) {
      root
        .append("path")
        .datum(referencePoint)
        .attr(
          "d",
          line(referencePoint)
        )
        .attr("fill", "none")
        .attr(
          "stroke",
          "#111827"
        )
        .attr(
          "stroke-width",
          1.8
        )
        .attr(
          "stroke-dasharray",
          "5 4"
        )
        .style(
          "pointer-events",
          "none"
        );

      root
        .append("g")
        .selectAll("circle")
        .data(
          referencePoint.map(
            (value, index) => ({
              value,
              index
            })
          )
        )
        .join("circle")
        .attr(
          "cx",
          (d) =>
            x(d.index) ?? 0
        )
        .attr(
          "cy",
          (d) =>
            yScales[
              d.index
            ](d.value)
        )
        .attr("r", 4)
        .attr(
          "fill",
          "#111827"
        )
        .attr(
          "stroke",
          "white"
        )
        .attr(
          "stroke-width",
          1.3
        )
        .style(
          "pointer-events",
          "none"
        );
    }

    // ------------------------------------------------
    // Objective axes
    // ------------------------------------------------

    const axes =
      root
        .selectAll(
          ".objective-axis"
        )
        .data(
          objectives.map(
            (
              objective,
              index
            ) => ({
              objective,
              index
            })
          )
        )
        .join("g")
        .attr(
          "class",
          "objective-axis"
        )
        .attr(
          "transform",
          (d) =>
            `translate(${x(
              d.index
            )},0)`
        );

    axes.each(
      function (d) {
        const axis =
          d3
            .axisLeft(
              yScales[
                d.index
              ]
            )
            .ticks(4)
            .tickSize(3)
            .tickFormat(
              (value) => {
                const number =
                  Number(value);

                if (
                  Math.abs(number) <
                    0.001 &&
                  number !== 0
                ) {
                  return d3.format(
                    ".1e"
                  )(number);
                }

                return d3.format(
                  ".2f"
                )(number);
              }
            );

        d3
          .select(this)
          .call(axis);
      }
    );

    axes
      .select(".domain")
      .attr(
        "stroke",
        "#9da5b4"
      );

    axes
      .selectAll(
        ".tick line"
      )
      .attr(
        "stroke",
        "#bbc1cd"
      );

    axes
      .selectAll(
        ".tick text"
      )
      .attr(
        "fill",
        "#8b92a2"
      )
      .attr(
        "font-size",
        8
      );

    axes
      .append("text")
      .attr("y", -14)
      .attr(
        "text-anchor",
        "middle"
      )
      .attr(
        "fill",
        "#252b38"
      )
      .attr(
        "font-size",
        11
      )
      .attr(
        "font-weight",
        700
      )
      .text(
        (d) =>
          d.objective
      );

    svg.on(
      "click",
      () => {
        selectedSolution = null;
        draw();
      }
    );
  }

  onMount(draw);

  $: if (
    svgEl &&
    selectedIteration &&
    effectiveGeneration !== null &&
    visibleMethods
  ) {
    draw();
  }
</script>


<div class="parallel-coordinates">

  <div class="context-bar">

    <div class="context-items">

      <div>
        <span>Interaction</span>
        <strong>
          {selectedIteration}
        </strong>
      </div>

      <div>
        <span>Phase</span>
        <strong class="phase">
          {iteration.phase}
        </strong>
      </div>

      <div>
        <span>ADM vector</span>
        <strong class="vector">
          {activeVector}
        </strong>
      </div>

      <div>
        <span>Objectives</span>
        <strong>
          {objectiveCount}
        </strong>
      </div>

    </div>


    <div class="generation-navigation">

      <button
        on:click={previousGeneration}
        disabled={
          effectiveGeneration === null ||
          availableGenerations.indexOf(
            effectiveGeneration
          ) <= 0
        }
      >
        ‹
      </button>

      <div>
        <span>Generation</span>

        <strong>
          {effectiveGeneration ?? "—"}

          {#if
            availableGenerations.length
          }
            <small>
              /
              {
                availableGenerations[
                  availableGenerations.length -
                    1
                ]
              }
            </small>
          {/if}
        </strong>
      </div>

      <button
        on:click={nextGeneration}
        disabled={
          effectiveGeneration === null ||
          availableGenerations.indexOf(
            effectiveGeneration
          ) ===
            availableGenerations.length -
              1
        }
      >
        ›
      </button>

      {#if selectedGeneration !== null}
        <button
          class="final"
          on:click={showFinalGeneration}
        >
          Final
        </button>
      {/if}

    </div>

  </div>


  <div class="toolbar">

    <div class="method-controls">

      {#each
        methodCounts
        as item, index
      }

        <button
          class:inactive={
            !visibleMethods.includes(
              item.method
            )
          }
          on:click={() =>
            toggleMethod(
              item.method
            )
          }
        >

          <i
            style:background={
              [
                "#6546e8",
                "#ef4444",
                "#0284c7",
                "#f59e0b",
                "#16a34a",
                "#db2777",
                "#0891b2",
                "#84cc16"
              ][index % 8]
            }
          ></i>

          {item.method}

          <strong>
            {item.count}
          </strong>

        </button>

      {/each}

    </div>

    <span>
      {generationRows.length}
      solutions
    </span>

  </div>


  <div class="chart-wrapper">

    <svg bind:this={svgEl}></svg>

    {#if
      tooltipVisible &&
      hoveredSolution
    }

      <div
        class="tooltip"
        style:left={`${tooltipX}px`}
        style:top={`${tooltipY}px`}
      >

        <div class="tooltip-header">

          <strong>
            {hoveredSolution.method}
          </strong>

          <span>
            Solution
            {
              hoveredSolution.solution_index
            }
          </span>

        </div>


        <div class="tooltip-values">

          {#each
            hoveredSolution.objectives
            as value, index
          }

            <div>
              <span>
                {objectives[index]}
              </span>

              <b>
                {value.toFixed(4)}
              </b>
            </div>

          {/each}

        </div>

      </div>

    {/if}

  </div>


  <div class="footer">

    <div class="legend">

      {#each
        log.methods
        as method, index
      }

        <span>

          <i
            class="method-line"
            style:background={
              [
                "#6546e8",
                "#ef4444",
                "#0284c7",
                "#f59e0b",
                "#16a34a",
                "#db2777",
                "#0891b2",
                "#84cc16"
              ][index % 8]
            }
          ></i>

          {method}

        </span>

      {/each}

      <span>
        <i class="reference-line"></i>
        ADM reference point
      </span>

    </div>

    <small>
      Axis ranges remain fixed within
      interaction {selectedIteration}.
    </small>

  </div>

</div>


<style>
  .parallel-coordinates {
    width: 100%;
    min-width: 0;
  }

  .context-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;

    gap: 0.8rem;
    flex-wrap: wrap;

    padding: 0.45rem 0.55rem;
    margin-bottom: 0.4rem;

    border: 1px solid #e8eaf0;
    border-radius: 7px;

    background: #fafbfc;
  }

  .context-items {
    display: flex;
    align-items: center;
    flex-wrap: wrap;

    gap: 1rem;
  }

  .context-items div {
    display: flex;
    flex-direction: column;
  }

  .context-items span,
  .generation-navigation span {
    color: #969dac;
    font-size: 0.5rem;
    text-transform: uppercase;
  }

  .context-items strong,
  .generation-navigation strong {
    color: #353b49;
    font-size: 0.63rem;
  }

  .context-items .phase {
    text-transform: capitalize;
  }

  .context-items .vector {
    color: #6344d8;
  }

  .generation-navigation {
    display: flex;
    align-items: center;
    gap: 0.3rem;
  }

  .generation-navigation > div {
    min-width: 70px;
    text-align: center;
  }

  .generation-navigation button {
    height: 27px;
    min-width: 27px;

    border: 1px solid #dfe2ea;
    border-radius: 5px;

    background: white;
    color: #596173;

    cursor: pointer;
  }

  .generation-navigation button:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .generation-navigation .final {
    padding: 0 0.5rem;
    color: #6041d6;
  }

  .generation-navigation small {
    color: #959baa;
    font-size: 0.52rem;
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;

    gap: 0.5rem;
    flex-wrap: wrap;

    margin-bottom: 0.25rem;
  }

  .toolbar > span {
    color: #8e95a4;
    font-size: 0.56rem;
  }

  .method-controls {
    display: flex;
    gap: 0.35rem;
    flex-wrap: wrap;
  }

  .method-controls button {
    display: flex;
    align-items: center;
    gap: 0.3rem;

    padding: 0.25rem 0.42rem;

    border: 1px solid #e5e7ed;
    border-radius: 5px;

    background: white;
    color: #5f6778;

    font-size: 0.56rem;
    cursor: pointer;
  }

  .method-controls button.inactive {
    opacity: 0.35;
  }

  .method-controls i {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .method-controls strong {
    color: #353b49;
  }

  .chart-wrapper {
    position: relative;
    width: 100%;
  }

  svg {
    display: block;
    width: 100%;
    height: auto;
    overflow: visible;
  }

  .tooltip {
    position: absolute;
    z-index: 30;

    min-width: 220px;
    padding: 0.6rem;

    pointer-events: none;

    border: 1px solid #e1e4eb;
    border-radius: 8px;

    background: rgba(255,255,255,0.98);

    box-shadow:
      0 10px 30px rgb(15 23 42 / 0.14);
  }

  .tooltip-header {
    display: flex;
    justify-content: space-between;

    margin-bottom: 0.45rem;

    color: #343a49;
    font-size: 0.62rem;
  }

  .tooltip-header span {
    color: #8b92a2;
    font-size: 0.54rem;
  }

  .tooltip-values {
    display: grid;
    grid-template-columns:
      repeat(
        auto-fit,
        minmax(52px, 1fr)
      );

    gap: 0.25rem;
  }

  .tooltip-values div {
    padding: 0.3rem;
    text-align: center;

    border-radius: 4px;
    background: #f7f8fb;
  }

  .tooltip-values span {
    display: block;
    color: #969dac;
    font-size: 0.5rem;
  }

  .tooltip-values b {
    color: #343a49;
    font-size: 0.57rem;
  }

  .footer {
    display: flex;
    justify-content: space-between;
    align-items: center;

    gap: 0.7rem;
    margin-top: 0.3rem;
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .legend span {
    display: flex;
    align-items: center;
    gap: 0.28rem;

    color: #757d8f;
    font-size: 0.57rem;
  }

  .method-line,
  .reference-line {
    display: inline-block;
    width: 16px;
  }

  .method-line {
    height: 2px;
  }

  .reference-line {
    height: 0;
    border-top:
      2px dashed #111827;
  }

  .footer small {
    color: #a0a6b3;
    font-size: 0.51rem;
  }
</style>