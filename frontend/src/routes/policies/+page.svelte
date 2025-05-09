<script lang="ts">
  import Navbar from '$lib/Navbar.svelte';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/auth';
  import { API_URL } from '$lib/config';
  type Policy = { id: string; domain: string; action: string };
  let activeTab = 'access';
  let filter = 'all';
  let search = '';
  let policies: Policy[] = [];
  let loading = false;
  let error = '';

  $: filteredPolicies = policies.filter(p =>
    (filter === 'all' || p.action === filter) &&
    (search === '' || p.domain.toLowerCase().includes(search.toLowerCase()))
  );

  let showModal = false;
  let isEdit = false;
  let modalPolicy: Policy = { id: '', domain: '', action: 'allow' };
  let isFormValid = false;

  $: isFormValid = modalPolicy.domain.trim() !== '';

  async function loadPolicies() {
    loading = true;
    error = '';
    try {
      const token = auth.token;
      if (!token) {
        auth.logout();
        goto('/login');
        return;
      }
      const res = await fetch(`${API_URL}/api/policies`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) {
        policies = data.data;
      } else {
        if (data.error?.includes('invalid JWT')) {
          auth.logout();
          goto('/login');
          return;
        }
        error = data.error || 'Error al cargar políticas';
      }
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    auth.init();
    if (!auth.token) {
      goto('/login');
      return;
    }
    loadPolicies();
  });

  function openCreateModal() {
    isEdit = false;
    modalPolicy = { id: '', domain: '', action: 'allow' };
    showModal = true;
  }

  function openEditModal(policy: Policy) {
    isEdit = true;
    modalPolicy = { ...policy };
    showModal = true;
  }

  async function savePolicy() {
    const token = auth.token;
    if (!token) {
      auth.logout();
      goto('/login');
      return;
    }

    try {
      if (isEdit) {
        // Editar
        const res = await fetch(`${API_URL}/api/policies/${modalPolicy.id}`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ domain: modalPolicy.domain, action: modalPolicy.action })
        });
        const data = await res.json();
        if (data.success) {
          policies = policies.map(p => p.id === modalPolicy.id ? data.data : p);
          showModal = false;
        } else {
          if (data.error?.includes('invalid JWT')) {
            auth.logout();
            goto('/login');
            return;
          }
          error = data.error || 'Error al editar política';
        }
      } else {
        // Crear
        const res = await fetch(`${API_URL}/api/policies`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ domain: modalPolicy.domain, action: modalPolicy.action })
        });
        const data = await res.json();
        if (data.success) {
          policies = [...policies, data.data];
          showModal = false;
        } else {
          if (data.error?.includes('invalid JWT')) {
            auth.logout();
            goto('/login');
            return;
          }
          error = data.error || 'Error al crear política';
        }
      }
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  async function deletePolicy(id: string) {
    const token = auth.token;
    if (!token) {
      auth.logout();
      goto('/login');
      return;
    }

    if (!confirm('¿Seguro que deseas eliminar esta política?')) return;
    try {
      const res = await fetch(`${API_URL}/api/policies/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) {
        policies = policies.filter(p => p.id !== id);
      } else {
        if (data.error?.includes('invalid JWT')) {
          auth.logout();
          goto('/login');
          return;
        }
        error = data.error || 'Error al eliminar política';
      }
    } catch (e) {
      error = 'Error de conexión';
    }
  }
</script>

<Navbar active="policies" />

<div class="max-w-4xl mx-auto mt-8 p-6 bg-white rounded shadow">
  <h1 class="text-2xl font-bold mb-4">Políticas de Navegación</h1>
  <p class="text-gray-600 mb-4">
    Aquí podrás gestionar las políticas de navegación de tu empresa: dominios bloqueados, permitidos y otras reglas.
  </p>
  <div class="text-gray-400 italic">
    (Próximamente: gestión de listas de dominios, horarios, excepciones, etc.)
  </div>

  <!-- Tabs -->
  <div class="flex space-x-4 mb-6">
    <button class="px-4 py-2 rounded-t bg-indigo-600 text-white font-semibold">Acceso</button>
    <button class="px-4 py-2 rounded-t bg-gray-200 text-gray-500 cursor-not-allowed" disabled>Extensión</button>
    <button class="px-4 py-2 rounded-t bg-gray-200 text-gray-500 cursor-not-allowed" disabled>Aislamiento</button>
  </div>

  <!-- Filtros y buscador -->
  <div class="flex items-center mb-4 space-x-2">
    <input type="text" placeholder="Buscar dominio..." bind:value={search} class="border rounded px-3 py-2 w-1/2" />
    <button class="px-4 py-2 rounded bg-indigo-500 text-white font-semibold" on:click={() => filter = 'all'} class:selected={filter === 'all'}>Todos</button>
    <button class="px-4 py-2 rounded bg-green-500 text-white font-semibold" on:click={() => filter = 'allow'} class:selected={filter === 'allow'}>Permitidos</button>
    <button class="px-4 py-2 rounded bg-red-500 text-white font-semibold" on:click={() => filter = 'block'} class:selected={filter === 'block'}>Bloqueados</button>
    <button class="ml-auto px-4 py-2 rounded bg-blue-600 text-white font-semibold" on:click={openCreateModal}>Agregar política</button>
  </div>

  {#if loading}
    <div class="text-center text-gray-500">Cargando políticas...</div>
  {:else if error}
    <div class="text-center text-red-500">{error}</div>
  {:else}
    <!-- Tabla de políticas -->
    <table class="min-w-full divide-y divide-gray-200 mt-4">
      <thead class="bg-gray-50">
        <tr>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Dominio</th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Acciones</th>
        </tr>
      </thead>
      <tbody class="bg-white divide-y divide-gray-200">
        {#each filteredPolicies as policy}
          <tr>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{policy.domain}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm">
              {#if policy.action === 'allow'}
                <span class="text-green-600 font-semibold">Permitido</span>
              {:else}
                <span class="text-red-600 font-semibold">Bloqueado</span>
              {/if}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm">
              <button class="text-indigo-600 hover:text-indigo-900 mr-2" on:click={() => openEditModal(policy)}>Editar</button>
              <button class="text-red-600 hover:text-red-900" on:click={() => deletePolicy(policy.id)}>Eliminar</button>
            </td>
          </tr>
        {/each}
        {#if filteredPolicies.length === 0}
          <tr>
            <td colspan="3" class="text-center text-gray-400 py-6">No hay políticas para mostrar.</td>
          </tr>
        {/if}
      </tbody>
    </table>
  {/if}
</div>

{#if showModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
    <div class="bg-white rounded-lg shadow-lg p-8 w-full max-w-md relative">
      <button class="absolute top-2 right-2 text-gray-400 hover:text-gray-600 text-2xl font-bold focus:outline-none" on:click={() => showModal = false} aria-label="Cerrar">×</button>
      <h2 class="text-xl font-bold mb-4">{isEdit ? 'Editar' : 'Agregar'} Política</h2>
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-1">Dominio</label>
        <input type="text" bind:value={modalPolicy.domain} class="w-full border border-gray-300 rounded-md px-3 py-2" placeholder="https://ejemplo.com" />
      </div>
      <div class="mb-6">
        <label class="block text-sm font-medium text-gray-700 mb-1">Acción</label>
        <select bind:value={modalPolicy.action} class="w-full border border-gray-300 rounded-md px-3 py-2">
          <option value="allow">Permitir</option>
          <option value="block">Bloquear</option>
        </select>
      </div>
      <div class="flex justify-end space-x-2">
        <button class="px-4 py-2 rounded bg-gray-200 text-gray-700 font-semibold" on:click={() => showModal = false}>Cancelar</button>
        <button 
          class="px-4 py-2 rounded bg-indigo-600 text-white font-semibold disabled:opacity-50 disabled:cursor-not-allowed" 
          on:click={savePolicy}
          disabled={!isFormValid}
        >
          {isEdit ? 'Guardar cambios' : 'Agregar'}
        </button>
      </div>
    </div>
  </div>
{/if} 