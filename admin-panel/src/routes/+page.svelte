<script lang="ts">
  import { onMount } from 'svelte';
  import { createClient } from '@supabase/supabase-js';

  const supabase = createClient(
    import.meta.env.VITE_SUPABASE_URL,
    import.meta.env.VITE_SUPABASE_ANON_KEY
  );

  let user = null;
  let tenants = [];
  let loading = true;

  onMount(async () => {
    const { data: { session } } = await supabase.auth.getSession();
    user = session?.user ?? null;
    
    if (user) {
      const { data } = await supabase
        .from('tenants')
        .select('*')
        .eq('admin_id', user.id);
      tenants = data || [];
    }
    
    loading = false;
  });

  const handleLogout = async () => {
    await supabase.auth.signOut();
    user = null;
  };
</script>

<main class="container mx-auto px-4 py-8">
  {#if loading}
    <div class="text-center">Cargando...</div>
  {:else if !user}
    <div class="max-w-md mx-auto bg-white rounded-lg shadow-md p-6">
      <h1 class="text-2xl font-bold mb-4">Iniciar Sesión</h1>
      <button
        class="w-full bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600"
        on:click={() => supabase.auth.signInWithOAuth({ provider: 'google' })}
      >
        Iniciar sesión con Google
      </button>
    </div>
  {:else}
    <div class="bg-white rounded-lg shadow-md p-6">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold">Panel de Control</h1>
        <button
          class="bg-red-500 text-white py-2 px-4 rounded hover:bg-red-600"
          on:click={handleLogout}
        >
          Cerrar Sesión
        </button>
      </div>

      <div class="mb-8">
        <h2 class="text-xl font-semibold mb-4">Tus Organizaciones</h2>
        {#if tenants.length === 0}
          <p class="text-gray-500">No tienes organizaciones asignadas.</p>
        {:else}
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {#each tenants as tenant}
              <div class="border rounded-lg p-4">
                <h3 class="font-semibold">{tenant.name}</h3>
                <p class="text-sm text-gray-600">{tenant.description}</p>
                <div class="mt-4">
                  <a
                    href="/tenant/{tenant.id}"
                    class="text-blue-500 hover:text-blue-600"
                  >
                    Gestionar →
                  </a>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {/if}
</main>

<style>
  :global(body) {
    background-color: #f3f4f6;
    font-family: system-ui, -apple-system, sans-serif;
  }
</style> 