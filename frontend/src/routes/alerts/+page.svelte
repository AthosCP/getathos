<script lang="ts">
  import Navbar from '$lib/Navbar.svelte';
  import { onMount } from 'svelte';
  import { auth } from '$lib/auth';
  import { goto } from '$app/navigation';
  import { API_URL } from '$lib/config';

  let alerts: any[] = [];
  let loading = true;
  let error = '';

  // Categorías dinámicas
  let categorias: string[] = [];

  // Mock de contadores (simulando alert_stats)
  let alertStats = [
    { category: 'apuestas/juegos de azar', count: 2 },
    { category: 'redes sociales', count: 5 },
    { category: 'adultos', count: 0 },
    { category: 'compras', count: 1 },
    // el resto se completará con 0 si no hay registro
  ];

  // Tarjetas de categorías
  let tarjetas: { category: string, count: number }[] = [];

  // Filtros globales
  let users: any[] = [];
  let selectedUser = '';
  let selectedCategoria = '';
  let dateFrom = '';
  let dateTo = '';

  // Registros reales
  let registros: any[] = [];
  let loadingRegistros = false;

  async function loadCategorias() {
    try {
      const res = await fetch(`${API_URL}/api/prohibidos`);
      const data = await res.json();
      if (data.success) {
        categorias = Object.keys(data.data);
      } else {
        categorias = [];
      }
    } catch {
      categorias = [];
    }
  }

  async function loadUsers() {
    try {
      const res = await fetch(`${API_URL}/api/users`, {
        headers: { 'Authorization': `Bearer ${auth.token}` }
      });
      const data = await res.json();
      if (data.success) {
        users = data.data;
      }
    } catch {}
  }

  async function loadRegistros() {
    loadingRegistros = true;
    let params = new URLSearchParams();
    params.append('action', 'bloqueado');
    if (selectedUser) params.append('user_id', selectedUser);
    if (selectedCategoria) params.append('category', selectedCategoria);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    try {
      const res = await fetch(`${API_URL}/api/navigation_logs?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${auth.token}` }
      });
      const data = await res.json();
      if (data.success) {
        registros = data.data;
      } else {
        registros = [];
      }
    } catch {
      registros = [];
    } finally {
      loadingRegistros = false;
    }
  }

  async function loadTarjetas() {
    let params = new URLSearchParams();
    if (selectedUser) params.append('user_id', selectedUser);
    if (selectedCategoria) params.append('category', selectedCategoria);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    try {
      const res = await fetch(`${API_URL}/api/alerts?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${auth.token}` }
      });
      const data = await res.json();
      if (data.success) {
        tarjetas = categorias.map(cat => {
          const found = data.data.find((a: any) => a.category === cat);
          return { category: cat, count: found ? found.count : 0 };
        });
      } else {
        tarjetas = categorias.map(cat => ({ category: cat, count: 0 }));
      }
    } catch {
      tarjetas = categorias.map(cat => ({ category: cat, count: 0 }));
    }
  }

  function filtrar() {
    loadRegistros();
    loadTarjetas();
  }

  // Función para capitalizar cada palabra (primera mayúscula, resto minúscula) y mapear nombres personalizados
  function mostrarCategoria(cat: string) {
    if (cat === 'apuestas/juegos de azar') return 'Juegos de azar';
    if (cat === 'hackeo/actividades ilegales') return 'Actividades ilegales';
    if (cat === 'violencia/terrorismo') return 'Violencia';
    return cat.replace(/\w\S*/g, (txt) =>
      txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase()
    );
  }

  onMount(async () => {
    if (!auth.token) {
      goto('/login');
      return;
    }
    await loadCategorias();
    await loadUsers();
    await loadRegistros();
    await loadTarjetas();
  });
</script>

<Navbar active="alerts" />

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
  <div class="py-6">
    <h1 class="text-2xl font-semibold text-gray-900">Alertas</h1>

    <!-- Filtro global de usuario, categoría y fecha -->
    <div class="flex flex-wrap gap-4 mb-8 items-end">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Usuario</label>
        <select class="border rounded px-2 py-1 min-w-[180px]" bind:value={selectedUser} on:change={filtrar}>
          <option value="">Todos</option>
          {#each users as user}
            <option value={user.id}>{user.email}</option>
          {/each}
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Categoría</label>
        <select class="border rounded px-2 py-1 min-w-[180px]" bind:value={selectedCategoria} on:change={filtrar}>
          <option value="">Todas</option>
          {#each categorias as cat}
            <option value={cat}>{cat}</option>
          {/each}
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Desde</label>
        <input class="border rounded px-2 py-1" type="date" bind:value={dateFrom} on:change={filtrar} />
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
        <input class="border rounded px-2 py-1" type="date" bind:value={dateTo} on:change={filtrar} />
      </div>
    </div>

    <!-- Tarjetas de categorías SIEMPRE visibles (ahora con datos reales) -->
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 my-6">
      {#each tarjetas as tarjeta}
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 flex flex-col items-center">
          <span class="text-lg font-bold text-blue-700">{mostrarCategoria(tarjeta.category)}</span>
          <span class="text-2xl font-extrabold text-blue-900">{tarjeta.count}</span>
        </div>
      {/each}
    </div>

    <!-- Tabla de registros (solo bloqueados) -->
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200 mt-4">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Usuario</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Dominio</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Categoría</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Motivo</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha/Hora</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          {#if loadingRegistros}
            <tr><td colspan="6" class="text-center text-gray-400 py-6">Cargando registros...</td></tr>
          {:else if registros.length === 0}
            <tr><td colspan="6" class="text-center text-gray-400 py-6">No hay bloqueos para mostrar.</td></tr>
          {:else}
            {#each registros as reg}
              <tr class="hover:bg-gray-50">
                <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{users.find(u => u.id === reg.user_id)?.email || reg.user_id}</td>
                <td class="px-4 py-4 whitespace-nowrap text-sm">{reg.domain}</td>
                <td class="px-4 py-4 whitespace-nowrap text-sm">{reg.policy_info?.category || '-'}</td>
                <td class="px-4 py-4 whitespace-nowrap text-sm">
                  <span class="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">Bloqueado</span>
                </td>
                <td class="px-4 py-4 whitespace-nowrap text-sm">{reg.policy_info?.block_reason || '-'}</td>
                <td class="px-4 py-4 whitespace-nowrap text-sm">{new Date(reg.timestamp).toLocaleString()}</td>
              </tr>
            {/each}
          {/if}
        </tbody>
      </table>
    </div>
  </div>
</div> 