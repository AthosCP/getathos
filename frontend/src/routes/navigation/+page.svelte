<script lang="ts">
  import Navbar from '$lib/Navbar.svelte';
  import { onMount } from 'svelte';
  import { API_URL } from '$lib/config';
  type User = { id: string; email: string };
  type Log = {
    id: string;
    user_id: string;
    tenant_id: string;
    domain: string;
    url: string;
    timestamp: string;
    action: string;
  };
  let users: User[] = [];
  let userId = '';
  let domain = '';
  let url = '';
  let dateFrom = '';
  let dateTo = '';
  let action = 'all';
  let logs: Log[] = [];
  let loading = false;
  let error = '';
  let page = 1;
  let pageSize = 10;
  let total = 0;
  let domainSuggestions: string[] = [];
  let urlSuggestions: string[] = [];
  let showDomainSuggestions = false;
  let showUrlSuggestions = false;
  let blocking = false;
  let blockError = '';
  let blockSuccess = '';

  async function loadUsers() {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/users`, {
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      const data = await res.json();
      if (data.success) {
        users = data.data.map((u: any) => ({ id: u.id, email: u.email }));
      }
    } catch {}
  }

  async function loadLogs() {
    loading = true;
    error = '';
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);
      if (domain) params.append('domain', domain);
      if (url) params.append('url', url);
      if (dateFrom) params.append('date_from', dateFrom);
      if (dateTo) params.append('date_to', dateTo);
      if (action && action !== 'all') params.append('action', action);
      params.append('page', String(page));
      params.append('page_size', String(pageSize));
      const res = await fetch(`${API_URL}/api/navigation_logs?${params.toString()}`, {
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      const data = await res.json();
      if (data.success) {
        logs = data.data;
        total = data.total;
      } else {
        error = data.error || 'Error al cargar historial';
      }
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  function filtrar() {
    page = 1;
    loadLogs();
  }

  function nextPage() {
    if (page * pageSize < total) {
      page += 1;
      loadLogs();
    }
  }

  function prevPage() {
    if (page > 1) {
      page -= 1;
      loadLogs();
    }
  }

  async function fetchDomainSuggestions(q: string) {
    if (!q) { domainSuggestions = []; return; }
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_URL}/api/navigation_logs?autocomplete=domain&q=${encodeURIComponent(q)}`, {
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    const data = await res.json();
    if (data.success) {
      domainSuggestions = data.suggestions;
    }
  }

  async function fetchUrlSuggestions(q: string) {
    if (!q) { urlSuggestions = []; return; }
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_URL}/api/navigation_logs?autocomplete=url&q=${encodeURIComponent(q)}`, {
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    const data = await res.json();
    if (data.success) {
      urlSuggestions = data.suggestions;
    }
  }

  async function blockDomain(domain: string) {
    if (!confirm(`¿Estás seguro de que deseas bloquear el dominio ${domain}?`)) {
      return;
    }
    
    blocking = true;
    blockError = '';
    blockSuccess = '';
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        blockError = 'No hay sesión activa';
        return;
      }

      const res = await fetch(`${API_URL}/api/navigation_logs/block`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ domain })
      });
      
      const data = await res.json();
      if (data.success) {
        blockSuccess = data.message;
        // Recargar los logs para reflejar el cambio
        await loadLogs();
      } else {
        blockError = data.error || 'Error al bloquear el dominio';
      }
    } catch (e: any) {
      blockError = e.message || 'Error al bloquear el dominio';
    } finally {
      blocking = false;
      // Limpiar mensajes después de 3 segundos
      setTimeout(() => {
        blockError = '';
        blockSuccess = '';
      }, 3000);
    }
  }

  onMount(() => {
    loadUsers();
    loadLogs();
  });
</script>

<Navbar active="navigation" />

<div class="max-w-6xl mx-auto mt-8 p-6 bg-white rounded shadow">
  <h1 class="text-2xl font-bold mb-4">Historial de Navegación</h1>
  <p class="text-gray-600 mb-4">
    Aquí puedes ver el registro completo de navegación de los usuarios con la extensión activa. Filtra, busca y bloquea sitios directamente desde este panel.
  </p>

  <!-- Filtros -->
  <div class="flex flex-col md:flex-row md:flex-wrap md:items-end gap-4 mb-6">
    <div class="flex-1 min-w-[150px]">
      <label class="block text-xs font-medium text-gray-700 mb-1">Usuario</label>
      <select bind:value={userId} class="border rounded px-3 py-2 w-full">
        <option value="">Todos</option>
        {#each users as user}
          <option value={user.id}>{user.email}</option>
        {/each}
      </select>
    </div>
    <div class="flex-1 min-w-[120px] relative">
      <label class="block text-xs font-medium text-gray-700 mb-1">Dominio</label>
      <input type="text" bind:value={domain} placeholder="ejemplo.com" class="border rounded px-3 py-2 w-full" 
        on:input={(e) => { fetchDomainSuggestions((e.target as HTMLInputElement).value); showDomainSuggestions = true; }}
        on:focus={() => { if(domain) fetchDomainSuggestions(domain); showDomainSuggestions = true; }}
        on:blur={() => setTimeout(() => showDomainSuggestions = false, 100)}
      />
      {#if showDomainSuggestions && domainSuggestions.length > 0}
        <ul class="absolute z-10 bg-white border rounded w-full mt-1 shadow">
          {#each domainSuggestions as suggestion}
            <li class="px-3 py-2 hover:bg-indigo-100 cursor-pointer" on:mousedown={() => { domain = suggestion; showDomainSuggestions = false; filtrar(); }}>{suggestion}</li>
          {/each}
        </ul>
      {/if}
    </div>
    <div class="flex-1 min-w-[180px] relative">
      <label class="block text-xs font-medium text-gray-700 mb-1">URL</label>
      <input type="text" bind:value={url} placeholder="/ruta" class="border rounded px-3 py-2 w-full"
        on:input={(e) => { fetchUrlSuggestions((e.target as HTMLInputElement).value); showUrlSuggestions = true; }}
        on:focus={() => { if(url) fetchUrlSuggestions(url); showUrlSuggestions = true; }}
        on:blur={() => setTimeout(() => showUrlSuggestions = false, 100)}
      />
      {#if showUrlSuggestions && urlSuggestions.length > 0}
        <ul class="absolute z-10 bg-white border rounded w-full mt-1 shadow">
          {#each urlSuggestions as suggestion}
            <li class="px-3 py-2 hover:bg-indigo-100 cursor-pointer" on:mousedown={() => { url = suggestion; showUrlSuggestions = false; filtrar(); }}>{suggestion}</li>
          {/each}
        </ul>
      {/if}
    </div>
    <div class="flex-1 min-w-[120px]">
      <label class="block text-xs font-medium text-gray-700 mb-1">Desde</label>
      <input type="date" bind:value={dateFrom} class="border rounded px-3 py-2 w-full" />
    </div>
    <div class="flex-1 min-w-[120px]">
      <label class="block text-xs font-medium text-gray-700 mb-1">Hasta</label>
      <input type="date" bind:value={dateTo} class="border rounded px-3 py-2 w-full" />
    </div>
    <div class="flex-1 min-w-[120px]">
      <label class="block text-xs font-medium text-gray-700 mb-1">Acción</label>
      <select bind:value={action} class="border rounded px-3 py-2 w-full">
        <option value="all">Todas</option>
        <option value="visitado">Visitado</option>
        <option value="bloqueado">Bloqueado</option>
        <option value="permitido">Permitido</option>
      </select>
    </div>
    <div class="flex flex-row gap-2 md:ml-auto mt-2 md:mt-0">
      <button class="px-4 py-2 rounded bg-indigo-600 text-white font-semibold w-full md:w-auto" on:click={filtrar}>Filtrar</button>
      <button class="px-4 py-2 rounded bg-gray-200 text-gray-700 font-semibold w-full md:w-auto">Exportar</button>
    </div>
  </div>

  {#if loading}
    <div class="text-center text-gray-500">Cargando historial...</div>
  {:else if error}
    <div class="text-center text-red-500">{error}</div>
  {:else}
    <div class="flex justify-between items-center mb-2">
      <span class="text-sm text-gray-500">Mostrando {logs.length > 0 ? ((page-1)*pageSize+1) : 0}–{(page-1)*pageSize+logs.length} de {total} registros</span>
      <span class="text-sm text-gray-500">Página {page} de {Math.ceil(total/pageSize) || 1}</span>
    </div>
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200 mt-4">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Usuario</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Dominio</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden md:table-cell">URL</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha/Hora</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Acción</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Bloquear</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          {#each logs as log}
            <tr class="hover:bg-gray-50">
              <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{users.find(u => u.id === log.user_id)?.email || log.user_id}</td>
              <td class="px-4 py-4 whitespace-nowrap text-sm">{log.domain}</td>
              <td class="px-4 py-4 text-sm hidden md:table-cell">
                <div class="max-w-xs truncate" title={log.url}>
                  {log.url}
                </div>
              </td>
              <td class="px-4 py-4 whitespace-nowrap text-sm">{new Date(log.timestamp).toLocaleString()}</td>
              <td class="px-4 py-4 whitespace-nowrap text-sm">
                {#if log.action === 'visitado'}
                  <span class="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">Visitado</span>
                {:else if log.action === 'bloqueado'}
                  <span class="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">Bloqueado</span>
                {:else}
                  <span class="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">Permitido</span>
                {/if}
              </td>
              <td class="px-4 py-4 whitespace-nowrap text-sm">
                {#if log.action !== 'bloqueado'}
                  <button 
                    class="px-2 py-1 text-xs font-semibold rounded bg-red-100 text-red-800 hover:bg-red-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    on:click={() => blockDomain(log.domain)}
                    disabled={blocking}
                  >
                    {blocking ? 'Bloqueando...' : 'Bloquear'}
                  </button>
                {:else}
                  <span class="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">Ya bloqueado</span>
                {/if}
              </td>
            </tr>
          {/each}
          {#if logs.length === 0}
            <tr>
              <td colspan="6" class="text-center text-gray-400 py-6">No hay registros para mostrar.</td>
            </tr>
          {/if}
        </tbody>
      </table>
    </div>
    <!-- Paginación -->
    <div class="flex justify-end mt-4 gap-2">
      <button class="px-3 py-1 rounded bg-gray-200 text-gray-700 font-semibold" on:click={prevPage} disabled={page === 1}>Anterior</button>
      <span class="px-3 py-1">Página {page} de {Math.ceil(total/pageSize) || 1}</span>
      <button class="px-3 py-1 rounded bg-gray-200 text-gray-700 font-semibold" on:click={nextPage} disabled={page * pageSize >= total}>Siguiente</button>
    </div>
  {/if}

  {#if blockError}
    <div class="fixed bottom-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
      {blockError}
    </div>
  {/if}
  
  {#if blockSuccess}
    <div class="fixed bottom-4 right-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
      {blockSuccess}
    </div>
  {/if}
</div> 