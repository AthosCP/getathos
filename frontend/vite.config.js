import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	build: {},
	server: {
		host: '0.0.0.0',
		port: process.env.PORT || 4173
	},
	preview: {
		host: '0.0.0.0',
		port: process.env.PORT || 4173,
		allowedHosts: ['athos-frontend.onrender.com']
	}
}); 