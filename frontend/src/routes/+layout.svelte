<script lang="ts">
	import '../app.css';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	
	let { children } = $props();

	onMount(() => {
		// Interceptor para manejar errores 401
		const originalFetch = window.fetch;
		window.fetch = async function(...args) {
			const response = await originalFetch.apply(window, args);
			if (response.status === 401) {
				// Limpiar datos de sesión
				localStorage.removeItem('token');
				localStorage.removeItem('user');
				// Redirigir al login
				goto('/login');
			}
			return response;
		};
	});
</script>

<svelte:head>
	<title>Athos</title>
	<link rel="icon" href="/images/icon.png" />
</svelte:head>

{@render children()}
