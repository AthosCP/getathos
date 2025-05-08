<script lang="ts">
  let message = '';
  let error = '';

  async function testGet() {
    try {
      const response = await fetch('http://localhost:5001/test', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      const data = await response.json();
      message = data.message;
      error = '';
    } catch (e) {
      error = 'Error en GET: ' + e;
      message = '';
    }
  }

  async function testPost() {
    try {
      const response = await fetch('http://localhost:5001/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ test: 'data' })
      });
      const data = await response.json();
      message = data.message;
      error = '';
    } catch (e) {
      error = 'Error en POST: ' + e;
      message = '';
    }
  }
</script>

<div class="p-4">
  <h1 class="text-2xl mb-4">Página de Prueba</h1>
  
  <div class="space-y-4">
    <button
      on:click={testGet}
      class="bg-blue-500 text-white px-4 py-2 rounded mr-2"
    >
      Probar GET
    </button>
    
    <button
      on:click={testPost}
      class="bg-green-500 text-white px-4 py-2 rounded"
    >
      Probar POST
    </button>

    {#if message}
      <div class="text-green-600 mt-4">{message}</div>
    {/if}

    {#if error}
      <div class="text-red-600 mt-4">{error}</div>
    {/if}
  </div>
</div> 