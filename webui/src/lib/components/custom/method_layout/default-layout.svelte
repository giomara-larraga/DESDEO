<script lang="ts">
	import { BaseLayout } from '$lib/components/custom/method_layout/index.js';

  const showLeftSidebar = true;
  const showRightSidebar = true;
</script>

<BaseLayout {showLeftSidebar} {showRightSidebar}>
  <!-- Left Sidebar Content -->
  {#snippet leftSidebar()}
    <h2 class="font-bold">Project Explorer</h2>
    <ul>
      <li>File1.svelte</li>
      <li>File2.ts</li>
    </ul>
  {/snippet}

  <!-- Menu Row -->
  {#snippet menuRow()}
    <button class="bg-blue-500 text-white px-2 py-1 rounded">Run</button>
    <button class="bg-gray-200 px-2 py-1 rounded">Settings</button>
  {/snippet}

  <!-- Main Panel -->
  {#snippet topPanel()}
    <h1 class="text-xl font-bold">Main Editor Area</h1>
    <p>This is where your editor or visualization would go.</p>
  {/snippet}

  <!-- Bottom Panel -->
  {#snippet bottomPanel()}
    <h3 class="font-semibold">Logs</h3>
    <pre>Error: Something went wrong</pre>
  {/snippet}

  <!-- Right Sidebar -->
  {#snippet rightSidebar()}
    <h2 class="font-bold">Inspector</h2>
    <p>Selected element details...</p>
  {/snippet}
</BaseLayout>
