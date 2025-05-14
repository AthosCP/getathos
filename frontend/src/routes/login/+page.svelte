<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { auth } from '$lib/auth';
  import { API_URL } from '$lib/config';

  let email = '';
  let password = '';
  let error = '';
  let loading = false;

  async function handleSubmit() {
    error = '';
    loading = true;
    
    try {
      const res = await fetch(`${API_URL}/api/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email,
          password
        })
      });
      
      const data = await res.json();
      
      if (data.success) {
        auth.login({
          email: data.user,
          user_id: data.user_id,
          role: data.role
        }, data.access_token);
        
        if (data.role === 'admin') {
          goto('/admin/dashboard');
        } else if (data.role === 'client') {
          goto('/dashboard');
        } else if (data.role === 'athos_owner') {
          goto('/athos/dashboard');
        } else {
          goto('/login');
        }
      } else {
        error = data.error || 'Error al iniciar sesión';
      }
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    auth.init();
    if (auth.user) {
      if (auth.user.role === 'admin') goto('/admin/dashboard');
      else if (auth.user.role === 'client') goto('/dashboard');
      else if (auth.user.role === 'athos_owner') goto('/athos/dashboard');
    }
  });
</script>

<div class="min-h-screen flex items-center justify-center bg-black py-12 px-4 sm:px-6 lg:px-8">
  <div class="max-w-md w-full space-y-8">
    <div class="text-center">
      <img class="mx-auto h-40 w-auto" src="/images/logo.png" alt="Athos" />
      <h2 class="mt-3 text-3xl font-extrabold text-white">
        Iniciar sesión
      </h2>
      <h3 class="text-2xl font-bold text-[#00a1ff]">
        Athos Cybersecurity Platform
      </h3>
    </div>
    <form class="mt-8 space-y-6" on:submit|preventDefault={handleSubmit}>
      <div class="rounded-md shadow-sm -space-y-px">
        <div>
          <label for="email" class="sr-only">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            required
            bind:value={email}
            class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-[#00a1ff] focus:border-[#00a1ff] focus:z-10 sm:text-sm"
            placeholder="Email"
          />
        </div>
        <div>
          <label for="password" class="sr-only">Contraseña</label>
          <input
            id="password"
            name="password"
            type="password"
            required
            bind:value={password}
            class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-[#00a1ff] focus:border-[#00a1ff] focus:z-10 sm:text-sm"
            placeholder="Contraseña"
          />
        </div>
      </div>

      {#if error}
        <div class="text-red-500 text-sm text-center">{error}</div>
      {/if}

      <div>
        <button
          type="submit"
          class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-[#00a1ff] hover:bg-[#0081cc] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#00a1ff]"
        >
          Iniciar Sesión
        </button>
      </div>
    </form>
  </div>
</div> 