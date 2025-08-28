<script lang="ts">
	import { BaseLayout } from '$lib/components/custom/method_layout/index.js';

  const showLeftSidebar = true;
  const showRightSidebar = true;
</script>

<BaseLayout {showLeftSidebar} {showRightSidebar}>
  <!-- Left Sidebar Content -->
  {#snippet leftSidebar()}
    <h2 class="font-bold">Preference information</h2>
    <ul>
      <li>Objective 1</li>
      <li>Objective 2</li>
    </ul>
  {/snippet}

  <!-- Menu Row -->
  {#snippet menuRow()}
    <button class="bg-gray-200 px-2 py-1 rounded">Intermediate solutions</button>
    <button class="bg-gray-200 px-2 py-1 rounded">View options</button>
    <button class="bg-red-500 px-2 py-1 rounded">Finish</button>
  {/snippet}

  <!-- Main Panel -->
  {#snippet topPanel()}
    <h1 class="text-xl font-bold">Main Area</h1>
    <p>This is where the visualizations would go.</p>
  {/snippet}

  <!-- Bottom Panel -->
  {#snippet bottomPanel()}
    <h3 class="font-semibold">Numerical values</h3>
    <pre>A table willbe shown here</pre>
  {/snippet}

  <!-- Right Sidebar -->
  {#snippet rightSidebar()}
    <h2 class="font-bold">Explanations</h2>
    <p>Selected solution details...</p>
  {/snippet}
</BaseLayout>
