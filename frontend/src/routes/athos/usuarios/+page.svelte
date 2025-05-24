<script lang="ts">
  import { onMount } from 'svelte';
  import { API_URL } from '$lib/config';

  type Usuario = {
    id?: string;
    email: string;
    role: string;
    tenant_id?: string;
    password?: string;
  };

  type Cliente = {
    id?: string;
    name: string;
    admin_id?: string;
  };

  let activeTab = 'people';
  let showCreateModal = false;
  let editingUsuario: Usuario | null = null;
  let usuarios: Usuario[] = [];
  let clientes: Cliente[] = [];
  let newUsuario: Usuario = {
    email: '',
    role: 'user',
    password: ''
  };
  let error = '';
  let loading = false;
  let filtroEmail = '';
  let filtroRol = '';
  let filtroCliente = '';

  type FiltrosUsuarios = { email?: string; role?: string; tenant_id?: string };

  async function fetchUsuarios(filtros: FiltrosUsuarios = {}) {
    loading = true;
    try {
      const token = localStorage.getItem('token');
      // Construir query string con los filtros
      const params = new URLSearchParams();
      if (filtros.email) params.append('email', filtros.email);
      if (filtros.role) params.append('role', filtros.role);
      if (filtros.tenant_id) params.append('tenant_id', filtros.tenant_id);
      const url = `${API_URL}/api/athos/usuarios${params.toString() ? '?' + params.toString() : ''}`;
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) usuarios = data.data;
      else error = data.error || 'Error al cargar usuarios';
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  async function fetchClientes() {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/athos/clientes`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) clientes = data.data;
    } catch (e) {}
  }

  let isMounted = false;

  onMount(async () => {
    await fetchClientes();
    // Initial data load
    await fetchUsuarios({ // Added await here for consistency, though not strictly necessary if not chaining
      email: filtroEmail,
      role: filtroRol,
      tenant_id: filtroCliente
    });
    isMounted = true; // Set isMounted after initial loads
  });

  // Debounce utility function
  function debounce<T extends (...args: any[]) => void>(func: T, delay: number) {
    let timeoutId: ReturnType<typeof setTimeout>;
    return function(this: ThisParameterType<T>, ...args: Parameters<T>) {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
  }

  // Debounced function for email filter changes
  const debouncedFetchOnEmailChange = debounce(() => {
    // No need to check isMounted here, as on:input implies the component is mounted and interactive.
    fetchUsuarios({
      email: filtroEmail, // filtroEmail is already updated by bind:value
      role: filtroRol,
      tenant_id: filtroCliente
    });
  }, 500); // 500ms delay

  // Handler for email input changes
  function handleEmailInputChange() {
    // Value of filtroEmail is updated via bind:value.
    // This handler just triggers the debounced fetch.
    debouncedFetchOnEmailChange();
  }

  // Reactive statements for Role and Client filter changes (immediate fetch after mount)
  // These will trigger if filtroRol or filtroCliente change respectively, after isMounted is true.
  $: if (isMounted && filtroRol !== undefined) {
    // console.log('Rol changed:', filtroRol); // Optional: for debugging
    fetchUsuarios({ email: filtroEmail, role: filtroRol, tenant_id: filtroCliente });
  }

  $: if (isMounted && filtroCliente !== undefined) {
    // console.log('Cliente changed:', filtroCliente); // Optional: for debugging
    fetchUsuarios({ email: filtroEmail, role: filtroRol, tenant_id: filtroCliente });
  }

  function openCreateModal() {
    editingUsuario = null;
    newUsuario = { email: '', role: 'user', password: '' };
    error = '';
    showCreateModal = true;
  }

  function openEditModal(usuario: Usuario) {
    editingUsuario = usuario;
    newUsuario = { ...usuario, password: '' };
    error = '';
    showCreateModal = true;
  }

  function resetModal() {
    showCreateModal = false;
    editingUsuario = null;
    newUsuario = { email: '', role: 'user', password: '' };
    error = '';
  }

  async function saveUsuario() {
    error = '';
    const token = localStorage.getItem('token');
    try {
      let res, data;
      if (editingUsuario) {
        res = await fetch(`${API_URL}/api/athos/usuarios/${editingUsuario.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(newUsuario)
        });
      } else {
        res = await fetch(`${API_URL}/api/athos/usuarios`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(newUsuario)
        });
      }
      data = await res.json();
      if (data.success) {
        await fetchUsuarios();
        resetModal();
      } else {
        error = data.error || 'Error al guardar usuario';
      }
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  async function deleteUsuario(usuario: Usuario) {
    if (!confirm('¿Seguro que deseas eliminar este usuario?')) return;
    const token = localStorage.getItem('token');
    try {
      const res = await fetch(`${API_URL}/api/athos/usuarios/${usuario.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) await fetchUsuarios();
      else error = data.error || 'Error al eliminar usuario';
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  function getClienteName(tenantId: string | undefined) {
    if (!tenantId) return '-';
    const cliente = clientes.find(c => c.id === tenantId);
    return cliente ? cliente.name : '-';
  }
</script>

<div class="min-h-screen bg-gray-100">
  <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
    <div class="px-4 sm:px-0">
      <h1 class="text-2xl font-semibold text-gray-900">Usuarios Protegidos</h1>

      <!-- Tabs -->
      <div class="border-b border-gray-200 mt-4">
        <nav class="-mb-px flex space-x-8">
          <button
            class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'people' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
            on:click={() => activeTab = 'people'}
          >
            Personas
          </button>
          <button
            class="py-4 px-1 border-b-2 font-medium text-sm {activeTab === 'groups' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
            on:click={() => activeTab = 'groups'}
          >
            Grupos
          </button>
        </nav>
      </div>

      <!-- Contenido principal -->
      <div class="mt-6">
        <div class="bg-white shadow overflow-hidden sm:rounded-lg">
          <div class="p-6 border-b border-gray-200">
            <h2 class="text-lg font-semibold text-gray-900 mb-2">
              {#if activeTab === 'people'}
                Gestión de Usuarios
              {:else}
                Gestión de Grupos
              {/if}
            </h2>
            <p class="text-gray-600">
              {#if activeTab === 'people'}
                Administra los usuarios que tienen acceso al sistema y sus permisos.
              {:else}
                Organiza los usuarios en grupos para facilitar la gestión de permisos.
              {/if}
            </p>
          </div>

          {#if activeTab === 'people'}
            <div class="px-4 py-5 sm:p-6">
              <div class="flex justify-between items-center mb-4">
                <div class="flex flex-wrap gap-4 items-end">
                  <div>
                    <label class="block text-xs font-medium text-gray-700">Buscar por email</label>
                    <input type="text" bind:value={filtroEmail} on:input={handleEmailInputChange} placeholder="Email" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-1 px-2 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-gray-700">Rol</label>
                    <select bind:value={filtroRol} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-1 px-2 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                      <option value="">Todos</option>
                      <option value="user">user</option>
                      <option value="admin">admin</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-gray-700">Cliente</label>
                    <select bind:value={filtroCliente} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-1 px-2 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                      <option value="">Todos</option>
                      {#each clientes as cliente}
                        <option value={cliente.id}>{cliente.name}</option>
                      {/each}
                    </select>
                  </div>
                </div>
                <button
                  on:click={openCreateModal}
                  class="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                >
                  Nuevo Usuario
                </button>
              </div>

              {#if loading}
                <div class="text-center py-8">
                  <p class="text-gray-500">Cargando usuarios...</p>
                </div>
              {:else if error}
                <div class="text-center py-8 text-red-500">
                  <p>{error}</p>
                </div>
              {:else}
                <div class="overflow-x-auto">
                  <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                      <tr>
                        <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">Email</th>
                        <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Rol</th>
                        <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Cliente</th>
                        <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Acciones</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200 bg-white">
                      {#each usuarios as usuario}
                        <tr>
                          <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">
                            {usuario.email}
                          </td>
                          <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                            {usuario.role}
                          </td>
                          <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                            {getClienteName(usuario.tenant_id)}
                          </td>
                          <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                            <button
                              on:click={() => openEditModal(usuario)}
                              class="text-indigo-600 hover:text-indigo-900 mr-4"
                            >
                              Editar
                            </button>
                            <button
                              on:click={() => deleteUsuario(usuario)}
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
              {/if}
            </div>
          {:else}
            <div class="p-6 text-center text-gray-500">
              <p>Esta funcionalidad estará disponible próximamente.</p>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </main>
</div>

{#if showCreateModal}
  <!-- Overlay -->
  <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity z-40" on:click={resetModal}></div>
  <!-- Modal -->
  <div class="fixed z-50 inset-0 flex items-center justify-center">
    <div class="bg-white rounded-lg shadow-xl max-w-lg w-full p-6 relative" on:click|stopPropagation>
      <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">{editingUsuario ? 'Editar Usuario' : 'Nuevo Usuario'}</h3>
      {#if error}
        <div class="text-red-500 text-center mb-2">{error}</div>
      {/if}
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700">Email</label>
          <input type="email" bind:value={newUsuario.email} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Contraseña</label>
          <input type="password" bind:value={newUsuario.password} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Rol</label>
          <select bind:value={newUsuario.role} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Cliente</label>
          <select bind:value={newUsuario.tenant_id} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
            <option value="">Seleccionar cliente</option>
            {#each clientes as cliente}
              <option value={cliente.id}>{cliente.name}</option>
            {/each}
          </select>
        </div>
      </div>
      <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse mt-6">
        <button type="button" on:click={saveUsuario} class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm">{editingUsuario ? 'Guardar' : 'Crear'}</button>
        <button type="button" on:click={resetModal} class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">Cancelar</button>
      </div>
    </div>
  </div>
{/if} 