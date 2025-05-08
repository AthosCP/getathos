<script lang="ts">
  import { onMount } from 'svelte';
  import { createClient } from '@supabase/supabase-js';

  // Usar solo variables PUBLIC_ para SvelteKit moderno
  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY
  );

  const API_URL = "http://127.0.0.1:5000";

  let usuarios = [];
  let loading = true;
  let error = '';
  let session = null;
  let nuevoEmail = '';
  let nuevoRol = 'user';
  let creando = false;
  let mensaje = '';

  onMount(async () => {
    const { data } = await supabase.auth.getSession();
    session = data.session;
    if (!session) {
      error = 'No autenticado';
      loading = false;
      return;
    }

    await cargarUsuarios();
  });

  async function cargarUsuarios() {
    loading = true;
    error = '';
    try {
      const res = await fetch(`${API_URL}/api/users`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`
        }
      });
      const json = await res.json();
      if (json.success) {
        usuarios = json.data;
      } else {
        error = json.error || 'Error al obtener usuarios';
      }
    } catch (e) {
      error = 'Error de red';
    }
    loading = false;
  }

  async function crearUsuario() {
    creando = true;
    mensaje = '';
    try {
      const res = await fetch(`${API_URL}/api/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          email: nuevoEmail,
          tenant_id: usuarios[0]?.tenant_id, // O el tenant_id del admin
          role: nuevoRol
        })
      });
      const json = await res.json();
      if (json.success) {
        mensaje = 'Usuario creado correctamente';
        usuarios = [...usuarios, json.data[0]];
        nuevoEmail = '';
        nuevoRol = 'user';
      } else {
        mensaje = json.error || 'Error al crear usuario';
      }
    } catch (e) {
      mensaje = 'Error de red';
    }
    creando = false;
  }
</script>

<main class="container mx-auto px-4 py-8">
  <h1 class="text-2xl font-bold mb-4">Usuarios del Tenant</h1>
  <div class="mb-6">
    <h2 class="font-semibold mb-2">Crear nuevo usuario</h2>
    <input type="email" placeholder="Email" bind:value={nuevoEmail} class="border px-2 py-1 mr-2" />
    <select bind:value={nuevoRol} class="border px-2 py-1 mr-2">
      <option value="user">Usuario</option>
      <option value="admin">Admin</option>
    </select>
    <button on:click={crearUsuario} disabled={creando} class="bg-blue-500 text-white px-4 py-1 rounded">
      {creando ? 'Creando...' : 'Crear'}
    </button>
    {#if mensaje}
      <p class="mt-2 text-sm">{mensaje}</p>
    {/if}
  </div>
  {#if loading}
    <p>Cargando...</p>
  {:else if error}
    <p class="text-red-500">{error}</p>
  {:else}
    <table class="min-w-full bg-white">
      <thead>
        <tr>
          <th class="py-2">Email</th>
          <th class="py-2">Rol</th>
        </tr>
      </thead>
      <tbody>
        {#each usuarios as usuario}
          <tr>
            <td class="py-2">{usuario.email}</td>
            <td class="py-2">{usuario.role}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</main> 