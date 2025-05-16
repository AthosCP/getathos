<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import AdminNavbar from '$lib/AdminNavbar.svelte';
  import { API_URL } from '$lib/config';
  import { supabase } from '$lib/supabaseClient';

  type Client = {
    id: string;
    name: string;
    description: string;
    users_count: number;
    created_at: string;
    status: string;
    max_users: number;
    primary_color: string;
    secondary_color: string;
    accent_color: string;
    logo_url: string;
    owner_id: string;
    commission?: number;
    license_price?: number;
  };

  let clients: Client[] = [];
  let loading = true;
  let error = '';
  let showCreateModal = false;
  let showEditModal = false;
  let selectedClient: Client | null = null;
  let newClient = {
    name: '',
    description: '',
    max_users: 10,
    primary_color: '#000000',
    secondary_color: '#ffffff',
    accent_color: '#ff0000',
    logo_url: '',
    owner_id: ''
  };
  let logoFile: File | null = null;
  let logoUploading = false;
  let logoUploadError = '';
  let showCommissionModal = false;
  let commissionClient: Client | null = null;
  let tempCommission = 0;
  let tempLicensePrice = 0;

  async function loadClients() {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        goto('/login');
        return;
      }

      const response = await fetch(`${API_URL}/api/admin/clients`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      if (data.success) {
        clients = data.data;
      } else {
        error = data.error || 'Error al cargar clientes';
      }
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  async function createClient() {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/admin/clients`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newClient)
      });

      const data = await response.json();
      if (data.success) {
        clients = [...clients, data.data];
        showCreateModal = false;
        newClient = {
          name: '',
          description: '',
          max_users: 10,
          primary_color: '#000000',
          secondary_color: '#ffffff',
          accent_color: '#ff0000',
          logo_url: '',
          owner_id: ''
        };
      } else {
        error = data.error || 'Error al crear cliente';
      }
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  async function updateClient() {
    if (!selectedClient) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/admin/clients/${selectedClient.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(selectedClient)
      });

      const data = await response.json();
      if (data.success) {
        clients = clients.map(c => c.id === selectedClient.id ? data.data : c);
        showEditModal = false;
      } else {
        error = data.error || 'Error al actualizar cliente';
      }
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  async function deleteClient(id: string) {
    if (!confirm('¿Estás seguro de que deseas eliminar este cliente?')) return;

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/admin/clients/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      if (data.success) {
        clients = clients.filter(c => c.id !== id);
      } else {
        error = data.error || 'Error al eliminar cliente';
      }
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  async function handleLogoUpload(file: File) {
    logoUploading = true;
    logoUploadError = '';
    try {
      if (!file) return;
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (ext !== 'png' && ext !== 'svg') {
        logoUploadError = 'Solo se permiten archivos PNG o SVG';
        logoUploading = false;
        return;
      }
      const fileName = `${crypto.randomUUID()}.${ext}`;
      const { data, error } = await supabase.storage.from('logos').upload(fileName, file, {
        cacheControl: '3600',
        upsert: false
      });
      if (error) {
        logoUploadError = 'Error al subir el logo';
        logoUploading = false;
        return;
      }
      // Obtener URL pública
      const { data: publicUrlData } = supabase.storage.from('logos').getPublicUrl(fileName);
      if (publicUrlData?.publicUrl) {
        newClient.logo_url = publicUrlData.publicUrl;
      }
    } catch (e) {
      logoUploadError = 'Error inesperado al subir el logo';
    } finally {
      logoUploading = false;
    }
  }

  async function handleLogoEditUpload(file: File) {
    logoUploading = true;
    logoUploadError = '';
    try {
      if (!file || !selectedClient) return;
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (ext !== 'png' && ext !== 'svg') {
        logoUploadError = 'Solo se permiten archivos PNG o SVG';
        logoUploading = false;
        return;
      }
      const fileName = `${crypto.randomUUID()}.${ext}`;
      const { data, error } = await supabase.storage.from('logos').upload(fileName, file, {
        cacheControl: '3600',
        upsert: false
      });
      if (error) {
        logoUploadError = 'Error al subir el logo';
        logoUploading = false;
        return;
      }
      // Obtener URL pública
      const { data: publicUrlData } = supabase.storage.from('logos').getPublicUrl(fileName);
      if (publicUrlData?.publicUrl) {
        selectedClient.logo_url = publicUrlData.publicUrl;
      }
    } catch (e) {
      logoUploadError = 'Error inesperado al subir el logo';
    } finally {
      logoUploading = false;
    }
  }

  function openCommissionModal(client: Client) {
    commissionClient = client;
    tempCommission = client.commission ?? 0;
    tempLicensePrice = client.license_price ?? 0;
    showCommissionModal = true;
  }

  function saveCommission() {
    if (commissionClient) {
      commissionClient.commission = tempCommission;
      commissionClient.license_price = tempLicensePrice;
      // Forzar refresco de la tabla
      clients = clients.map(c => c.id === commissionClient?.id ? { ...c } : c);
      showCommissionModal = false;
    }
  }

  onMount(() => {
    const userRaw = localStorage.getItem('user');
    if (!userRaw) {
      goto('/login');
      return;
    }
    const user = JSON.parse(userRaw);
    if (user.role !== 'admin') {
      goto('/login');
      return;
    }
    loadClients();
  });
</script>

<AdminNavbar active="clients" />

<div class="min-h-screen bg-gray-100">
  <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
    <div class="px-4 sm:px-0">
      <div class="flex justify-between items-center">
        <h1 class="text-2xl font-bold text-gray-900">Gestión de Clientes</h1>
        <button
          on:click={() => showCreateModal = true}
          class="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
        >
          Nuevo Cliente
        </button>
      </div>
    </div>

    {#if loading}
      <div class="text-center mt-8">Cargando...</div>
    {:else if error}
      <div class="text-red-500 text-center mt-8">{error}</div>
    {:else}
      <div class="mt-8 flex flex-col">
        <div class="-my-2 -mx-4 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div class="inline-block min-w-full py-2 align-middle md:px-6 lg:px-8">
            <div class="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
              <table class="min-w-full divide-y divide-gray-300">
                <thead class="bg-gray-50">
                  <tr>
                    <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">Nombre</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Descripción</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Usuarios</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Comisión (%)</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Precio Licencia (USD, IVA incl.)</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Estado</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Acciones</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200 bg-white">
                  {#each clients as client}
                    <tr>
                      <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">
                        {client.name}
                      </td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{client.description}</td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                        {client.users_count} / {client.max_users}
                      </td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                        {client.commission ?? '-'}%
                      </td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                        {client.license_price ? `$${(client.license_price * 1.19).toFixed(2)}` : '-'}
                      </td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full {client.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}">
                          {client.status === 'active' ? 'Activo' : 'Pendiente'}
                        </span>
                      </td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                        <button
                          on:click={() => { selectedClient = client; showEditModal = true; }}
                          class="text-indigo-600 hover:text-indigo-900 mr-4"
                        >
                          Editar
                        </button>
                        <button
                          on:click={() => openCommissionModal(client)}
                          class="text-green-600 hover:text-green-900 mr-4"
                        >
                          Comisión
                        </button>
                        <button
                          on:click={() => deleteClient(client.id)}
                          class="text-red-600 hover:text-red-900"
                        >
                          Eliminar
                        </button>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    {/if}
  </main>
</div>

{#if showCreateModal}
  <!-- Overlay -->
  <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity z-40" on:click={() => { showCreateModal = false; error = ''; }}></div>
  <!-- Modal -->
  <div class="fixed z-50 inset-0 flex items-center justify-center">
    <div class="bg-white rounded-lg shadow-xl max-w-lg w-full p-6 relative" on:click|stopPropagation>
      <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">Nuevo Cliente</h3>
      {#if error}
        <div class="text-red-500 text-center mb-2">{error}</div>
      {/if}
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700">Nombre</label>
          <input type="text" bind:value={newClient.name} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Descripción</label>
          <textarea bind:value={newClient.description} rows="3" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"></textarea>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Límite de Usuarios</label>
          <input type="number" bind:value={newClient.max_users} min="1" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
        </div>
        <div class="flex space-x-2">
          <div class="flex-1">
            <label class="block text-sm font-medium text-gray-700">Color Primario</label>
            <input type="color" bind:value={newClient.primary_color} class="w-full h-10 p-0 border-none" />
          </div>
          <div class="flex-1">
            <label class="block text-sm font-medium text-gray-700">Color Secundario</label>
            <input type="color" bind:value={newClient.secondary_color} class="w-full h-10 p-0 border-none" />
          </div>
          <div class="flex-1">
            <label class="block text-sm font-medium text-gray-700">Color de Acento</label>
            <input type="color" bind:value={newClient.accent_color} class="w-full h-10 p-0 border-none" />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Logo (PNG o SVG)</label>
          <input type="file" accept=".png,.svg" on:change={(e) => {
            const input = e.target as HTMLInputElement;
            if (input?.files && input.files.length > 0) {
              handleLogoUpload(input.files[0]);
            }
          }} class="mt-1 block w-full" />
          {#if logoUploading}
            <div class="text-blue-500 text-sm mt-1">Subiendo logo...</div>
          {/if}
          {#if logoUploadError}
            <div class="text-red-500 text-sm mt-1">{logoUploadError}</div>
          {/if}
          {#if newClient.logo_url}
            <img src={newClient.logo_url} alt="Logo preview" class="mt-2 h-12" />
          {/if}
        </div>
      </div>
      <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse mt-6">
        <button type="button" on:click={createClient} class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm">Crear</button>
        <button type="button" on:click={() => { showCreateModal = false; error = ''; }} class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">Cancelar</button>
      </div>
    </div>
  </div>
{/if}

{#if showEditModal && selectedClient}
  <!-- Overlay -->
  <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity z-40" on:click={() => { showEditModal = false; error = ''; }}></div>
  <!-- Modal -->
  <div class="fixed z-50 inset-0 flex items-center justify-center">
    {#if selectedClient}
    <div class="bg-white rounded-lg shadow-xl max-w-lg w-full p-6 relative" on:click|stopPropagation>
      <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">Editar Cliente</h3>
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700">Nombre</label>
          <input type="text" bind:value={selectedClient.name} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Descripción</label>
          <textarea bind:value={selectedClient.description} rows="3" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"></textarea>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Límite de Usuarios</label>
          <input type="number" bind:value={selectedClient.max_users} min="1" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
        </div>
        <div class="flex space-x-2">
          <div class="flex-1">
            <label class="block text-sm font-medium text-gray-700">Color Primario</label>
            <input type="color" bind:value={selectedClient.primary_color} class="w-full h-10 p-0 border-none" />
          </div>
          <div class="flex-1">
            <label class="block text-sm font-medium text-gray-700">Color Secundario</label>
            <input type="color" bind:value={selectedClient.secondary_color} class="w-full h-10 p-0 border-none" />
          </div>
          <div class="flex-1">
            <label class="block text-sm font-medium text-gray-700">Color de Acento</label>
            <input type="color" bind:value={selectedClient.accent_color} class="w-full h-10 p-0 border-none" />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Logo (PNG o SVG)</label>
          <input type="file" accept=".png,.svg" on:change={(e) => {
            const input = e.target as HTMLInputElement;
            if (input?.files && input.files.length > 0) {
              handleLogoEditUpload(input.files[0]);
            }
          }} class="mt-1 block w-full" />
          {#if logoUploading}
            <div class="text-blue-500 text-sm mt-1">Subiendo logo...</div>
          {/if}
          {#if logoUploadError}
            <div class="text-red-500 text-sm mt-1">{logoUploadError}</div>
          {/if}
          {#if selectedClient.logo_url}
            <img src={selectedClient.logo_url} alt="Logo preview" class="mt-2 h-12" />
          {/if}
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Estado</label>
          <select bind:value={selectedClient.status} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
            <option value="active">Activo</option>
            <option value="pending">Pendiente</option>
          </select>
        </div>
      </div>
      <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse mt-6">
        <button type="button" on:click={updateClient} class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm">Guardar</button>
        <button type="button" on:click={() => { showEditModal = false; error = ''; }} class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">Cancelar</button>
      </div>
    </div>
    {/if}
  </div>
{/if}

{#if showCommissionModal && commissionClient}
  <!-- Overlay -->
  <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity z-40" on:click={() => { showCommissionModal = false; }}></div>
  <!-- Modal -->
  <div class="fixed z-50 inset-0 flex items-center justify-center">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6 relative" on:click|stopPropagation>
      <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">Editar Comisión y Precio de Licencia</h3>
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700">Comisión (%)</label>
          <input type="number" min="0" max="100" bind:value={tempCommission} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Precio de Licencia (USD, sin IVA)</label>
          <input type="number" min="0" step="0.01" bind:value={tempLicensePrice} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
          <div class="mt-1 text-xs text-gray-500">Con IVA (19%): <span class="font-semibold">${(tempLicensePrice * 1.19).toFixed(2)}</span> USD</div>
        </div>
      </div>
      <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse mt-6">
        <button type="button" on:click={saveCommission} class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm">Guardar</button>
        <button type="button" on:click={() => { showCommissionModal = false; }} class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">Cancelar</button>
      </div>
    </div>
  </div>
{/if} 